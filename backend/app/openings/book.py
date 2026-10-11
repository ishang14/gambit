"""Known opening theory, from the Lichess openings dataset (see data/README.md)."""

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chess

from app.analysis.engine import normalize_fen

DATA_DIR = Path(__file__).parent / "data"
MOVE_NUMBER = re.compile(r"^\d+\.+$")


@dataclass(frozen=True)
class OpeningBook:
    positions: frozenset[str]  # every position on any named line (normalized FEN)
    names: dict[str, str]  # positions where a named line ends -> its name

    def contains(self, fen_key: str) -> bool:
        return fen_key in self.positions

    def name(self, fen_key: str) -> str | None:
        return self.names.get(fen_key)


def parse_line(pgn: str) -> list[str]:
    """'1. e4 e5 2. Nf3' -> [fen_key after e4, after e5, after Nf3]"""
    board = chess.Board()
    keys = []
    for token in pgn.split():
        if MOVE_NUMBER.match(token):
            continue
        board.push_san(token)
        keys.append(normalize_fen(board))
    return keys


@lru_cache
def load_book() -> OpeningBook:
    positions = {normalize_fen(chess.Board())}
    names: dict[str, str] = {}
    for path in sorted(DATA_DIR.glob("*.tsv")):
        with path.open(encoding="utf-8") as file:
            for row in csv.DictReader(file, delimiter="\t"):
                keys = parse_line(row["pgn"])
                positions.update(keys)
                # Keep the first name for a position (the files are sorted by ECO code).
                names.setdefault(keys[-1], row["name"])
    return OpeningBook(positions=frozenset(positions), names=names)
