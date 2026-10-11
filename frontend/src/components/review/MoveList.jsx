import { useEffect, useRef } from 'react'
import { CLASSIFICATION_STYLES, CLASSIFICATION_SYMBOLS } from '../../utils/classification.js'

function MoveButton({ move, ply, current, classification, onSelect }) {
  if (!move) return <span />
  const style = classification ? CLASSIFICATION_STYLES[classification] : null
  const symbol = classification ? CLASSIFICATION_SYMBOLS[classification] : null
  return (
    <button
      type="button"
      onClick={() => onSelect(ply)}
      aria-current={current ? 'true' : undefined}
      aria-label={style ? `${move.san} (${style.label})` : move.san}
      title={style?.label}
      className={`rounded-md px-2 py-1 text-left font-medium transition-colors ${
        current ? 'bg-brand text-on-brand' : 'text-ink hover:bg-raised'
      } ${!current && style && symbol ? style.text : ''}`}
    >
      {move.san}
      {symbol && <span className="ml-0.5 font-bold">{symbol}</span>}
    </button>
  )
}

/** Moves in numbered pairs. `classifications[k]` labels the move that reaches ply k + 1. */
export default function MoveList({ moves, classifications, ply, onSelect }) {
  const listRef = useRef(null)

  useEffect(() => {
    listRef.current?.querySelector('[aria-current="true"]')?.scrollIntoView?.({ block: 'nearest' })
  }, [ply])

  const rows = []
  for (let i = 0; i < moves.length; i += 2) rows.push(i)

  return (
    <section className="card overflow-hidden">
      <h2 className="border-b border-line px-5 py-3 font-semibold text-ink">Moves</h2>
      <ol ref={listRef} aria-label="Moves" className="max-h-80 overflow-y-auto p-2 text-sm">
        {rows.map((i) => (
          <li key={i} className={`grid grid-cols-[2.5rem_1fr_1fr] items-center gap-1 rounded-md ${(i / 2) % 2 ? 'bg-panel-2/60' : ''}`}>
            <span className="pl-2 text-muted tabular-nums">{i / 2 + 1}.</span>
            <MoveButton
              move={moves[i]}
              ply={i + 1}
              current={ply === i + 1}
              classification={classifications?.[i]}
              onSelect={onSelect}
            />
            <MoveButton
              move={moves[i + 1]}
              ply={i + 2}
              current={ply === i + 2}
              classification={classifications?.[i + 1]}
              onSelect={onSelect}
            />
          </li>
        ))}
      </ol>
    </section>
  )
}
