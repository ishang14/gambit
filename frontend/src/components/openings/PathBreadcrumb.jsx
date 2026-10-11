import { moveNumber } from '../../utils/moves.js'

/** "Start 1. e4 e5 2. Nf3": click any step to go back to it. */
export default function PathBreadcrumb({ path, onSelect }) {
  const link = 'rounded-md px-1.5 py-0.5 text-ink-2 transition hover:bg-raised hover:text-ink'
  return (
    <nav aria-label="Current line" className="flex flex-wrap items-center gap-x-0.5 gap-y-1 rounded-xl bg-panel-2 px-3 py-2 text-sm">
      <button type="button" onClick={() => onSelect(0)} className={`${link} ${path.length === 0 ? '!text-ink font-bold' : ''}`}>
        Start
      </button>
      {path.map((step, index) => (
        <span key={`${index}-${step.uci}`} className="flex items-center">
          {index % 2 === 0 && <span className="text-muted">{moveNumber(index)}</span>}
          <button
            type="button"
            onClick={() => onSelect(index + 1)}
            aria-current={index === path.length - 1 ? 'step' : undefined}
            className={`${link} ${index === path.length - 1 ? '!text-brand font-bold' : ''}`}
          >
            {step.san}
          </button>
        </span>
      ))}
    </nav>
  )
}
