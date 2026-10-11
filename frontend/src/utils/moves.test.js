import { fenFromKey, formatLine, moveNumber } from './moves.js'

it('moveNumber', () => {
  expect(moveNumber(0)).toBe('1.')
  expect(moveNumber(1)).toBe('1...')
  expect(moveNumber(4)).toBe('3.')
})

it('formatLine', () => {
  expect(formatLine(['e4', 'e5', 'Nf3'])).toBe('1. e4 e5 2. Nf3')
  expect(formatLine([])).toBe('')
})

it('fenFromKey', () => {
  expect(fenFromKey('8/8/8/8/8/8/8/K6k w - -')).toBe('8/8/8/8/8/8/8/K6k w - - 0 1')
})
