import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatPeriod } from '../../utils/insights.js'
import ChartCard, { DataTable } from './ChartCard.jsx'
import TooltipBox from './TooltipBox.jsx'
import { AXIS_TICK, VIZ } from './viz.js'

const formatAccuracy = (value) => (value == null ? '—' : `${value.toFixed(1)}%`)

function AccuracyTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return (
    <TooltipBox
      title={`${point.label} · ${point.games} ${point.games === 1 ? 'game' : 'games'}`}
      rows={[
        { label: 'you', value: formatAccuracy(point.accuracy), color: VIZ.series1 },
        { label: 'opponents', value: formatAccuracy(point.opponent_accuracy), color: VIZ.deemphasis },
      ]}
    />
  )
}

/** Your accuracy is the line that matters; opponents' is context in gray. */
export default function AccuracyTrendChart({ trend }) {
  const data = trend.points.map((point) => ({ ...point, label: formatPeriod(point.period) }))
  const values = data.flatMap((p) => [p.accuracy, p.opponent_accuracy]).filter((v) => v != null)
  const low = values.length ? Math.max(0, Math.floor((Math.min(...values) - 5) / 10) * 10) : 0

  return (
    <ChartCard
      title="Accuracy over time"
      description={`Average accuracy per ${trend.bucket} in analyzed games.`}
      legend={[
        { label: 'You', color: VIZ.series1, shape: 'line' },
        { label: 'Opponents', color: VIZ.deemphasis, shape: 'line' },
      ]}
      empty={data.length === 0 && 'No analyzed games in this period. Analyze games to see your accuracy trend.'}
      table={
        <DataTable
          caption="Accuracy over time"
          columns={[trend.bucket === 'week' ? 'Week of' : 'Month', 'Games', 'You', 'Opponents']}
          rows={data.map((p) => [p.label, p.games, formatAccuracy(p.accuracy), formatAccuracy(p.opponent_accuracy)])}
        />
      }
    >
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke={VIZ.grid} />
          <XAxis dataKey="label" tick={AXIS_TICK} axisLine={{ stroke: VIZ.axis }} tickLine={false} minTickGap={16} />
          <YAxis domain={[low, 100]} tickFormatter={(v) => `${v}%`} tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
          <Tooltip cursor={{ stroke: VIZ.axis, strokeWidth: 1 }} content={<AccuracyTooltip />} />
          <Line
            dataKey="opponent_accuracy"
            stroke={VIZ.deemphasis}
            strokeWidth={2}
            dot={{ r: 4, fill: VIZ.deemphasis, stroke: VIZ.surface, strokeWidth: 2 }}
            activeDot={{ r: 5, stroke: VIZ.surface, strokeWidth: 2 }}
            connectNulls
            isAnimationActive={false}
          />
          <Line
            dataKey="accuracy"
            stroke={VIZ.series1}
            strokeWidth={2}
            dot={{ r: 4, fill: VIZ.series1, stroke: VIZ.surface, strokeWidth: 2 }}
            activeDot={{ r: 5, stroke: VIZ.surface, strokeWidth: 2 }}
            connectNulls
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
