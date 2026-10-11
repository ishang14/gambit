import { formatHour, formatPeriod, isoWeekStart, sinceDate } from './insights.js'

it('isoWeekStart finds the Monday of an ISO week', () => {
  expect(isoWeekStart('2026-W36').toISOString().slice(0, 10)).toBe('2026-08-31')
  expect(isoWeekStart('2026-W01').toISOString().slice(0, 10)).toBe('2025-12-29')
  expect(isoWeekStart('2021-W01').toISOString().slice(0, 10)).toBe('2021-01-04')
})

it('formatPeriod', () => {
  expect(formatPeriod('2026-W36')).toBe('Aug 31')
  expect(formatPeriod('2026-09')).toBe('Sep 2026')
})

it('sinceDate', () => {
  const today = new Date(2026, 9, 10)
  expect(sinceDate('30d', today)).toBe('2026-09-10')
  expect(sinceDate('1y', today)).toBe('2025-10-10')
  expect(sinceDate('all', today)).toBeNull()
})

it('formatHour', () => {
  expect(formatHour(0)).toBe('00:00')
  expect(formatHour(13)).toBe('13:00')
})
