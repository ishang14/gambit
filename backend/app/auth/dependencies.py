from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.security import decode_access_token
from app.config import Settings, get_settings
from app.db import get_db

_bearer = HTTPBearer(auto_error=False)

_unauthorized = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncIOMotorDatabase = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Resolve the user from the Bearer token, or raise 401."""
    if credentials is None:
        raise _unauthorized
    user_id = decode_access_token(credentials.credentials, settings)
    if user_id is None:
        raise _unauthorized
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except InvalidId:
        raise _unauthorized
    if user is None:
        raise _unauthorized
    return user
