import { capitalize, formatMonth, formatTimeControl } from './format.js'

describe('formatTimeControl', () => {
  it.each([
    ['600', '10 min'],
    ['180+2', '3+2'],
    ['60', '1 min'],
    ['30', '30s'],
    ['1/86400', '1 day'],
    ['1/604800', '7 days'],
    [null, ''],
  ])('%s -> %s', (input, expected) => {
    expect(formatTimeControl(input)).toBe(expected)
  })
})

it('formatMonth', () => {
  expect(formatMonth(2026, 9)).toBe('Sep 2026')
  expect(formatMonth(2025, 1)).toBe('Jan 2025')
})

it('capitalize', () => {
  expect(capitalize('rapid')).toBe('Rapid')
  expect(capitalize('')).toBe('')
})
