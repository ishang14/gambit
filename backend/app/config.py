from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-change-me-please-32-bytes-min"


class Settings(BaseSettings):
    """App settings, read from environment variables (or a local .env file)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "production"] = "development"
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "gambit"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:5173"]

    # Override JWT_SECRET in any real deployment.
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # chess.com asks API clients to identify themselves and not send parallel requests.
    chesscom_user_agent: str = "Gambit/0.1 (personal chess training app)"
    chesscom_request_delay_seconds: float = 1.0

    # Engine analysis
    stockfish_path: str = "stockfish"
    analysis_depth: int = 14
    engine_threads: int = 1
    engine_hash_mb: int = 64

    # Move classification: how many percentage points of win chance a move may
    # lose before it counts as an inaccuracy / mistake / blunder.
    inaccuracy_threshold: float = 5.0
    mistake_threshold: float = 10.0
    blunder_threshold: float = 20.0

    # Opening tree: how many plies of each game count as "the opening".
    opening_plies: int = 20
    # A leak is a position you reached at least `leak_min_occurrences` times where you
    # played the same move at least `leak_min_move_games` times and either scored at
    # most `leak_max_score` with it (needs `leak_min_occurrences` games with the move)
    # or lost on average at least `leak_min_eval_loss` points of win chance.
    leak_min_occurrences: int = 3
    leak_min_move_games: int = 2
    leak_max_score: float = 0.35
    leak_min_eval_loss: float = 8.0

    # Training: at most this many never-seen cards are introduced per 24 hours, so a big
    # batch of analyzed games doesn't bury the reviews that are actually due.
    training_new_cards_per_day: int = 20


    @model_validator(mode="after")
    def production_needs_a_real_secret(self) -> "Settings":
        if self.environment == "production" and (self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < 32):
            raise ValueError("In production, set JWT_SECRET to a random string of at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
