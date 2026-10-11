import chess

from app.analysis.phase import game_phase


def test_start_of_game_is_the_opening() -> None:
    assert game_phase(chess.Board(), 1) == "opening"
    assert game_phase(chess.Board(), 20) == "opening"


def test_after_the_opening_plies_it_is_the_middlegame() -> None:
    assert game_phase(chess.Board(), 21) == "middlegame"


def test_few_pieces_left_is_the_endgame_whatever_the_move_number() -> None:
    rook_ending = chess.Board("8/5k2/8/8/8/8/2R2K2/r7 w - - 0 40")
    assert game_phase(rook_ending, 79) == "endgame"
    # Even early: a (silly) position with 6 pieces at ply 10.
    six_pieces = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R1B1KB1R w KQkq - 0 6")
    assert game_phase(six_pieces, 10) == "endgame"


def test_seven_pieces_is_not_yet_an_endgame() -> None:
    seven = chess.Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/RNB1KB1R w KQkq - 0 20")
    assert game_phase(seven, 40) == "middlegame"
