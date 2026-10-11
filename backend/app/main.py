import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.analysis.queue import close_queue, connect_queue
from app.analysis.router import router as analysis_router
from app.auth.router import router as auth_router
from app.config import get_settings
from app.games.chesscom import close_chesscom_client
from app.games.router import router as games_router
from app.insights.router import router as insights_router
from app.openings.book import load_book
from app.openings.router import router as openings_router
from app.training.router import router as training_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db.connect(get_settings())
    await db.ensure_indexes(db.get_db())
    await connect_queue(get_settings())
    # Parsing the opening book takes a couple of seconds; do it before anyone asks.
    warm_book = asyncio.create_task(asyncio.to_thread(load_book))
    yield
    warm_book.cancel()
    await close_queue()
    await close_chesscom_client()
    await db.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Gambit API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(games_router)
    app.include_router(analysis_router)
    app.include_router(openings_router)
    app.include_router(training_router)
    app.include_router(insights_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        mongo_ok = await db.ping_mongo()
        redis_ok = await db.ping_redis()
        return {
            "status": "ok" if mongo_ok and redis_ok else "degraded",
            "mongo": "up" if mongo_ok else "down",
            "redis": "up" if redis_ok else "down",
        }

    return app


app = create_app()
