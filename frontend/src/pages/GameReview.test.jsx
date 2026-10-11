import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { analysisPolling } from '../hooks/useAnalysisJob.js'
import { loggedInWith, renderApp } from '../test/renderApp.jsx'
import { makeGame, SCHOLARS_MATE_ANALYSIS, START_FEN } from '../test/reviewFixtures.js'

// The real board needs layout APIs jsdom lacks; record what it is asked to show instead.
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

const board = () => screen.getByTestId('board')

// The page is lazy-loaded; compile it once up front so the first test isn't timing the compiler.
beforeAll(() => import('./GameReview.jsx'))
beforeEach(() => {
  localStorage.clear()
  analysisPolling.intervalMs = 10
})
afterEach(() => vi.unstubAllGlobals())

function analyzedGame() {
  return loggedInWith({
    'GET /games/game1': { body: makeGame({ analysis_status: 'done', accuracy: 96.4 }) },
    'GET /games/game1/analysis': { body: SCHOLARS_MATE_ANALYSIS },
  })
}

describe('before analysis', () => {
  it('shows the game and lets you step through moves', async () => {
    loggedInWith({ 'GET /games/game1': { body: makeGame() } })
    renderApp('/games/game1')

    expect(await screen.findByRole('button', { name: 'Analyze with Stockfish' })).toBeInTheDocument()
    expect(board()).toHaveAttribute('data-fen', START_FEN)
    expect(board()).toHaveAttribute('data-orientation', 'white')
    expect(screen.queryByRole('meter', { name: 'Evaluation' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next move' }))
    expect(board().dataset.fen).toMatch(/^rnbqkbnr\/pppppppp\/8\/8\/4P3/)

    fireEvent.click(screen.getByRole('button', { name: 'Last move' }))
    expect(board().dataset.fen).toMatch(/^r1bqkb1r\/pppp1Qpp/)
    expect(screen.getByRole('button', { name: 'Next move' })).toBeDisabled()
  })

  it('supports arrow keys and clicking a move', async () => {
    loggedInWith({ 'GET /games/game1': { body: makeGame() } })
    renderApp('/games/game1')
    await screen.findByTestId('board')

    fireEvent.keyDown(window, { key: 'End' })
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    expect(within(screen.getByRole('list', { name: 'Moves' })).getByRole('button', { name: 'Nf6' })).toHaveAttribute(
      'aria-current',
      'true',
    )

    fireEvent.click(screen.getByRole('button', { name: 'e4' }))
    expect(board().dataset.fen).toMatch(/4P3/)
    fireEvent.keyDown(window, { key: 'Home' })
    expect(board()).toHaveAttribute('data-fen', START_FEN)
  })

  it('flips the board when you played black', async () => {
    loggedInWith({ 'GET /games/game1': { body: makeGame({ user_color: 'black' }) } })
    renderApp('/games/game1')

    expect(await screen.findByTestId('board')).toHaveAttribute('data-orientation', 'black')
  })
})

describe('running analysis', () => {
  it('queues a job, shows progress, then loads the results', async () => {
    let polls = 0
    let analyzed = false
    loggedInWith({
      'GET /games/game1': () => ({
        body: makeGame(analyzed ? { analysis_status: 'done', accuracy: 96.4 } : {}),
      }),
      'POST /games/game1/analysis': {
        status: 202,
        body: { job_id: 'job1', game_id: 'game1', status: 'queued', progress: 0 },
      },
      'GET /analysis/jobs/job1': () => {
        polls += 1
        if (polls === 1) return { body: { job_id: 'job1', game_id: 'game1', status: 'running', progress: 0.5 } }
        analyzed = true
        return { body: { job_id: 'job1', game_id: 'game1', status: 'done', progress: 1 } }
      },
      'GET /games/game1/analysis': { body: SCHOLARS_MATE_ANALYSIS },
    })
    renderApp('/games/game1')

    fireEvent.click(await screen.findByRole('button', { name: 'Analyze with Stockfish' }))

    expect(await screen.findByText(/Waiting for the engine|Analyzing… 50%/)).toBeInTheDocument()
    expect(await screen.findByLabelText('hikaru accuracy')).toHaveTextContent('96.4%')
    expect(screen.getByRole('meter', { name: 'Evaluation' })).toBeInTheDocument()
  })

  it('resumes polling a job that was already running', async () => {
    let analyzed = false
    loggedInWith({
      'GET /games/game1': () => ({
        body: makeGame(
          analyzed
            ? { analysis_status: 'done' }
            : { analysis_status: 'running', analysis_job_id: 'job9', analysis_progress: 0.3 },
        ),
      }),
      'GET /analysis/jobs/job9': () => {
        analyzed = true
        return { body: { job_id: 'job9', game_id: 'game1', status: 'done', progress: 1 } }
      },
      'GET /games/game1/analysis': { body: SCHOLARS_MATE_ANALYSIS },
    })
    renderApp('/games/game1')

    expect(await screen.findByText('Analyzing… 30%')).toBeInTheDocument()
    expect(await screen.findByLabelText('villain accuracy')).toHaveTextContent('68.2%')
  })

  it('shows a failed analysis with a retry button', async () => {
    loggedInWith({
      'GET /games/game1': { body: makeGame({ analysis_status: 'failed', analysis_error: 'engine crashed' }) },
    })
    renderApp('/games/game1')

    expect(await screen.findByText('Analysis failed: engine crashed.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

describe('after analysis', () => {
  it('shows accuracy and move counts', async () => {
    analyzedGame()
    renderApp('/games/game1')

    expect(await screen.findByLabelText('hikaru accuracy')).toHaveTextContent('96.4%')
    expect(screen.getByLabelText('villain accuracy')).toHaveTextContent('68.2%')
    expect(screen.getByText('Stockfish, depth 14')).toBeInTheDocument()
  })

  it('labels the moves and explains the current one', async () => {
    analyzedGame()
    renderApp('/games/game1')

    const nf6 = await screen.findByRole('button', { name: 'Nf6 (Blunder)' })
    fireEvent.click(nf6)

    expect(screen.getByText(/−50\.9% win chance/)).toBeInTheDocument()
    expect(screen.getByText('Blunder', { selector: 'span' })).toBeInTheDocument()
    expect(screen.getByText('g6')).toBeInTheDocument()
  })

  it('updates the eval bar as you move', async () => {
    analyzedGame()
    renderApp('/games/game1')
    const meter = await screen.findByRole('meter', { name: 'Evaluation' })

    expect(meter).toHaveAttribute('aria-valuetext', '+0.3')
    fireEvent.keyDown(window, { key: 'End' })
    await waitFor(() => expect(meter).toHaveAttribute('aria-valuetext', '1-0'))
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    expect(meter).toHaveAttribute('aria-valuetext', 'M1')
  })

  it("draws the engine's best move for the current position", async () => {
    analyzedGame()
    renderApp('/games/game1')
    await screen.findByRole('meter', { name: 'Evaluation' })

    fireEvent.click(screen.getByRole('button', { name: 'Nf6 (Blunder)' }))

    expect(JSON.parse(board().dataset.arrows)).toEqual([
      { startSquare: 'h5', endSquare: 'f7', color: expect.any(String) },
    ])
  })
})

it('shows an error for a missing game', async () => {
  loggedInWith({ 'GET /games/nope': { status: 404, body: { detail: 'Game not found' } } })
  renderApp('/games/nope')

  expect(await screen.findByRole('alert')).toHaveTextContent('Game not found')
})
