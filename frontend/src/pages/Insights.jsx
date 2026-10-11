import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchInsights } from '../api/insights.js'
import AccuracyTrendChart from '../components/insights/AccuracyTrendChart.jsx'
import InsightFilters from '../components/insights/InsightFilters.jsx'
import MistakesByPhaseChart from '../components/insights/MistakesByPhaseChart.jsx'
import OpeningResultsChart from '../components/insights/OpeningResultsChart.jsx'
import StatTiles from '../components/insights/StatTiles.jsx'
import TimeOfDayChart from '../components/insights/TimeOfDayChart.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import PageHeader from '../components/ui/PageHeader.jsx'
import Spinner from '../components/ui/Spinner.jsx'
import { browserTimezone, PERIODS, sinceDate } from '../utils/insights.js'

const DEFAULT_PERIOD = '90d'

export default function Insights() {
  const [searchParams, setSearchParams] = useSearchParams()
  const period = PERIODS.some((p) => p.value === searchParams.get('period')) ? searchParams.get('period') : DEFAULT_PERIOD
  const timeClass = searchParams.get('time_class') ?? ''

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    const bucket = PERIODS.find((p) => p.value === period).bucket
    fetchInsights({ timeClass, since: sinceDate(period), bucket, tz: browserTimezone() })
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [period, timeClass])

  function changeFilters(changes) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      for (const [key, value] of Object.entries(changes)) {
        if (value) next.set(key, value)
        else next.delete(key)
      }
      return next
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Insights" description="How your games have gone, and where the points slip away." />

      <InsightFilters period={period} timeClass={timeClass} onChange={changeFilters} />

      {error && (
        <p role="alert" className="alert alert-danger">
          {error}
        </p>
      )}
      {!data && loading && <Spinner>Crunching your games…</Spinner>}

      {data && data.summary.games === 0 && !loading && (
        <EmptyState title="No games in this period" glyph="♝">
          <Link to="/import" className="font-semibold text-brand hover:underline">
            Import games
          </Link>{' '}
          or choose a longer period.
        </EmptyState>
      )}

      {data && data.summary.games > 0 && (
        // While new filters load, keep the old charts on screen, dimmed.
        <div className={`space-y-6 transition-opacity ${loading ? 'opacity-60' : ''}`} aria-busy={loading}>
          <StatTiles summary={data.summary} />
          <OpeningResultsChart openings={data.openings} />
          <div className="grid gap-6 lg:grid-cols-2">
            <AccuracyTrendChart trend={data.accuracy} />
            <MistakesByPhaseChart mistakes={data.mistakes} />
          </div>
          <TimeOfDayChart timeOfDay={data.timeOfDay} />
        </div>
      )}
    </div>
  )
}
