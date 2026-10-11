from typing import Any

import chess
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analysis.engine import normalize_fen
from app.config import Settings
from tests.conftest import make_user, user_id_for
from tests.helpers import add_games, analyze, blunder_engine, key_after

ROOT = normalize_fen(chess.Board())


# As White: 2. Qh5 three times, all lost; 2. Nf3 twice, both won. One game as Black.
GAMES = [
    ("1. e4 e5 2. Qh5 Nc6 3. Bc4 g6", "white", "loss"),
    ("1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6", "white", "loss"),
    ("1. e4 e5 2. Qh5 Nf6", "white", "loss"),
    ("1. e4 e5 2. Nf3 Nc6 3. Bb5", "white", "win"),
    ("1. e4 e5 2. Nf3 d6", "white", "win"),
    ("1. d4 d5 2. c4", "black", "draw"),
]


async def get_openings(client: AsyncClient, headers: dict, **params: Any) -> dict:
    response = await client.get("/openings", params={"color": "white", **params}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_tree_and_leaks(client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase) -> None:
    await add_games(test_db, await user_id_for(client, auth_headers), GAMES)

    body = await get_openings(client, auth_headers)

    assert body["color"] == "white"
    assert body["root"] == ROOT
    assert body["games"] == 5
    root = body["positions"][ROOT]
    assert root["games"] == 5
    assert [(m["san"], m["games"]) for m in root["moves"]] == [("e4", 5)]
    after_e5 = body["positions"][key_after("e4", "e5")]
    assert [(m["san"], m["games"], m["score"]) for m in after_e5["moves"]] == [("Qh5", 3, 0.0), ("Nf3", 2, 1.0)]
    assert after_e5["user_to_move"] is True

    assert len(body["leaks"]) == 1
    leak = body["leaks"][0]
    assert (leak["move_san"], leak["games"], leak["position_games"]) == ("Qh5", 3, 5)
    assert leak["reasons"] == ["poor_results"]
    assert [step["san"] for step in leak["path"]] == ["e4", "e5"]
    assert leak["example_game_id"] is not None


async def test_min_games_prunes_the_tree(client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase) -> None:
    await add_games(test_db, await user_id_for(client, auth_headers), GAMES)

    default = await get_openings(client, auth_headers)
    everything = await get_openings(client, auth_headers, min_games=1)

    after_nf3_nc6 = key_after("e4", "e5", "Nf3", "Nc6")
    assert after_nf3_nc6 not in default["positions"]  # 3. Bb5 was played once
    assert after_nf3_nc6 in everything["positions"]


async def test_black_tree_only_has_black_games(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    await add_games(test_db, await user_id_for(client, auth_headers), GAMES)

    body = await get_openings(client, auth_headers, color="black", min_games=1)

    assert body["games"] == 1
    assert [m["san"] for m in body["positions"][ROOT]["moves"]] == ["d4"]
    assert body["positions"][ROOT]["user_to_move"] is False


async def test_only_the_opening_is_indexed(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    long_game = " ".join(f"{n}. Nf3 Nf6 {n + 1}. Ng1 Ng8" for n in range(1, 30, 2))
    await add_games(test_db, await user_id_for(client, auth_headers), [(long_game, "white", "draw")])

    await get_openings(client, auth_headers)

    assert await test_db.opening_moves.count_documents({}) == Settings().opening_plies


async def test_indexing_is_lazy_and_idempotent(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    user_id = await user_id_for(client, auth_headers)
    await add_games(test_db, user_id, GAMES[:2])
    await get_openings(client, auth_headers)
    first_count = await test_db.opening_moves.count_documents({})

    await get_openings(client, auth_headers)
    await add_games(test_db, user_id, [("1. e4 c5", "white", "win")])
    body = await get_openings(client, auth_headers, min_games=1)

    assert await test_db.opening_moves.count_documents({}) == first_count + 2
    assert [m["san"] for m in body["positions"][key_after("e4")]["moves"]] == ["e5", "c5"]


async def test_users_only_see_their_own_openings(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    await add_games(test_db, await user_id_for(client, auth_headers), GAMES)
    other = await make_user(client, "other@example.com")

    body = await get_openings(client, other)

    assert body["games"] == 0
    assert body["positions"][ROOT]["moves"] == []
    assert body["leaks"] == []


async def test_requires_login_and_valid_color(client: AsyncClient, auth_headers: dict) -> None:
    assert (await client.get("/openings", params={"color": "white"})).status_code == 401
    assert (await client.get("/openings", params={"color": "green"}, headers=auth_headers)).status_code == 422


# --- engine analysis feeds the tree ---

WINNING_KE2 = [("1. e4 e5 2. Ke2 Nc6", "white", "win")] * 2 + [("1. e4 e5 2. Nf3", "white", "win")]


async def test_analysis_after_indexing_creates_eval_leak(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    ids = await add_games(test_db, await user_id_for(client, auth_headers), WINNING_KE2)
    assert (await get_openings(client, auth_headers))["leaks"] == []  # won both, no analysis yet

    for game_id in ids[:2]:
        await analyze(test_db, game_id, blunder_engine(("e4", "e5"), "e1e2"))
    body = await get_openings(client, auth_headers)

    assert [(l["move_san"], l["reasons"], l["analyzed"]) for l in body["leaks"]] == [("Ke2", ["eval_loss"], 2)]
    assert body["leaks"][0]["best_move_san"] == "Nf3"
    ke2 = body["positions"][key_after("e4", "e5")]["moves"][0]
    assert ke2["analyzed"] == 2
    assert ke2["avg_win_chance_loss"] > 8


async def test_analysis_before_indexing_is_picked_up(
    client: AsyncClient, auth_headers: dict, test_db: AsyncIOMotorDatabase
) -> None:
    ids = await add_games(test_db, await user_id_for(client, auth_headers), WINNING_KE2)
    for game_id in ids[:2]:
        await analyze(test_db, game_id, blunder_engine(("e4", "e5"), "e1e2"))

    body = await get_openings(client, auth_headers)

    assert [l["move_san"] for l in body["leaks"]] == ["Ke2"]
