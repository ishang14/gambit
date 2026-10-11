"""Insights: MongoDB aggregation pipelines over a user's games and analyzed moves.

Every pipeline starts from the same game filter (user, optional time control, optional
start date), so all charts on the page describe the same slice of games.
"""

from datetime import date, datetime, time, timezone
from typing import Any

import chess
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne

from app.analysis.phase import game_phase

RESULTS = ("wins", "draws", "losses")
PHASES = ("opening", "middlegame", "endgame")
BUCKET_FORMATS = {"week": "%G-W%V", "month": "%Y-%m"}  # ISO week / calendar month


def game_filter(user_id: ObjectId, time_class: str | None, since: date | None) -> dict[str, Any]:
    query: dict[str, Any] = {"user_id": user_id}
    if time_class:
        query["time_class"] = time_class
    if since:
        query["played_at"] = {"$gte": datetime.combine(since, time.min, tzinfo=timezone.utc)}
    return query


def count_results() -> dict[str, Any]:
    """$group accumulators: number of games and W/D/L from the user's side."""
    return {
        "games": {"$sum": 1},
        "wins": {"$sum": {"$cond": [{"$eq": ["$user_result", "win"]}, 1, 0]}},
        "draws": {"$sum": {"$cond": [{"$eq": ["$user_result", "draw"]}, 1, 0]}},
        "losses": {"$sum": {"$cond": [{"$eq": ["$user_result", "loss"]}, 1, 0]}},
    }


def user_count(classification: str) -> dict[str, Any]:
    """The user's count of one move label, read from the game's analysis summary."""
    return {
        "$cond": [
            {"$eq": ["$user_color", "white"]},
            f"$analysis.counts.white.{classification}",
            f"$analysis.counts.black.{classification}",
        ]
    }


def score(row: dict[str, Any]) -> float | None:
    """Points per game from the user's side (win 1, draw 0.5)."""
    return round((row["wins"] + 0.5 * row["draws"]) / row["games"], 3) if row["games"] else None


def results_of(row: dict[str, Any] | None) -> dict[str, Any]:
    row = row or {"games": 0, "wins": 0, "draws": 0, "losses": 0}
    out = {"games": row["games"], **{key: row[key] for key in RESULTS}}
    out["score"] = score(out)
    return out


async def summary(db: AsyncIOMotorDatabase, match: dict[str, Any]) -> dict[str, Any]:
    pipeline = [
        {"$match": match},
        {
            "$facet": {
                "by_color": [{"$group": {"_id": "$user_color", **count_results()}}],
                "analyzed": [
                    {"$match": {"analysis_status": "done"}},
                    {
                        "$group": {
                            "_id": None,
                            "games": {"$sum": 1},
                            "accuracy": {"$avg": "$accuracy"},
                            "inaccuracies": {"$sum": user_count("inaccuracy")},
                            "mistakes": {"$sum": user_count("mistake")},
                            "blunders": {"$sum": user_count("blunder")},
                        }
                    },
                ],
            }
        },
    ]
    facets = (await db.games.aggregate(pipeline).to_list(None))[0]
    by_color = {row["_id"]: row for row in facets["by_color"]}
    total = {key: sum(row[key] for row in by_color.values()) for key in ("games", *RESULTS)}
    analyzed = facets["analyzed"][0] if facets["analyzed"] and facets["analyzed"][0]["games"] else None

    def per_game(key: str) -> float | None:
        return round(analyzed[key] / analyzed["games"], 2) if analyzed else None

    return {
        **results_of(total),
        "by_color": {color: results_of(by_color.get(color)) for color in ("white", "black")},
        "analyzed_games": analyzed["games"] if analyzed else 0,
        "avg_accuracy": round(analyzed["accuracy"], 1) if analyzed and analyzed["accuracy"] is not None else None,
        "inaccuracies_per_game": per_game("inaccuracies"),
        "mistakes_per_game": per_game("mistakes"),
        "blunders_per_game": per_game("blunders"),
    }


