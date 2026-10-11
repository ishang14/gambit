"""SM-2 spaced repetition (https://super-memory.com/english/ol/sm2.htm).

One change from the original: a failed card comes back after `RELEARN_DELAY` (10 minutes)
instead of tomorrow, so it is drilled again in the same session.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

Rating = Literal["again", "hard", "good", "easy"]

# SM-2 grades answers 0-5; 3 and above is a pass.
QUALITY: dict[str, int] = {"again": 1, "hard": 3, "good": 4, "easy": 5}
PASSING_QUALITY = 3
MIN_EASE = 1.3
DEFAULT_EASE = 2.5
RELEARN_DELAY = timedelta(minutes=10)


@dataclass(frozen=True)
class Schedule:
    ease: float = DEFAULT_EASE
    interval: int = 0  # days
    repetitions: int = 0  # passes in a row


def next_ease(ease: float, quality: int) -> float:
    miss = 5 - quality
    return max(MIN_EASE, ease + 0.1 - miss * (0.08 + miss * 0.02))


def review(schedule: Schedule, quality: int, now: datetime) -> tuple[Schedule, datetime]:
    """Apply one review graded `quality` (0-5). Returns the new schedule and when the card is next due."""
    ease = next_ease(schedule.ease, quality)
    if quality < PASSING_QUALITY:
        return Schedule(ease=ease, interval=0, repetitions=0), now + RELEARN_DELAY

    if schedule.repetitions == 0:
        interval = 1
    elif schedule.repetitions == 1:
        interval = 6
    else:
        interval = math.ceil(schedule.interval * schedule.ease)
    return Schedule(ease=ease, interval=interval, repetitions=schedule.repetitions + 1), now + timedelta(days=interval)


def quality_for(correct: bool, rating: Rating) -> int:
    """A wrong move is always a fail, whatever the rating."""
    return QUALITY[rating] if correct else QUALITY["again"]
