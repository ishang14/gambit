import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App.jsx'
import { tokenStore } from '../api/client.js'
import { AuthProvider } from '../auth/AuthContext.jsx'
import { mockApi, testUser } from './mockApi.js'

/** Render the whole app at `path`. */
export function renderApp(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  )
}

/** Log in as `user` and mock the given API routes. Returns the fetch mock. */
export function loggedInWith(routes = {}, user = testUser) {
  tokenStore.set('valid-token')
  return mockApi({ 'GET /auth/me': { body: user }, ...routes })
}
