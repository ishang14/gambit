import pytest
from bson import ObjectId
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analysis.jobs import run_analysis
from app.analysis.queue import get_analysis_queue
from app.config import Settings
from app.main import app
from tests.conftest import insert_game, make_user, user_id_for
from tests.fakes import SCHOLARS_MATE_PGN, scholars_mate_engine


class FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, str]] = []
        self.fail = False

    async def enqueue_analysis(self, game_id: str, job_id: str) -> None:
        if self.fail:
            raise ConnectionError("redis down")
        self.jobs.append((game_id, job_id))


@pytest.fixture
def queue() -> FakeQueue:
    fake = FakeQueue()
    app.dependency_overrides[get_analysis_queue] = lambda: fake
    return fake


@pytest.fixture
async def game_id(client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase) -> ObjectId:
    user_id = await user_id_for(client, auth_headers)
    return await insert_game(test_db, user_id, pgn=SCHOLARS_MATE_PGN, user_color="black")


async def request_analysis(client: AsyncClient, game_id: ObjectId, headers: dict) -> dict:
    response = await client.post(f"/games/{game_id}/analysis", headers=headers)
    assert response.status_code == 202, response.text
    return response.json()


# --- starting jobs ---

async def test_queues_a_job(
    client: AsyncClient, auth_headers: dict, queue: FakeQueue, game_id: ObjectId, test_db: AsyncIOMotorDatabase
) -> None:
    job = await request_analysis(client, game_id, auth_headers)

    assert job["status"] == "queued"
    assert job["progress"] == 0.0
    assert job["game_id"] == str(game_id)
    assert queue.jobs == [(str(game_id), job["job_id"])]
    game = await test_db.games.find_one({"_id": game_id})
    assert game["analysis_job_id"] == job["job_id"]


async def test_second_request_returns_the_same_job(
    client: AsyncClient, auth_headers: dict, queue: FakeQueue, game_id: ObjectId
) -> None:
    first = await request_analysis(client, game_id, auth_headers)
    second = await request_analysis(client, game_id, auth_headers)

    assert second["job_id"] == first["job_id"]
    assert len(queue.jobs) == 1


async def test_finished_game_can_be_reanalyzed(
    client: AsyncClient, auth_headers: dict, queue: FakeQueue, game_id: ObjectId, test_db: AsyncIOMotorDatabase
) -> None:
    first = await request_analysis(client, game_id, auth_headers)
    await test_db.games.update_one({"_id": game_id}, {"$set": {"analysis_status": "done"}})

    second = await request_analysis(client, game_id, auth_headers)

    assert second["job_id"] != first["job_id"]
    assert len(queue.jobs) == 2


async def test_cannot_analyze_someone_elses_game(
    client: AsyncClient, queue: FakeQueue, game_id: ObjectId
) -> None:
    other = await make_user(client, "other@example.com")

    response = await client.post(f"/games/{game_id}/analysis", headers=other)

    assert response.status_code == 404
    assert queue.jobs == []


async def test_bad_game_id(client: AsyncClient, auth_headers: dict, queue: FakeQueue) -> None:
    response = await client.post("/games/nope/analysis", headers=auth_headers)

    assert response.status_code == 404


async def test_queue_down_marks_the_game_failed(
    client: AsyncClient, auth_headers: dict, queue: FakeQueue, game_id: ObjectId, test_db: AsyncIOMotorDatabase
) -> None:
    queue.fail = True

    response = await client.post(f"/games/{game_id}/analysis", headers=auth_headers)

    assert response.status_code == 503
    game = await test_db.games.find_one({"_id": game_id})
    assert game["analysis_status"] == "failed"


# --- job status ---

async def test_job_status_tracks_the_game(
    client: AsyncClient, auth_headers: dict, queue: FakeQueue, game_id: ObjectId, test_db: AsyncIOMotorDatabase
) -> None:
    job = await request_analysis(client, game_id, auth_headers)
    await test_db.games.update_one(
        {"_id": game_id}, {"$set": {"analysis_status": "running", "analysis_progress": 0.4}}
    )

    response = await client.get(f"/analysis/jobs/{job['job_id']}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["progress"] == 0.4


async def test_job_status_is_private(
    client: AsyncClient, auth_headers: dict, queue: FakeQueue, game_id: ObjectId
) -> None:
    job = await request_analysis(client, game_id, auth_headers)
    other = await make_user(client, "other@example.com")

    response = await client.get(f"/analysis/jobs/{job['job_id']}", headers=other)

    assert response.status_code == 404


# --- queue all ---

async def test_queue_all_skips_analyzed_and_active_games(
    client: AsyncClient, auth_headers: dict, queue: FakeQueue, test_db: AsyncIOMotorDatabase
) -> None:
    user_id = await user_id_for(client, auth_headers)
    for index, status in enumerate(["none", "failed", "done", "queued", "running", "none"]):
        await insert_game(test_db, user_id, source_url=f"https://example.com/{index}", analysis_status=status)
    other_user_game = await insert_game(test_db, ObjectId())

    response = await client.post("/analysis/queue-all", headers=auth_headers)

    assert response.json() == {"queued": 3}
    assert len(queue.jobs) == 3
    assert str(other_user_game) not in {game_id for game_id, _ in queue.jobs}


# --- results ---

async def test_analysis_not_ready(client: AsyncClient, auth_headers: dict, game_id: ObjectId) -> None:
    response = await client.get(f"/games/{game_id}/analysis", headers=auth_headers)

    assert response.status_code == 409


async def test_analysis_results(
    client: AsyncClient, auth_headers: dict, queue: FakeQueue, game_id: ObjectId, test_db: AsyncIOMotorDatabase
) -> None:
    job = await request_analysis(client, game_id, auth_headers)
    await run_analysis(test_db, scholars_mate_engine(), game_id, job["job_id"], Settings(analysis_depth=10))

    status = (await client.get(f"/analysis/jobs/{job['job_id']}", headers=auth_headers)).json()
    response = await client.get(f"/games/{game_id}/analysis", headers=auth_headers)
    game = (await client.get(f"/games/{game_id}", headers=auth_headers)).json()

    assert status["status"] == "done"
    body = response.json()
    assert body["depth"] == 10
    assert len(body["moves"]) == 7
    assert body["moves"][5]["classification"] == "blunder"
    assert body["moves"][5]["best_move_san"] == "g6"
    assert body["counts"]["black"]["blunder"] == 1
    assert game["analysis_status"] == "done"
    assert game["accuracy"] == body["accuracy"]["black"]
