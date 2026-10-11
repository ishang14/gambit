import io
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import chess
import chess.pgn

from app.analysis.engine import Engine, EngineResult, normalize_fen
from app.analysis.phase import game_phase
from app.analysis.scoring import (
    Thresholds,
    classify,
    game_accuracies,
    move_accuracy,
    to_centipawns,
    white_win_percent,
    win_percent,
)

ProgressCallback = Callable[[int, int], Awaitable[None]]

CLASSIFICATIONS = ("best", "good", "inaccuracy", "mistake", "blunder")
# Centipawn loss is capped so one missed mate doesn't swamp an average.
CP_LOSS_CAP = 1000


@dataclass
class GameAnalysis:
    positions: list[dict[str, Any]]  # one per move, in order
    accuracy: dict[str, float | None]  # by color
    counts: dict[str, dict[str, int]]  # by color, then classification


async def evaluate(board: chess.Board, engine: Engine, depth: int) -> EngineResult:
    """Evaluate a position, answering finished games without the engine."""
    if board.is_checkmate():
        return EngineResult(evaluation={"cp": None, "mate": 0}, best_move=None)
    if board.is_game_over():  # stalemate, insufficient material, ...
        return EngineResult(evaluation={"cp": 0, "mate": None}, best_move=None)
    return await engine.analyse(board, depth)


def capped_cp(result: EngineResult, white_to_move: bool) -> int:
    cp = to_centipawns(result.evaluation, white_to_move)
    return max(-CP_LOSS_CAP, min(CP_LOSS_CAP, cp))


async def analyze_pgn(
    pgn: str,
    engine: Engine,
    depth: int,
    thresholds: Thresholds,
    on_progress: ProgressCallback | None = None,
) -> GameAnalysis:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None or game.errors:
        raise ValueError("Could not parse the game's PGN")
    moves = list(game.mainline_moves())

    # Engines with a cache can load every position of the game in one go.
    prefetch = getattr(engine, "prefetch", None)
    if prefetch is not None:
        boards, board = [], game.board()
        for move in [None, *moves]:
            if move is not None:
                board.push(move)
            boards.append(board.copy(stack=False))
        await prefetch(boards, depth)

    # Evaluate each position once: the start, then after every move.
    board = game.board()
    results: list[EngineResult] = []
    white_win_percents: list[float] = []
    for index in range(len(moves) + 1):
        results.append(await evaluate(board, engine, depth))
        white_win_percents.append(white_win_percent(results[-1].evaluation, board.turn == chess.WHITE))
        if on_progress is not None:
            await on_progress(index + 1, len(moves) + 1)
        if index < len(moves):
            board.push(moves[index])

    board = game.board()
    positions = []
    for ply, move in enumerate(moves, start=1):
        before, after = results[ply - 1], results[ply]
        white_moved = board.turn == chess.WHITE
        fen, fen_key, phase = board.fen(), normalize_fen(board), game_phase(board, ply)
        san = board.san(move)
        best_san = board.san(chess.Move.from_uci(before.best_move)) if before.best_move else None
        win_before = win_percent(before.evaluation, white_to_move=white_moved, for_white=white_moved)
        cp_before = capped_cp(before, white_moved)

        board.push(move)

        win_after = win_percent(after.evaluation, white_to_move=not white_moved, for_white=white_moved)
        cp_after = capped_cp(after, not white_moved)
        win_chance_loss = max(0.0, win_before - win_after)
        cp_loss = max(0, cp_before - cp_after if white_moved else cp_after - cp_before)

        positions.append(
            {
                "ply": ply,
                "color": "white" if white_moved else "black",
                "fen": fen,
                "fen_key": fen_key,
                "phase": phase,
                "move_played": move.uci(),
                "move_san": san,
                "best_move": before.best_move,
                "best_move_san": best_san,
                "eval_before": before.evaluation,
                "eval_after": after.evaluation,
                "win_chance_loss": round(win_chance_loss, 2),
                "cp_loss": cp_loss,
                "accuracy": round(move_accuracy(win_chance_loss), 1),
                "classification": classify(win_chance_loss, move.uci() == before.best_move, thresholds),
            }
        )

    accuracy = game_accuracies(white_win_percents, [p["color"] for p in positions])
    counts = {}
    for color in ("white", "black"):
        own = [p for p in positions if p["color"] == color]
        counts[color] = {c: sum(p["classification"] == c for p in own) for c in CLASSIFICATIONS}
    return GameAnalysis(positions=positions, accuracy=accuracy, counts=counts)
