"""Enqueueing analysis jobs on ARQ (Redis). The worker side lives in worker.py."""

from typing import Protocol

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import Settings

ANALYZE_GAME = "analyze_game"


class AnalysisQueue(Protocol):
    async def enqueue_analysis(self, game_id: str, job_id: str) -> None: ...


class ArqAnalysisQueue:
    def __init__(self, pool: ArqRedis) -> None:
        self._pool = pool

    async def enqueue_analysis(self, game_id: str, job_id: str) -> None:
        # _job_id makes ARQ ignore a duplicate enqueue of the same job.
        await self._pool.enqueue_job(ANALYZE_GAME, game_id, job_id, _job_id=job_id)


_queue: ArqAnalysisQueue | None = None
_pool: ArqRedis | None = None


async def connect_queue(settings: Settings) -> None:
    global _queue, _pool
    _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    _queue = ArqAnalysisQueue(_pool)


async def close_queue() -> None:
    global _queue, _pool
    if _pool is not None:
        await _pool.aclose()
    _queue, _pool = None, None


def get_analysis_queue() -> AnalysisQueue:
    """FastAPI dependency. Tests override this with an in-memory fake."""
    if _queue is None:
        raise RuntimeError("Analysis queue not connected")
    return _queue
