import { apiFetch } from './client.js'

export function fetchOpenings({ color, minGames }) {
  const params = new URLSearchParams({ color, min_games: String(minGames) })
  return apiFetch(`/openings?${params}`)
}
