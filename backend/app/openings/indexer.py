"""Index the opening of each game as one `opening_moves` document per ply, keyed by position.

Indexing is lazy: the opening endpoint indexes any games that aren't indexed yet (or were
indexed with a different `opening_plies`). Analysis results are copied onto the documents
so the tree can be built with a single aggregation, with no joins.
"""

import io
from typing import Any

import chess
import chess.pgn
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne

from app.analysis.engine import normalize_fen
from app.openings.book import OpeningBook, load_book

# Insert in batches rather than one round trip per game.
BATCH_GAMES = 200


def analysis_fields(position: dict[str, Any]) -> dict[str, Any]:
    return {
        "analyzed": True,
        "win_chance_loss": position["win_chance_loss"],
        "cp_loss": position["cp_loss"],
        "best_move": position["best_move"],
        "best_move_san": position["best_move_san"],
        "classification": position["classification"],
    }


def opening_moves_for(game: dict[str, Any], plies: int) -> list[dict[str, Any]]:
    parsed = chess.pgn.read_game(io.StringIO(game["pgn"]))
    if parsed is None:
        return []
    board = parsed.board()
    docs = []
    for ply, move in enumerate(parsed.mainline_moves(), start=1):
        if ply > plies:
            break
        mover = "white" if board.turn == chess.WHITE else "black"
        fen_key, san = normalize_fen(board), board.san(move)
        board.push(move)
        docs.append(
            {
                "user_id": game["user_id"],
                "game_id": game["_id"],
                "user_color": game["user_color"],
                "user_result": game["user_result"],
                "ply": ply,
                "fen_key": fen_key,
                "next_fen_key": normalize_fen(board),
                "move_uci": move.uci(),
                "move_san": san,
                "is_user_move": mover == game["user_color"],
                "analyzed": False,
            }
        )
    return docs


async def index_user_games(db: AsyncIOMotorDatabase, user_id: ObjectId, plies: int) -> int:
    """Index this user's unindexed games. Returns how many games were indexed."""
    cursor = db.games.find(
        {
            "user_id": user_id,
            # Not indexed, indexed with another depth, or indexed before openings were named.
            "$or": [{"opening_index_plies": {"$ne": plies}}, {"opening_family": {"$exists": False}}],
        },
        {"pgn": 1, "user_id": 1, "user_color": 1, "user_result": 1, "analysis_status": 1},
    )
    batch: list[dict[str, Any]] = []
    indexed = 0
    async for game in cursor:
        batch.append(game)
        if len(batch) >= BATCH_GAMES:
            indexed += await _index_batch(db, batch, plies)
            batch = []
    if batch:
        indexed += await _index_batch(db, batch, plies)
    return indexed


async def _index_batch(db: AsyncIOMotorDatabase, games: list[dict[str, Any]], plies: int) -> int:
    game_ids = [game["_id"] for game in games]
    analyzed_ids = [game["_id"] for game in games if game.get("analysis_status") == "done"]

    analysis: dict[tuple[ObjectId, int], dict[str, Any]] = {}
    if analyzed_ids:
        async for position in db.positions.find({"game_id": {"$in": analyzed_ids}, "ply": {"$lte": plies}}):
            analysis[(position["game_id"], position["ply"])] = analysis_fields(position)

    book = load_book()
    docs = []
    game_updates = []
    for game in games:
        moves = opening_moves_for(game, plies)
        for doc in moves:
            doc.update(analysis.get((game["_id"], doc["ply"]), {}))
            docs.append(doc)
        name = book_opening(moves, book)
        game_updates.append(
            UpdateOne(
                {"_id": game["_id"]},
                {
                    "$set": {
                        "opening_index_plies": plies,
                        "book_opening": name,
                        "opening_family": name.split(":")[0] if name else None,
                    }
                },
            )
        )

    await db.opening_moves.delete_many({"game_id": {"$in": game_ids}})
    if docs:
        await db.opening_moves.insert_many(docs)
    await db.games.bulk_write(game_updates, ordered=False)
    return len(games)


def book_opening(moves: list[dict[str, Any]], book: OpeningBook) -> str | None:
    """Name of the deepest named book position the game passed through, e.g.
    "Sicilian Defense: Najdorf Variation". Its family is the part before the colon."""
    name = None
    for doc in moves:
        name = book.name(doc["next_fen_key"]) or name
    return name


async def attach_analysis(db: AsyncIOMotorDatabase, game_id: ObjectId, positions: list[dict[str, Any]]) -> None:
    """Copy fresh analysis onto an already-indexed game. A game indexed later picks the
    analysis up from `positions` instead, so nothing is lost if this matches no documents."""
    operations = [
        UpdateOne({"game_id": game_id, "ply": p["ply"]}, {"$set": analysis_fields(p)}) for p in positions
    ]
    if operations:
        await db.opening_moves.bulk_write(operations, ordered=False)
