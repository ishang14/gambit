import { percent } from './viz.js'

function Tile({ label, value, detail }) {
  return (
    <div className="card px-4 py-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-[color:var(--viz-muted)]">{label}</div>
      <div className="mt-1.5 text-3xl font-extrabold tracking-tight text-[color:var(--viz-text-primary)]" aria-label={label}>
        {value}
      </div>
      {detail && <div className="mt-0.5 text-xs text-[color:var(--viz-muted)]">{detail}</div>}
    </div>
  )
}

const wdl = (r) => `${r.wins} won · ${r.draws} drawn · ${r.losses} lost`

export default function StatTiles({ summary }) {
  return (
    <div className="viz grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <Tile label="Games" value={summary.games.toLocaleString()} detail={`${summary.analyzed_games} analyzed`} />
      <Tile label="Score" value={percent(summary.score)} detail={wdl(summary)} />
      <Tile label="Score as White" value={percent(summary.by_color.white.score)} detail={`${summary.by_color.white.games} games`} />
      <Tile label="Score as Black" value={percent(summary.by_color.black.score)} detail={`${summary.by_color.black.games} games`} />
      <Tile
        label="Accuracy"
        value={summary.avg_accuracy != null ? `${summary.avg_accuracy.toFixed(1)}%` : '—'}
        detail="average, analyzed games"
      />
      <Tile
        label="Blunders per game"
        value={summary.blunders_per_game != null ? summary.blunders_per_game.toFixed(2) : '—'}
        detail={summary.mistakes_per_game != null ? `${summary.mistakes_per_game.toFixed(2)} mistakes per game` : 'analyzed games'}
      />
    </div>
  )
}
