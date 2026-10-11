import { fireEvent, screen, waitFor } from '@testing-library/react'
import { callsTo } from '../test/mockApi.js'
import { loggedInWith, renderApp } from '../test/renderApp.jsx'
import { makeGame as makeReviewGame } from '../test/reviewFixtures.js'
import { listRefresh } from './GameList.jsx'

vi.mock('react-chessboard', () => ({ Chessboard: () => <div data-testid="board" /> }))

function makeGame(overrides = {}) {
  return {
    id: 'g1',
    source_url: 'https://www.chess.com/game/live/1',
    white: 'hikaru',
    black: 'rival',
    white_rating: 1500,
    black_rating: 1480,
    user_color: 'white',
    user_rating: 1500,
    opponent: 'rival',
    opponent_rating: 1480,
    result: '1-0',
    user_result: 'win',
    time_control: '600',
    time_class: 'rapid',
    rated: true,
    played_at: '2026-09-15T12:00:00Z',
    eco: 'B20',
    opening: 'Sicilian Defense',
    ply_count: 60,
    analysis_status: 'none',
    accuracy: null,
    ...overrides,
  }
}

function gamesResponse(items, total = items.length) {
  return { body: { items, total } }
}

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

it('shows games in a table', async () => {
  loggedInWith({
    'GET /games': gamesResponse([
      makeGame(),
      makeGame({
        id: 'g2',
        opponent: 'other',
        opponent_rating: 1610,
        user_result: 'loss',
        analysis_status: 'done',
        accuracy: 87.25,
        opening: 'French Defense',
      }),
    ]),
  })
  renderApp('/games')

  expect(await screen.findByText('rival')).toBeInTheDocument()
  expect(screen.getByText('(1480)')).toBeInTheDocument()
  expect(screen.getByText('Win')).toBeInTheDocument()
  expect(screen.getByText('Loss')).toBeInTheDocument()
  expect(screen.getByText('Sicilian Defense')).toBeInTheDocument()
  expect(screen.getAllByText('Rapid · 10 min')).toHaveLength(2)
  expect(screen.getByText('87.3%')).toBeInTheDocument()
  expect(screen.getByText('1–2 of 2')).toBeInTheDocument()
})

it('opens a game when its row is clicked', async () => {
  loggedInWith({
    'GET /games': gamesResponse([makeGame({ id: 'abc' })]),
    'GET /games/abc': { body: makeReviewGame({ id: 'abc' }) },
  })
  renderApp('/games')

  fireEvent.click(await screen.findByText('rival'))

  expect(await screen.findByRole('heading', { level: 1, name: 'Game Review' })).toBeInTheDocument()
})

it('sends filters to the API', async () => {
  const fetchMock = loggedInWith({ 'GET /games': gamesResponse([makeGame()]) })
  renderApp('/games')
  await screen.findByText('rival')

  fireEvent.change(screen.getByLabelText('Result'), { target: { value: 'loss' } })
  fireEvent.change(screen.getByLabelText('Opening'), { target: { value: 'Sicilian' } })

  await waitFor(() => {
    const last = callsTo(fetchMock, '/games').at(-1)
    expect(last.searchParams.get('result')).toBe('loss')
    expect(last.searchParams.get('opening')).toBe('Sicilian')
  })
})

it('pages through results', async () => {
  const fetchMock = loggedInWith({ 'GET /games': gamesResponse([makeGame()], 30) })
  renderApp('/games')
  await screen.findByText('1–25 of 30')

  fireEvent.click(screen.getByRole('button', { name: 'Next' }))

  await screen.findByText('26–30 of 30')
  const last = callsTo(fetchMock, '/games').at(-1)
  expect(last.searchParams.get('offset')).toBe('25')
  expect(last.searchParams.get('limit')).toBe('25')
})

it('reads filters from the URL', async () => {
  const fetchMock = loggedInWith({ 'GET /games': gamesResponse([makeGame()]) })
  renderApp('/games?color=black&time_class=blitz')
  await screen.findByText('rival')

  const first = callsTo(fetchMock, '/games')[0]
  expect(first.searchParams.get('color')).toBe('black')
  expect(first.searchParams.get('time_class')).toBe('blitz')
  expect(screen.getByLabelText('Color')).toHaveValue('black')
})

it('points new users to the import page', async () => {
  loggedInWith({ 'GET /games': gamesResponse([]) })
  renderApp('/games')

  expect(await screen.findByRole('link', { name: 'Import your games' })).toHaveAttribute('href', '/import')
})

it('says when no games match the filters', async () => {
  loggedInWith({ 'GET /games': gamesResponse([]) })
  renderApp('/games?result=draw')

  expect(await screen.findByText('No games match these filters')).toBeInTheDocument()
})

it('shows analysis status in the accuracy column', async () => {
  loggedInWith({
    'GET /games': gamesResponse([
      makeGame({ id: 'a', analysis_status: 'queued' }),
      makeGame({ id: 'b', opponent: 'two', analysis_status: 'running' }),
      makeGame({ id: 'c', opponent: 'three', analysis_status: 'failed' }),
      makeGame({ id: 'd', opponent: 'four', analysis_status: 'done', accuracy: 91.04 }),
    ]),
  })
  renderApp('/games')

  expect(await screen.findByText('Queued')).toBeInTheDocument()
  expect(screen.getByText('Analyzing…')).toBeInTheDocument()
  expect(screen.getByText('Failed')).toBeInTheDocument()
  expect(screen.getByText('91.0%')).toBeInTheDocument()
})

it('queues all games and refreshes until they are analyzed', async () => {
  listRefresh.intervalMs = 10
  let queued = false
  let listCalls = 0
  loggedInWith({
    'POST /analysis/queue-all': () => {
      queued = true
      return { body: { queued: 1 } }
    },
    'GET /games': () => {
      listCalls += 1
      if (!queued) return gamesResponse([makeGame()])
      // Queued on the first refresh, done on the next.
      const status = listCalls <= 2 ? 'queued' : 'done'
      return gamesResponse([makeGame({ analysis_status: status, accuracy: status === 'done' ? 88 : null })])
    },
  })
  renderApp('/games')
  await screen.findByText('rival')

  fireEvent.click(screen.getByRole('button', { name: 'Analyze all' }))

  expect(await screen.findByRole('status')).toHaveTextContent('Queued 1 game for analysis.')
  expect(await screen.findByText('88.0%')).toBeInTheDocument()
})
