import { useEffect, useRef, useState } from 'react'
import { importMonth } from '../api/games.js'
import { formatMonth } from '../utils/format.js'

/**
 * Imports months one at a time (the API takes one month per request), tracking
 * progress. Stops at the first error so we don't keep hitting chess.com.
 */
export function useGameImport() {
  const [total, setTotal] = useState(0)
  const [current, setCurrent] = useState(null)
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)
  const [running, setRunning] = useState(false)
  const stopRequested = useRef(false)

  useEffect(() => () => {
    stopRequested.current = true
  }, [])

  async function start(username, months) {
    stopRequested.current = false
    setTotal(months.length)
    setResults([])
    setError(null)
    setRunning(true)
    for (const month of months) {
      if (stopRequested.current) break
      setCurrent(month)
      try {
        const result = await importMonth({ username, ...month })
        setResults((previous) => [...previous, result])
      } catch (err) {
        setError(`${formatMonth(month.year, month.month)}: ${err.message}`)
        break
      }
    }
    setCurrent(null)
    setRunning(false)
  }

  function stop() {
    stopRequested.current = true
  }

  return { start, stop, running, total, current, results, error }
}
