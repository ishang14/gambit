from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analysis.jobs import run_analysis
from app.config import Settings
from scripts.recompute_accuracy import recompute
from tests.conftest import insert_game
from tests.fakes import SCHOLARS_MATE_PGN, scholars_mate_engine


async def test_recompute_matches_a_fresh_analysis(test_db: AsyncIOMotorDatabase) -> None:
    game_id = await insert_game(
        test_db, ObjectId(), pgn=SCHOLARS_MATE_PGN, user_color="black", analysis_status="queued", analysis_job_id="job"
    )
    await run_analysis(test_db, scholars_mate_engine(), game_id, "job", Settings())
    fresh = await test_db.games.find_one({"_id": game_id})
    # Pretend it was analyzed with the old method.
    await test_db.games.update_one({"_id": game_id}, {"$set": {"accuracy": 1.0, "opponent_accuracy": 2.0}})

    assert await recompute(test_db) == 1

    game = await test_db.games.find_one({"_id": game_id})
    assert game["accuracy"] == fresh["accuracy"]
    assert game["opponent_accuracy"] == fresh["opponent_accuracy"]
    assert game["analysis"]["accuracy"] == fresh["analysis"]["accuracy"]


async def test_games_without_analysis_are_untouched(test_db: AsyncIOMotorDatabase) -> None:
    await insert_game(test_db, ObjectId())

    assert await recompute(test_db) == 0
