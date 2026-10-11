import { CLASSIFICATIONS, CLASSIFICATION_STYLES } from '../../utils/classification.js'

function JobProgress({ job }) {
  const percent = Math.round((job.progress ?? 0) * 100)
  return (
    <div className="space-y-2" aria-live="polite">
      <p className="text-sm text-ink-2">
        {job.status === 'queued' ? 'Waiting for the engine…' : `Analyzing… ${percent}%`}
      </p>
      <div role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} className="h-2.5 rounded-full bg-raised">
        <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

function Summary({ analysis, game }) {
  const sides = [
    { color: 'white', name: game.white },
    { color: 'black', name: game.black },
  ]
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        {sides.map(({ color, name }) => (
          <div key={color} className="rounded-xl border border-line bg-panel-2 p-4 text-center">
            <div className="truncate text-sm text-muted">{name}</div>
            <div className="text-3xl font-extrabold tracking-tight text-ink" aria-label={`${name} accuracy`}>
              {analysis.accuracy[color] != null ? `${analysis.accuracy[color].toFixed(1)}%` : '—'}
            </div>
            <div className="text-xs text-muted">accuracy</div>
          </div>
        ))}
      </div>
      <table className="w-full text-sm">
        <tbody>
          {CLASSIFICATIONS.map((name) => (
            <tr key={name} className="border-t border-line">
              <td className="py-2 text-center tabular-nums text-ink">{analysis.counts.white[name]}</td>
              <td className={`py-2 text-center font-semibold ${CLASSIFICATION_STYLES[name].text}`}>
                <span aria-hidden="true" className={`mr-2 inline-block h-2 w-2 rounded-full ${CLASSIFICATION_STYLES[name].dot}`} />
                {CLASSIFICATION_STYLES[name].label}
              </td>
              <td className="py-2 text-center tabular-nums text-ink">{analysis.counts.black[name]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-muted">Stockfish, depth {analysis.depth}</p>
    </div>
  )
}

/** Shows the summary when analyzed; otherwise the Analyze button or job progress. */
export default function AnalysisPanel({ game, analysis, job, error, onAnalyze }) {
  const active = job && ['queued', 'running'].includes(job.status)
  const failed = job?.status === 'failed' || (!job && game.analysis_status === 'failed')

  return (
    <section className="card space-y-4 p-5">
      <h2 className="font-semibold text-ink">Analysis</h2>
      {analysis && <Summary analysis={analysis} game={game} />}
      {!analysis && active && <JobProgress job={job} />}
      {!analysis && !active && (
        <div className="space-y-2">
          {failed && (
            <p className="text-sm text-danger">
              Analysis failed{job?.error || game.analysis_error ? `: ${job?.error ?? game.analysis_error}` : ''}.
            </p>
          )}
          <button type="button" className="btn btn-primary" onClick={onAnalyze}>
            {failed ? 'Try again' : 'Analyze with Stockfish'}
          </button>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </section>
  )
}
