from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.config import Settings, get_settings
from app.db import get_db
from app.models.user import LoginRequest, SignupRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


def to_public(user: dict[str, Any]) -> UserPublic:
    return UserPublic(
        id=str(user["_id"]),
        email=user["email"],
        chesscom_username=user.get("chesscom_username"),
        created_at=user["created_at"],
    )


def token_response(user: dict[str, Any], settings: Settings) -> TokenResponse:
    token = create_access_token(str(user["_id"]), settings)
    return TokenResponse(access_token=token, user=to_public(user))


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = {
        "email": body.email.lower(),
        "password_hash": hash_password(body.password),
        "chesscom_username": body.chesscom_username,
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = await db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user["_id"] = result.inserted_id
    return token_response(user, settings)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = await db.users.find_one({"email": body.email.lower()})
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return token_response(user, settings)


@router.get("/me", response_model=UserPublic)
async def me(user: dict[str, Any] = Depends(get_current_user)) -> UserPublic:
    return to_public(user)
