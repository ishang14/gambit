import chess

from app.analysis.engine import normalize_fen
from app.openings.book import load_book, parse_line


def key_after(*sans: str) -> str:
    board = chess.Board()
    for san in sans:
        board.push_san(san)
    return normalize_fen(board)


def test_parse_line() -> None:
    assert parse_line("1. e4 e5 2. Nf3") == [key_after("e4"), key_after("e4", "e5"), key_after("e4", "e5", "Nf3")]


def test_named_positions() -> None:
    book = load_book()
    assert book.name(key_after("e4", "e5", "Nf3", "Nc6", "Bb5")) == "Ruy Lopez"
    assert book.name(key_after("e4", "c5")) == "Sicilian Defense"


def test_positions_along_lines_are_in_book() -> None:
    book = load_book()
    assert book.contains(key_after())  # start position
    assert book.contains(key_after("e4", "e5", "Nf3", "Nc6"))
    assert not book.contains(key_after("a4", "h5", "Ra3", "Rh6"))


def test_transpositions_share_a_position() -> None:
    book = load_book()
    assert book.contains(key_after("Nf3", "d5", "d4"))  # same as 1. d4 d5 2. Nf3
