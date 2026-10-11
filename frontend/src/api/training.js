import { apiFetch } from './client.js'

export function syncCards() {
  return apiFetch('/training/sync', { method: 'POST' })
}

export function fetchDueCards(limit = 50) {
  return apiFetch(`/training/due?limit=${limit}`)
}

export function reviewCard(cardId, { move, rating }) {
  return apiFetch(`/training/cards/${encodeURIComponent(cardId)}/review`, {
    method: 'POST',
    body: JSON.stringify({ move, rating }),
  })
}

export function fetchTrainingStats() {
  return apiFetch('/training/stats')
}
