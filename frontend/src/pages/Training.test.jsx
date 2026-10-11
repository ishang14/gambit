import { fireEvent, screen, waitFor } from '@testing-library/react'
import { tryMove } from '../hooks/useTrainingSession.js'
import { loggedInWith, renderApp } from '../test/renderApp.jsx'

// The mock board records what it shows and lets a test "drop" a piece via globalThis.nextDrop.
vi.mock('react-chessboard', () => ({
  Chessboard: ({ options }) => (
    <div
      data-testid="board"
      data-fen={options.position}
      data-orientation={options.boardOrientation}
      data-dragging={String(options.allowDragging)}
      data-arrows={JSON.stringify(options.arrows ?? [])}
    >
      <button type="button" onClick={() => (globalThis.dropResult = options.onPieceDrop?.(globalThis.nextDrop))}>
        drop
      </button>
    </div>
  ),
}))

// Black to move after 1. e4 e5 2. Qh5 Nc6 3. Bc4: 3... Nf6?? was played, 3... g6 is best.
const FEN = 'r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3'

function makeCard(overrides = {}) {
  return {
    id: 'card1',
    source: 'blunder',
    fen: FEN,
    color: 'black',
    correct_move: 'g7g6',
    correct_move_san: 'g6',
    user_move: 'g8f6',
    user_move_san: 'Nf6',
    context: { game_id: 'game1', opponent: 'hero', played_at: '2026-09-15T12:00:00Z', move_number: '3...', win_chance_loss: 50.9 },
    ease: 2.5,
    interval: 0,
    repetitions: 0,
    due_at: '2026-10-10T00:00:00Z',
    last_reviewed_at: null,
    reviews: 0,
    lapses: 0,
    ...overrides,
  }
}

const LEAK_CARD = makeCard({
  id: 'card2',
  source: 'leak',
  context: { opening_name: "King's Pawn Game", path: ['e4', 'e5'], games: 3, position_games: 5, score: 0, example_game_id: 'g9' },
})

function makeStats(overrides = {}) {
  return {
    total: 2,
    due_now: 2,
    new: 2,
    learning: 0,
    mature: 0,
    by_source: { blunder: 1, leak: 1 },
    reviews_last_24h: 0,
    accuracy_last_7d: null,
    next_due_at: null,
    new_cards_per_day: 20,
    new_left_today: 20,
    ...overrides,
  }
}

function api({ cards = [makeCard(), LEAK_CARD], created = 0, stats = makeStats(), reviews = [] } = {}) {
  return loggedInWith({
    'POST /training/sync': { body: { created, total: stats.total } },
    'GET /training/due': { body: { due: cards.length, cards } },
    'GET /training/stats': { body: stats },
    'POST /training/cards/card1/review': (options) => {
      const body = JSON.parse(options.body)
      reviews.push(body)
      const correct = body.move === 'g7g6'
      return {
        body: {
          correct,
          played_san: correct ? 'g6' : 'Nf6',
          correct_move_san: 'g6',
          card: makeCard({ reviews: 1, repetitions: correct ? 1 : 0, lapses: correct ? 0 : 1 }),
        },
      }
    },
  })
}

function drop(from, to) {
  globalThis.nextDrop = { piece: { pieceType: 'bP', position: from, isSparePiece: false }, sourceSquare: from, targetSquare: to }
  fireEvent.click(screen.getByRole('button', { name: 'drop' }))
  return globalThis.dropResult
}

const board = () => screen.getByTestId('board')

// The page is lazy-loaded; compile it once up front so the first test isn't timing the compiler.
beforeAll(() => import('./Training.jsx'))
beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

it('tryMove handles legal, illegal and promotion moves', () => {
  expect(tryMove(FEN, 'g7', 'g6')).toMatchObject({ uci: 'g7g6', san: 'g6' })
  expect(tryMove(FEN, 'g7', 'g4')).toBeNull()
  expect(tryMove('8/P6k/8/8/8/8/8/K7 w - - 0 1', 'a7', 'a8')).toMatchObject({ uci: 'a7a8q', san: 'a8=Q' })
})

