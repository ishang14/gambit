"""Training cards: one per (position, wrong move) the user should unlearn.

Cards come from the user's analyzed blunders and from opening leaks that have an engine
move to play instead. Creating them is idempotent: a card that already exists keeps its
review schedule.
"""

from datetime import datetime, timezone
from typing import Any

import chess
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne

from app.config import Settings
from app.openings.service import user_leaks
from app.training.sm2 import Schedule


def move_label(ply: int) -> str:
    """Ply 1 -> "1.", ply 2 -> "1...", ply 45 -> "23."."""
    number = (ply + 1) // 2
    return f"{number}." if ply % 2 == 1 else f"{number}..."


def new_card(
    user_id: ObjectId,
    source: str,
    fen: str,
    fen_key: str,
    correct_move: str,
    correct_move_san: str,
    user_move: str,
    user_move_san: str,
    context: dict[str, Any],
    now: datetime,
) -> UpdateOne:
    color = "white" if fen.split(" ")[1] == "w" else "black"
    schedule = Schedule()
    return UpdateOne(
        {"user_id": user_id, "fen_key": fen_key, "user_move": user_move},
        {
            "$setOnInsert": {
                "source": source,
                "fen": fen,
                "color": color,
                "correct_move": correct_move,
                "correct_move_san": correct_move_san,
                "user_move_san": user_move_san,
                "context": context,
                "ease": schedule.ease,
                "interval": schedule.interval,
                "repetitions": schedule.repetitions,
                "due_at": now,
                "created_at": now,
                "last_reviewed_at": None,
                "reviews": 0,
                "lapses": 0,
            }
        },
        upsert=True,
    )


async def blunder_cards(db: AsyncIOMotorDatabase, user_id: ObjectId, now: datetime) -> list[UpdateOne]:
    positions = await db.positions.find(
        {"user_id": user_id, "is_user_move": True, "classification": "blunder", "best_move": {"$ne": None}}
    ).to_list(None)
    game_ids = list({p["game_id"] for p in positions})
    games = {
        g["_id"]: g
        async for g in db.games.find({"_id": {"$in": game_ids}}, {"opponent": 1, "played_at": 1, "opening": 1})
    }
    operations = []
    for p in positions:
        game = games.get(p["game_id"], {})
        operations.append(
            new_card(
                user_id,
                "blunder",
                p["fen"],
                p["fen_key"],
                p["best_move"],
                p["best_move_san"],
                p["move_played"],
                p["move_san"],
                {
                    "game_id": str(p["game_id"]),
                    "opponent": game.get("opponent"),
                    "played_at": game.get("played_at"),
                    "move_number": move_label(p["ply"]),
                    "win_chance_loss": p["win_chance_loss"],
                },
                now,
            )
        )
    return operations


async def leak_cards(
    db: AsyncIOMotorDatabase, user_id: ObjectId, settings: Settings, now: datetime
) -> list[UpdateOne]:
    operations = []
    for color in ("white", "black"):
        for leak in await user_leaks(db, user_id, color, settings):
            if not leak["best_move_uci"] or leak["best_move_uci"] == leak["move_uci"]:
                continue  # needs an engine move to train towards
            operations.append(
                new_card(
                    user_id,
                    "leak",
                    leak["fen"],
                    leak["fen_key"],
                    leak["best_move_uci"],
                    leak["best_move_san"],
                    leak["move_uci"],
                    leak["move_san"],
                    {
                        "opening_name": leak["opening_name"],
                        "path": [step["san"] for step in leak["path"]],
                        "games": leak["games"],
                        "position_games": leak["position_games"],
                        "score": leak["score"],
                        "example_game_id": leak["example_game_id"],
                    },
                    now,
                )
            )
    return operations


async def sync_cards(db: AsyncIOMotorDatabase, user_id: ObjectId, settings: Settings) -> dict[str, int]:
    """Create cards for any new blunders and leaks. Returns how many were new."""
    now = datetime.now(timezone.utc)
    # Leaks first: a position that is both a leak and a blunder is more useful with the leak's context.
    operations = await leak_cards(db, user_id, settings, now) + await blunder_cards(db, user_id, now)
    created = 0
    if operations:
        result = await db.training_cards.bulk_write(operations, ordered=True)
        created = result.upserted_count
    total = await db.training_cards.count_documents({"user_id": user_id})
    return {"created": created, "total": total}


def legal_san(fen: str, uci: str) -> str | None:
    """SAN for a UCI move in this position, or None if it isn't legal."""
    board = chess.Board(fen)
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return None
    return board.san(move) if move in board.legal_moves else None
