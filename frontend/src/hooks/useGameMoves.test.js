import { SCHOLARS_MATE_PGN, START_FEN } from '../test/reviewFixtures.js'
import { parseGame } from './useGameMoves.js'

it('parses moves and positions from a PGN with clock comments', () => {
  const { moves, fens } = parseGame(SCHOLARS_MATE_PGN)

  expect(moves.map((m) => m.san)).toEqual(['e4', 'e5', 'Qh5', 'Nc6', 'Bc4', 'Nf6', 'Qxf7#'])
  expect(moves[0]).toEqual({ san: 'e4', from: 'e2', to: 'e4', color: 'w' })
  expect(fens).toHaveLength(8)
  expect(fens[0]).toBe(START_FEN)
  expect(fens[7]).toBe('r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4')
})

it('throws on an illegal game', () => {
  expect(() => parseGame('1. e4 e5 2. Ke3 Ke6 3. Kd5')).toThrow()
})
