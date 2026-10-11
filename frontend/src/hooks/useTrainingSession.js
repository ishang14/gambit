import { Chess } from 'chess.js'
import { useCallback, useEffect, useState } from 'react'
import { fetchDueCards, fetchTrainingStats, reviewCard, syncCards } from '../api/training.js'

/** Try a move on the card's position. Returns { uci, san, fenAfter } or null if illegal. */
export function tryMove(fen, from, to) {
  const chess = new Chess(fen)
  try {
    // No promotion picker: pawns always promote to a queen.
    const move = chess.move({ from, to, promotion: 'q' })
    return { uci: `${move.from}${move.to}${move.promotion ?? ''}`, san: move.san, fenAfter: chess.fen() }
  } catch {
    return null
  }
}

/**
 * A review session: load due cards, take one attempt per card, then submit a rating.
 * Failed cards go back to the end of the queue so they're drilled again this session.
 */
export function useTrainingSession() {
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [error, setError] = useState(null)
  const [created, setCreated] = useState(0)
  const [queue, setQueue] = useState([])
  const [stats, setStats] = useState(null)
  const [attempt, setAttempt] = useState(null) // { uci, san, fenAfter, correct, gaveUp }
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const sync = await syncCards()
        const [due, latestStats] = await Promise.all([fetchDueCards(), fetchTrainingStats()])
        if (cancelled) return
        setCreated(sync.created)
        setQueue(due.cards)
        setStats(latestStats)
        setStatus('ready')
      } catch (err) {
        if (cancelled) return
        setError(err.message)
        setStatus('error')
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const card = queue[0] ?? null

  const play = useCallback(
    (from, to) => {
      if (!card || attempt || !to) return false
      const move = tryMove(card.fen, from, to)
      if (!move) return false
      setAttempt({ ...move, correct: move.uci === card.correct_move, gaveUp: false })
      return true
    },
    [card, attempt],
  )

  const giveUp = useCallback(() => {
    if (card && !attempt) setAttempt({ uci: null, san: null, fenAfter: null, correct: false, gaveUp: true })
  }, [card, attempt])

  const rate = useCallback(
    async (rating) => {
      if (!card || !attempt || submitting) return
      setSubmitting(true)
      setError(null)
      try {
        // Giving up counts as playing the move from the game: a fail.
        const result = await reviewCard(card.id, { move: attempt.uci ?? card.user_move, rating })
        setQueue((current) => {
          const rest = current.slice(1)
          return result.correct ? rest : [...rest, result.card]
        })
        setAttempt(null)
        setStats(await fetchTrainingStats())
      } catch (err) {
        setError(err.message)
      } finally {
        setSubmitting(false)
      }
    },
    [card, attempt, submitting],
  )

  return { status, error, created, card, remaining: queue.length, stats, attempt, submitting, play, giveUp, rate }
}
