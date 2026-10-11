"""Evaluation maths: win chances, move classification and accuracy.

Evaluations are stored from White's point of view as {"cp": int | None, "mate": int | None}:
  - cp: centipawns (+100 = White is a pawn up)
  - mate: moves to mate (+3 = White mates in 3, -2 = Black mates in 2).
    mate == 0 means the side to move is checkmated (Stockfish's convention).

Win chance uses the same logistic curve as Lichess, so losing 100cp in an equal
position costs far more than losing 100cp when already a rook up.
"""

import math
import statistics
from dataclasses import dataclass
from typing import Literal, TypedDict


class Evaluation(TypedDict):
    cp: int | None
    mate: int | None


Classification = Literal["best", "good", "inaccuracy", "mistake", "blunder"]

# Converts mate scores into centipawns when a single number is needed (e.g. cp loss).
MATE_CP = 10_000


@dataclass(frozen=True)
class Thresholds:
    inaccuracy: float = 5.0
    mistake: float = 10.0
    blunder: float = 20.0


def white_win_percent(evaluation: Evaluation, white_to_move: bool) -> float:
    """White's winning chances, 0-100."""
    mate = evaluation["mate"]
    if mate is not None:
        if mate == 0:
            return 0.0 if white_to_move else 100.0
        return 100.0 if mate > 0 else 0.0
    cp = max(-MATE_CP, min(MATE_CP, evaluation["cp"] or 0))
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)


def win_percent(evaluation: Evaluation, white_to_move: bool, for_white: bool) -> float:
    white = white_win_percent(evaluation, white_to_move)
    return white if for_white else 100 - white


def to_centipawns(evaluation: Evaluation, white_to_move: bool) -> int:
    """White-POV centipawns, with mates mapped to +/-MATE_CP."""
    mate = evaluation["mate"]
    if mate is None:
        return evaluation["cp"] or 0
    if mate == 0:
        return -MATE_CP if white_to_move else MATE_CP
    return MATE_CP if mate > 0 else -MATE_CP


def move_accuracy(win_chance_loss: float) -> float:
    """Per-move accuracy 0-100 from lost win chance (Lichess's formula)."""
    raw = 103.1668 * math.exp(-0.04354 * win_chance_loss) - 3.1669
    return max(0.0, min(100.0, raw))


def classify(win_chance_loss: float, played_best: bool, thresholds: Thresholds) -> Classification:
    if played_best:
        return "best"
    if win_chance_loss >= thresholds.blunder:
        return "blunder"
    if win_chance_loss >= thresholds.mistake:
        return "mistake"
    if win_chance_loss >= thresholds.inaccuracy:
        return "inaccuracy"
    return "good"


def game_accuracies(white_win_percents: list[float], movers: list[str]) -> dict[str, float | None]:
    """Each side's accuracy for the game, the way Lichess computes it.

    A plain average of move accuracies runs high, because most moves in a game are
    easy (forced recaptures, quiet positions). Lichess combines two means instead:
      - a volatility-weighted mean: each move is weighted by how much the win chance
        was swinging around it (standard deviation over a sliding window), so moves
        in sharp positions count more than moves in dead ones;
      - a harmonic mean, which a few very bad moves drag down hard.
    The result is their average.

    `white_win_percents` has White's win chance for every position (start, then after
    each move); `movers[i]` is the color that played move i.
    """
    move_count = len(white_win_percents) - 1
    if move_count < 1:
        return {"white": None, "black": None}

    window = max(2, min(8, move_count // 10))
    if len(white_win_percents) <= window:
        windows = [white_win_percents] * move_count
    else:
        sliding = [white_win_percents[i : i + window] for i in range(len(white_win_percents) - window + 1)]
        windows = [white_win_percents[:window]] * (window - 2) + sliding
    weights = [max(0.5, min(12.0, statistics.pstdev(w))) for w in windows]

    by_color: dict[str, list[tuple[float, float]]] = {"white": [], "black": []}
    for i, color in enumerate(movers):
        before, after = white_win_percents[i], white_win_percents[i + 1]
        loss = before - after if color == "white" else after - before
        by_color[color].append((move_accuracy(max(0.0, loss)), weights[i]))

    result: dict[str, float | None] = {}
    for color, moves in by_color.items():
        if not moves:
            result[color] = None
            continue
        weighted = sum(acc * weight for acc, weight in moves) / sum(weight for _, weight in moves)
        # A 0% move would make the harmonic mean 0 outright; floor each move at 1%.
        harmonic = len(moves) / sum(1 / max(acc, 1.0) for acc, _ in moves)
        result[color] = round((weighted + harmonic) / 2, 1)
    return result
