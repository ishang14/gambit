from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.games import service
from app.games.chesscom import ChessComClient, ChessComUnavailable, PlayerNotFound, get_chesscom_client
from app.models.game import (
    CHESSCOM_USERNAME_PATTERN,
    ArchiveMonth,
    Color,
    GameDetail,
    GameListResponse,
    ImportRequest,
    ImportResult,
    TimeClass,
    UserResult,
)

router = APIRouter(prefix="/games", tags=["games"])


def chesscom_error(exc: Exception, username: str) -> HTTPException:
    if isinstance(exc, PlayerNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, f"chess.com player '{username}' not found")
    return HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc))


@router.get("/import/months", response_model=list[ArchiveMonth])
async def import_months(
    username: str = Query(pattern=CHESSCOM_USERNAME_PATTERN),
    user: dict[str, Any] = Depends(get_current_user),
    chesscom: ChessComClient = Depends(get_chesscom_client),
) -> list[ArchiveMonth]:
    """Months that have games on chess.com for this player, newest first."""
    try:
        months = await chesscom.list_archives(username)
    except (PlayerNotFound, ChessComUnavailable) as exc:
        raise chesscom_error(exc, username)
    return [ArchiveMonth(year=y, month=m) for y, m in reversed(months)]


@router.post("/import", response_model=ImportResult)
async def import_month(
    body: ImportRequest,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
    chesscom: ChessComClient = Depends(get_chesscom_client),
) -> ImportResult:
    """Import one month of games. The client calls this once per month, in order."""
    try:
        raw_games = await chesscom.get_month(body.username, body.year, body.month)
    except (PlayerNotFound, ChessComUnavailable) as exc:
        raise chesscom_error(exc, body.username)

    result = await service.store_month(db, user["_id"], body.username, body.year, body.month, raw_games)
    if not user.get("chesscom_username"):
        await db.users.update_one({"_id": user["_id"]}, {"$set": {"chesscom_username": body.username}})
    return result


@router.get("", response_model=GameListResponse)
async def list_games(
    result: UserResult | None = None,
    color: Color | None = None,
    time_class: TimeClass | None = None,
    opening: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> GameListResponse:
    query = service.build_filter(user["_id"], result, color, time_class, opening)
    items, total = await service.list_games(db, query, limit, offset)
    return GameListResponse(items=items, total=total)


@router.get("/{game_id}", response_model=GameDetail)
async def get_game(
    game_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> GameDetail:
    game = await service.get_game(db, user["_id"], game_id)
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found")
    return game
