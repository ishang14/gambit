from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# chess.com usernames: letters, digits, underscores and hyphens.
CHESSCOM_USERNAME_PATTERN = r"^[A-Za-z0-9_-]{2,30}$"

Color = Literal["white", "black"]
UserResult = Literal["win", "loss", "draw"]
TimeClass = Literal["bullet", "blitz", "rapid", "daily"]
AnalysisStatus = Literal["none", "queued", "running", "done", "failed"]


class ImportRequest(BaseModel):
    username: str = Field(pattern=CHESSCOM_USERNAME_PATTERN)
    year: int = Field(ge=2005, le=2100)
    month: int = Field(ge=1, le=12)


class ImportResult(BaseModel):
    year: int
    month: int
    imported: int
    duplicates: int
    unsupported: int


class ArchiveMonth(BaseModel):
    year: int
    month: int


class GameSummary(BaseModel):
    id: str
    source_url: str
    white: str
    black: str
    white_rating: int | None
    black_rating: int | None
    user_color: Color
    user_rating: int | None
    opponent: str
    opponent_rating: int | None
    result: str
    user_result: UserResult
    time_control: str | None
    time_class: str | None
    rated: bool | None
    played_at: datetime
    eco: str | None
    opening: str | None
    ply_count: int
    analysis_status: AnalysisStatus
    analysis_job_id: str | None = None
    analysis_progress: float | None = None
    accuracy: float | None
    opponent_accuracy: float | None = None


class GameDetail(GameSummary):
    pgn: str


class GameListResponse(BaseModel):
    items: list[GameSummary]
    total: int
