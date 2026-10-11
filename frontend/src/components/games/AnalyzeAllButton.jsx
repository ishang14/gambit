import { useState } from 'react'
import { queueAllAnalysis } from '../../api/analysis.js'

export default function AnalyzeAllButton({ onQueued }) {
  const [message, setMessage] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleClick() {
    setBusy(true)
    setMessage(null)
    try {
      const { queued } = await queueAllAnalysis()
      setMessage(
        queued === 0
          ? 'All games are already analyzed or queued.'
          : `Queued ${queued} ${queued === 1 ? 'game' : 'games'} for analysis.`,
      )
      onQueued?.()
    } catch (err) {
      setMessage(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex items-center gap-3">
      {message && (
        <span role="status" className="text-sm text-ink-2">
          {message}
        </span>
      )}
      <button type="button" onClick={handleClick} disabled={busy} className="btn btn-primary">
        Analyze all
      </button>
    </div>
  )
}
