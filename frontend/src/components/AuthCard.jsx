import Logo from './ui/Logo.jsx'
import ThemeToggle from './ui/ThemeToggle.jsx'

const FILES = 8
const RANKS = 8

/** A decorative board with a short opening line highlighted. Purely visual. */
function ShowcaseBoard() {
  const highlighted = new Set(['4,4', '3,4', '5,5', '2,5']) // [file,rank]: e4/e5/Nf3/Nc6-ish squares
  const squares = []
  for (let rank = RANKS - 1; rank >= 0; rank--) {
    for (let file = 0; file < FILES; file++) {
      const dark = (file + rank) % 2 === 0
      const lit = highlighted.has(`${file},${rank}`)
      squares.push(
        <div
          key={`${file}${rank}`}
          className={`aspect-square ${dark ? 'bg-[#6b9150]' : 'bg-[#eaecd2]'} ${lit ? 'brightness-110 saturate-150' : ''}`}
          style={lit ? { boxShadow: 'inset 0 0 0 100px rgba(250, 204, 21, 0.38)' } : undefined}
        />,
      )
    }
  }
  return (
    <div
      aria-hidden="true"
      className="mx-auto w-full max-w-72 -rotate-6 overflow-hidden rounded-xl shadow-2xl ring-1 ring-black/20"
    >
      <div className="grid grid-cols-8">{squares}</div>
    </div>
  )
}

const POINTS = [
  'Stockfish reviews every move of your chess.com games',
  'Spot the openings where you keep losing points',
  'Drill your own mistakes until they stop happening',
]

/** Sign-in / sign-up layout: a brand panel beside the form. */
export default function AuthCard({ title, error, onSubmit, submitLabel, submitting, footer, children }) {
  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-2">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-panel p-12 lg:flex">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-brand/15 blur-3xl" aria-hidden="true" />
        <Logo />
        <div className="relative space-y-10">
          <ShowcaseBoard />
          <div className="space-y-3">
            <p className="text-3xl font-extrabold leading-tight tracking-tight text-ink">
              Learn from every game you play.
            </p>
            <ul className="space-y-2 text-ink-2">
              {POINTS.map((point) => (
                <li key={point} className="flex items-start gap-2.5">
                  <span aria-hidden="true" className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand" />
                  {point}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <p className="relative text-xs text-muted">Uses public chess.com game data. Not affiliated with chess.com.</p>
      </aside>

      <main className="relative flex flex-col justify-center px-4 py-12 sm:px-12">
        <div className="absolute right-4 top-4">
          <ThemeToggle />
        </div>
        <form onSubmit={onSubmit} className="mx-auto w-full max-w-sm space-y-5">
          <div className="space-y-4">
            <Logo className="lg:hidden" />
            <h1 className="text-3xl font-extrabold tracking-tight text-ink">{title}</h1>
          </div>
          {error && (
            <p role="alert" className="alert alert-danger">
              {error}
            </p>
          )}
          {children}
          <button type="submit" disabled={submitting} className="btn btn-primary w-full !py-2.5">
            {submitting ? 'Please wait…' : submitLabel}
          </button>
          <p className="text-center text-sm text-ink-2">{footer}</p>
        </form>
      </main>
    </div>
  )
}
