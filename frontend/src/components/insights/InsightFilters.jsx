import { PERIODS } from '../../utils/insights.js'

const TIME_CLASSES = [
  ['', 'All time controls'],
  ['bullet', 'Bullet'],
  ['blitz', 'Blitz'],
  ['rapid', 'Rapid'],
  ['daily', 'Daily'],
]

/** One row of filters above everything; every chart below uses the same slice. */
export default function InsightFilters({ period, timeClass, onChange }) {
  const control = 'input !w-auto min-w-44'
  return (
    <div className="card flex flex-wrap items-end gap-4 p-4">
      <label className="text-sm">
        <span className="label !mb-1 !text-xs">Period</span>
        <select className={control} value={period} onChange={(e) => onChange({ period: e.target.value })}>
          {PERIODS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      <label className="text-sm">
        <span className="label !mb-1 !text-xs">Time control</span>
        <select className={control} value={timeClass} onChange={(e) => onChange({ time_class: e.target.value })}>
          {TIME_CLASSES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}
