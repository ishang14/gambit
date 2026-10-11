"""Client for the chess.com public API (https://www.chess.com/news/view/published-data-api)."""

import asyncio
import time
from typing import Any

import httpx

from app.config import get_settings


class PlayerNotFound(Exception):
    pass


class ChessComUnavailable(Exception):
    pass


class ChessComClient:
    BASE_URL = "https://api.chess.com/pub"

    def __init__(
        self,
        user_agent: str,
        delay_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=20,
            transport=transport,
        )
        self._delay = delay_seconds
        # One request at a time, spaced by at least `delay_seconds`.
        self._lock = asyncio.Lock()
        self._last_request = float("-inf")

    async def close(self) -> None:
        await self._http.aclose()

    async def list_archives(self, username: str) -> list[tuple[int, int]]:
        """Months with games for this player, as (year, month), oldest first."""
        data = await self._get(f"/player/{username.lower()}/games/archives")
        months = []
        for url in data.get("archives", []):
            year, month = url.rstrip("/").split("/")[-2:]
            months.append((int(year), int(month)))
        return months

    async def get_month(self, username: str, year: int, month: int) -> list[dict[str, Any]]:
        data = await self._get(f"/player/{username.lower()}/games/{year}/{month:02d}")
        return data.get("games", [])

    async def _get(self, path: str) -> dict[str, Any]:
        async with self._lock:
            wait = self._last_request + self._delay - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                response = await self._http.get(path)
            except httpx.HTTPError as exc:
                raise ChessComUnavailable("Could not reach chess.com") from exc
            finally:
                self._last_request = time.monotonic()

        if response.status_code == 404:
            raise PlayerNotFound()
        if response.status_code == 429:
            raise ChessComUnavailable("chess.com is rate limiting requests; try again in a minute")
        if response.status_code != 200:
            raise ChessComUnavailable(f"chess.com returned an error ({response.status_code})")
        return response.json()


_client: ChessComClient | None = None


def get_chesscom_client() -> ChessComClient:
    """FastAPI dependency: one shared client, so the request spacing applies app-wide."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = ChessComClient(settings.chesscom_user_agent, settings.chesscom_request_delay_seconds)
    return _client


async def close_chesscom_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
