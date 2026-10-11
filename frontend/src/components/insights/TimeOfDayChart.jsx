import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatHour } from '../../utils/insights.js'
import ChartCard, { DataTable } from './ChartCard.jsx'
import TooltipBox from './TooltipBox.jsx'
import { AXIS_TICK, percent, VIZ } from './viz.js'

// Fewer games than this in an hour and the score is mostly noise: fade the bar.
const FEW_GAMES = 3

function HourTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  if (!row.games) return null
  return (
    <TooltipBox
      title={`${formatHour(row.hour)}–${formatHour((row.hour + 1) % 24)} · ${row.games} ${row.games === 1 ? 'game' : 'games'}`}
      rows={[
        { label: 'score', value: percent(row.score), color: VIZ.series1 },
        { label: 'won / drawn / lost', value: `${row.wins} / ${row.draws} / ${row.losses}` },
      ]}
    />
  )
}

export default function TimeOfDayChart({ timeOfDay }) {
  const hours = timeOfDay.hours
  const played = hours.filter((h) => h.games > 0)

  return (
    <ChartCard
      title="Results by time of day"
      description={`Score by the hour your games ended, in your time zone (${timeOfDay.timezone}). Daily games aren't included. Faded bars: fewer than ${FEW_GAMES} games.`}
      empty={played.length === 0 && 'No timed games in this period (daily games have no meaningful time of day).'}
      table={
        <DataTable
          caption="Results by time of day"
          columns={['Hour', 'Games', 'Won', 'Drawn', 'Lost', 'Score']}
          rows={played.map((h) => [formatHour(h.hour), h.games, h.wins, h.draws, h.losses, percent(h.score)])}
        />
      }
    >
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={hours} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke={VIZ.grid} />
          <XAxis dataKey="hour" tickFormatter={formatHour} interval={2} tick={AXIS_TICK} axisLine={{ stroke: VIZ.axis }} tickLine={false} />
          <YAxis domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={percent} tick={AXIS_TICK} axisLine={false} tickLine={false} width={44} />
          <ReferenceLine y={0.5} stroke={VIZ.axis} />
          <Tooltip cursor={{ fill: VIZ.grid, fillOpacity: 0.5 }} content={<HourTooltip />} />
          <Bar dataKey="score" maxBarSize={24} radius={[4, 4, 0, 0]} isAnimationActive={false}>
            {hours.map((h) => (
              <Cell key={h.hour} fill={VIZ.series1} fillOpacity={h.games < FEW_GAMES ? 0.35 : 1} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
