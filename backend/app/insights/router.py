from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import OperationFailure

from app.auth.dependencies import get_current_user
from app.config import Settings, get_settings
from app.db import get_db
from app.insights import service
from app.models.game import TimeClass
from app.models.insights import AccuracyTrend, MistakesInsight, OpeningsInsight, Summary, TimeOfDayInsight
from app.openings.indexer import index_user_games

router = APIRouter(prefix="/insights", tags=["insights"])

# IANA zone names like "UTC" or "America/Argentina/Buenos_Aires". MongoDB rejects unknown
# zones itself; this only keeps arbitrary strings out of the pipeline.
TIMEZONE_PATTERN = r"^[A-Za-z][A-Za-z0-9_+\-]*(/[A-Za-z0-9_+\-]+)*$"


@dataclass
class Filters:
    user_id: Any
    match: dict[str, Any]
    tz: str


def filters(
    time_class: TimeClass | None = None,
    since: date | None = Query(default=None, description="Only games from this date (UTC) on"),
    tz: str = Query(default="UTC", max_length=64, pattern=TIMEZONE_PATTERN),
    user: dict[str, Any] = Depends(get_current_user),
) -> Filters:
    """The filters every insight shares, so all charts describe the same games."""
    return Filters(user["_id"], service.game_filter(user["_id"], time_class, since), tz)


async def with_timezone(coroutine):
    try:
        return await coroutine
    except OperationFailure as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown timezone") from exc


@router.get("/summary", response_model=Summary)
async def summary(f: Filters = Depends(filters), db: AsyncIOMotorDatabase = Depends(get_db)) -> dict[str, Any]:
    return await service.summary(db, f.match)


@router.get("/openings", response_model=OpeningsInsight)
async def openings(
    limit: int = Query(default=8, ge=1, le=20),
    f: Filters = Depends(filters),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    await index_user_games(db, f.user_id, settings.opening_plies)  # names each game's opening
    return await service.openings(db, f.match, limit)


@router.get("/accuracy", response_model=AccuracyTrend)
async def accuracy(
    bucket: Literal["week", "month"] = "week",
    f: Filters = Depends(filters),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> dict[str, Any]:
    points = await with_timezone(service.accuracy_trend(db, f.match, bucket, f.tz))
    return {"bucket": bucket, "points": points}


@router.get("/mistakes", response_model=MistakesInsight)
async def mistakes(f: Filters = Depends(filters), db: AsyncIOMotorDatabase = Depends(get_db)) -> dict[str, Any]:
    return await service.mistakes(db, f.match, f.user_id)


@router.get("/time-of-day", response_model=TimeOfDayInsight)
async def time_of_day(f: Filters = Depends(filters), db: AsyncIOMotorDatabase = Depends(get_db)) -> dict[str, Any]:
    hours = await with_timezone(service.time_of_day(db, f.match, f.tz))
    return {"timezone": f.tz, "hours": hours}
