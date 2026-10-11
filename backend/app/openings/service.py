from typing import Any

import chess
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analysis.engine import normalize_fen
from app.config import Settings
from app.openings.book import load_book
from app.openings.indexer import index_user_games
from app.openings.tree import Edge, LeakRules, build_explorer, find_leaks

ROOT = normalize_fen(chess.Board())


def leak_rules(settings: Settings) -> LeakRules:
    return LeakRules(
        min_occurrences=settings.leak_min_occurrences,
        min_move_games=settings.leak_min_move_games,
        max_score=settings.leak_max_score,
        min_eval_loss=settings.leak_min_eval_loss,
    )


def edges_pipeline(user_id: ObjectId, color: str) -> list[dict[str, Any]]:
    return [
        {"$match": {"user_id": user_id, "user_color": color}},
        # 1) One row per game per (position, move), so a repeated position counts once.
        {
            "$group": {
                "_id": {"fen": "$fen_key", "move": "$move_uci", "game": "$game_id"},
                "san": {"$first": "$move_san"},
                "next": {"$first": "$next_fen_key"},
                "is_user_move": {"$first": "$is_user_move"},
                "result": {"$first": "$user_result"},
                "analyzed": {"$max": "$analyzed"},
                "wcl": {"$avg": "$win_chance_loss"},
                "cpl": {"$avg": "$cp_loss"},
                "best_uci": {"$max": "$best_move"},
                "best_san": {"$max": "$best_move_san"},
            }
        },
        # 2) Sum those per (position, move).
        {
            "$group": {
                "_id": {"fen": "$_id.fen", "move": "$_id.move"},
                "san": {"$first": "$san"},
                "next": {"$first": "$next"},
                "is_user_move": {"$first": "$is_user_move"},
                "games": {"$sum": 1},
                "wins": {"$sum": {"$cond": [{"$eq": ["$result", "win"]}, 1, 0]}},
                "draws": {"$sum": {"$cond": [{"$eq": ["$result", "draw"]}, 1, 0]}},
                "losses": {"$sum": {"$cond": [{"$eq": ["$result", "loss"]}, 1, 0]}},
                "analyzed": {"$sum": {"$cond": ["$analyzed", 1, 0]}},
                "wcl_sum": {"$sum": "$wcl"},
                "cpl_sum": {"$sum": "$cpl"},
                "best_uci": {"$max": "$best_uci"},
                "best_san": {"$max": "$best_san"},
                "example_game": {"$max": "$_id.game"},
            }
        },
    ]


async def load_edges(db: AsyncIOMotorDatabase, user_id: ObjectId, color: str) -> list[Edge]:
    edges = []
    async for row in db.opening_moves.aggregate(edges_pipeline(user_id, color)):
        edges.append(
            Edge(
                fen_key=row["_id"]["fen"],
                move_uci=row["_id"]["move"],
                move_san=row["san"],
                next_fen_key=row["next"],
                is_user_move=row["is_user_move"],
                games=row["games"],
                wins=row["wins"],
                draws=row["draws"],
                losses=row["losses"],
                analyzed=row["analyzed"],
                win_chance_loss_sum=row["wcl_sum"] or 0.0,
                cp_loss_sum=row["cpl_sum"] or 0.0,
                best_move_uci=row["best_uci"],
                best_move_san=row["best_san"],
                example_game_id=str(row["example_game"]),
            )
        )
    return edges


async def user_leaks(db: AsyncIOMotorDatabase, user_id: ObjectId, color: str, settings: Settings) -> list[dict[str, Any]]:
    await index_user_games(db, user_id, settings.opening_plies)
    edges = await load_edges(db, user_id, color)
    return find_leaks(edges, ROOT, leak_rules(settings), load_book())


async def opening_explorer(
    db: AsyncIOMotorDatabase, user_id: ObjectId, color: str, min_games: int, settings: Settings
) -> dict[str, Any]:
    await index_user_games(db, user_id, settings.opening_plies)
    edges = await load_edges(db, user_id, color)
    book = load_book()
    leaks = find_leaks(edges, ROOT, leak_rules(settings), book)
    return {
        "color": color,
        "root": ROOT,
        "games": await db.games.count_documents({"user_id": user_id, "user_color": color}),
        "opening_plies": settings.opening_plies,
        "positions": build_explorer(edges, ROOT, color, min_games, book, leaks),
        "leaks": leaks,
    }
