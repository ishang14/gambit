import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { capitalize } from '../../utils/format.js'
import ChartCard, { DataTable } from './ChartCard.jsx'
import TooltipBox from './TooltipBox.jsx'
import { AXIS_TICK, VIZ } from './viz.js'

const KINDS = [
  { key: 'inaccuracies', label: 'Inaccuracies' },
  { key: 'mistakes', label: 'Mistakes' },
  { key: 'blunders', label: 'Blunders' },
]

const rate = (value) => (value == null ? '—' : value.toFixed(1))

function PhaseTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <TooltipBox
      title={`${row.label} · ${row.moves} moves`}
      rows={KINDS.map(({ key, label }, index) => ({
        label: `${label.toLowerCase()} per 100 moves`,
        value: rate(row[`${key}_per_100`]),
        color: VIZ.severity[index],
      })).reverse()}
    />
  )
}

/** Rates per 100 of your moves in each phase, stacked from mildest to most severe. */
export default function MistakesByPhaseChart({ mistakes }) {
  const data = mistakes.phases.map((row) => ({
    ...row,
    label: capitalize(row.phase),
    ...Object.fromEntries(KINDS.map(({ key }) => [`${key}Rate`, row[`${key}_per_100`] ?? 0])),
  }))

  return (
    <ChartCard
      title="Where your mistakes happen"
      description={`Per 100 of your moves in each phase, from ${mistakes.analyzed_games} analyzed ${
        mistakes.analyzed_games === 1 ? 'game' : 'games'
      }. The endgame starts when 6 or fewer pieces (not counting kings and pawns) are left.`}
      legend={KINDS.map(({ label }, index) => ({ label, color: VIZ.severity[index] }))}
      empty={mistakes.analyzed_games === 0 && 'No analyzed games in this period. Analyze games to see where your mistakes happen.'}
      table={
        <DataTable
          caption="Mistakes by phase"
          columns={['Phase', 'Your moves', ...KINDS.map((k) => k.label), ...KINDS.map((k) => `${k.label} / 100`)]}
          rows={data.map((row) => [
            row.label,
            row.moves,
            ...KINDS.map(({ key }) => row[key]),
            ...KINDS.map(({ key }) => rate(row[`${key}_per_100`])),
          ])}
        />
      }
    >
      <ResponsiveContainer width="100%" height={3 * 44 + 32}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid horizontal={false} stroke={VIZ.grid} />
          <XAxis type="number" tick={AXIS_TICK} axisLine={{ stroke: VIZ.axis }} tickLine={false} allowDecimals={false} />
          <YAxis type="category" dataKey="label" width={96} tick={AXIS_TICK} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: VIZ.grid, fillOpacity: 0.5 }} content={<PhaseTooltip />} />
          {KINDS.map(({ key }, index) => (
            <Bar
              key={key}
              dataKey={`${key}Rate`}
              stackId="severity"
              fill={VIZ.severity[index]}
              stroke={VIZ.surface}
              strokeWidth={2}
              barSize={20}
              radius={index === KINDS.length - 1 ? [0, 4, 4, 0] : 0}
              isAnimationActive={false}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}
