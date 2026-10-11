const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'gambit_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

let unauthorizedHandler = null

/** Called when an authenticated request gets a 401 (e.g. the token expired). */
export function onUnauthorized(handler) {
  unauthorizedHandler = handler
}

function errorMessage(body, status) {
  const detail = body?.detail
  if (typeof detail === 'string') return detail
  // FastAPI validation errors: [{ loc: ['body', 'password'], msg: '...' }, ...]
  if (Array.isArray(detail) && detail.length > 0) {
    const { loc, msg } = detail[0]
    const field = loc?.[loc.length - 1]
    return field ? `${field}: ${msg}` : msg
  }
  return `Request failed (${status})`
}

export async function apiFetch(path, options = {}) {
  const token = tokenStore.get()
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    // Only end the session if it's still the one this request was sent with.
    if (response.status === 401 && token && token === tokenStore.get()) unauthorizedHandler?.()
    throw new ApiError(response.status, errorMessage(body, response.status))
  }
  return body
}
