import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { callsTo } from '../test/mockApi.js'
import { loggedInWith, renderApp } from '../test/renderApp.jsx'

vi.mock('react-chessboard', () => ({
  Chessboard: ({ options }) => (
    <div
      data-testid="board"
      data-fen={options.position}
      data-orientation={options.boardOrientation}
      data-arrows={JSON.stringify(options.arrows ?? [])}
    />
  ),
}))

const ROOT = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -'
const E4 = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -'
const E4E5 = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -'
const QH5 = 'rnbqkbnr/pppp1ppp/8/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR b KQkq -'
const NF3 = 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq -'

function move(san, uci, next, games, wins, extra = {}) {
  return {
    uci,
    san,
    next,
    games,
    wins,
    draws: 0,
    losses: games - wins,
    score: wins / games,
    analyzed: 0,
    avg_win_chance_loss: null,
    avg_cp_loss: null,
    best_move_san: null,
    in_book: true,
    leaves_book: false,
    is_leak: false,
    ...extra,
  }
}

function position(fenKey, games, userToMove, name, moves) {
  return { fen: `${fenKey} 0 1`, games, user_to_move: userToMove, in_book: true, name, moves }
}

const LEAK = {
  fen_key: E4E5,
  fen: `${E4E5} 0 1`,
  path: [
    { san: 'e4', uci: 'e2e4', fen_key: E4 },
    { san: 'e5', uci: 'e7e5', fen_key: E4E5 },
  ],
  opening_name: "King's Pawn Game",
  move_uci: 'd1h5',
  move_san: 'Qh5',
  games: 3,
  position_games: 5,
  wins: 0,
  draws: 0,
  losses: 3,
  score: 0,
  analyzed: 2,
  avg_win_chance_loss: 12.3,
  best_move_uci: 'g1f3',
  best_move_san: 'Nf3',
  reasons: ['poor_results', 'eval_loss'],
  impact: 150,
  example_game_id: 'game42',
}

function explorer(overrides = {}) {
  return {
    color: 'white',
    root: ROOT,
    games: 5,
    opening_plies: 20,
    positions: {
      [ROOT]: position(ROOT, 5, true, null, [move('e4', 'e2e4', E4, 5, 2)]),
      [E4]: position(E4, 5, false, "King's Pawn Game", [move('e5', 'e7e5', E4E5, 5, 2)]),
      [E4E5]: position(E4E5, 5, true, "King's Pawn Game", [
        move('Qh5', 'd1h5', QH5, 3, 0, { is_leak: true, analyzed: 2, avg_win_chance_loss: 12.3 }),
        move('Nf3', 'g1f3', NF3, 2, 2),
      ]),
    },
    leaks: [LEAK],
    ...overrides,
  }
}

const board = () => screen.getByTestId('board')

// The page is lazy-loaded; compile it once up front so the first test isn't timing the compiler.
beforeAll(() => import('./OpeningTree.jsx'))
beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

it('starts at the initial position as White', async () => {
  const fetchMock = loggedInWith({ 'GET /openings': { body: explorer() } })
  renderApp('/openings')

  expect(await screen.findByRole('button', { name: 'e4' })).toBeInTheDocument()
  expect(screen.getByText('5 games as White · first 10 moves of each game')).toBeInTheDocument()
  expect(board()).toHaveAttribute('data-fen', `${ROOT} 0 1`)
  expect(board()).toHaveAttribute('data-orientation', 'white')
  const request = callsTo(fetchMock, '/openings')[0]
  expect(request.searchParams.get('color')).toBe('white')
  expect(request.searchParams.get('min_games')).toBe('2')
})

it('walks down the tree and back with the breadcrumb', async () => {
  loggedInWith({ 'GET /openings': { body: explorer() } })
  renderApp('/openings')

  fireEvent.click(await screen.findByRole('button', { name: 'e4' }))
  expect(screen.getByRole('table', { name: "Opponents' replies" })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'e5' }))

  expect(screen.getByRole('table', { name: 'Your moves' })).toBeInTheDocument()
  expect(screen.getByRole('heading', { level: 2, name: "King's Pawn Game" })).toBeInTheDocument()
  expect(board()).toHaveAttribute('data-fen', `${E4E5} 0 1`)
  const qh5Row = screen.getByRole('button', { name: 'Qh5' }).closest('tr')
  expect(within(qh5Row).getByText('Leak')).toBeInTheDocument()
  expect(within(qh5Row).getByText('0%')).toBeInTheDocument()
  expect(within(qh5Row).getByText('−12.3%')).toBeInTheDocument()

  const line = screen.getByRole('navigation', { name: 'Current line' })
  fireEvent.click(within(line).getByRole('button', { name: 'Start' }))
  expect(board()).toHaveAttribute('data-fen', `${ROOT} 0 1`)
})

it('lists leaks and jumps to one with arrows for your move and the better one', async () => {
  loggedInWith({ 'GET /openings': { body: explorer() } })
  renderApp('/openings')

  const leaks = await screen.findByRole('heading', { name: 'Opening leaks' })
  const panel = leaks.closest('section')
  expect(within(panel).getByText('1. e4 e5')).toBeInTheDocument()
  expect(within(panel).getByText('2. Qh5')).toBeInTheDocument()
  expect(within(panel).getByText(/in 3 of 5 games/)).toBeInTheDocument()
  expect(within(panel).getByText('0% score · −12.3% win chance on average')).toBeInTheDocument()
  expect(within(panel).getByRole('link', { name: 'Example game' })).toHaveAttribute('href', '/games/game42')

  fireEvent.click(within(panel).getByText('1. e4 e5'))

  expect(board()).toHaveAttribute('data-fen', `${E4E5} 0 1`)
  expect(JSON.parse(board().dataset.arrows)).toEqual([
    { startSquare: 'd1', endSquare: 'h5', color: expect.any(String) },
    { startSquare: 'g1', endSquare: 'f3', color: expect.any(String) },
  ])
  const line = screen.getByRole('navigation', { name: 'Current line' })
  expect(within(line).getByRole('button', { name: 'e5' })).toHaveAttribute('aria-current', 'step')
})

it('switches color and min games', async () => {
  const fetchMock = loggedInWith({
    'GET /openings': (options, url) => ({
      body: explorer({ color: url.searchParams.get('color'), leaks: [] }),
    }),
  })
  renderApp('/openings')
  await screen.findByRole('button', { name: 'e4' })

  fireEvent.click(screen.getByRole('button', { name: 'As Black' }))
  await waitFor(() => expect(board()).toHaveAttribute('data-orientation', 'black'))
  fireEvent.change(screen.getByLabelText('Min games'), { target: { value: '5' } })

  await waitFor(() => {
    const last = callsTo(fetchMock, '/openings').at(-1)
    expect(last.searchParams.get('color')).toBe('black')
    expect(last.searchParams.get('min_games')).toBe('5')
  })
  expect(screen.getByRole('button', { name: 'As Black' })).toHaveAttribute('aria-pressed', 'true')
})

it('explains an empty tree', async () => {
  loggedInWith({
    'GET /openings': { body: explorer({ games: 0, positions: { [ROOT]: position(ROOT, 0, true, null, []) }, leaks: [] }) },
  })
  renderApp('/openings')

  expect(await screen.findByText('No games as White yet')).toBeInTheDocument()
  expect(screen.getByText('Import some games first.')).toBeInTheDocument()
})

it('explains when there are no leaks', async () => {
  loggedInWith({ 'GET /openings': { body: explorer({ leaks: [] }) } })
  renderApp('/openings')

  expect(await screen.findByText(/No leaks found/)).toBeInTheDocument()
})
