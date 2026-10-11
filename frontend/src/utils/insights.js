const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

export const PERIODS = [
  { value: '30d', label: 'Last 30 days', days: 30, bucket: 'week' },
  { value: '90d', label: 'Last 90 days', days: 90, bucket: 'week' },
  { value: '1y', label: 'Last 12 months', days: 365, bucket: 'month' },
  { value: 'all', label: 'All time', days: null, bucket: 'month' },
]

/** The first day of a period as YYYY-MM-DD (local date), or null for "all time". */
export function sinceDate(period, today = new Date()) {
  const preset = PERIODS.find((p) => p.value === period)
  if (!preset?.days) return null
  const start = new Date(today.getFullYear(), today.getMonth(), today.getDate() - preset.days)
  const pad = (n) => String(n).padStart(2, '0')
  return `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}`
}

/** Monday of an ISO week: "2026-W36" -> Date(2026-08-31). */
export function isoWeekStart(isoWeek) {
  const [year, week] = isoWeek.split('-W').map(Number)
  const jan4 = new Date(Date.UTC(year, 0, 4)) // always in ISO week 1
  const mondayOfWeek1 = new Date(jan4)
  mondayOfWeek1.setUTCDate(jan4.getUTCDate() - ((jan4.getUTCDay() + 6) % 7))
  const start = new Date(mondayOfWeek1)
  start.setUTCDate(mondayOfWeek1.getUTCDate() + (week - 1) * 7)
  return start
}

/** "2026-W36" -> "Aug 31", "2026-09" -> "Sep 2026" */
export function formatPeriod(period) {
  if (period.includes('-W')) {
    const start = isoWeekStart(period)
    return `${MONTHS[start.getUTCMonth()]} ${start.getUTCDate()}`
  }
  const [year, month] = period.split('-').map(Number)
  return `${MONTHS[month - 1]} ${year}`
}

/** 0 -> "00:00", 13 -> "13:00" */
export function formatHour(hour) {
  return `${String(hour).padStart(2, '0')}:00`
}

export function browserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  } catch {
    return 'UTC'
  }
}
