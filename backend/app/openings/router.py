from typing import Any

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.config import Settings, get_settings
from app.db import get_db
from app.models.game import Color
from app.models.opening import OpeningExplorer
from app.openings.service import opening_explorer

router = APIRouter(prefix="/openings", tags=["openings"])


@router.get("", response_model=OpeningExplorer)
async def get_openings(
    color: Color,
    min_games: int = Query(default=2, ge=1, le=100),
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """The user's opening tree as one color (positions keyed by normalized FEN, moves
    played at least `min_games` times) and their ranked opening leaks."""
    return await opening_explorer(db, user["_id"], color, min_games, settings)
