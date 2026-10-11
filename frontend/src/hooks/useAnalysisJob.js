import { useCallback, useEffect, useState } from 'react'
import { fetchAnalysisJob, requestAnalysis } from '../api/analysis.js'

// Exported so tests can poll faster.
export const analysisPolling = { intervalMs: 1500 }

const ACTIVE = new Set(['queued', 'running'])

/**
 * Track a game's analysis job: start one, and poll its status while it is queued
 * or running. Calls `onDone` once when it finishes.
 */
export function useAnalysisJob(game, onDone) {
  const [job, setJob] = useState(null)
  const [error, setError] = useState(null)

  // Resume polling if the game was already queued/running when the page opened.
  useEffect(() => {
    if (game && ACTIVE.has(game.analysis_status) && game.analysis_job_id) {
      setJob({
        job_id: game.analysis_job_id,
        status: game.analysis_status,
        progress: game.analysis_progress ?? 0,
        error: null,
      })
    }
  }, [game])

  const active = job ? ACTIVE.has(job.status) : false

  // Each poll sets a new `job`, which schedules the next poll.
  useEffect(() => {
    if (!job || !ACTIVE.has(job.status)) return
    let cancelled = false
    const timer = setTimeout(async () => {
      try {
        const next = await fetchAnalysisJob(job.job_id)
        if (cancelled) return
        setJob(next)
        if (next.status === 'done') onDone?.()
      } catch (err) {
        if (!cancelled) setError(err.message)
      }
    }, analysisPolling.intervalMs)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [job, onDone])

  const start = useCallback(async () => {
    setError(null)
    try {
      setJob(await requestAnalysis(game.id))
    } catch (err) {
      setError(err.message)
    }
  }, [game])

  return { job, error, start, active }
}
