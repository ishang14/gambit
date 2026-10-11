import { Chess } from 'chess.js'
import { useMemo } from 'react'

/** Parse a PGN into the move list and the FEN before/after every move. */
export function parseGame(pgn) {
  const chess = new Chess()
  chess.loadPgn(pgn)
  const history = chess.history({ verbose: true })
  const startFen = history.length > 0 ? history[0].before : chess.fen()
  return {
    moves: history.map((move) => ({ san: move.san, from: move.from, to: move.to, color: move.color })),
    // fens[k] is the position after k moves; fens[0] is the start.
    fens: [startFen, ...history.map((move) => move.after)],
  }
}

export function useGameMoves(pgn) {
  return useMemo(() => {
    if (!pgn) return null
    try {
      return parseGame(pgn)
    } catch {
      return null
    }
  }, [pgn])
}
