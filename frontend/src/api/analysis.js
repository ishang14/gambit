import { apiFetch } from './client.js'

export function requestAnalysis(gameId) {
  return apiFetch(`/games/${encodeURIComponent(gameId)}/analysis`, { method: 'POST' })
}

export function fetchAnalysisJob(jobId) {
  return apiFetch(`/analysis/jobs/${encodeURIComponent(jobId)}`)
}

export function fetchGameAnalysis(gameId) {
  return apiFetch(`/games/${encodeURIComponent(gameId)}/analysis`)
}

export function queueAllAnalysis() {
  return apiFetch('/analysis/queue-all', { method: 'POST' })
}
