import { formatMonth } from '../../utils/format.js'

export const monthKey = ({ year, month }) => `${year}-${month}`

/** Checkbox list of months (newest first) with quick-select buttons. */
export default function MonthPicker({ months, selected, onChange, disabled }) {
  function toggle(key) {
    const next = new Set(selected)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    onChange(next)
  }

  function selectNewest(count) {
    onChange(new Set(months.slice(0, count).map(monthKey)))
  }

  const quickButton = 'btn btn-secondary btn-sm'

  return (
    <fieldset disabled={disabled} className="space-y-3">
      <legend className="mb-3 font-semibold text-ink">Months to import</legend>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={quickButton} onClick={() => selectNewest(3)}>
          Last 3
        </button>
        <button type="button" className={quickButton} onClick={() => selectNewest(12)}>
          Last 12
        </button>
        <button type="button" className={quickButton} onClick={() => selectNewest(months.length)}>
          All ({months.length})
        </button>
        <button type="button" className={quickButton} onClick={() => onChange(new Set())}>
          Clear
        </button>
      </div>
      <ul className="grid max-h-72 grid-cols-2 gap-1.5 overflow-y-auto rounded-xl border border-line bg-panel-2 p-2 sm:grid-cols-3 md:grid-cols-4">
        {months.map((month) => {
          const key = monthKey(month)
          return (
            <li key={key}>
              <label className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm text-ink-2 transition hover:bg-raised hover:text-ink">
                <input type="checkbox" className="h-4 w-4 accent-brand" checked={selected.has(key)} onChange={() => toggle(key)} />
                {formatMonth(month.year, month.month)}
              </label>
            </li>
          )
        })}
      </ul>
    </fieldset>
  )
}
