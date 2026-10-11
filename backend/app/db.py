from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.config import Settings, get_settings

_mongo_client: AsyncIOMotorClient | None = None
_redis: Redis | None = None


def connect(settings: Settings) -> None:
    """Create the MongoDB and Redis clients. Neither connects until first use."""
    global _mongo_client, _redis
    # tz_aware: return datetimes as UTC-aware, so the API serializes them with an offset.
    _mongo_client = AsyncIOMotorClient(
        settings.mongo_url, serverSelectionTimeoutMS=2000, tz_aware=True
    )
    _redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2)


async def close() -> None:
    global _mongo_client, _redis
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency for the app database. Tests override this."""
    if _mongo_client is None:
        raise RuntimeError("Database not connected")
    return _mongo_client[get_settings().mongo_db]


def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis not connected")
    return _redis


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index("email", unique=True)
    # One copy of each game per user; also serves "this user's games" lookups.
    await db.games.create_index([("user_id", 1), ("source_url", 1)], unique=True)
    await db.games.create_index([("user_id", 1), ("played_at", -1)])
    await db.games.create_index("analysis_job_id", sparse=True)
    await db.positions.create_index([("game_id", 1), ("ply", 1)])
    await db.positions.create_index([("user_id", 1), ("fen_key", 1)])
    await db.positions.create_index([("game_id", 1), ("is_user_move", 1)])
    await db.analysis_cache.create_index([("fen", 1), ("depth", 1)], unique=True)
    await db.opening_moves.create_index([("user_id", 1), ("user_color", 1), ("fen_key", 1)])
    await db.opening_moves.create_index([("game_id", 1), ("ply", 1)], unique=True)
    await db.training_cards.create_index([("user_id", 1), ("due_at", 1)])
    await db.training_cards.create_index([("user_id", 1), ("fen_key", 1), ("user_move", 1)], unique=True)
    await db.training_reviews.create_index([("user_id", 1), ("reviewed_at", -1)])


async def ping_mongo() -> bool:
    try:
        if _mongo_client is None:
            return False
        await _mongo_client.admin.command("ping")
        return True
    except Exception:
        return False


async def ping_redis() -> bool:
    try:
        if _redis is None:
            return False
        return bool(await _redis.ping())
    except Exception:
        return False
