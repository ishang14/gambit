import re
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne

from app.games.parser import parse_game
from app.models.game import GameDetail, GameSummary, ImportResult


async def store_month(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    username: str,
    year: int,
    month: int,
    raw_games: list[dict[str, Any]],
) -> ImportResult:
    """Store a month of chess.com games. Games already imported are left untouched."""
    now = datetime.now(timezone.utc)
    operations = []
    unsupported = 0
    for raw in raw_games:
        parsed = parse_game(raw, username)
        if parsed is None:
            unsupported += 1
            continue
        source_url = parsed.pop("source_url")
        new_fields = {
            **parsed,
            "chesscom_username": username.lower(),
            "analysis_status": "none",
            "accuracy": None,
            "imported_at": now,
        }
        operations.append(
            UpdateOne(
                {"user_id": user_id, "source_url": source_url},
                {"$setOnInsert": new_fields},
                upsert=True,
            )
        )

    imported = 0
    if operations:
        result = await db.games.bulk_write(operations, ordered=False)
        imported = result.upserted_count
    return ImportResult(
        year=year,
        month=month,
        imported=imported,
        duplicates=len(operations) - imported,
        unsupported=unsupported,
    )


def build_filter(
    user_id: ObjectId,
    result: str | None = None,
    color: str | None = None,
    time_class: str | None = None,
    opening: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {"user_id": user_id}
    if result:
        query["user_result"] = result
    if color:
        query["user_color"] = color
    if time_class:
        query["time_class"] = time_class
    if opening:
        query["opening"] = {"$regex": re.escape(opening), "$options": "i"}
    return query


async def list_games(
    db: AsyncIOMotorDatabase, query: dict[str, Any], limit: int, offset: int
) -> tuple[list[GameSummary], int]:
    total = await db.games.count_documents(query)
    cursor = (
        db.games.find(query, {"pgn": 0})
        .sort([("played_at", -1), ("_id", -1)])
        .skip(offset)
        .limit(limit)
    )
    items = [GameSummary(id=str(doc["_id"]), **doc) async for doc in cursor]
    return items, total


async def get_game(db: AsyncIOMotorDatabase, user_id: ObjectId, game_id: str) -> GameDetail | None:
    if not ObjectId.is_valid(game_id):
        return None
    doc = await db.games.find_one({"_id": ObjectId(game_id), "user_id": user_id})
    if doc is None:
        return None
    return GameDetail(id=str(doc["_id"]), **doc)
