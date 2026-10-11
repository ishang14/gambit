import pytest
from httpx import AsyncClient

from app import db


async def _up() -> bool:
    return True


async def _down() -> bool:
    return False


async def test_health_ok_when_services_up(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "ping_mongo", _up)
    monkeypatch.setattr(db, "ping_redis", _up)

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mongo": "up", "redis": "up"}


async def test_health_degraded_when_a_service_is_down(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(db, "ping_mongo", _up)
    monkeypatch.setattr(db, "ping_redis", _down)

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "degraded", "mongo": "up", "redis": "down"}
