from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.training.sm2 import Rating

CardSource = Literal["blunder", "leak"]


class TrainingCard(BaseModel):
    id: str
    source: CardSource
    fen: str
    color: Literal["white", "black"]  # side to move: the user's side
    correct_move: str  # UCI
    correct_move_san: str
    user_move: str  # the move the user usually played
    user_move_san: str
    context: dict[str, Any]
    ease: float
    interval: int
    repetitions: int
    due_at: datetime
    last_reviewed_at: datetime | None
    reviews: int
    lapses: int


class SyncResult(BaseModel):
    created: int
    total: int


class DueCards(BaseModel):
    due: int  # reviews due now + new cards allowed now (the list may be shorter)
    cards: list[TrainingCard]


class ReviewRequest(BaseModel):
    move: str = Field(pattern=r"^[a-h][1-8][a-h][1-8][qrbn]?$")  # UCI
    rating: Rating


class ReviewResult(BaseModel):
    correct: bool
    played_san: str | None
    correct_move_san: str
    card: TrainingCard


class TrainingStats(BaseModel):
    total: int
    due_now: int
    new: int  # never reviewed
    learning: int  # reviewed, interval under 21 days
    mature: int  # interval of 21 days or more
    by_source: dict[str, int]
    reviews_last_24h: int
    accuracy_last_7d: float | None  # share of correct reviews, 0-1
    next_due_at: datetime | None  # next review (new cards wait for the daily allowance)
    new_cards_per_day: int
    new_left_today: int  # new cards that can still be started in the current 24 hours
