from datetime import datetime, timedelta, timezone

import jwt
from bson import ObjectId
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.security import create_access_token, hash_password, verify_password
from app.config import get_settings

EMAIL = "player@example.com"
PASSWORD = "correct-horse-battery"


async def signup(client: AsyncClient, email: str = EMAIL, password: str = PASSWORD) -> dict:
    response = await client.post(
        "/auth/signup",
        json={"email": email, "password": password, "chesscom_username": "hikaru"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- password hashing ---

def test_hash_password_round_trip() -> None:
    hashed = hash_password(PASSWORD)
    assert hashed != PASSWORD
    assert verify_password(PASSWORD, hashed)
    assert not verify_password("wrong-password", hashed)


# --- signup ---

async def test_signup_returns_token_and_user(client: AsyncClient) -> None:
    body = await signup(client)

    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == EMAIL
    assert body["user"]["chesscom_username"] == "hikaru"
    assert "password_hash" not in body["user"]


async def test_signup_stores_hashed_password(client: AsyncClient, test_db: AsyncIOMotorDatabase) -> None:
    await signup(client)

    user = await test_db.users.find_one({"email": EMAIL})
    assert user is not None
    assert user["password_hash"] != PASSWORD
    assert verify_password(PASSWORD, user["password_hash"])


async def test_signup_rejects_duplicate_email_case_insensitively(client: AsyncClient) -> None:
    await signup(client)

    response = await client.post("/auth/signup", json={"email": EMAIL.upper(), "password": PASSWORD})

    assert response.status_code == 409


async def test_signup_validates_input(client: AsyncClient) -> None:
    bad_email = await client.post("/auth/signup", json={"email": "not-an-email", "password": PASSWORD})
    short_password = await client.post("/auth/signup", json={"email": EMAIL, "password": "short"})
    long_password = await client.post("/auth/signup", json={"email": EMAIL, "password": "x" * 73})

    assert bad_email.status_code == 422
    assert short_password.status_code == 422
    assert long_password.status_code == 422


# --- login ---

async def test_login_with_correct_credentials(client: AsyncClient) -> None:
    await signup(client)

    response = await client.post("/auth/login", json={"email": EMAIL.upper(), "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == EMAIL


async def test_login_with_wrong_password_or_unknown_email(client: AsyncClient) -> None:
    await signup(client)

    wrong_password = await client.post("/auth/login", json={"email": EMAIL, "password": "nope-nope-nope"})
    unknown_email = await client.post("/auth/login", json={"email": "who@example.com", "password": PASSWORD})

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # Same message either way, so the API doesn't reveal which emails exist.
    assert wrong_password.json() == unknown_email.json()


# --- /auth/me ---

async def test_me_returns_current_user(client: AsyncClient) -> None:
    token = (await signup(client))["access_token"]

    response = await client.get("/auth/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


async def test_me_requires_token(client: AsyncClient) -> None:
    response = await client.get("/auth/me")

    assert response.status_code == 401


async def test_me_rejects_bad_tokens(client: AsyncClient) -> None:
    await signup(client)
    settings = get_settings()
    expired = jwt.encode(
        {"sub": str(ObjectId()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    wrong_secret = jwt.encode({"sub": str(ObjectId())}, "some-other-secret-that-is-long-enough", algorithm="HS256")
    deleted_user = create_access_token(str(ObjectId()), settings)
    not_an_object_id = create_access_token("not-an-id", settings)

    for token in ["garbage", expired, wrong_secret, deleted_user, not_an_object_id]:
        response = await client.get("/auth/me", headers=bearer(token))
        assert response.status_code == 401, token
