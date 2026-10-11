import pytest
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analysis.jobs import run_analysis
from app.config import Settings
from tests.conftest import insert_game
from tests.fakes import SCHOLARS_MATE_PGN, BrokenEngine, scholars_mate_engine

SETTINGS = Settings(analysis_depth=10)


async def queued_game(db: AsyncIOMotorDatabase, job_id: str = "job-1", user_color: str = "black") -> ObjectId:
    return await insert_game(
        db,
        ObjectId(),
        pgn=SCHOLARS_MATE_PGN,
        user_color=user_color,
        analysis_status="queued",
        analysis_job_id=job_id,
        analysis_progress=0.0,
    )


async def test_stores_positions_and_summary(test_db: AsyncIOMotorDatabase) -> None:
    game_id = await queued_game(test_db, user_color="black")

    await run_analysis(test_db, scholars_mate_engine(), game_id, "job-1", SETTINGS)

    game = await test_db.games.find_one({"_id": game_id})
    assert game["analysis_status"] == "done"
    assert game["analysis_progress"] == 1.0
    assert game["accuracy"] == game["analysis"]["accuracy"]["black"]
    assert game["opponent_accuracy"] == game["analysis"]["accuracy"]["white"]
    assert game["analysis"]["depth"] == 10
    assert game["analysis"]["counts"]["black"]["blunder"] == 1

    positions = await test_db.positions.find({"game_id": game_id}).sort("ply", 1).to_list(None)
    assert [p["ply"] for p in positions] == list(range(1, 8))
    assert [p["is_user_move"] for p in positions] == [False, True] * 3 + [False]
    assert all(p["user_id"] == game["user_id"] for p in positions)


async def test_reanalysis_replaces_positions_and_uses_the_cache(test_db: AsyncIOMotorDatabase) -> None:
    game_id = await queued_game(test_db)
    await run_analysis(test_db, scholars_mate_engine(), game_id, "job-1", SETTINGS)

    await test_db.games.update_one({"_id": game_id}, {"$set": {"analysis_job_id": "job-2"}})
    engine = scholars_mate_engine()
    await run_analysis(test_db, engine, game_id, "job-2", SETTINGS)

    game = await test_db.games.find_one({"_id": game_id})
    assert await test_db.positions.count_documents({"game_id": game_id}) == 7
    assert engine.calls == []
    assert (game["analysis"]["cache_hits"], game["analysis"]["cache_misses"]) == (7, 0)


async def test_stale_job_is_ignored(test_db: AsyncIOMotorDatabase) -> None:
    game_id = await queued_game(test_db, job_id="newer-job")
    engine = scholars_mate_engine()

    await run_analysis(test_db, engine, game_id, "older-job", SETTINGS)

    game = await test_db.games.find_one({"_id": game_id})
    assert game["analysis_status"] == "queued"
    assert engine.calls == []


async def test_missing_game_is_ignored(test_db: AsyncIOMotorDatabase) -> None:
    await run_analysis(test_db, scholars_mate_engine(), ObjectId(), "job-1", SETTINGS)


async def test_engine_failure_marks_the_game_failed(test_db: AsyncIOMotorDatabase) -> None:
    game_id = await queued_game(test_db)

    with pytest.raises(RuntimeError):
        await run_analysis(test_db, BrokenEngine(), game_id, "job-1", SETTINGS)

    game = await test_db.games.find_one({"_id": game_id})
    assert game["analysis_status"] == "failed"
    assert game["analysis_error"] == "engine crashed"
    assert await test_db.positions.count_documents({"game_id": game_id}) == 0
