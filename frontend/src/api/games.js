import { apiFetch } from './client.js'

export function fetchImportMonths(username) {
  return apiFetch(`/games/import/months?username=${encodeURIComponent(username)}`)
}

export function importMonth({ username, year, month }) {
  return apiFetch('/games/import', {
    method: 'POST',
    body: JSON.stringify({ username, year, month }),
  })
}

/** filters: { result, color, time_class, opening, limit, offset }; empty values are left out. */
export function fetchGames(filters = {}) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, value)
  }
  const query = params.toString()
  return apiFetch(query ? `/games?${query}` : '/games')
}

export function fetchGame(gameId) {
  return apiFetch(`/games/${encodeURIComponent(gameId)}`)
}
