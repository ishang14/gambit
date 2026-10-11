import time

import httpx
import pytest

from app.games.chesscom import ChessComClient, ChessComUnavailable, PlayerNotFound
from tests.conftest import load_fixture


def client_with(handler, delay: float = 0) -> ChessComClient:
    return ChessComClient("Gambit-test/1.0", delay, transport=httpx.MockTransport(handler))


async def test_list_archives_parses_months_and_sends_user_agent() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=load_fixture("chesscom/archives.json"))

    client = client_with(handler)
    months = await client.list_archives("Erik")

    assert months == [(2026, 8), (2026, 9), (2026, 10)]
    assert seen[0].url.path == "/pub/player/erik/games/archives"
    assert seen[0].headers["User-Agent"] == "Gambit-test/1.0"


async def test_get_month_uses_zero_padded_month() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/pub/player/erik/games/2026/09"
        return httpx.Response(200, json=load_fixture("chesscom/games_2026_09.json"))

    games = await client_with(handler).get_month("erik", 2026, 9)

    assert len(games) == 8


async def test_unknown_player_raises_player_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json=load_fixture("chesscom/player_not_found.json"))

    with pytest.raises(PlayerNotFound):
        await client_with(handler).list_archives("nobody")


@pytest.mark.parametrize("status", [429, 500, 503])
async def test_error_statuses_raise_unavailable(status: int) -> None:
    client = client_with(lambda request: httpx.Response(status))

    with pytest.raises(ChessComUnavailable):
        await client.list_archives("erik")


async def test_network_error_raises_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with pytest.raises(ChessComUnavailable):
        await client_with(handler).list_archives("erik")


async def test_requests_are_spaced_by_the_delay() -> None:
    sent_at: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_at.append(time.monotonic())
        return httpx.Response(200, json={"games": []})

    client = client_with(handler, delay=0.2)
    for month in (1, 2, 3):
        await client.get_month("erik", 2026, month)

    gaps = [later - earlier for earlier, later in zip(sent_at, sent_at[1:])]
    assert all(gap >= 0.19 for gap in gaps), gaps
