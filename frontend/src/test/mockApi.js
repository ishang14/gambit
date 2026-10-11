import { vi } from 'vitest'

/**
 * Replace global fetch with canned API responses.
 * `routes` maps "METHOD /path" (query string ignored) to { status, body },
 * or to a function (options, url) => { status, body }.
 * Unknown routes return 404. Returns the mock so tests can inspect calls.
 */
export function mockApi(routes) {
  const fetchMock = vi.fn(async (url, options = {}) => {
    const method = options.method ?? 'GET'
    const parsed = new URL(url)
    const route = routes[`${method} ${parsed.pathname}`]
    const { status = 200, body = null } =
      typeof route === 'function'
        ? await route(options, parsed)
        : (route ?? { status: 404, body: { detail: 'Not found' } })
    return { ok: status >= 200 && status < 300, status, json: async () => body }
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/** The URLs fetched for a given path, e.g. callsTo(fetchMock, '/games'). */
export function callsTo(fetchMock, pathname) {
  return fetchMock.mock.calls.map(([url]) => new URL(url)).filter((url) => url.pathname === pathname)
}

export const testUser = {
  id: '64b000000000000000000001',
  email: 'player@example.com',
  chesscom_username: 'hikaru',
  created_at: '2026-10-10T00:00:00Z',
}