async def openings(db: AsyncIOMotorDatabase, match: dict[str, Any], limit: int) -> dict[str, list[dict[str, Any]]]:
    """Results by opening family and color, most played first. Beyond `limit`
    openings per color, the rest are folded into "Other"."""
    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {"color": "$user_color", "opening": {"$ifNull": ["$opening_family", "Unknown"]}},
                **count_results(),
                "accuracy": {"$avg": "$accuracy"},
            }
        },
        {"$sort": {"games": -1, "_id.opening": 1}},
    ]
    rows: dict[str, list[dict[str, Any]]] = {"white": [], "black": []}
    async for row in db.games.aggregate(pipeline):
        rows[row["_id"]["color"]].append(row)

    def shape(row: dict[str, Any], name: str) -> dict[str, Any]:
        accuracy = row.get("accuracy")
        return {"opening": name, **results_of(row), "avg_accuracy": round(accuracy, 1) if accuracy is not None else None}

    out: dict[str, list[dict[str, Any]]] = {}
    for color, color_rows in rows.items():
        shown = [shape(row, row["_id"]["opening"]) for row in color_rows[:limit]]
        rest = color_rows[limit:]
        if rest:
            other = {key: sum(row[key] for row in rest) for key in ("games", *RESULTS)}
            shown.append(shape(other, f"Other ({len(rest)} openings)"))
        out[color] = shown
    return out


async def accuracy_trend(
    db: AsyncIOMotorDatabase, match: dict[str, Any], bucket: str, tz: str
) -> list[dict[str, Any]]:
    """Average accuracy (yours and your opponents') per week or month, analyzed games only."""
    pipeline = [
        {"$match": {**match, "analysis_status": "done"}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": BUCKET_FORMATS[bucket], "date": "$played_at", "timezone": tz}},
                "games": {"$sum": 1},
                "accuracy": {"$avg": "$accuracy"},
                "opponent_accuracy": {"$avg": "$opponent_accuracy"},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    return [
        {
            "period": row["_id"],
            "games": row["games"],
            "accuracy": round(row["accuracy"], 1) if row["accuracy"] is not None else None,
            "opponent_accuracy": round(row["opponent_accuracy"], 1) if row["opponent_accuracy"] is not None else None,
        }
        async for row in db.games.aggregate(pipeline)
    ]


async def ensure_phases(db: AsyncIOMotorDatabase, user_id: ObjectId) -> int:
    """Backfill `phase` on moves analyzed before phases were stored."""
    operations = [
        UpdateOne({"_id": doc["_id"]}, {"$set": {"phase": game_phase(chess.Board(doc["fen"]), doc["ply"])}})
        async for doc in db.positions.find({"user_id": user_id, "phase": {"$exists": False}}, {"fen": 1, "ply": 1})
    ]
    if operations:
        await db.positions.bulk_write(operations, ordered=False)
    return len(operations)


async def mistakes(db: AsyncIOMotorDatabase, match: dict[str, Any], user_id: ObjectId) -> dict[str, Any]:
    """Your inaccuracies, mistakes and blunders by game phase, with rates per 100 moves
    (phases have very different numbers of moves, so raw counts would mislead)."""
    await ensure_phases(db, user_id)
    game_ids = await db.games.distinct("_id", {**match, "analysis_status": "done"})
    pipeline = [
        {"$match": {"game_id": {"$in": game_ids}, "is_user_move": True}},
        {
            "$group": {
                "_id": "$phase",
                "moves": {"$sum": 1},
                **{
                    plural: {"$sum": {"$cond": [{"$eq": ["$classification", label]}, 1, 0]}}
                    for label, plural in (("inaccuracy", "inaccuracies"), ("mistake", "mistakes"), ("blunder", "blunders"))
                },
            }
        },
    ]
    rows = {row["_id"]: row async for row in db.positions.aggregate(pipeline)}

    def per_100(row: dict[str, Any], key: str) -> float | None:
        return round(100 * row[key] / row["moves"], 2) if row["moves"] else None

    phases = []
    for phase in PHASES:
        row = rows.get(phase, {"moves": 0, "inaccuracies": 0, "mistakes": 0, "blunders": 0})
        phases.append(
            {
                "phase": phase,
                "moves": row["moves"],
                **{key: row[key] for key in ("inaccuracies", "mistakes", "blunders")},
                **{f"{key}_per_100": per_100(row, key) for key in ("inaccuracies", "mistakes", "blunders")},
            }
        )
    return {"analyzed_games": len(game_ids), "phases": phases}


async def time_of_day(db: AsyncIOMotorDatabase, match: dict[str, Any], tz: str) -> list[dict[str, Any]]:
    """Results by the hour (in the viewer's timezone) each game ended. Daily games are
    left out: their moves are spread over days, so the end time says nothing."""
    if match.get("time_class") == "daily":
        return []
    query = {**match, "time_class": match.get("time_class", {"$ne": "daily"})}
    pipeline = [
        {"$match": query},
        {"$group": {"_id": {"$hour": {"date": "$played_at", "timezone": tz}}, **count_results()}},
    ]
    rows = {row["_id"]: row async for row in db.games.aggregate(pipeline)}
    return [{"hour": hour, **results_of(rows.get(hour))} for hour in range(24)]
