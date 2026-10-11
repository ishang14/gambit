/** Legend swatches mirror the mark: a square for bars, a short stroke for lines. */
export function Legend({ items }) {
  return (
    <ul aria-label="Legend" className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[color:var(--viz-text-secondary)]">
      {items.map(({ label, color, shape = 'rect' }) => (
        <li key={label} className="flex items-center gap-1.5">
          {shape === 'line' ? (
            <span className="inline-block h-0.5 w-4 rounded" style={{ background: color }} />
          ) : (
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
          )}
          {label}
        </li>
      ))}
    </ul>
  )
}

/** A chart with its title, legend, and a table view that holds every value. */
export default function ChartCard({ title, description, legend, table, empty, children }) {
  return (
    <section className="card space-y-4 p-5" aria-label={title}>
      <div className="space-y-1">
        <h2 className="text-lg font-bold tracking-tight text-[color:var(--viz-text-primary)]">{title}</h2>
        {description && <p className="text-sm text-[color:var(--viz-text-secondary)]">{description}</p>}
        {legend && !empty && <Legend items={legend} />}
      </div>
      {empty ? <p className="py-8 text-center text-sm text-[color:var(--viz-muted)]">{empty}</p> : children}
      {table && !empty && (
        <details className="text-sm">
          <summary className="cursor-pointer font-medium text-[color:var(--viz-text-secondary)] hover:text-brand">Show as table</summary>
          <div className="mt-2 overflow-x-auto">{table}</div>
        </details>
      )}
    </section>
  )
}

/** A plain data table for the "Show as table" view. */
export function DataTable({ caption, columns, rows }) {
  return (
    <table className="w-full text-left tabular-nums">
      <caption className="sr-only">{caption}</caption>
      <thead className="text-[color:var(--viz-text-secondary)]">
        <tr>
          {columns.map((column) => (
            <th key={column} className="py-1 pr-4 font-medium">
              {column}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index} className="border-t border-[color:var(--viz-grid)]">
            {row.map((cell, cellIndex) => (
              <td key={cellIndex} className="py-1 pr-4">
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
