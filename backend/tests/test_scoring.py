import pytest

from app.analysis.scoring import (
    MATE_CP,
    Thresholds,
    classify,
    game_accuracies,
    move_accuracy,
    to_centipawns,
    white_win_percent,
    win_percent,
)


def cp(value: int) -> dict:
    return {"cp": value, "mate": None}


def mate(value: int) -> dict:
    return {"cp": None, "mate": value}


def test_equal_position_is_fifty_percent() -> None:
    assert white_win_percent(cp(0), white_to_move=True) == pytest.approx(50)


def test_win_percent_rises_with_advantage_and_saturates() -> None:
    values = [white_win_percent(cp(c), True) for c in (-500, -100, 0, 100, 500)]
    assert values == sorted(values)
    assert white_win_percent(cp(100), True) == pytest.approx(59.1, abs=0.1)
    assert white_win_percent(cp(5000), True) > 99


def test_same_cp_matters_less_when_already_winning() -> None:
    equal_drop = white_win_percent(cp(100), True) - white_win_percent(cp(0), True)
    winning_drop = white_win_percent(cp(900), True) - white_win_percent(cp(800), True)
    assert equal_drop > 3 * winning_drop


@pytest.mark.parametrize(
    ("evaluation", "white_to_move", "expected"),
    [
        (mate(3), True, 100),
        (mate(-2), True, 0),
        (mate(0), True, 0),  # White to move and checkmated
        (mate(0), False, 100),  # Black to move and checkmated
    ],
)
def test_mate_scores(evaluation: dict, white_to_move: bool, expected: float) -> None:
    assert white_win_percent(evaluation, white_to_move) == expected


def test_win_percent_for_black_is_the_complement() -> None:
    assert win_percent(cp(100), True, for_white=False) == pytest.approx(100 - white_win_percent(cp(100), True))


def test_to_centipawns() -> None:
    assert to_centipawns(cp(-35), True) == -35
    assert to_centipawns(mate(2), True) == MATE_CP
    assert to_centipawns(mate(-1), False) == -MATE_CP
    assert to_centipawns(mate(0), False) == MATE_CP


def test_move_accuracy() -> None:
    assert move_accuracy(0) == pytest.approx(100, abs=0.01)
    assert move_accuracy(100) == 0
    assert move_accuracy(5) > move_accuracy(10) > move_accuracy(20)


@pytest.mark.parametrize(
    ("loss", "played_best", "expected"),
    [
        (0.0, True, "best"),
        (3.0, True, "best"),  # the engine's move is always "best"
        (0.0, False, "good"),
        (4.99, False, "good"),
        (5.0, False, "inaccuracy"),
        (10.0, False, "mistake"),
        (19.9, False, "mistake"),
        (20.0, False, "blunder"),
        (80.0, False, "blunder"),
    ],
)
def test_classify_default_thresholds(loss: float, played_best: bool, expected: str) -> None:
    assert classify(loss, played_best, Thresholds()) == expected


def test_classify_custom_thresholds() -> None:
    strict = Thresholds(inaccuracy=1, mistake=2, blunder=3)
    assert classify(2.5, False, strict) == "mistake"


def alternating(n: int) -> list[str]:
    return ["white" if i % 2 == 0 else "black" for i in range(n)]


def test_perfect_game_is_100_for_both() -> None:
    assert game_accuracies([50.0] * 41, alternating(40)) == {"white": 100.0, "black": 100.0}


def test_one_blunder_counts_for_more_than_a_plain_average() -> None:
    # 40 moves at a steady 50%; on move 21 (White) White drops to 20%, and it stays there.
    win = [50.0] * 21 + [20.0] * 20
    moves = alternating(40)

    accuracy = game_accuracies(win, moves)

    white_moves = [move_accuracy(0.0)] * 19 + [move_accuracy(30.0)]
    plain_average = sum(white_moves) / len(white_moves)
    assert accuracy["black"] == 100.0
    assert accuracy["white"] < plain_average - 10


def test_black_losing_win_chance_hurts_black() -> None:
    win = [50.0, 50.0, 80.0]  # White keeps 50%, then Black's move hands White 80%

    accuracy = game_accuracies(win, ["white", "black"])

    assert accuracy["white"] == 100.0
    assert accuracy["black"] < 50


def test_short_and_empty_games() -> None:
    assert game_accuracies([50.0], []) == {"white": None, "black": None}
    assert game_accuracies([50.0, 50.0], ["white"]) == {"white": 100.0, "black": None}
