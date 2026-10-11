from datetime import datetime, timezone
from typing import Any

import pytest
from bson import ObjectId
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from tests.conftest import insert_game, make_user, user_id_for
from tests.helpers import pgn

SICILIAN = "1. e4 c5 2. Nf3 d6"
RUY_LOPEZ = "1. e4 e5 2. Nf3 Nc6 3. Bb5"
QUEENS_GAMBIT = "1. d4 d5 2. c4"


def when(day: int, hour: int = 12, month: int = 9) -> datetime:
    return datetime(2026, month, day, hour, 0, tzinfo=timezone.utc)


def counts(blunders: int = 0, mistakes: int = 0, inaccuracies: int = 0) -> dict[str, int]:
    return {"best": 10, "good": 10, "inaccuracy": inaccuracies, "mistake": mistakes, "blunder": blunders}


async def add(db: AsyncIOMotorDatabase, user_id: ObjectId, moves: str, color: str, result: str, **fields: Any) -> ObjectId:
    return await insert_game(
        db,
        user_id,
        source_url=f"https://example.com/{ObjectId()}",
        pgn=pgn(moves),
        user_color=color,
        user_result=result,
        **fields,
    )


async def analyzed(db, user_id, moves, color, result, accuracy, opponent_accuracy, blunders=0, **fields) -> ObjectId:
    other = "black" if color == "white" else "white"
    return await add(
        db,
        user_id,
        moves,
        color,
        result,
        analysis_status="done",
        accuracy=accuracy,
        opponent_accuracy=opponent_accuracy,
        analysis={"counts": {color: counts(blunders=blunders), other: counts()}},
        **fields,
    )


@pytest.fixture
async def user_id(client: AsyncClient, auth_headers: dict) -> ObjectId:
    return await user_id_for(client, auth_headers)


