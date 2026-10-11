from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# bcrypt only looks at the first 72 bytes of a password.
MAX_PASSWORD_BYTES = 72


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    chesscom_username: str | None = Field(default=None, max_length=50)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    chesscom_username: str | None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
