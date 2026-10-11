import { formatEval, isWhiteToMove, whiteWinPercent } from './evaluation.js'

const cp = (value) => ({ cp: value, mate: null })
const mate = (value) => ({ cp: null, mate: value })

describe('whiteWinPercent', () => {
  it('is 50 for an equal position', () => {
    expect(whiteWinPercent(cp(0), true)).toBeCloseTo(50)
  })

  it('matches the backend curve', () => {
    expect(whiteWinPercent(cp(100), true)).toBeCloseTo(59.1, 1)
    expect(whiteWinPercent(cp(-100), true)).toBeCloseTo(40.9, 1)
  })

  it('handles mates', () => {
    expect(whiteWinPercent(mate(2), true)).toBe(100)
    expect(whiteWinPercent(mate(-1), false)).toBe(0)
    expect(whiteWinPercent(mate(0), true)).toBe(0)
    expect(whiteWinPercent(mate(0), false)).toBe(100)
  })
})

describe('formatEval', () => {
  it.each([
    [cp(130), true, '+1.3'],
    [cp(-45), true, '-0.5'],
    [cp(0), true, '0.0'],
    [mate(3), true, 'M3'],
    [mate(-2), false, '-M2'],
    [mate(0), false, '1-0'],
    [mate(0), true, '0-1'],
  ])('%j -> %s', (evaluation, whiteToMove, expected) => {
    expect(formatEval(evaluation, whiteToMove)).toBe(expected)
  })
})

it('isWhiteToMove', () => {
  expect(isWhiteToMove('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1')).toBe(true)
  expect(isWhiteToMove('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1')).toBe(false)
})