async def get(client: AsyncClient, headers: dict, path: str, **params: Any) -> dict:
    response = await client.get(f"/insights/{path}", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


# --- summary ---

async def test_summary(client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db) -> None:
    await analyzed(test_db, user_id, SICILIAN, "white", "win", 90.0, 80.0, blunders=1, played_at=when(1))
    await analyzed(test_db, user_id, SICILIAN, "white", "loss", 70.0, 85.0, blunders=3, played_at=when(2))
    await add(test_db, user_id, RUY_LOPEZ, "black", "draw", played_at=when(3))
    await add(test_db, user_id, RUY_LOPEZ, "black", "win", played_at=when(4))

    body = await get(client, auth_headers, "summary")

    assert (body["games"], body["wins"], body["draws"], body["losses"]) == (4, 2, 1, 1)
    assert body["score"] == 0.625
    assert body["by_color"]["white"] == {"games": 2, "wins": 1, "draws": 0, "losses": 1, "score": 0.5}
    assert body["by_color"]["black"]["score"] == 0.75
    assert body["analyzed_games"] == 2
    assert body["avg_accuracy"] == 80.0
    assert body["blunders_per_game"] == 2.0


async def test_summary_with_no_games(client: AsyncClient, auth_headers: dict) -> None:
    body = await get(client, auth_headers, "summary")

    assert body["games"] == 0
    assert body["score"] is None
    assert body["avg_accuracy"] is None
    assert body["blunders_per_game"] is None


async def test_filters_apply_to_every_insight(client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db) -> None:
    await add(test_db, user_id, SICILIAN, "white", "win", time_class="blitz", played_at=when(1))
    await add(test_db, user_id, SICILIAN, "white", "loss", time_class="rapid", played_at=when(1))
    await add(test_db, user_id, SICILIAN, "white", "loss", time_class="blitz", played_at=when(1, month=6))

    blitz = await get(client, auth_headers, "summary", time_class="blitz")
    recent = await get(client, auth_headers, "summary", since="2026-08-01")
    recent_blitz = await get(client, auth_headers, "summary", time_class="blitz", since="2026-08-01")

    assert blitz["games"] == 2
    assert recent["games"] == 2
    assert (recent_blitz["games"], recent_blitz["wins"]) == (1, 1)


async def test_insights_are_private(client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db) -> None:
    await add(test_db, user_id, SICILIAN, "white", "win")
    other = await make_user(client, "other@example.com")

    assert (await get(client, other, "summary"))["games"] == 0
    assert (await get(client, other, "openings"))["white"] == []


async def test_requires_login(client: AsyncClient) -> None:
    for path in ("summary", "openings", "accuracy", "mistakes", "time-of-day"):
        assert (await client.get(f"/insights/{path}")).status_code == 401


# --- openings ---

async def test_results_by_opening_family_and_color(
    client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db
) -> None:
    for result in ("win", "win", "loss"):
        await add(test_db, user_id, SICILIAN, "white", result)
    await add(test_db, user_id, RUY_LOPEZ, "white", "draw")
    await add(test_db, user_id, QUEENS_GAMBIT, "black", "loss")

    body = await get(client, auth_headers, "openings")

    assert [(o["opening"], o["games"], o["score"]) for o in body["white"]] == [
        ("Sicilian Defense", 3, 0.667),
        ("Ruy Lopez", 1, 0.5),
    ]
    assert [(o["opening"], o["losses"]) for o in body["black"]] == [("Queen's Gambit", 1)]


async def test_openings_beyond_the_limit_fold_into_other(
    client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db
) -> None:
    for moves in (SICILIAN, SICILIAN, RUY_LOPEZ, QUEENS_GAMBIT):
        await add(test_db, user_id, moves, "white", "win")

    body = await get(client, auth_headers, "openings", limit=1)

    assert [(o["opening"], o["games"]) for o in body["white"]] == [("Sicilian Defense", 2), ("Other (2 openings)", 2)]


# --- accuracy over time (real MongoDB: the fake lacks timezones in $dateToString) ---

async def test_accuracy_by_week_and_month(real_client: AsyncClient, real_db) -> None:
    headers = await make_user(real_client)
    user_id = await user_id_for(real_client, headers)
    await analyzed(real_db, user_id, SICILIAN, "white", "win", 80.0, 70.0, played_at=when(1))  # Tue, ISO week 36
    await analyzed(real_db, user_id, SICILIAN, "white", "win", 90.0, 60.0, played_at=when(3))  # week 36
    await analyzed(real_db, user_id, SICILIAN, "white", "win", 70.0, 75.0, played_at=when(9))  # week 37
    await add(real_db, user_id, SICILIAN, "white", "win", played_at=when(10))  # not analyzed

    weekly = await get(real_client, headers, "accuracy")
    monthly = await get(real_client, headers, "accuracy", bucket="month")

    assert weekly["bucket"] == "week"
    assert weekly["points"] == [
        {"period": "2026-W36", "games": 2, "accuracy": 85.0, "opponent_accuracy": 65.0},
        {"period": "2026-W37", "games": 1, "accuracy": 70.0, "opponent_accuracy": 75.0},
    ]
    assert monthly["points"] == [{"period": "2026-09", "games": 3, "accuracy": 80.0, "opponent_accuracy": 68.3}]


async def test_accuracy_buckets_use_the_viewers_timezone(real_client: AsyncClient, real_db) -> None:
    headers = await make_user(real_client)
    user_id = await user_id_for(real_client, headers)
    # 02:00 UTC on Oct 1 is still Sep 30 in New York.
    await analyzed(real_db, user_id, SICILIAN, "white", "win", 80.0, 70.0, played_at=when(1, hour=2, month=10))

    utc = await get(real_client, headers, "accuracy", bucket="month")
    new_york = await get(real_client, headers, "accuracy", bucket="month", tz="America/New_York")

    assert utc["points"][0]["period"] == "2026-10"
    assert new_york["points"][0]["period"] == "2026-09"


async def test_unknown_timezone_is_rejected(real_client: AsyncClient) -> None:
    headers = await make_user(real_client)

    response = await real_client.get("/insights/accuracy", params={"tz": "Mars/Olympus_Mons"}, headers=headers)

    assert response.status_code == 422
    assert response.json()["detail"] == "Unknown timezone"


# --- mistakes by phase ---

async def add_moves(db, user_id: ObjectId, game_id: ObjectId, moves: list[tuple[str, str, bool]]) -> None:
    """moves: (phase, classification, is_user_move)"""
    await db.positions.insert_many(
        [
            {"game_id": game_id, "user_id": user_id, "ply": i + 1, "phase": phase, "classification": label, "is_user_move": mine}
            for i, (phase, label, mine) in enumerate(moves)
        ]
    )


async def test_mistakes_by_phase(client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db) -> None:
    game = await analyzed(test_db, user_id, SICILIAN, "white", "loss", 70.0, 80.0)
    await add_moves(
        test_db,
        user_id,
        game,
        [("opening", "best", True)] * 9
        + [("opening", "inaccuracy", True)]
        + [("middlegame", "blunder", True), ("middlegame", "mistake", True), ("middlegame", "good", True), ("middlegame", "good", True)]
        + [("endgame", "blunder", False)],  # the opponent's: not counted
    )

    body = await get(client, auth_headers, "mistakes")

    assert body["analyzed_games"] == 1
    opening, middlegame, endgame = body["phases"]
    assert (opening["phase"], opening["moves"], opening["inaccuracies"], opening["inaccuracies_per_100"]) == (
        "opening",
        10,
        1,
        10.0,
    )
    assert (middlegame["moves"], middlegame["blunders"], middlegame["mistakes"], middlegame["blunders_per_100"]) == (
        4,
        1,
        1,
        25.0,
    )
    assert (endgame["moves"], endgame["blunders"], endgame["blunders_per_100"]) == (0, 0, None)


async def test_mistakes_only_count_filtered_games(
    client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db
) -> None:
    blitz = await analyzed(test_db, user_id, SICILIAN, "white", "loss", 70.0, 80.0, time_class="blitz")
    rapid = await analyzed(test_db, user_id, SICILIAN, "white", "loss", 70.0, 80.0, time_class="rapid")
    await add_moves(test_db, user_id, blitz, [("opening", "blunder", True)])
    await add_moves(test_db, user_id, rapid, [("opening", "best", True)])

    body = await get(client, auth_headers, "mistakes", time_class="rapid")

    assert body["analyzed_games"] == 1
    assert body["phases"][0]["blunders"] == 0


async def test_phase_is_backfilled_for_older_analysis(
    client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db
) -> None:
    game = await analyzed(test_db, user_id, SICILIAN, "white", "loss", 70.0, 80.0)
    await test_db.positions.insert_one(
        {
            "game_id": game,
            "user_id": user_id,
            "ply": 79,
            "fen": "8/5k2/8/8/8/8/2R2K2/r7 w - - 0 40",
            "classification": "blunder",
            "is_user_move": True,
        }
    )

    body = await get(client, auth_headers, "mistakes")

    assert body["phases"][2]["blunders"] == 1
    assert (await test_db.positions.find_one({"game_id": game}))["phase"] == "endgame"


# --- time of day ---

async def test_results_by_hour_skip_daily_games(
    client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db
) -> None:
    await add(test_db, user_id, SICILIAN, "white", "win", time_class="blitz", played_at=when(1, hour=21))
    await add(test_db, user_id, SICILIAN, "white", "loss", time_class="blitz", played_at=when(2, hour=21))
    await add(test_db, user_id, SICILIAN, "white", "win", time_class="rapid", played_at=when(3, hour=8))
    await add(test_db, user_id, SICILIAN, "white", "loss", time_class="daily", played_at=when(4, hour=8))

    body = await get(client, auth_headers, "time-of-day")

    assert body["timezone"] == "UTC"
    hours = {h["hour"]: h for h in body["hours"]}
    assert len(body["hours"]) == 24
    assert (hours[21]["games"], hours[21]["score"]) == (2, 0.5)
    assert (hours[8]["games"], hours[8]["wins"]) == (1, 1)
    assert hours[3] == {"hour": 3, "games": 0, "wins": 0, "draws": 0, "losses": 0, "score": None}


async def test_hours_follow_the_viewers_timezone(
    client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db
) -> None:
    await add(test_db, user_id, SICILIAN, "white", "win", time_class="blitz", played_at=when(7, hour=3, month=10))

    body = await get(client, auth_headers, "time-of-day", tz="America/New_York")

    assert [h["hour"] for h in body["hours"] if h["games"]] == [23]  # 03:00 UTC = 23:00 EDT


async def test_daily_only_filter_has_no_hours(client: AsyncClient, auth_headers: dict, user_id: ObjectId, test_db) -> None:
    await add(test_db, user_id, SICILIAN, "white", "win", time_class="daily")

    assert (await get(client, auth_headers, "time-of-day", time_class="daily"))["hours"] == []


@pytest.mark.parametrize("tz", ["Not a zone!", "../etc", "x" * 65])
async def test_rejects_malformed_timezones(client: AsyncClient, auth_headers: dict, tz: str) -> None:
    response = await client.get("/insights/time-of-day", params={"tz": tz}, headers=auth_headers)

    assert response.status_code == 422
