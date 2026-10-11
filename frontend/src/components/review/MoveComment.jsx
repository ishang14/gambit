import { CLASSIFICATION_STYLES } from '../../utils/classification.js'

/** One line about the move that led to the current position. */
export default function MoveComment({ move, ply }) {
  if (!move) {
    return (
      <p className="rounded-xl bg-panel-2 px-4 py-3 text-sm text-muted">
        Starting position. Use ← → to step through the game.
      </p>
    )
  }

  const style = CLASSIFICATION_STYLES[move.classification]
  const number = `${Math.ceil(ply / 2)}${move.color === 'white' ? '.' : '...'}`
  const missedBetter = move.classification !== 'best' && move.best_move_san

  return (
    <p className="rounded-xl bg-panel-2 px-4 py-3 text-sm text-ink-2" aria-live="polite">
      <span className="font-bold text-ink">
        {number} {move.move_san}
      </span>{' '}
      <span className={`badge ${style.badge}`}>{style.label}</span>
      {move.win_chance_loss >= 1 && (
        <span className="text-muted"> (−{move.win_chance_loss.toFixed(1)}% win chance)</span>
      )}
      {missedBetter && (
        <>
          . Best was <span className="font-bold text-brand">{move.best_move_san}</span>
        </>
      )}
      .
    </p>
  )
}
