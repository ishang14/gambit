from typing import Any

import pytest
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.games.chesscom import ChessComUnavailable, PlayerNotFound, get_chesscom_client
from app.main import app
from tests.conftest import load_fixture, make_user


class FakeChessCom:
    """Serves the saved chess.com responses instead of calling the real API."""

    def __init__(self) -> None:
        self.error: Exception | None = None
        self.month_requests: list[tuple[str, int, int]] = []

    async def list_archives(self, username: str) -> list[tuple[int, int]]:
        if self.error:
            raise self.error
        return [(2026, 8), (2026, 9), (2026, 10)]

    async def get_month(self, username: str, year: int, month: int) -> list[dict[str, Any]]:
        if self.error:
            raise self.error
        self.month_requests.append((username, year, month))
        if (year, month) == (2026, 9):
            return load_fixture("chesscom/games_2026_09.json")["games"]
        return []


@pytest.fixture
def chesscom() -> FakeChessCom:
    fake = FakeChessCom()
    app.dependency_overrides[get_chesscom_client] = lambda: fake
    return fake


async def import_september(client: AsyncClient, headers: dict[str, str]) -> dict:
    response = await client.post(
        "/games/import", json={"username": "erik", "year": 2026, "month": 9}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


# --- months ---

async def test_months_newest_first(client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom) -> None:
    response = await client.get("/games/import/months", params={"username": "erik"}, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == [
        {"year": 2026, "month": 10},
        {"year": 2026, "month": 9},
        {"year": 2026, "month": 8},
    ]


async def test_months_unknown_player(client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom) -> None:
    chesscom.error = PlayerNotFound()

    response = await client.get("/games/import/months", params={"username": "nobody"}, headers=auth_headers)

    assert response.status_code == 404
    assert "nobody" in response.json()["detail"]


async def test_chesscom_down_returns_502(client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom) -> None:
    chesscom.error = ChessComUnavailable("chess.com is rate limiting requests")

    response = await client.post(
        "/games/import", json={"username": "erik", "year": 2026, "month": 9}, headers=auth_headers
    )

    assert response.status_code == 502
    assert "rate limiting" in response.json()["detail"]


@pytest.mark.parametrize("username", ["../admin", "a b", "x" * 31, "e"])
async def test_rejects_bad_usernames(
    client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom, username: str
) -> None:
    response = await client.get("/games/import/months", params={"username": username}, headers=auth_headers)

    assert response.status_code == 422


# --- import ---

async def test_import_stores_standard_games(
    client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom, test_db: AsyncIOMotorDatabase
) -> None:
    result = await import_september(client, auth_headers)

    assert result == {"year": 2026, "month": 9, "imported": 5, "duplicates": 0, "unsupported": 3}
    assert await test_db.games.count_documents({}) == 5
    stored = await test_db.games.find_one({"source_url": "https://www.chess.com/game/daily/1016260528"})
    assert stored["analysis_status"] == "none"
    assert stored["accuracy"] is None
    assert stored["pgn"].startswith('[Event "Let\'s Play!"]')


async def test_reimport_does_not_duplicate(
    client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom, test_db: AsyncIOMotorDatabase
) -> None:
    await import_september(client, auth_headers)
    result = await import_september(client, auth_headers)

    assert result["imported"] == 0
    assert result["duplicates"] == 5
    assert await test_db.games.count_documents({}) == 5


async def test_same_game_can_belong_to_two_users(
    client: AsyncClient, chesscom: FakeChessCom, test_db: AsyncIOMotorDatabase
) -> None:
    alice = await make_user(client, "alice@example.com")
    bob = await make_user(client, "bob@example.com")

    await import_september(client, alice)
    result = await import_september(client, bob)

    assert result["imported"] == 5
    assert await test_db.games.count_documents({}) == 10


async def test_empty_month(client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom) -> None:
    response = await client.post(
        "/games/import", json={"username": "erik", "year": 2026, "month": 8}, headers=auth_headers
    )

    assert response.json() == {"year": 2026, "month": 8, "imported": 0, "duplicates": 0, "unsupported": 0}


async def test_import_remembers_chesscom_username(
    client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom
) -> None:
    await import_september(client, auth_headers)

    me = await client.get("/auth/me", headers=auth_headers)

    assert me.json()["chesscom_username"] == "erik"


async def test_import_requires_login(client: AsyncClient, chesscom: FakeChessCom) -> None:
    response = await client.post("/games/import", json={"username": "erik", "year": 2026, "month": 9})

    assert response.status_code == 401
    assert chesscom.month_requests == []


# --- list and detail ---

async def test_list_newest_first_without_pgn(client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom) -> None:
    await import_september(client, auth_headers)

    body = (await client.get("/games", headers=auth_headers)).json()

    assert body["total"] == 5
    dates = [game["played_at"] for game in body["items"]]
    assert dates == sorted(dates, reverse=True)
    assert "pgn" not in body["items"][0]


@pytest.mark.parametrize(
    ("params", "expected_total"),
    [
        ({"result": "win"}, 2),
        ({"result": "draw"}, 2),
        ({"result": "loss"}, 1),
        ({"color": "black"}, 2),
        ({"time_class": "rapid"}, 1),
        ({"opening": "pirc"}, 2),
        ({"opening": "Caro Kann"}, 1),
        ({"opening": "no such opening"}, 0),
        ({"result": "win", "color": "black"}, 1),
    ],
)
async def test_list_filters(
    client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom, params: dict, expected_total: int
) -> None:
    await import_september(client, auth_headers)

    body = (await client.get("/games", params=params, headers=auth_headers)).json()

    assert body["total"] == expected_total
    assert len(body["items"]) == expected_total


async def test_list_opening_filter_treats_input_as_text(
    client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom
) -> None:
    await import_september(client, auth_headers)

    body = (await client.get("/games", params={"opening": ".*"}, headers=auth_headers)).json()

    assert body["total"] == 0


async def test_list_pagination(client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom) -> None:
    await import_september(client, auth_headers)

    page1 = (await client.get("/games", params={"limit": 2}, headers=auth_headers)).json()
    page3 = (await client.get("/games", params={"limit": 2, "offset": 4}, headers=auth_headers)).json()

    assert page1["total"] == page3["total"] == 5
    assert len(page1["items"]) == 2
    assert len(page3["items"]) == 1


async def test_users_only_see_their_own_games(client: AsyncClient, chesscom: FakeChessCom) -> None:
    alice = await make_user(client, "alice@example.com")
    bob = await make_user(client, "bob@example.com")
    await import_september(client, alice)

    bob_list = (await client.get("/games", headers=bob)).json()
    alice_game_id = (await client.get("/games", headers=alice)).json()["items"][0]["id"]
    bob_detail = await client.get(f"/games/{alice_game_id}", headers=bob)

    assert bob_list["total"] == 0
    assert bob_detail.status_code == 404


async def test_game_detail_includes_pgn(client: AsyncClient, auth_headers: dict, chesscom: FakeChessCom) -> None:
    await import_september(client, auth_headers)
    game_id = (await client.get("/games", headers=auth_headers)).json()["items"][0]["id"]

    response = await client.get(f"/games/{game_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["pgn"].startswith("[Event")


async def test_game_detail_bad_id(client: AsyncClient, auth_headers: dict) -> None:
    response = await client.get("/games/not-an-id", headers=auth_headers)

    assert response.status_code == 404
