import { Link } from 'react-router-dom'
import { formatLine, moveNumber } from '../../utils/moves.js'

function LeakDetails({ leak }) {
  const parts = [`${Math.round(leak.score * 100)}% score`]
  if (leak.avg_win_chance_loss != null) parts.push(`−${leak.avg_win_chance_loss.toFixed(1)}% win chance on average`)
  return <p className="text-xs text-muted">{parts.join(' · ')}</p>
}

/** Ranked list of opening leaks; clicking one jumps the explorer to it. */
export default function LeaksPanel({ leaks, onSelect }) {
  return (
    <section className="card space-y-4 p-5">
      <h2 className="font-semibold text-ink">Opening leaks</h2>
      {leaks.length === 0 ? (
        <p className="text-sm text-muted">
          No leaks found. A leak is a position you keep reaching where your usual move scores poorly or the engine
          says it loses a lot. Import and analyze more games to find them.
        </p>
      ) : (
        <ol className="space-y-3">
          {leaks.map((leak, index) => (
            <li key={`${leak.fen_key}-${leak.move_uci}`} className="rounded-xl border border-line bg-panel-2 p-3 transition hover:border-danger/50">
              <button type="button" onClick={() => onSelect(leak)} className="w-full text-left">
                <span className="badge mr-1 bg-danger/15 text-danger">#{index + 1}</span>{' '}
                <span className="text-sm font-semibold text-ink">{leak.opening_name ?? 'Unnamed line'}</span>
                <span className="block text-sm text-ink-2">{formatLine(leak.path.map((s) => s.san)) || 'Start'}</span>
                <span className="mt-1 block text-sm text-ink-2">
                  You played{' '}
                  <span className="font-semibold text-danger">
                    {moveNumber(leak.path.length)} {leak.move_san}
                  </span>{' '}
                  in {leak.games} of {leak.position_games} games
                  {leak.best_move_san && leak.best_move_san !== leak.move_san && (
                    <>
                      ; engine prefers <span className="font-semibold text-brand">{leak.best_move_san}</span>
                    </>
                  )}
                  .
                </span>
              </button>
              <div className="mt-2 flex items-center justify-between gap-2">
                <LeakDetails leak={leak} />
                {leak.example_game_id && (
                  <Link to={`/games/${leak.example_game_id}`} className="text-xs font-semibold text-brand hover:underline">
                    Example game
                  </Link>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
