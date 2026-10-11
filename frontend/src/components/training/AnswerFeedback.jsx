import Icon from '../ui/Icon.jsx'

// Hard / Good / Easy, tinted so the scale reads at a glance. The hint is the tooltip.
const RATINGS = [
  { rating: 'hard', label: 'Hard', hint: 'Got it, but it took effort', tone: 'border-warning/40 text-warning hover:bg-warning/10' },
  { rating: 'good', label: 'Good', hint: 'Got it after some thought', tone: 'border-info/40 text-info hover:bg-info/10' },
  { rating: 'easy', label: 'Easy', hint: 'Knew it straight away', tone: 'border-brand/40 text-brand hover:bg-brand/10' },
]

/** Before an answer: a "show answer" button. After: the verdict and how to rate it. */
export default function AnswerFeedback({ card, attempt, submitting, onGiveUp, onRate }) {
  if (!attempt) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-panel-2 px-4 py-3">
        <p className="text-sm text-ink-2">Drag a piece to play your move.</p>
        <button type="button" onClick={onGiveUp} className="btn btn-secondary btn-sm">
          Show answer
        </button>
      </div>
    )
  }

  if (attempt.correct) {
    return (
      <div className="space-y-4" aria-live="polite">
        <p role="status" className="alert alert-success flex items-center gap-2.5 !px-4 !py-3 text-base">
          <Icon name="check" className="h-5 w-5 shrink-0" />
          <span>
            Correct: <span className="font-bold">{attempt.san}</span> is the engine&apos;s move.
          </span>
        </p>
        <div>
          <p className="mb-2 text-sm font-medium text-ink-2">How hard was it?</p>
          <div className="grid grid-cols-3 gap-2" role="group" aria-label="How hard was it?">
            {RATINGS.map(({ rating, label, hint, tone }) => (
              <button
                key={rating}
                type="button"
                title={hint}
                disabled={submitting}
                onClick={() => onRate(rating)}
                className={`btn border bg-panel-2 !py-3 ${tone}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4" aria-live="polite">
      <p role="status" className="alert alert-danger flex items-start gap-2.5 !px-4 !py-3 text-base">
        <Icon name="alert" className="mt-0.5 h-5 w-5 shrink-0" />
        <span>
          {attempt.gaveUp ? (
            'The engine plays '
          ) : (
            <>
              Not quite: <span className="font-bold">{attempt.san}</span> isn&apos;t the engine&apos;s move. Best
              was{' '}
            </>
          )}
          <span className="font-bold">{card.correct_move_san}</span>. This card will come back shortly.
        </span>
      </p>
      <button type="button" disabled={submitting} onClick={() => onRate('again')} className="btn btn-primary w-full !py-3">
        Continue
      </button>
    </div>
  )
}
