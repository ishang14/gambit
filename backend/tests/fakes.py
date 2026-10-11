import chess

from app.analysis.engine import EngineResult, normalize_fen
from app.analysis.scoring import Evaluation

# Scholar's mate, with a weak 2. Qh5 and the losing 3...Nf6.
SCHOLARS_MATE_PGN = """[Event "Test"]
[White "hero"]
[Black "villain"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
"""

# White eval and engine best move for each position before a move, in order.
SCHOLARS_MATE_SCRIPT: list[tuple[Evaluation, str]] = [
    ({"cp": 30, "mate": None}, "e2e4"),  # start           -> 1. e4 (best)
    ({"cp": 30, "mate": None}, "e7e5"),  # after 1. e4     -> 1... e5 (best)
    ({"cp": 30, "mate": None}, "g1f3"),  # after 1... e5   -> 2. Qh5 (not best, small loss)
    ({"cp": -20, "mate": None}, "b8c6"),  # after 2. Qh5   -> 2... Nc6 (best)
    ({"cp": -20, "mate": None}, "f1c4"),  # after 2... Nc6 -> 3. Bc4 (best)
    ({"cp": -10, "mate": None}, "g7g6"),  # after 3. Bc4   -> 3... Nf6?? (blunder)
    ({"cp": None, "mate": 1}, "h5f7"),  # after 3... Nf6   -> 4. Qxf7# (best)
]


def scholars_mate_engine() -> "ScriptedEngine":
    board = chess.Board()
    script = {}
    for (evaluation, best), move in zip(SCHOLARS_MATE_SCRIPT, ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"]):
        script[normalize_fen(board)] = EngineResult(evaluation=evaluation, best_move=best)
        board.push_san(move)
    return ScriptedEngine(script)


class ScriptedEngine:
    """Returns pre-set results by position; unknown positions get 0.00 and the first legal move."""

    def __init__(self, script: dict[str, EngineResult] | None = None) -> None:
        self.script = script or {}
        self.calls: list[tuple[str, int]] = []

    async def analyse(self, board: chess.Board, depth: int) -> EngineResult:
        key = normalize_fen(board)
        self.calls.append((key, depth))
        if key in self.script:
            return self.script[key]
        first = min(board.legal_moves, key=lambda m: m.uci())
        return EngineResult(evaluation={"cp": 0, "mate": None}, best_move=first.uci())


class BrokenEngine:
    async def analyse(self, board: chess.Board, depth: int) -> EngineResult:
        raise RuntimeError("engine crashed")
