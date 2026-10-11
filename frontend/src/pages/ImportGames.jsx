import { useState } from 'react'
import { fetchImportMonths } from '../api/games.js'
import { useAuth } from '../auth/AuthContext.jsx'
import ImportProgress from '../components/import/ImportProgress.jsx'
import MonthPicker, { monthKey } from '../components/import/MonthPicker.jsx'
import TextField from '../components/TextField.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import { useGameImport } from '../hooks/useGameImport.js'

export default function ImportGames() {
  const { user } = useAuth()
  const [username, setUsername] = useState(user.chesscom_username ?? '')
  // The username the month list was loaded for, so edits to the input don't mix players.
  const [loadedFor, setLoadedFor] = useState(null)
  const [months, setMonths] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [loadingMonths, setLoadingMonths] = useState(false)
  const [monthsError, setMonthsError] = useState(null)
  const gameImport = useGameImport()

  async function handleFindMonths(event) {
    event.preventDefault()
    setLoadingMonths(true)
    setMonthsError(null)
    try {
      const found = await fetchImportMonths(username.trim())
      setMonths(found)
      setSelected(new Set(found.slice(0, 3).map(monthKey)))
      setLoadedFor(username.trim())
    } catch (err) {
      setMonths([])
      setLoadedFor(null)
      setMonthsError(err.message)
    } finally {
      setLoadingMonths(false)
    }
  }

  function handleImport() {
    const chosen = months.filter((month) => selected.has(monthKey(month)))
    gameImport.start(loadedFor, chosen)
  }

  const busy = loadingMonths || gameImport.running

  return (
    <div className="space-y-6">
      <PageHeader
        title="Import Games"
        description="Load your public games from chess.com. Only standard chess is imported; variants are skipped."
      />

      <form onSubmit={handleFindMonths} className="card flex flex-wrap items-end gap-3 p-5">
        <div className="w-full sm:w-72">
          <TextField
            label="chess.com username"
            id="username"
            required
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={busy}
          />
        </div>
        <button type="submit" disabled={busy || !username.trim()} className="btn btn-primary">
          {loadingMonths ? 'Looking up…' : 'Find games'}
        </button>
      </form>

      {monthsError && (
        <p role="alert" className="alert alert-danger">
          {monthsError}
        </p>
      )}

      {loadedFor && months.length === 0 && <EmptyState title={`No games found for ${loadedFor}`} glyph="♙" />}

      {months.length > 0 && (
        <div className="card space-y-5 p-5">
          <MonthPicker months={months} selected={selected} onChange={setSelected} disabled={busy} />
          <button type="button" onClick={handleImport} disabled={busy || selected.size === 0} className="btn btn-primary">
            Import {selected.size} {selected.size === 1 ? 'month' : 'months'}
          </button>
        </div>
      )}

      {gameImport.total > 0 && <ImportProgress {...gameImport} onStop={gameImport.stop} />}
    </div>
  )
}
