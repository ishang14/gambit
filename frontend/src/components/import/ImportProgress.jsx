import { Link } from 'react-router-dom'
import { formatMonth } from '../../utils/format.js'

export default function ImportProgress({ running, total, current, results, error, onStop }) {
  const done = results.length
  const imported = results.reduce((sum, r) => sum + r.imported, 0)
  const percent = total ? Math.round((done / total) * 100) : 0

  return (
    <section className="card space-y-4 p-5" aria-live="polite">
      <div className="flex items-center justify-between text-sm">
        <span>
          {running && current
            ? `Importing ${formatMonth(current.year, current.month)} (${done + 1} of ${total})`
            : `Finished ${done} of ${total} months`}
        </span>
        {running && (
          <button type="button" onClick={onStop} className="btn btn-secondary btn-sm">
            Stop
          </button>
        )}
      </div>
      <div
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2.5 overflow-hidden rounded-full bg-raised"
      >
        <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${percent}%` }} />
      </div>

      {error && (
        <p role="alert" className="alert alert-danger">
          {error}
        </p>
      )}

      {results.length > 0 && (
        <table className="w-full text-left text-sm text-ink-2">
          <thead className="text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="py-2 font-semibold">Month</th>
              <th className="py-2 font-semibold">New</th>
              <th className="py-2 font-semibold">Already imported</th>
              <th className="py-2 font-semibold">Skipped (variants)</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={`${r.year}-${r.month}`} className="border-t border-line">
                <td className="py-2 font-medium text-ink">{formatMonth(r.year, r.month)}</td>
                <td className="py-2 font-semibold text-brand">{r.imported}</td>
                <td className="py-2">{r.duplicates}</td>
                <td className="py-2">{r.unsupported}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!running && done > 0 && (
        <p className="text-sm">
          Imported {imported} new {imported === 1 ? 'game' : 'games'}.{' '}
          <Link to="/games" className="text-brand hover:underline">
            View games
          </Link>
        </p>
      )}
    </section>
  )
}
