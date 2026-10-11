import logging
from typing import Any
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.analysis.queue import AnalysisQueue, get_analysis_queue
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.analysis import AnalysisJob, AnalyzedMove, GameAnalysisOut, QueueAllResult

logger = logging.getLogger(__name__)
router = APIRouter(tags=["analysis"])

ACTIVE_STATUSES = ["queued", "running"]


def job_out(game: dict[str, Any]) -> AnalysisJob:
    return AnalysisJob(
        job_id=game["analysis_job_id"],
        game_id=str(game["_id"]),
        status=game["analysis_status"],
        progress=game.get("analysis_progress", 0.0),
        error=game.get("analysis_error"),
    )


def owned_game_filter(game_id: str, user: dict[str, Any]) -> dict[str, Any]:
    if not ObjectId.is_valid(game_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found")
    return {"_id": ObjectId(game_id), "user_id": user["_id"]}


async def start_job(
    db: AsyncIOMotorDatabase, queue: AnalysisQueue, game_filter: dict[str, Any]
) -> dict[str, Any] | None:
    """Mark a game as queued and enqueue it, unless it is already queued or running.
    The status check and update are one atomic operation, so double clicks enqueue once."""
    job_id = uuid4().hex
    game = await db.games.find_one_and_update(
        {**game_filter, "analysis_status": {"$nin": ACTIVE_STATUSES}},
        {
            "$set": {
                "analysis_status": "queued",
                "analysis_job_id": job_id,
                "analysis_progress": 0.0,
                "analysis_error": None,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if game is None:
        return None
    try:
        await queue.enqueue_analysis(str(game["_id"]), job_id)
    except Exception:
        logger.exception("Could not enqueue analysis for game %s", game["_id"])
        await db.games.update_one(
            {"_id": game["_id"]},
            {"$set": {"analysis_status": "failed", "analysis_error": "Could not queue the analysis job"}},
        )
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Analysis queue is unavailable")
    return game


@router.post("/games/{game_id}/analysis", response_model=AnalysisJob, status_code=status.HTTP_202_ACCEPTED)
async def analyze_game(
    game_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    queue: AnalysisQueue = Depends(get_analysis_queue),
) -> AnalysisJob:
    """Queue analysis for one game. If it is already queued or running, returns that job."""
    game_filter = owned_game_filter(game_id, user)
    game = await start_job(db, queue, game_filter)
    if game is None:
        game = await db.games.find_one(game_filter)
        if game is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found")
    return job_out(game)


@router.post("/analysis/queue-all", response_model=QueueAllResult)
async def queue_all(
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    queue: AnalysisQueue = Depends(get_analysis_queue),
) -> QueueAllResult:
    """Queue every game that hasn't been analyzed yet (or whose analysis failed)."""
    cursor = db.games.find(
        {"user_id": user["_id"], "analysis_status": {"$in": ["none", "failed"]}},
        {"_id": 1},
    ).sort("played_at", -1)
    queued = 0
    async for game in cursor:
        if await start_job(db, queue, {"_id": game["_id"], "user_id": user["_id"]}):
            queued += 1
    return QueueAllResult(queued=queued)


@router.get("/analysis/jobs/{job_id}", response_model=AnalysisJob)
async def job_status(
    job_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> AnalysisJob:
    game = await db.games.find_one({"analysis_job_id": job_id, "user_id": user["_id"]})
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job_out(game)


@router.get("/games/{game_id}/analysis", response_model=GameAnalysisOut)
async def game_analysis(
    game_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> GameAnalysisOut:
    game = await db.games.find_one(owned_game_filter(game_id, user))
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found")
    if game.get("analysis_status") != "done":
        raise HTTPException(status.HTTP_409_CONFLICT, "This game has not been analyzed yet")

    cursor = db.positions.find({"game_id": game["_id"]}).sort("ply", 1)
    moves = [AnalyzedMove(**doc) async for doc in cursor]
    summary = game["analysis"]
    return GameAnalysisOut(
        game_id=game_id,
        depth=summary["depth"],
        accuracy=summary["accuracy"],
        counts=summary["counts"],
        moves=moves,
    )
