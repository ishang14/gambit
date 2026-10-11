import { apiFetch } from './client.js'

function query(params) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, value)
  }
  return search.toString()
}

/** All five insights for the same filters, fetched in parallel. */
export async function fetchInsights({ timeClass, since, bucket, tz }) {
  const shared = query({ time_class: timeClass, since, tz })
  const [summary, openings, accuracy, mistakes, timeOfDay] = await Promise.all([
    apiFetch(`/insights/summary?${shared}`),
    apiFetch(`/insights/openings?${shared}`),
    apiFetch(`/insights/accuracy?${shared}&bucket=${bucket}`),
    apiFetch(`/insights/mistakes?${shared}`),
    apiFetch(`/insights/time-of-day?${shared}`),
  ])
  return { summary, openings, accuracy, mistakes, timeOfDay }
}
