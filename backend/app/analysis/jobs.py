"""The analysis job. The ARQ worker calls `run_analysis`; tests call it directly with a fake engine."""

import logging
import time
from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analysis.analyzer import analyze_pgn
from app.analysis.engine import CachedEngine, Engine
from app.analysis.scoring import Thresholds
from app.config import Settings
from app.openings.indexer import attach_analysis

logger = logging.getLogger(__name__)

# Write progress to the game every N evaluated positions, not on every one.
PROGRESS_EVERY = 5


def thresholds_from(settings: Settings) -> Thresholds:
    return Thresholds(
        inaccuracy=settings.inaccuracy_threshold,
        mistake=settings.mistake_threshold,
        blunder=settings.blunder_threshold,
    )


async def run_analysis(
    db: AsyncIOMotorDatabase,
    engine: Engine,
    game_id: ObjectId,
    job_id: str,
    settings: Settings,
) -> None:
    game = await db.games.find_one({"_id": game_id})
    # Skip deleted games and jobs that a newer request has replaced.
    if game is None or game.get("analysis_job_id") != job_id:
        logger.info("Skipping stale analysis job %s for game %s", job_id, game_id)
        return

    async def set_fields(fields: dict) -> None:
        await db.games.update_one({"_id": game_id, "analysis_job_id": job_id}, {"$set": fields})

    async def on_progress(done: int, total: int) -> None:
        if done == total or done % PROGRESS_EVERY == 0:
            await set_fields({"analysis_progress": round(done / total, 3)})

    await set_fields({"analysis_status": "running", "analysis_progress": 0.0, "analysis_error": None})
    cached = CachedEngine(engine, db)
    started = time.perf_counter()
    try:
        analysis = await analyze_pgn(
            game["pgn"], cached, settings.analysis_depth, thresholds_from(settings), on_progress
        )
    except Exception as exc:
        logger.exception("Analysis failed for game %s", game_id)
        await set_fields({"analysis_status": "failed", "analysis_error": str(exc) or type(exc).__name__})
        raise

    user_color = game["user_color"]
    opponent_color = "black" if user_color == "white" else "white"
    await db.positions.delete_many({"game_id": game_id})
    if analysis.positions:
        await db.positions.insert_many(
            [
                {**p, "game_id": game_id, "user_id": game["user_id"], "is_user_move": p["color"] == user_color}
                for p in analysis.positions
            ]
        )
        await attach_analysis(db, game_id, analysis.positions)
    await set_fields(
        {
            "analysis_status": "done",
            "analysis_progress": 1.0,
            "accuracy": analysis.accuracy[user_color],
            "opponent_accuracy": analysis.accuracy[opponent_color],
            "analysis": {
                "depth": settings.analysis_depth,
                "counts": analysis.counts,
                "accuracy": analysis.accuracy,
                "positions_evaluated": cached.hits + cached.misses,
                "cache_hits": cached.hits,
                "cache_misses": cached.misses,
                "duration_seconds": round(time.perf_counter() - started, 2),
                "analyzed_at": datetime.now(timezone.utc),
            },
        }
    )
