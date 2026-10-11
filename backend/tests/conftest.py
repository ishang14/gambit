import json
import os
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings
from app.db import ensure_indexes, get_db
from app.games.parser import parse_game
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"

# CI sets this so tests needing MongoDB or Stockfish fail instead of quietly skipping.
REQUIRE_INTEGRATION = os.environ.get("GAMBIT_REQUIRE_INTEGRATION") == "1"


def skip_or_fail(reason: str) -> None:
    if REQUIRE_INTEGRATION:
        pytest.fail(f"{reason} (GAMBIT_REQUIRE_INTEGRATION=1)")
    pytest.skip(reason)


def load_fixture(name: str) -> Any:
    """Load a saved JSON response, e.g. load_fixture('chesscom/archives.json')."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
async def test_db() -> AsyncIOMotorDatabase:
    """A fresh in-memory database for each test."""
    # tz_aware matches the real client (app/db.py): datetimes come back as UTC.
    database = AsyncMongoMockClient(tz_aware=True)["gambit_test"]
    await ensure_indexes(database)
    return database


@pytest.fixture
async def client(test_db: AsyncIOMotorDatabase) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def real_db() -> AsyncIterator[AsyncIOMotorDatabase]:
    """A throwaway database on a real MongoDB, for pipeline features the in-memory fake
    lacks (e.g. timezones in $dateToString). Skipped when MongoDB isn't reachable."""
    mongo = AsyncIOMotorClient(get_settings().mongo_url, serverSelectionTimeoutMS=1000, tz_aware=True)
    try:
        await mongo.admin.command("ping")
    except Exception:
        mongo.close()
        skip_or_fail("MongoDB is not running")
    name = f"gambit_test_{uuid4().hex[:12]}"
    database = mongo[name]
    await ensure_indexes(database)
    yield database
    await mongo.drop_database(name)
    mongo.close()


@pytest.fixture
async def real_client(real_db: AsyncIOMotorDatabase) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: real_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def make_user(client: AsyncClient, email: str = "player@example.com") -> dict[str, str]:
    """Sign up a user and return Authorization headers for them."""
    response = await client.post("/auth/signup", json={"email": email, "password": "correct-horse-battery"})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    return await make_user(client)


async def user_id_for(client: AsyncClient, headers: dict[str, str]) -> ObjectId:
    me = await client.get("/auth/me", headers=headers)
    return ObjectId(me.json()["id"])


async def insert_game(db: AsyncIOMotorDatabase, user_id: ObjectId, **overrides: Any) -> ObjectId:
    """Store a game directly (as an import would), built from the first fixture game."""
    raw = load_fixture("chesscom/games_2026_09.json")["games"][0]
    game = parse_game(raw, "erik")
    assert game is not None
    game.update(
        user_id=user_id,
        chesscom_username="erik",
        analysis_status="none",
        accuracy=None,
        imported_at=datetime.now(timezone.utc),
    )
    game.update(overrides)
    result = await db.games.insert_one(game)
    return result.inserted_id
