from typing import Literal

from pydantic import BaseModel

LeakReason = Literal["poor_results", "eval_loss"]


class MoveStats(BaseModel):
    uci: str
    san: str
    next: str  # normalized FEN after the move
    games: int
    wins: int
    draws: int
    losses: int
    score: float  # user's points per game, 0-1
    analyzed: int  # games with engine analysis for this move
    avg_win_chance_loss: float | None
    avg_cp_loss: int | None
    best_move_san: str | None
    in_book: bool
    leaves_book: bool
    is_leak: bool


class PositionNode(BaseModel):
    fen: str
    games: int
    user_to_move: bool
    in_book: bool
    name: str | None
    moves: list[MoveStats]


class PathStep(BaseModel):
    san: str
    uci: str
    fen_key: str  # position after this move


class Leak(BaseModel):
    fen_key: str
    fen: str
    path: list[PathStep]  # moves from the start position to the leak position
    opening_name: str | None
    move_uci: str
    move_san: str
    games: int
    position_games: int
    wins: int
    draws: int
    losses: int
    score: float
    analyzed: int
    avg_win_chance_loss: float | None
    best_move_uci: str | None
    best_move_san: str | None
    reasons: list[LeakReason]
    impact: float
    example_game_id: str | None


class OpeningExplorer(BaseModel):
    color: Literal["white", "black"]
    root: str
    games: int
    opening_plies: int
    positions: dict[str, PositionNode]  # keyed by normalized FEN
    leaks: list[Leak]
