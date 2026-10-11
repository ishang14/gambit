import pytest
from pydantic import ValidationError

from app.config import DEV_JWT_SECRET, Settings


def test_development_allows_the_default_secret() -> None:
    assert Settings(environment="development").jwt_secret == DEV_JWT_SECRET


@pytest.mark.parametrize("secret", [DEV_JWT_SECRET, "too-short"])
def test_production_refuses_weak_secrets(secret: str) -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(environment="production", jwt_secret=secret)


def test_production_accepts_a_long_secret() -> None:
    assert Settings(environment="production", jwt_secret="x" * 40).environment == "production"