it('shows the first due card with its context and stats', async () => {
  api({ created: 2 })
  renderApp('/training')

  expect(await screen.findByRole('heading', { name: 'Black to move: find the best move' })).toBeInTheDocument()
  expect(screen.getByText('Added 2 new cards from your games.')).toBeInTheDocument()
  expect(screen.getByText(/Your game vs hero/)).toBeInTheDocument()
  expect(screen.getByText('2 left in this session')).toBeInTheDocument()
  expect(screen.getByLabelText('Due now')).toHaveTextContent('2')
  expect(board()).toHaveAttribute('data-fen', FEN)
  expect(board()).toHaveAttribute('data-orientation', 'black')
  expect(board()).toHaveAttribute('data-dragging', 'true')
  // The move from the game stays hidden until the card is answered.
  expect(screen.queryByText('In the game you played Nf6.')).not.toBeInTheDocument()
})

it('accepts the right move, asks for a rating and moves on', async () => {
  const reviews = []
  api({ reviews })
  renderApp('/training')
  await screen.findByRole('heading', { name: /find the best move/ })

  expect(drop('g7', 'g6')).toBe(true)

  expect(screen.getByRole('status')).toHaveTextContent("Correct: g6 is the engine's move.")
  expect(screen.getByText('In the game you played Nf6.')).toBeInTheDocument()
  expect(board().dataset.fen).toMatch(/^r1bqkbnr\/pppp1p1p\/2n3p1/)
  expect(board()).toHaveAttribute('data-dragging', 'false')

  fireEvent.click(screen.getByRole('button', { name: 'Good' }))

  expect(await screen.findByText(/King's Pawn Game · 1\. e4 e5/)).toBeInTheDocument()
  expect(reviews).toEqual([{ move: 'g7g6', rating: 'good' }])
  expect(screen.getByText('1 left in this session')).toBeInTheDocument()
})

it('explains a wrong move, shows both moves, and brings the card back', async () => {
  const reviews = []
  api({ cards: [makeCard()], reviews })
  renderApp('/training')
  await screen.findByRole('heading', { name: /find the best move/ })

  drop('g8', 'f6')

  expect(screen.getByRole('status')).toHaveTextContent("Not quite: Nf6 isn't the engine's move. Best was g6.")
  expect(board()).toHaveAttribute('data-fen', FEN)
  expect(JSON.parse(board().dataset.arrows)).toEqual([
    { startSquare: 'g8', endSquare: 'f6', color: expect.any(String) },
    { startSquare: 'g7', endSquare: 'g6', color: expect.any(String) },
  ])
  expect(screen.queryByRole('button', { name: 'Good' })).not.toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

  await waitFor(() => expect(reviews).toEqual([{ move: 'g8f6', rating: 'again' }]))
  // Same card again, fresh attempt.
  expect(await screen.findByText('Drag a piece to play your move.')).toBeInTheDocument()
  expect(screen.getByText('1 left in this session')).toBeInTheDocument()
})

it('ignores illegal moves', async () => {
  api()
  renderApp('/training')
  await screen.findByRole('heading', { name: /find the best move/ })

  expect(drop('g7', 'g4')).toBe(false)
  expect(drop('g7', null)).toBe(false)
  expect(screen.queryByRole('status')).not.toBeInTheDocument()
})

it('show answer counts as a miss', async () => {
  const reviews = []
  api({ cards: [makeCard()], reviews })
  renderApp('/training')
  await screen.findByRole('heading', { name: /find the best move/ })

  fireEvent.click(screen.getByRole('button', { name: 'Show answer' }))
  expect(screen.getByRole('status')).toHaveTextContent('The engine plays g6.')
  fireEvent.click(screen.getByRole('button', { name: 'Continue' }))

  await waitFor(() => expect(reviews).toEqual([{ move: 'g8f6', rating: 'again' }]))
})

it('says when there are no cards at all', async () => {
  api({ cards: [], stats: makeStats({ total: 0, due_now: 0, new: 0 }) })
  renderApp('/training')

  expect(await screen.findByText('No training cards yet.')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Analyze some games' })).toHaveAttribute('href', '/games')
})

it('says when everything is done for now', async () => {
  api({ cards: [], stats: makeStats({ due_now: 0, next_due_at: '2026-10-11T09:00:00Z' }) })
  renderApp('/training')

  expect(await screen.findByText('All caught up!')).toBeInTheDocument()
  expect(screen.getByText(/Next review due/)).toBeInTheDocument()
  expect(screen.queryByText(/new cards a day/)).not.toBeInTheDocument()
})

it('explains new cards held back by the daily limit', async () => {
  api({ cards: [], stats: makeStats({ due_now: 0, new: 12, new_left_today: 0 }) })
  renderApp('/training')

  expect(await screen.findByText(/12 new cards are waiting\. You start up to 20 new cards a day/)).toBeInTheDocument()
})
