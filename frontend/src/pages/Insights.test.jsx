import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { cloneElement } from 'react'
import { callsTo } from '../test/mockApi.js'
import { loggedInWith, renderApp } from '../test/renderApp.jsx'

// ResponsiveContainer measures its parent, which is 0x0 in jsdom; give charts a fixed size.
vi.mock('recharts', async (importOriginal) => {
  const recharts = await importOriginal()
  return { ...recharts, ResponsiveContainer: ({ children }) => cloneElement(children, { width: 800, height: 300 }) }
})

function results(games, wins, draws, losses) {
  return { games, wins, draws, losses, score: games ? (wins + draws / 2) / games : null }
}

const SUMMARY = {
  ...results(40, 20, 8, 12),
  by_color: { white: results(22, 13, 4, 5), black: results(18, 7, 4, 7) },
  analyzed_games: 30,
  avg_accuracy: 84.25,
  inaccuracies_per_game: 3.1,
  mistakes_per_game: 1.2,
  blunders_per_game: 0.57,
}

const OPENINGS = {
  white: [
    { opening: 'Sicilian Defense', ...results(12, 8, 2, 2), avg_accuracy: 86.1 },
    { opening: 'Ruy Lopez', ...results(10, 5, 2, 3), avg_accuracy: null },
  ],
  black: [{ opening: "Queen's Gambit Declined", ...results(18, 7, 4, 7), avg_accuracy: 80.2 }],
}

const ACCURACY = {
  bucket: 'week',
  points: [
    { period: '2026-W36', games: 4, accuracy: 82.5, opponent_accuracy: 79.0 },
    { period: '2026-W37', games: 6, accuracy: 86.0, opponent_accuracy: 81.4 },
  ],
}

const MISTAKES = {
  analyzed_games: 30,
  phases: [
    { phase: 'opening', moves: 300, inaccuracies: 9, mistakes: 3, blunders: 1, inaccuracies_per_100: 3, mistakes_per_100: 1, blunders_per_100: 0.33 },
    { phase: 'middlegame', moves: 600, inaccuracies: 48, mistakes: 24, blunders: 12, inaccuracies_per_100: 8, mistakes_per_100: 4, blunders_per_100: 2 },
    { phase: 'endgame', moves: 0, inaccuracies: 0, mistakes: 0, blunders: 0, inaccuracies_per_100: null, mistakes_per_100: null, blunders_per_100: null },
  ],
}

function hours(overrides = {}) {
  return Array.from({ length: 24 }, (_, hour) => ({ hour, ...(overrides[hour] ?? results(0, 0, 0, 0)) }))
}

const TIME_OF_DAY = { timezone: 'Europe/London', hours: hours({ 9: results(4, 3, 0, 1), 21: results(2, 0, 1, 1) }) }

function api(overrides = {}) {
  const body = { SUMMARY, OPENINGS, ACCURACY, MISTAKES, TIME_OF_DAY, ...overrides }
  return loggedInWith({
    'GET /insights/summary': { body: body.SUMMARY },
    'GET /insights/openings': { body: body.OPENINGS },
    'GET /insights/accuracy': { body: body.ACCURACY },
    'GET /insights/mistakes': { body: body.MISTAKES },
    'GET /insights/time-of-day': { body: body.TIME_OF_DAY },
  })
}

function tableIn(title) {
  return within(screen.getByRole('region', { name: title })).getByRole('table', { hidden: true })
}

function rowsOf(table) {
  return within(table)
    .getAllByRole('row', { hidden: true })
    .slice(1)
    .map((row) => within(row).getAllByRole('cell', { hidden: true }).map((cell) => cell.textContent))
}

// The page is lazy-loaded; compile it once up front so the first test isn't timing the compiler.
beforeAll(() => import('./Insights.jsx'))
beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

it('shows the headline numbers', async () => {
  api()
  renderApp('/insights')

  expect(await screen.findByLabelText('Games')).toHaveTextContent('40')
  expect(screen.getByLabelText('Score')).toHaveTextContent('60%')
  expect(screen.getByText('20 won · 8 drawn · 12 lost')).toBeInTheDocument()
  expect(screen.getByLabelText('Score as White')).toHaveTextContent('68%')
  expect(screen.getByLabelText('Score as Black')).toHaveTextContent('50%')
  expect(screen.getByLabelText('Accuracy')).toHaveTextContent('84.3%')
  expect(screen.getByLabelText('Blunders per game')).toHaveTextContent('0.57')
})

