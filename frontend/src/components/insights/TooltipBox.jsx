/** Tooltip body: the value is the strong element, the series name secondary, keyed by a short stroke. */
export default function TooltipBox({ title, rows }) {
  return (
    <div className="viz min-w-40 rounded-md border bg-[color:var(--viz-surface)] px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-medium text-[color:var(--viz-text-secondary)]">{title}</div>
      <ul className="space-y-0.5">
        {rows.map(({ label, value, color }) => (
          <li key={label} className="flex items-center gap-2">
            {color && <span className="inline-block h-0.5 w-3 rounded" style={{ background: color }} />}
            <span className="font-semibold text-[color:var(--viz-text-primary)] tabular-nums">{value}</span>
            <span className="text-[color:var(--viz-text-secondary)]">{label}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
