from pydantic import BaseModel

from app.models.game import AnalysisStatus


class EvaluationOut(BaseModel):
    cp: int | None
    mate: int | None


class AnalysisJob(BaseModel):
    job_id: str
    game_id: str
    status: AnalysisStatus
    progress: float
    error: str | None = None


class QueueAllResult(BaseModel):
    queued: int


class AnalyzedMove(BaseModel):
    ply: int
    color: str
    fen: str
    move_played: str
    move_san: str
    best_move: str | None
    best_move_san: str | None
    eval_before: EvaluationOut
    eval_after: EvaluationOut
    win_chance_loss: float
    cp_loss: int
    accuracy: float
    classification: str


class GameAnalysisOut(BaseModel):
    game_id: str
    depth: int
    accuracy: dict[str, float | None]
    counts: dict[str, dict[str, int]]
    moves: list[AnalyzedMove]
