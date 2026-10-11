/** Name, rating and (once analyzed) accuracy for one side, shown above/below the board. */
export default function PlayerBar({ game, color, analysis }) {
  const name = color === 'white' ? game.white : game.black
  const rating = color === 'white' ? game.white_rating : game.black_rating
  const accuracy = analysis?.accuracy?.[color]
  const you = game.user_color === color
  const chip = color === 'white' ? 'bg-[#f4f1e6] border-black/20' : 'bg-[#2b2824] border-white/20'

  return (
    <div className="flex items-center justify-between gap-3 px-1">
      <div className="flex min-w-0 items-center gap-2.5">
        <span aria-hidden="true" className={`h-4 w-4 shrink-0 rounded-[5px] border ${chip}`} />
        <span className="truncate font-semibold text-ink">{name}</span>
        {rating && <span className="text-sm text-muted">({rating})</span>}
        {you && <span className="badge bg-brand/15 text-brand">You</span>}
      </div>
      {accuracy != null && (
        <span className="badge bg-raised text-ink-2 tabular-nums" title="Accuracy in this game">
          {accuracy.toFixed(1)}%
        </span>
      )}
    </div>
  )
}
