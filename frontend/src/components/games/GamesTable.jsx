import { Link, useNavigate } from 'react-router-dom'
import { capitalize, formatDate, formatTimeControl } from '../../utils/format.js'

const RESULT_STYLES = {
  win: 'bg-brand/15 text-brand',
  loss: 'bg-danger/15 text-danger',
  draw: 'bg-raised text-ink-2',
}

/** A tiny piece-colored square showing which side you played. */
function ColorChip({ color }) {
  const style = color === 'white' ? 'bg-[#f4f1e6] border-black/20' : 'bg-[#2b2824] border-white/20'
  return <span title={`You played ${color}`} className={`inline-block h-3.5 w-3.5 shrink-0 rounded-[4px] border ${style}`} />
}

function accuracyTone(accuracy) {
  if (accuracy >= 90) return 'bg-brand/15 text-brand'
  if (accuracy >= 75) return 'bg-info/15 text-info'
  return 'bg-warning/15 text-warning'
}

function AccuracyCell({ game }) {
  switch (game.analysis_status) {
    case 'done':
      return game.accuracy != null ? (
        <span className={`badge tabular-nums ${accuracyTone(game.accuracy)}`}>{`${game.accuracy.toFixed(1)}%`}</span>
      ) : (
        '—'
      )
    case 'queued':
      return <span className="text-muted">Queued</span>
    case 'running':
      return <span className="text-muted">Analyzing…</span>
    case 'failed':
      return <span className="text-danger">Failed</span>
    default:
      return <span className="text-muted">—</span>
  }
}

export default function GamesTable({ games }) {
  const navigate = useNavigate()

  return (
    <div className="overflow-x-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Opponent</th>
            <th>Result</th>
            <th>Opening</th>
            <th>Time</th>
            <th>Accuracy</th>
          </tr>
        </thead>
        <tbody>
          {games.map((game) => (
            <tr
              key={game.id}
              onClick={() => navigate(`/games/${game.id}`)}
              className="cursor-pointer transition-colors hover:bg-panel-2"
            >
              <td className="whitespace-nowrap">
                <Link to={`/games/${game.id}`} onClick={(event) => event.stopPropagation()} className="hover:text-brand">
                  {formatDate(game.played_at)}
                </Link>
              </td>
              <td className="whitespace-nowrap">
                <span className="flex items-center gap-2.5">
                  <ColorChip color={game.user_color} />
                  <span className="font-semibold text-ink">{game.opponent}</span>
                  {game.opponent_rating && <span className="text-muted">({game.opponent_rating})</span>}
                </span>
              </td>
              <td>
                <span className={`badge ${RESULT_STYLES[game.user_result]}`}>{capitalize(game.user_result)}</span>
              </td>
              <td className="max-w-xs truncate text-ink-2" title={game.opening ?? ''}>
                {game.opening ?? '—'}
              </td>
              <td className="whitespace-nowrap text-ink-2">
                {capitalize(game.time_class)} · {formatTimeControl(game.time_control)}
              </td>
              <td className="whitespace-nowrap">
                <AccuracyCell game={game} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
