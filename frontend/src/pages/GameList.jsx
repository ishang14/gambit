import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchGames } from '../api/games.js'
import AnalyzeAllButton from '../components/games/AnalyzeAllButton.jsx'
import GameFilters from '../components/games/GameFilters.jsx'
import GamesTable from '../components/games/GamesTable.jsx'
import Pagination from '../components/Pagination.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Spinner from '../components/ui/Spinner.jsx'

export const PAGE_SIZE = 25
const FILTER_NAMES = ['result', 'color', 'time_class', 'opening']
// While games on this page are being analyzed, refresh quietly this often.
export const listRefresh = { intervalMs: 3000 }

export default function GameList() {
  // Filters and page live in the URL, so back/forward and shared links work.
  const [searchParams, setSearchParams] = useSearchParams()
  const filters = Object.fromEntries(FILTER_NAMES.map((name) => [name, searchParams.get(name) ?? '']))
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const queryKey = searchParams.toString()

  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshCount, setRefreshCount] = useState(0)

  const loadPage = useCallback(
    () => fetchGames({ ...filters, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }),
    // queryKey captures every input (filters and page).
    [queryKey],
  )

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    loadPage()
      .then((body) => !cancelled && setData(body))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [loadPage, refreshCount])

  const analyzing = data?.items.some((game) => ['queued', 'running'].includes(game.analysis_status))

  useEffect(() => {
    if (!analyzing) return
    let cancelled = false
    const timer = setTimeout(() => {
      loadPage()
        .then((body) => !cancelled && setData(body))
        .catch(() => {})
    }, listRefresh.intervalMs)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [analyzing, data, loadPage])

  const updateFilter = useCallback(
    (name, value) => {
      setSearchParams((current) => {
        const next = new URLSearchParams(current)
        if (value) next.set(name, value)
        else next.delete(name)
        next.delete('page')
        return next
      })
    },
    [setSearchParams],
  )

  function goToPage(nextPage) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      next.set('page', String(nextPage))
      return next
    })
  }

  const hasFilters = FILTER_NAMES.some((name) => filters[name])

  return (
    <div className="space-y-6">
      <PageHeader title="Games" description="Your imported games, newest first." />

      <div className="card flex flex-wrap items-end justify-between gap-4 p-4">
        <GameFilters filters={filters} onChange={updateFilter} />
        <AnalyzeAllButton onQueued={() => setRefreshCount((count) => count + 1)} />
      </div>

      {error && (
        <p role="alert" className="alert alert-danger">
          {error}
        </p>
      )}

      {data && data.total === 0 && !hasFilters && (
        <EmptyState title="No games yet">
          <Link to="/import" className="font-semibold text-brand hover:underline">
            Import your games
          </Link>{' '}
          from chess.com to get started.
        </EmptyState>
      )}
      {data && data.total === 0 && hasFilters && (
        <EmptyState title="No games match these filters" glyph="♟">
          Try removing a filter.
        </EmptyState>
      )}

      {data && data.total > 0 && (
        <div className={`card overflow-hidden transition-opacity ${loading ? 'opacity-60' : ''}`}>
          <GamesTable games={data.items} />
          <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onPageChange={goToPage} />
        </div>
      )}

      {loading && !data && <Spinner>Loading games…</Spinner>}
    </div>
  )
}
