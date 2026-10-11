"""Turn a chess.com game object into the document we store in `games`."""

import io
from datetime import datetime, timezone
from typing import Any

import chess.pgn

# chess.com result codes that mean the game was drawn. Everything that isn't
# "win" or a draw is a loss (checkmated, resigned, timeout, abandoned, ...).
DRAW_CODES = {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"}


def outcome(result_code: str) -> str:
    if result_code == "win":
        return "win"
    if result_code in DRAW_CODES:
        return "draw"
    return "loss"


def opening_name(eco_url: str | None) -> str | None:
    """'https://www.chess.com/openings/Pirc-Defense-Classical' -> 'Pirc Defense Classical'."""
    if not eco_url:
        return None
    slug = eco_url.rstrip("/").rsplit("/", 1)[-1]
    return slug.replace("-", " ") or None


def parse_game(raw: dict[str, Any], username: str) -> dict[str, Any] | None:
    """Return the game fields to store, or None for games we don't support
    (variants, unparseable PGN, or games the player wasn't in)."""
    if raw.get("rules") != "chess" or not raw.get("pgn"):
        return None

    game = chess.pgn.read_game(io.StringIO(raw["pgn"]))
    if game is None or game.errors:
        return None

    white, black = raw["white"], raw["black"]
    if white["username"].lower() == username.lower():
        color, me, opponent = "white", white, black
    elif black["username"].lower() == username.lower():
        color, me, opponent = "black", black, white
    else:
        return None

    headers = game.headers
    return {
        "source_url": raw["url"],
        "pgn": raw["pgn"],
        "white": white["username"],
        "black": black["username"],
        "white_rating": white.get("rating"),
        "black_rating": black.get("rating"),
        "user_color": color,
        "user_rating": me.get("rating"),
        "opponent": opponent["username"],
        "opponent_rating": opponent.get("rating"),
        "result": headers.get("Result", "*"),
        "user_result": outcome(me["result"]),
        "time_control": raw.get("time_control"),
        "time_class": raw.get("time_class"),
        "rated": raw.get("rated"),
        # chess.com files games under the month they ended, so use end_time.
        "played_at": datetime.fromtimestamp(raw["end_time"], tz=timezone.utc),
        "eco": headers.get("ECO"),
        "opening": opening_name(headers.get("ECOUrl") or raw.get("eco")),
        "ply_count": game.end().ply(),
    }
