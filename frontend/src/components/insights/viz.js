// Chart colors by role (values live in index.css under .viz).
export const VIZ = {
  surface: 'var(--viz-surface)',
  textSecondary: 'var(--viz-text-secondary)',
  muted: 'var(--viz-muted)',
  grid: 'var(--viz-grid)',
  axis: 'var(--viz-axis)',
  series1: 'var(--viz-series-1)',
  deemphasis: 'var(--viz-deemphasis)',
  win: 'var(--viz-win)',
  draw: 'var(--viz-draw)',
  loss: 'var(--viz-loss)',
  severity: ['var(--viz-severity-1)', 'var(--viz-severity-2)', 'var(--viz-severity-3)'],
}

export const AXIS_TICK = { fill: 'var(--viz-muted)', fontSize: 12 }

export const percent = (value) => (value == null ? '—' : `${Math.round(value * 100)}%`)
