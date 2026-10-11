import { useEffect, useState } from 'react'

const SELECTS = [
  {
    name: 'result',
    label: 'Result',
    options: [['win', 'Wins'], ['loss', 'Losses'], ['draw', 'Draws']],
  },
  {
    name: 'color',
    label: 'Color',
    options: [['white', 'White'], ['black', 'Black']],
  },
  {
    name: 'time_class',
    label: 'Time control',
    options: [['bullet', 'Bullet'], ['blitz', 'Blitz'], ['rapid', 'Rapid'], ['daily', 'Daily']],
  },
]

const OPENING_DEBOUNCE_MS = 300

export default function GameFilters({ filters, onChange }) {
  // Opening is free text: keep a local copy and only apply it after typing pauses.
  const [opening, setOpening] = useState(filters.opening)

  useEffect(() => setOpening(filters.opening), [filters.opening])

  useEffect(() => {
    if (opening === filters.opening) return
    const timer = setTimeout(() => onChange('opening', opening), OPENING_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [opening, filters.opening, onChange])

  const control = 'input !w-auto min-w-32'

  return (
    <div className="flex flex-wrap items-end gap-3">
      {SELECTS.map(({ name, label, options }) => (
        <label key={name} className="text-sm">
          <span className="label !mb-1 !text-xs">{label}</span>
          <select className={control} value={filters[name]} onChange={(event) => onChange(name, event.target.value)}>
            <option value="">All</option>
            {options.map(([value, text]) => (
              <option key={value} value={value}>
                {text}
              </option>
            ))}
          </select>
        </label>
      ))}
      <label className="text-sm">
        <span className="label !mb-1 !text-xs">Opening</span>
        <input
          type="search"
          className={control}
          placeholder="e.g. Sicilian"
          value={opening}
          onChange={(event) => setOpening(event.target.value)}
        />
      </label>
    </div>
  )
}
