import { apiFetch, ApiError, onUnauthorized, tokenStore } from './client.js'

function respondWith(status, body, beforeResolve) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => {
      beforeResolve?.()
      return { ok: status < 400, status, json: async () => body }
    }),
  )
}

beforeEach(() => localStorage.clear())
afterEach(() => {
  vi.unstubAllGlobals()
  onUnauthorized(null)
})

it('sends the token and returns the body', async () => {
  tokenStore.set('abc')
  respondWith(200, { ok: 1 })

  expect(await apiFetch('/thing')).toEqual({ ok: 1 })
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer abc')
})

it('turns FastAPI validation errors into a readable message', async () => {
  respondWith(422, { detail: [{ loc: ['body', 'password'], msg: 'too short' }] })

  await expect(apiFetch('/thing')).rejects.toThrow('password: too short')
})

it('logs out on a 401 for the current session', async () => {
  const handler = vi.fn()
  onUnauthorized(handler)
  tokenStore.set('abc')
  respondWith(401, { detail: 'Not authenticated' })

  await expect(apiFetch('/thing')).rejects.toBeInstanceOf(ApiError)
  expect(handler).toHaveBeenCalledOnce()
})

it('ignores a 401 for a session that has since been replaced', async () => {
  const handler = vi.fn()
  onUnauthorized(handler)
  tokenStore.set('old-token')
  // The user logs in again while the old request is in flight.
  respondWith(401, { detail: 'Not authenticated' }, () => tokenStore.set('new-token'))

  await expect(apiFetch('/thing')).rejects.toThrow('Not authenticated')
  expect(handler).not.toHaveBeenCalled()
})
