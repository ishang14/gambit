import { fireEvent, screen, within } from '@testing-library/react'
import { callsTo } from '../test/mockApi.js'
import { loggedInWith, renderApp } from '../test/renderApp.jsx'

const MONTHS = [
  { year: 2026, month: 10 },
  { year: 2026, month: 9 },
  { year: 2026, month: 8 },
  { year: 2026, month: 7 },
]

function monthResult(year, month, imported) {
  return { year, month, imported, duplicates: 1, unsupported: 0 }
}

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

async function findMonths() {
  fireEvent.click(await screen.findByRole('button', { name: 'Find games' }))
  return screen.findByRole('group', { name: 'Months to import' })
}

it('prefills the username from the profile', async () => {
  loggedInWith()
  renderApp('/import')

  expect(await screen.findByLabelText('chess.com username')).toHaveValue('hikaru')
})

it('lists months and preselects the newest three', async () => {
  const fetchMock = loggedInWith({ 'GET /games/import/months': { body: MONTHS } })
  renderApp('/import')

  const picker = await findMonths()

  expect(callsTo(fetchMock, '/games/import/months')[0].searchParams.get('username')).toBe('hikaru')
  expect(within(picker).getByLabelText('Oct 2026')).toBeChecked()
  expect(within(picker).getByLabelText('Aug 2026')).toBeChecked()
  expect(within(picker).getByLabelText('Jul 2026')).not.toBeChecked()
  expect(screen.getByRole('button', { name: 'Import 3 months' })).toBeEnabled()
})

it('imports the selected months one at a time and shows the totals', async () => {
  const bodies = []
  loggedInWith({
    'GET /games/import/months': { body: MONTHS },
    'POST /games/import': (options) => {
      const { year, month } = JSON.parse(options.body)
      bodies.push({ year, month })
      return { body: monthResult(year, month, month) }
    },
  })
  renderApp('/import')
  const picker = await findMonths()

  fireEvent.click(within(picker).getByRole('button', { name: 'Clear' }))
  fireEvent.click(within(picker).getByLabelText('Sep 2026'))
  fireEvent.click(within(picker).getByLabelText('Jul 2026'))
  fireEvent.click(screen.getByRole('button', { name: 'Import 2 months' }))

  expect(await screen.findByText(/Imported 16 new games/)).toBeInTheDocument()
  expect(bodies).toEqual([
    { year: 2026, month: 9 },
    { year: 2026, month: 7 },
  ])
  expect(screen.getByText('Finished 2 of 2 months')).toBeInTheDocument()
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100')
  expect(screen.getByRole('link', { name: 'View games' })).toHaveAttribute('href', '/games')
})

it('stops at the first failed month', async () => {
  let calls = 0
  loggedInWith({
    'GET /games/import/months': { body: MONTHS },
    'POST /games/import': (options) => {
      calls += 1
      const { year, month } = JSON.parse(options.body)
      if (calls === 2) return { status: 502, body: { detail: 'chess.com is rate limiting requests' } }
      return { body: monthResult(year, month, 5) }
    },
  })
  renderApp('/import')
  await findMonths()

  fireEvent.click(screen.getByRole('button', { name: 'Import 3 months' }))

  expect(await screen.findByText('Sep 2026: chess.com is rate limiting requests')).toBeInTheDocument()
  expect(calls).toBe(2)
  expect(screen.getByText('Finished 1 of 3 months')).toBeInTheDocument()
})

it('shows an error for an unknown player', async () => {
  loggedInWith({
    'GET /games/import/months': { status: 404, body: { detail: "chess.com player 'nobody' not found" } },
  })
  renderApp('/import')

  fireEvent.change(await screen.findByLabelText('chess.com username'), { target: { value: 'nobody' } })
  fireEvent.click(screen.getByRole('button', { name: 'Find games' }))

  expect(await screen.findByRole('alert')).toHaveTextContent("chess.com player 'nobody' not found")
  expect(screen.queryByRole('group', { name: 'Months to import' })).not.toBeInTheDocument()
})
