import ResultBar from './ResultBar.jsx'

function Badge({ className, children }) {
  return <span className={`badge ml-2 ${className}`}>{children}</span>
}

/** Moves played from the current position, most common first. */
export default function MovesTable({ position, onSelect }) {
  if (position.moves.length === 0) {
    return <p className="text-sm text-muted">No moves here with enough games. Try lowering “Min games”.</p>
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-line">
      <table className="data-table">
        <caption className="bg-panel-2 px-4 pt-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">
          {position.user_to_move ? 'Your moves' : "Opponents' replies"}
        </caption>
        <thead>
          <tr>
            <th>Move</th>
            <th>Games</th>
            <th>Results</th>
            <th>Score</th>
            <th title="Average win chance lost by the move (analyzed games only)">
              Avg loss
            </th>
          </tr>
        </thead>
        <tbody>
          {position.moves.map((move) => (
            <tr key={move.uci} className={move.is_leak ? 'bg-danger/10' : ''}>
              <td className="whitespace-nowrap">
                <button
                  type="button"
                  onClick={() => onSelect(move)}
                  className="text-base font-bold text-brand hover:underline"
                >
                  {move.san}
                </button>
                {move.is_leak && <Badge className="bg-danger/15 text-danger">Leak</Badge>}
                {move.leaves_book && <Badge className="bg-warning/15 text-warning">Leaves book</Badge>}
              </td>
              <td className="tabular-nums">{move.games}</td>
              <td>
                <ResultBar wins={move.wins} draws={move.draws} losses={move.losses} />
              </td>
              <td className="font-semibold tabular-nums text-ink">{Math.round(move.score * 100)}%</td>
              <td className="tabular-nums text-ink-2">
                {move.avg_win_chance_loss != null ? `−${move.avg_win_chance_loss.toFixed(1)}%` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
