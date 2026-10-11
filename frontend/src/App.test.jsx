import { fireEvent, screen } from '@testing-library/react'
import { tokenStore } from './api/client.js'
import { mockApi, testUser } from './test/mockApi.js'
import { loggedInWith, renderApp as renderAt } from './test/renderApp.jsx'

const logInAs = () => loggedInWith({ 'GET /games': { body: { items: [], total: 0 } } })

function fillIn(label, value) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('routing when logged in', () => {
  it.each([
    ['/import', 'Import Games'],
    ['/games', 'Games'],
    ['/openings', 'Opening Tree'],
    ['/training', 'Training'],
    ['/insights', 'Insights'],
  ])('renders %s', async (path, heading) => {
    logInAs()
    renderAt(path)
    expect(await screen.findByRole('heading', { level: 1, name: heading })).toBeInTheDocument()
  })

  it('redirects / to the game list', async () => {
    logInAs()
    renderAt('/')
    expect(await screen.findByRole('heading', { level: 1, name: 'Games' })).toBeInTheDocument()
  })

  it('shows the nav bar, with the user email tucked into the account menu', async () => {
    logInAs()
    renderAt('/games')
    expect(await screen.findByRole('link', { name: 'Training' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Account menu' })).toHaveTextContent(testUser.email[0].toUpperCase())
    expect(screen.queryByText(testUser.email)).not.toBeInTheDocument()
  })

  it('sends logged-in users away from the login page', async () => {
    logInAs()
    renderAt('/login')
    expect(await screen.findByRole('heading', { level: 1, name: 'Games' })).toBeInTheDocument()
  })
})

describe('protected routes', () => {
  it('redirects to login when there is no token', async () => {
    mockApi({})
    renderAt('/training')
    expect(await screen.findByRole('heading', { level: 1, name: 'Log in' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Training' })).not.toBeInTheDocument()
  })

  it('clears a stale token and redirects to login', async () => {
    tokenStore.set('expired-token')
    mockApi({ 'GET /auth/me': { status: 401, body: { detail: 'Not authenticated' } } })
    renderAt('/games')
    expect(await screen.findByRole('heading', { level: 1, name: 'Log in' })).toBeInTheDocument()
    expect(tokenStore.get()).toBeNull()
  })
})

describe('login', () => {
  it('logs in and returns to the page the user wanted', async () => {
    const fetchMock = mockApi({
      'POST /auth/login': { body: { access_token: 'new-token', token_type: 'bearer', user: testUser } },
    })
    renderAt('/training')

    await screen.findByRole('heading', { level: 1, name: 'Log in' })
    fillIn('Email', testUser.email)
    fillIn('Password', 'correct-horse-battery')
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Training' })).toBeInTheDocument()
    expect(tokenStore.get()).toBe('new-token')
    const [, options] = fetchMock.mock.calls[0]
    expect(JSON.parse(options.body)).toEqual({ email: testUser.email, password: 'correct-horse-battery' })
  })

  it('shows the error message when login fails', async () => {
    mockApi({ 'POST /auth/login': { status: 401, body: { detail: 'Incorrect email or password' } } })
    renderAt('/login')

    fillIn('Email', testUser.email)
    fillIn('Password', 'wrong-password')
    fireEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password')
    expect(tokenStore.get()).toBeNull()
  })
})

describe('signup', () => {
  it('creates an account and lands on the app', async () => {
    const fetchMock = mockApi({
      'POST /auth/signup': { status: 201, body: { access_token: 'new-token', token_type: 'bearer', user: testUser } },
    })
    renderAt('/signup')

    fillIn('Email', testUser.email)
    fillIn('Password (at least 8 characters)', 'correct-horse-battery')
    fillIn('chess.com username (optional)', 'hikaru')
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Games' })).toBeInTheDocument()
    const [, options] = fetchMock.mock.calls[0]
    expect(JSON.parse(options.body)).toEqual({
      email: testUser.email,
      password: 'correct-horse-battery',
      chesscom_username: 'hikaru',
    })
  })

  it('shows the error when the email is taken', async () => {
    mockApi({ 'POST /auth/signup': { status: 409, body: { detail: 'An account with this email already exists' } } })
    renderAt('/signup')

    fillIn('Email', testUser.email)
    fillIn('Password (at least 8 characters)', 'correct-horse-battery')
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('already exists')
  })
})

describe('logout', () => {
  it('clears the session and returns to login', async () => {
    logInAs()
    renderAt('/games')

    fireEvent.click(await screen.findByRole('button', { name: 'Account menu' }))
    fireEvent.click(screen.getByRole('menuitem', { name: 'Log out' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Log in' })).toBeInTheDocument()
    expect(tokenStore.get()).toBeNull()
  })
})