it('has a table view for every chart', async () => {
  api()
  renderApp('/insights')
  await screen.findByLabelText('Games')

  expect(rowsOf(tableIn('Results by opening'))).toEqual([
    ['White', 'Sicilian Defense', '12', '8', '2', '2', '75%', '86.1%'],
    ['White', 'Ruy Lopez', '10', '5', '2', '3', '60%', '—'],
    ['Black', "Queen's Gambit Declined", '18', '7', '4', '7', '50%', '80.2%'],
  ])
  expect(rowsOf(tableIn('Accuracy over time'))).toEqual([
    ['Aug 31', '4', '82.5%', '79.0%'],
    ['Sep 7', '6', '86.0%', '81.4%'],
  ])
  expect(rowsOf(tableIn('Where your mistakes happen'))[1]).toEqual(['Middlegame', '600', '48', '24', '12', '8.0', '4.0', '2.0'])
  expect(rowsOf(tableIn('Results by time of day'))).toEqual([
    ['09:00', '4', '3', '0', '1', '75%'],
    ['21:00', '2', '0', '1', '1', '25%'],
  ])
})

it('labels charts with legends and draws them', async () => {
  api()
  renderApp('/insights')
  await screen.findByLabelText('Games')

  const openings = screen.getByRole('region', { name: 'Results by opening' })
  const legend = within(openings).getByRole('list', { name: 'Legend' })
  expect(within(legend).getAllByRole('listitem').map((item) => item.textContent)).toEqual(['Won', 'Drawn', 'Lost'])
  expect(openings.querySelectorAll('.recharts-bar-rectangle').length).toBeGreaterThan(0)
  const accuracy = screen.getByRole('region', { name: 'Accuracy over time' })
  expect(within(within(accuracy).getByRole('list', { name: 'Legend' })).getByText('Opponents')).toBeInTheDocument()
  // A single-series chart needs no legend: its title says what is plotted.
  expect(within(screen.getByRole('region', { name: 'Results by time of day' })).queryByRole('list', { name: 'Legend' })).toBeNull()
  expect(screen.getByText(/in your time zone \(Europe\/London\)/)).toBeInTheDocument()
})

it('sends the same filters to every insight', async () => {
  const fetchMock = api()
  renderApp('/insights')
  await screen.findByLabelText('Games')

  fireEvent.change(screen.getByLabelText('Time control'), { target: { value: 'blitz' } })
  fireEvent.change(screen.getByLabelText('Period'), { target: { value: 'all' } })

  await waitFor(() => {
    const latest = ['summary', 'openings', 'accuracy', 'mistakes', 'time-of-day'].map((name) =>
      callsTo(fetchMock, `/insights/${name}`).at(-1),
    )
    for (const url of latest) {
      expect(url.searchParams.get('time_class')).toBe('blitz')
      expect(url.searchParams.get('since')).toBeNull() // all time
      expect(url.searchParams.get('tz')).toBeTruthy()
    }
    expect(latest[2].searchParams.get('bucket')).toBe('month')
  })
})

it('defaults to the last 90 days by week', async () => {
  const fetchMock = api()
  renderApp('/insights')
  await screen.findByLabelText('Games')

  const accuracy = callsTo(fetchMock, '/insights/accuracy')[0]
  expect(accuracy.searchParams.get('since')).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  expect(accuracy.searchParams.get('bucket')).toBe('week')
  expect(screen.getByLabelText('Period')).toHaveValue('90d')
})

it('explains charts that need analyzed games', async () => {
  api({
    ACCURACY: { bucket: 'week', points: [] },
    MISTAKES: { analyzed_games: 0, phases: MISTAKES.phases },
    TIME_OF_DAY: { timezone: 'UTC', hours: hours() },
  })
  renderApp('/insights')
  await screen.findByLabelText('Games')

  expect(screen.getByText(/Analyze games to see your accuracy trend/)).toBeInTheDocument()
  expect(screen.getByText(/Analyze games to see where your mistakes happen/)).toBeInTheDocument()
  expect(screen.getByText(/No timed games in this period/)).toBeInTheDocument()
})

it('says when there are no games at all', async () => {
  api({ SUMMARY: { ...SUMMARY, ...results(0, 0, 0, 0), analyzed_games: 0 } })
  renderApp('/insights')

  expect(await screen.findByText(/No games in this period/)).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Import games' })).toHaveAttribute('href', '/import')
})
