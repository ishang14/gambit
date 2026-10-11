from typing import Literal

from pydantic import BaseModel

Phase = Literal["opening", "middlegame", "endgame"]


class Results(BaseModel):
    games: int
    wins: int
    draws: int
    losses: int
    score: float | None  # points per game from your side, 0-1


class Summary(Results):
    by_color: dict[str, Results]
    analyzed_games: int
    avg_accuracy: float | None
    inaccuracies_per_game: float | None
    mistakes_per_game: float | None
    blunders_per_game: float | None


class OpeningResults(Results):
    opening: str
    avg_accuracy: float | None


class OpeningsInsight(BaseModel):
    white: list[OpeningResults]
    black: list[OpeningResults]


class AccuracyPoint(BaseModel):
    period: str  # "2026-W41" (ISO week) or "2026-10" (month)
    games: int
    accuracy: float | None
    opponent_accuracy: float | None


class AccuracyTrend(BaseModel):
    bucket: Literal["week", "month"]
    points: list[AccuracyPoint]


class PhaseMistakes(BaseModel):
    phase: Phase
    moves: int
    inaccuracies: int
    mistakes: int
    blunders: int
    inaccuracies_per_100: float | None
    mistakes_per_100: float | None
    blunders_per_100: float | None


class MistakesInsight(BaseModel):
    analyzed_games: int
    phases: list[PhaseMistakes]


class HourResults(Results):
    hour: int  # 0-23 in the requested timezone


class TimeOfDayInsight(BaseModel):
    timezone: str
    hours: list[HourResults]
