import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchOpenings } from '../api/openings.js'
import ChessBoard from '../components/ChessBoard.jsx'
import LeaksPanel from '../components/openings/LeaksPanel.jsx'
import MovesTable from '../components/openings/MovesTable.jsx'
import PathBreadcrumb from '../components/openings/PathBreadcrumb.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Spinner from '../components/ui/Spinner.jsx'
import { capitalize } from '../utils/format.js'
import { fenFromKey } from '../utils/moves.js'

const MIN_GAMES_OPTIONS = [1, 2, 3, 5, 10]
const LEAK_ARROW = 'rgba(220, 38, 38, 0.8)'
const BEST_ARROW = 'rgba(22, 163, 74, 0.8)'

function arrow(uci, color) {
  return { startSquare: uci.slice(0, 2), endSquare: uci.slice(2, 4), color }
}

function Controls({ color, minGames, onChange }) {
  const tab = (active) =>
    `px-4 py-2 text-sm font-semibold transition ${active ? 'bg-brand text-on-brand' : 'bg-panel-2 text-ink-2 hover:bg-raised hover:text-ink'}`
  return (
    <div className="card flex flex-wrap items-center gap-4 p-4">
      <div role="group" aria-label="Color" className="flex overflow-hidden rounded-lg border border-line">
        {['white', 'black'].map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={color === option}
            onClick={() => onChange({ color: option })}
            className={tab(color === option)}
          >
            As {capitalize(option)}
          </button>
        ))}
      </div>
      <label className="flex items-center gap-2 text-sm font-medium text-ink-2">
        Min games
        <select
          value={minGames}
          onChange={(event) => onChange({ min_games: event.target.value })}
          className="input !w-auto"
        >
          {MIN_GAMES_OPTIONS.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}

export default function OpeningTree() {
  const [searchParams, setSearchParams] = useSearchParams()
  const color = searchParams.get('color') === 'black' ? 'black' : 'white'
  const minGames = Number(searchParams.get('min_games')) || 2

  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  // The line being explored: [{ san, uci, fen_key }], fen_key = position after the move.
  const [path, setPath] = useState([])

  useEffect(() => {
    let cancelled = false
    setError(null)
    fetchOpenings({ color, minGames })
      .then((body) => !cancelled && setData(body))
      .catch((err) => !cancelled && setError(err.message))
    return () => {
      cancelled = true
    }
  }, [color, minGames])

  function changeSettings(changes) {
    if (changes.color && changes.color !== color) setPath([])
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      for (const [key, value] of Object.entries(changes)) next.set(key, value)
      return next
    })
  }

  const header = (
    <div className="space-y-5">
      <PageHeader
        title="Opening Tree"
        description="Every position from the first moves of your games, with how each move has worked out for you."
      />
      <Controls color={color} minGames={minGames} onChange={changeSettings} />
    </div>
  )

  if (error) {
    return (
      <div className="space-y-6">
        {header}
        <p role="alert" className="alert alert-danger">
          {error}
        </p>
      </div>
    )
  }
  if (!data || data.color !== color) {
    return (
      <div className="space-y-6">
        {header}
        <Spinner>Building your opening tree…</Spinner>
      </div>
    )
  }
  if (data.games === 0) {
    return (
      <div className="space-y-6">
        {header}
        <EmptyState title={`No games as ${capitalize(color)} yet`} glyph="♙">
          Import some games first.
        </EmptyState>
      </div>
    )
  }

  const currentKey = path.length > 0 ? path[path.length - 1].fen_key : data.root
  const position = data.positions[currentKey]
  const lineKeys = [data.root, ...path.map((step) => step.fen_key)]
  const openingName = lineKeys.reduce((name, key) => data.positions[key]?.name ?? name, null)
  const leaksHere = data.leaks.filter((leak) => leak.fen_key === currentKey)
  const arrows = leaksHere.flatMap((leak) => [
    arrow(leak.move_uci, LEAK_ARROW),
    ...(leak.best_move_uci && leak.best_move_uci !== leak.move_uci ? [arrow(leak.best_move_uci, BEST_ARROW)] : []),
  ])

  function selectMove(move) {
    setPath([...path, { san: move.san, uci: move.uci, fen_key: move.next }])
  }

  return (
    <div className="space-y-6">
      {header}
      <p className="text-sm text-muted">
        {data.games} games as {capitalize(color)} · first {data.opening_plies / 2} moves of each game
      </p>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,480px)_1fr]">
        <div className="space-y-6">
          <div className="card p-4">
            <ChessBoard
              options={{
                id: 'opening-board',
                position: position?.fen ?? fenFromKey(currentKey),
                boardOrientation: color,
                arrows,
              }}
            />
          </div>
          <LeaksPanel leaks={data.leaks} onSelect={(leak) => setPath(leak.path)} />
        </div>

        <div className="card space-y-5 p-5">
          <PathBreadcrumb path={path} onSelect={(length) => setPath(path.slice(0, length))} />
          <div>
            <h2 className="text-xl font-bold tracking-tight text-ink">{openingName ?? 'Starting position'}</h2>
            {position && (
              <p className="text-sm text-muted">
                Reached in {position.games} {position.games === 1 ? 'game' : 'games'}
                {!position.in_book && ' · out of book'}
              </p>
            )}
          </div>
          {position ? (
            <MovesTable position={position} onSelect={selectMove} />
          ) : (
            <p className="text-sm text-muted">
              The moves leading here were played fewer than {minGames} times, so this position isn&apos;t in the tree
              at this setting. Lower “Min games” to see it.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
