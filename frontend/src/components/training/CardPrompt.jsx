import { Link } from 'react-router-dom'
import { capitalize, formatDate } from '../../utils/format.js'
import { formatLine } from '../../utils/moves.js'

function SourceBadge({ source }) {
  return source === 'leak' ? (
    <span className="badge bg-warning/15 text-warning">Opening leak</span>
  ) : (
    <span className="badge bg-danger/15 text-danger">Blunder</span>
  )
}

function Context({ card }) {
  const { context } = card
  if (card.source === 'leak') {
    return (
      <p className="text-sm text-ink-2">
        {context.opening_name ?? 'Opening'}
        {context.path.length > 0 && <> · {formatLine(context.path)}</>}
      </p>
    )
  }
  return (
    <p className="text-sm text-ink-2">
      {context.opponent ? `Your game vs ${context.opponent}` : 'Your game'}
      {context.played_at && <>, {formatDate(context.played_at)}</>} · move {context.move_number}{' '}
      {context.game_id && (
        <Link to={`/games/${context.game_id}`} className="font-semibold text-brand hover:underline">
          Open game
        </Link>
      )}
    </p>
  )
}

/** What the card is and what to do. Once answered, also what the user did before. */
export default function CardPrompt({ card, answered }) {
  const { context } = card
  return (
    <div className="space-y-2">
      <SourceBadge source={card.source} />
      <h2 className="text-xl font-bold tracking-tight text-ink">{capitalize(card.color)} to move: find the best move</h2>
      <Context card={card} />
      {answered && (
        <p className="text-sm text-ink-2">
          {card.source === 'leak'
            ? `You've played ${card.user_move_san} here in ${context.games} of ${context.position_games} games.`
            : `In the game you played ${card.user_move_san}.`}
        </p>
      )}
    </div>
  )
}
