const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** formatMonth(2026, 9) -> "Sep 2026" */
export function formatMonth(year, month) {
  return `${MONTHS[month - 1]} ${year}`
}

/** ISO date string -> "Sep 1, 2026" in the viewer's timezone. */
export function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

/**
 * chess.com time controls: "600" -> "10 min", "180+2" -> "3+2", "30" -> "30s",
 * "1/86400" -> "1 day" (daily games: seconds per move).
 */
export function formatTimeControl(timeControl) {
  if (!timeControl) return ''
  if (timeControl.includes('/')) {
    const days = Number(timeControl.split('/')[1]) / 86400
    return days === 1 ? '1 day' : `${days} days`
  }
  const [base, increment] = timeControl.split('+').map(Number)
  const minutes = base >= 60 ? `${base / 60}` : `${base}s`
  if (increment) return `${minutes}+${increment}`
  return base >= 60 ? `${minutes} min` : minutes
}

export function capitalize(text) {
  return text ? text[0].toUpperCase() + text.slice(1) : ''
}
