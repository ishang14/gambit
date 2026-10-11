/** Win / draw / loss split as a thin stacked bar, from the user's side. */
export default function ResultBar({ wins, draws, losses }) {
  const total = wins + draws + losses || 1
  const part = (count) => `${(count / total) * 100}%`
  return (
    <div
      className="flex h-2.5 w-28 gap-0.5 overflow-hidden rounded-full bg-raised"
      title={`${wins} won · ${draws} drawn · ${losses} lost`}
      aria-label={`${wins} won, ${draws} drawn, ${losses} lost`}
      role="img"
    >
      <div style={{ width: part(wins), background: 'var(--viz-win)' }} />
      <div style={{ width: part(draws), background: 'var(--viz-draw)' }} />
      <div style={{ width: part(losses), background: 'var(--viz-loss)' }} />
    </div>
  )
}
