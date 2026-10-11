import { Link } from 'react-router-dom'
import ChessBoard from '../components/ChessBoard.jsx'
import AnswerFeedback from '../components/training/AnswerFeedback.jsx'
import CardPrompt from '../components/training/CardPrompt.jsx'
import TrainingStats from '../components/training/TrainingStats.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Spinner from '../components/ui/Spinner.jsx'
import { useTrainingSession } from '../hooks/useTrainingSession.js'

const PLAYED_ARROW = 'rgba(220, 38, 38, 0.85)'
const BEST_ARROW = 'rgba(22, 163, 74, 0.85)'

function arrow(uci, color) {
  return { startSquare: uci.slice(0, 2), endSquare: uci.slice(2, 4), color }
}

function formatWhen(iso) {
  return new Date(iso).toLocaleString('en-US', { weekday: 'short', hour: 'numeric', minute: '2-digit' })
}

function SessionOver({ stats }) {
  if (stats.total === 0) {
    return (
      <EmptyState title="No training cards yet." glyph="♜">
        Cards come from blunders in your analyzed games and from opening leaks.{' '}
        <Link to="/games" className="font-semibold text-brand hover:underline">
          Analyze some games
        </Link>{' '}
        and come back.
      </EmptyState>
    )
  }
  return (
    <EmptyState title="All caught up!" glyph="✓">
      {stats.next_due_at && <p>Next review due {formatWhen(stats.next_due_at)}.</p>}
      {stats.new > 0 && stats.new_left_today === 0 && (
        <p className="mt-1">
          {stats.new} new {stats.new === 1 ? 'card is' : 'cards are'} waiting. You start up to {stats.new_cards_per_day}{' '}
          new cards a day, so more will come in tomorrow.
        </p>
      )}
    </EmptyState>
  )
}

export default function Training() {
  const session = useTrainingSession()
  const { card, attempt, stats } = session

  // After a correct move, show it played. After a miss, show the position with both moves drawn.
  let position = card?.fen
  let arrows = []
  if (attempt?.correct) {
    position = attempt.fenAfter
  } else if (attempt && card) {
    arrows = [...(attempt.uci ? [arrow(attempt.uci, PLAYED_ARROW)] : []), arrow(card.correct_move, BEST_ARROW)]
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Training"
        description="Positions from your own games where you went wrong. Find the engine's move; cards you miss come back sooner (SM-2 spaced repetition)."
      />

      {session.status === 'loading' && <Spinner>Looking for new mistakes to practice…</Spinner>}
      {session.error && (
        <p role="alert" className="alert alert-danger">
          {session.error}
        </p>
      )}

      {session.status === 'ready' && (
        <>
          {stats && <TrainingStats stats={stats} />}
          {session.created > 0 && (
            <p className="alert alert-success">
              Added {session.created} new {session.created === 1 ? 'card' : 'cards'} from your games.
            </p>
          )}

          {card ? (
            <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,520px)_1fr]">
              <div className="card p-4">
                <ChessBoard
                  options={{
                    id: 'training-board',
                    position,
                    boardOrientation: card.color,
                    allowDragging: !attempt,
                    arrows,
                    onPieceDrop: ({ sourceSquare, targetSquare }) => session.play(sourceSquare, targetSquare),
                  }}
                />
              </div>
              <div className="card space-y-5 p-6">
                <p className="text-sm font-medium text-muted">{session.remaining} left in this session</p>
                <CardPrompt card={card} answered={Boolean(attempt)} />
                <AnswerFeedback
                  card={card}
                  attempt={attempt}
                  submitting={session.submitting}
                  onGiveUp={session.giveUp}
                  onRate={session.rate}
                />
              </div>
            </div>
          ) : (
            stats && <SessionOver stats={stats} />
          )}
        </>
      )}
    </div>
  )
}
