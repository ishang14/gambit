from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings
from app.main import app
from app.training.cards import move_label
from tests.conftest import insert_game, make_user, user_id_for
from tests.fakes import SCHOLARS_MATE_PGN, scholars_mate_engine
from tests.helpers import add_games, analyze, blunder_engine

# In the scripted Scholar's mate, Black (the user) blunders 3... Nf6?? where 3... g6 was best.
NF6_FEN = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"


async def blunder_setup(client: AsyncClient, headers: dict, db: AsyncIOMotorDatabase) -> ObjectId:
    user_id = await user_id_for(client, headers)
    game_id = await insert_game(db, user_id, pgn=SCHOLARS_MATE_PGN, user_color="black", opponent="hero")
    await analyze(db, game_id, scholars_mate_engine())
    return game_id


async def sync(client: AsyncClient, headers: dict) -> dict:
    response = await client.post("/training/sync", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def due(client: AsyncClient, headers: dict) -> dict:
    response = await client.get("/training/due", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def submit(client: AsyncClient, headers: dict, card_id: str, move: str, rating: str):
    return await client.post(f"/training/cards/{card_id}/review", json={"move": move, "rating": rating}, headers=headers)


def test_move_label() -> None:
    assert [move_label(p) for p in (1, 2, 45, 46)] == ["1.", "1...", "23.", "23..."]


# --- card generation ---

async def test_blunders_become_cards(client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase) -> None:
    game_id = await blunder_setup(client, auth_headers, test_db)

    assert await sync(client, auth_headers) == {"created": 1, "total": 1}

    card = (await due(client, auth_headers))["cards"][0]
    assert card["source"] == "blunder"
    assert card["fen"] == NF6_FEN
    assert card["color"] == "black"
    assert (card["correct_move"], card["correct_move_san"]) == ("g7g6", "g6")
    assert (card["user_move"], card["user_move_san"]) == ("g8f6", "Nf6")
    assert card["context"]["game_id"] == str(game_id)
    assert card["context"]["opponent"] == "hero"
    assert card["context"]["move_number"] == "3..."
    assert (card["repetitions"], card["interval"], card["reviews"]) == (0, 0, 0)


async def test_sync_is_idempotent_and_keeps_progress(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    await blunder_setup(client, auth_headers, test_db)
    await sync(client, auth_headers)
    card_id = (await due(client, auth_headers))["cards"][0]["id"]
    await submit(client, auth_headers, card_id, "g7g6", "good")

    again = await sync(client, auth_headers)

    assert again == {"created": 0, "total": 1}
    card = await test_db.training_cards.find_one({"_id": ObjectId(card_id)})
    assert card["repetitions"] == 1


async def test_engine_flagged_leaks_become_cards(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    user_id = await user_id_for(client, auth_headers)
    ids = await add_games(test_db, user_id, [("1. e4 e5 2. Ke2 Nc6", "white", "win")] * 2 + [("1. e4 e5 2. Nf3", "white", "win")])
    for game_id in ids[:2]:
        await analyze(test_db, game_id, blunder_engine(("e4", "e5"), "e1e2"))

    result = await sync(client, auth_headers)

    cards = (await due(client, auth_headers))["cards"]
    leak_cards = [c for c in cards if c["source"] == "leak"]
    # 2. Ke2 is also a blunder in each game, but it's one position + move, so one card (the leak).
    assert result["created"] == 1
    assert len(leak_cards) == 1
    card = leak_cards[0]
    assert (card["user_move_san"], card["correct_move_san"]) == ("Ke2", "Nf3")
    assert card["context"]["path"] == ["e4", "e5"]
    assert card["context"]["games"] == 2


async def test_results_only_leaks_without_analysis_make_no_cards(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    await add_games(test_db, await user_id_for(client, auth_headers), [("1. e4 e5 2. Qh5", "white", "loss")] * 3)

    assert await sync(client, auth_headers) == {"created": 0, "total": 0}


async def test_cards_are_private(client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase) -> None:
    await blunder_setup(client, auth_headers, test_db)
    await sync(client, auth_headers)
    card_id = (await due(client, auth_headers))["cards"][0]["id"]
    other = await make_user(client, "other@example.com")

    assert (await sync(client, other))["total"] == 0
    assert (await due(client, other))["cards"] == []
    assert (await submit(client, other, card_id, "g7g6", "good")).status_code == 404


# --- reviewing ---

async def test_correct_answer_schedules_tomorrow(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    await blunder_setup(client, auth_headers, test_db)
    await sync(client, auth_headers)
    card_id = (await due(client, auth_headers))["cards"][0]["id"]

    response = await submit(client, auth_headers, card_id, "g7g6", "good")

    body = response.json()
    assert body["correct"] is True
    assert body["played_san"] == "g6"
    card = body["card"]
    assert (card["repetitions"], card["interval"], card["reviews"], card["lapses"]) == (1, 1, 1, 0)
    due_at = datetime.fromisoformat(card["due_at"])
    assert timedelta(hours=23) < due_at - datetime.now(timezone.utc) <= timedelta(days=1)
    assert (await due(client, auth_headers))["due"] == 0
    log = await test_db.training_reviews.find_one({"card_id": ObjectId(card_id)})
    assert (log["correct"], log["rating"], log["quality"]) == (True, "good", 4)


async def test_wrong_answer_fails_whatever_the_rating(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    await blunder_setup(client, auth_headers, test_db)
    await sync(client, auth_headers)
    card_id = (await due(client, auth_headers))["cards"][0]["id"]

    body = (await submit(client, auth_headers, card_id, "g8f6", "easy")).json()

    assert body["correct"] is False
    assert (body["played_san"], body["correct_move_san"]) == ("Nf6", "g6")
    card = body["card"]
    assert (card["repetitions"], card["interval"], card["lapses"]) == (0, 0, 1)
    assert card["ease"] < 2.5
    due_at = datetime.fromisoformat(card["due_at"])
    assert due_at - datetime.now(timezone.utc) <= timedelta(minutes=10)


@pytest.mark.parametrize(("move", "status"), [("e2e4", 422), ("a1a1", 422), ("nonsense", 422)])
async def test_rejects_illegal_or_malformed_moves(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase, move: str, status: int
) -> None:
    await blunder_setup(client, auth_headers, test_db)
    await sync(client, auth_headers)
    card_id = (await due(client, auth_headers))["cards"][0]["id"]

    response = await submit(client, auth_headers, card_id, move, "good")

    assert response.status_code == status


async def test_bad_card_id(client: AsyncClient, auth_headers: dict) -> None:
    assert (await submit(client, auth_headers, "nope", "e2e4", "good")).status_code == 404
    assert (await submit(client, auth_headers, str(ObjectId()), "e2e4", "good")).status_code == 404


async def test_due_reviews_are_limited_and_oldest_first(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    user_id = await user_id_for(client, auth_headers)
    now = datetime.now(timezone.utc)
    for index, minutes_ago in enumerate([5, 30, 10, -60]):  # the last one isn't due yet
        await test_db.training_cards.insert_one(
            {
                "user_id": user_id,
                "source": "blunder",
                "fen": NF6_FEN,
                "fen_key": f"key{index}",
                "color": "black",
                "correct_move": "g7g6",
                "correct_move_san": "g6",
                "user_move": "g8f6",
                "user_move_san": "Nf6",
                "context": {"minutes_ago": minutes_ago},
                "ease": 2.5,
                "interval": 1,
                "repetitions": 1,
                "due_at": now - timedelta(minutes=minutes_ago),
                "last_reviewed_at": now - timedelta(days=1),
                "reviews": 1,
                "lapses": 0,
            }
        )

    response = await client.get("/training/due", params={"limit": 2}, headers=auth_headers)

    body = response.json()
    assert body["due"] == 3
    assert [c["context"]["minutes_ago"] for c in body["cards"]] == [30, 10]


# --- daily allowance of new cards ---

async def insert_cards(db: AsyncIOMotorDatabase, user_id: ObjectId, count: int, **fields) -> None:
    now = datetime.now(timezone.utc)
    await db.training_cards.insert_many(
        [
            {
                "user_id": user_id,
                "source": "blunder",
                "fen": NF6_FEN,
                "fen_key": f"{fields.get('prefix', 'new')}{i}",
                "color": "black",
                "correct_move": "g7g6",
                "correct_move_san": "g6",
                "user_move": "g8f6",
                "user_move_san": "Nf6",
                "context": {},
                "ease": 2.5,
                "interval": 0,
                "repetitions": 0,
                "due_at": now,
                "created_at": now + timedelta(seconds=i),
                "last_reviewed_at": None,
                "reviews": 0,
                "lapses": 0,
                **{k: v for k, v in fields.items() if k != "prefix"},
            }
            for i in range(count)
        ]
    )


@pytest.fixture
def three_new_cards_a_day():
    app.dependency_overrides[get_settings] = lambda: get_settings().model_copy(update={"training_new_cards_per_day": 3})
    yield
    app.dependency_overrides.pop(get_settings, None)


async def test_new_cards_are_capped_per_day(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase, three_new_cards_a_day
) -> None:
    user_id = await user_id_for(client, auth_headers)
    await insert_cards(test_db, user_id, 10)

    first = await due(client, auth_headers)
    assert (first["due"], len(first["cards"])) == (3, 3)
    assert [c["context"] for c in first["cards"]] == [{}, {}, {}]

    for card in first["cards"][:2]:
        await submit(client, auth_headers, card["id"], "g7g6", "good")

    after = await due(client, auth_headers)
    assert after["due"] == 1  # 3 allowed, 2 started
    stats = (await client.get("/training/stats", headers=auth_headers)).json()
    assert (stats["new"], stats["new_left_today"], stats["new_cards_per_day"], stats["due_now"]) == (8, 1, 3, 1)


async def test_reviews_come_before_new_cards_and_ignore_the_cap(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase, three_new_cards_a_day
) -> None:
    user_id = await user_id_for(client, auth_headers)
    now = datetime.now(timezone.utc)
    await insert_cards(test_db, user_id, 5, prefix="old", reviews=2, repetitions=2, interval=6, due_at=now - timedelta(hours=1))
    await insert_cards(test_db, user_id, 5, prefix="new")

    body = (await client.get("/training/due", params={"limit": 7}, headers=auth_headers)).json()

    assert body["due"] == 8  # 5 reviews + 3 new
    assert [c["reviews"] for c in body["cards"]] == [2, 2, 2, 2, 2, 0, 0]


# --- stats ---

async def test_stats(client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase) -> None:
    await blunder_setup(client, auth_headers, test_db)
    user_id = await user_id_for(client, auth_headers)
    ids = await add_games(test_db, user_id, [("1. e4 e5 2. Ke2 Nc6", "white", "win")] * 2 + [("1. e4 e5 2. Nf3", "white", "win")])
    for game_id in ids[:2]:
        await analyze(test_db, game_id, blunder_engine(("e4", "e5"), "e1e2"))
    await sync(client, auth_headers)
    cards = (await due(client, auth_headers))["cards"]
    blunder = next(c for c in cards if c["source"] == "blunder")
    await submit(client, auth_headers, blunder["id"], "g7g6", "good")

    stats = (await client.get("/training/stats", headers=auth_headers)).json()

    assert stats["total"] == 2
    assert stats["by_source"] == {"blunder": 1, "leak": 1}
    assert stats["due_now"] == 1
    assert stats["new"] == 1
    assert stats["learning"] == 1
    assert stats["mature"] == 0
    assert stats["reviews_last_24h"] == 1
    assert stats["accuracy_last_7d"] == 1.0
    assert stats["next_due_at"] is not None


async def test_stats_when_empty(client: AsyncClient, auth_headers: dict) -> None:
    stats = (await client.get("/training/stats", headers=auth_headers)).json()

    assert stats["total"] == 0
    assert stats["accuracy_last_7d"] is None
    assert stats["next_due_at"] is None

