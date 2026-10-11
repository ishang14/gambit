from datetime import datetime, timedelta, timezone

import pytest

from app.training.sm2 import (
    DEFAULT_EASE,
    MIN_EASE,
    RELEARN_DELAY,
    Schedule,
    next_ease,
    quality_for,
    review,
)

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def test_first_passes_use_fixed_intervals() -> None:
    first, due1 = review(Schedule(), 4, NOW)
    second, due2 = review(first, 4, NOW)

    assert (first.interval, first.repetitions) == (1, 1)
    assert due1 == NOW + timedelta(days=1)
    assert (second.interval, second.repetitions) == (6, 2)
    assert due2 == NOW + timedelta(days=6)


def test_later_intervals_grow_by_ease() -> None:
    schedule = Schedule(ease=2.5, interval=6, repetitions=2)

    after, due = review(schedule, 4, NOW)

    assert after.interval == 15  # ceil(6 x 2.5)
    assert due == NOW + timedelta(days=15)


def test_fail_resets_and_comes_back_soon() -> None:
    schedule = Schedule(ease=2.5, interval=15, repetitions=3)

    after, due = review(schedule, 1, NOW)

    assert (after.interval, after.repetitions) == (0, 0)
    assert due == NOW + RELEARN_DELAY
    assert after.ease < 2.5


@pytest.mark.parametrize(
    ("quality", "change"),
    [(5, 0.1), (4, 0.0), (3, -0.14), (1, -0.54)],
)
def test_ease_changes_by_grade(quality: int, change: float) -> None:
    assert next_ease(DEFAULT_EASE, quality) == pytest.approx(DEFAULT_EASE + change)


def test_ease_has_a_floor() -> None:
    assert next_ease(1.35, 0) == MIN_EASE


def test_easy_cards_space_out_faster_than_hard_ones() -> None:
    easy = hard = Schedule()
    for _ in range(4):
        easy, _ = review(easy, 5, NOW)
        hard, _ = review(hard, 3, NOW)
    assert easy.interval > hard.interval


def test_quality_for() -> None:
    assert quality_for(True, "easy") == 5
    assert quality_for(True, "hard") == 3
    assert quality_for(False, "easy") == 1  # wrong moves always fail
