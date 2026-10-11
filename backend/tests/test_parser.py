from datetime import datetime, timezone

import pytest

from app.games.parser import opening_name, outcome, parse_game
from tests.conftest import load_fixture

GAMES = load_fixture("chesscom/games_2026_09.json")["games"]


def parsed_games() -> list[dict]:
    return [g for g in (parse_game(raw, "erik") for raw in GAMES) if g is not None]


def test_variants_are_skipped() -> None:
    assert sum(raw["rules"] == "chess960" for raw in GAMES) == 3
    assert len(parsed_games()) == 5


def test_parses_a_game_from_the_players_side() -> None:
    game = parse_game(GAMES[0], "erik")

    assert game is not None
    assert game["source_url"] == "https://www.chess.com/game/daily/1016260528"
    assert game["user_color"] == "black"
    assert game["user_result"] == "win"
    assert game["result"] == "0-1"
    assert game["opponent"] == "opponent1"
    assert game["user_rating"] == 1470
    assert game["opponent_rating"] == 1106
    assert game["eco"] == "B08"
    assert game["opening"] == "Pirc Defense Classical Variation 4...Bg7"
    assert game["time_class"] == "daily"
    assert game["played_at"] == datetime.fromtimestamp(GAMES[0]["end_time"], tz=timezone.utc)
    assert game["ply_count"] > 0


def test_username_match_is_case_insensitive() -> None:
    assert parse_game(GAMES[0], "ERIK") == parse_game(GAMES[0], "erik")


def test_results_cover_wins_losses_and_draws() -> None:
    results = sorted(g["user_result"] for g in parsed_games())
    assert results == ["draw", "draw", "loss", "win", "win"]


def test_game_without_the_player_is_skipped() -> None:
    assert parse_game(GAMES[0], "someone-else") is None


def test_broken_pgn_is_skipped() -> None:
    raw = {**GAMES[0], "pgn": '[Event "x"]\n\n1. e4 e5 2. Ke3 Ke6 *'}
    assert parse_game(raw, "erik") is None


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("win", "win"),
        ("agreed", "draw"),
        ("repetition", "draw"),
        ("stalemate", "draw"),
        ("insufficient", "draw"),
        ("50move", "draw"),
        ("timevsinsufficient", "draw"),
        ("checkmated", "loss"),
        ("resigned", "loss"),
        ("timeout", "loss"),
        ("abandoned", "loss"),
    ],
)
def test_outcome(code: str, expected: str) -> None:
    assert outcome(code) == expected


def test_opening_name() -> None:
    assert opening_name("https://www.chess.com/openings/Sicilian-Defense-Najdorf") == "Sicilian Defense Najdorf"
    assert opening_name(None) is None
