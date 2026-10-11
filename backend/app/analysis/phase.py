"""Which phase of the game a position is in, for "where do my mistakes happen?".

A simplified version of Lichess's divider: the endgame starts once few pieces are
left (by material, not move number); before that, the first plies are the opening
and everything else is the middlegame.
"""

from typing import Literal

import chess

Phase = Literal["opening", "middlegame", "endgame"]

OPENING_PLIES = 20  # same as the opening tree's default depth
ENDGAME_MAX_PIECES = 6  # knights, bishops, rooks and queens, both sides together

PIECES = (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)


def game_phase(board: chess.Board, ply: int) -> Phase:
    """Phase of the position in which move number `ply` (1-based) is played."""
    pieces = sum(len(board.pieces(piece, color)) for piece in PIECES for color in chess.COLORS)
    if pieces <= ENDGAME_MAX_PIECES:
        return "endgame"
    if ply <= OPENING_PLIES:
        return "opening"
    return "middlegame"
