"""ARQ worker entrypoint: `arq worker.WorkerSettings`.

Each worker process keeps one Stockfish process alive and runs one job at a time.
Scale by running more worker containers.
"""

import logging
from typing import Any

import chess.engine
from arq.connections import RedisSettings
from bson import ObjectId

from app import db
from app.analysis.engine import StockfishEngine
from app.analysis.jobs import run_analysis
from app.analysis.queue import ANALYZE_GAME
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
settings = get_settings()


async def startup(ctx: dict[str, Any]) -> None:
    db.connect(settings)
    ctx["db"] = db.get_db()
    engine = StockfishEngine(settings.stockfish_path, settings.engine_threads, settings.engine_hash_mb)
    await engine.start()
    ctx["engine"] = engine


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["engine"].close()
    await db.close()


async def analyze_game(ctx: dict[str, Any], game_id: str, job_id: str) -> None:
    engine: StockfishEngine = ctx["engine"]
    try:
        await run_analysis(ctx["db"], engine, ObjectId(game_id), job_id, settings)
    except chess.engine.EngineTerminatedError:
        # Stockfish died: start a fresh one for the next job.
        await engine.restart()
        raise


# ARQ registers functions by name; the API enqueues by this constant.
assert analyze_game.__name__ == ANALYZE_GAME


class WorkerSettings:
    functions = [analyze_game]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 1
    job_timeout = 600
