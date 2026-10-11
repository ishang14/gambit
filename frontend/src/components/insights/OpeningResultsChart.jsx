import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import ChartCard, { DataTable } from './ChartCard.jsx'
import TooltipBox from './TooltipBox.jsx'
import { AXIS_TICK, percent, VIZ } from './viz.js'

const ROW_HEIGHT = 34
const AXIS_BAND = 28
const NAME_MAX = 26

function shorten(name) {
  return name.length > NAME_MAX ? `${name.slice(0, NAME_MAX - 1)}…` : name
}

function OpeningTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <TooltipBox
      title={row.opening}
      rows={[
        { label: 'won', value: row.wins, color: VIZ.win },
        { label: 'drawn', value: row.draws, color: VIZ.draw },
        { label: 'lost', value: row.losses, color: VIZ.loss },
        { label: 'score', value: percent(row.score) },
      ]}
    />
  )
}

/** One color's openings as 100% bars: won / drawn / lost, with score and games at the end. */
function OpeningBars({ title, rows }) {
  if (rows.length === 0) {
    return (
      <div>
        <h3 className="text-sm font-medium text-[color:var(--viz-text-secondary)]">{title}</h3>
        <p className="py-3 text-sm text-[color:var(--viz-muted)]">No games.</p>
      </div>
    )
  }
  const data = rows.map((row) => ({
    ...row,
    winShare: row.wins / row.games,
    drawShare: row.draws / row.games,
    lossShare: row.losses / row.games,
    summary: `${percent(row.score)} · ${row.games}`,
  }))

  return (
    <div>
      <h3 className="text-sm font-medium text-[color:var(--viz-text-secondary)]">{title}</h3>
      <ResponsiveContainer width="100%" height={data.length * ROW_HEIGHT + AXIS_BAND}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid horizontal={false} stroke={VIZ.grid} />
          <XAxis
            type="number"
            domain={[0, 1]}
            ticks={[0, 0.25, 0.5, 0.75, 1]}
            tickFormatter={percent}
            tick={AXIS_TICK}
            axisLine={{ stroke: VIZ.axis }}
            tickLine={false}
          />
          <YAxis
            yAxisId="name"
            type="category"
            dataKey="opening"
            width={180}
            tickFormatter={shorten}
            tick={AXIS_TICK}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            yAxisId="summary"
            orientation="right"
            type="category"
            dataKey="summary"
            width={72}
            tick={AXIS_TICK}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip cursor={{ fill: VIZ.grid, fillOpacity: 0.5 }} content={<OpeningTooltip />} />
          {/* The surface-colored stroke is the 2px gap between segments. */}
          <Bar yAxisId="name" dataKey="winShare" stackId="result" fill={VIZ.win} stroke={VIZ.surface} strokeWidth={2} barSize={16} isAnimationActive={false} />
          <Bar yAxisId="name" dataKey="drawShare" stackId="result" fill={VIZ.draw} stroke={VIZ.surface} strokeWidth={2} barSize={16} isAnimationActive={false} />
          <Bar yAxisId="name" dataKey="lossShare" stackId="result" fill={VIZ.loss} stroke={VIZ.surface} strokeWidth={2} barSize={16} radius={[0, 4, 4, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function OpeningResultsChart({ openings }) {
  const empty = openings.white.length === 0 && openings.black.length === 0
  const tableRows = ['white', 'black'].flatMap((color) =>
    openings[color].map((row) => [
      color === 'white' ? 'White' : 'Black',
      row.opening,
      row.games,
      row.wins,
      row.draws,
      row.losses,
      percent(row.score),
      row.avg_accuracy != null ? `${row.avg_accuracy}%` : '—',
    ]),
  )

  return (
    <ChartCard
      title="Results by opening"
      description="Your most played openings, by the family name of the deepest known line. Score at the end: points per game · games."
      legend={[
        { label: 'Won', color: VIZ.win },
        { label: 'Drawn', color: VIZ.draw },
        { label: 'Lost', color: VIZ.loss },
      ]}
      empty={empty && 'No games in this period.'}
      table={
        <DataTable
          caption="Results by opening"
          columns={['Color', 'Opening', 'Games', 'Won', 'Drawn', 'Lost', 'Score', 'Accuracy']}
          rows={tableRows}
        />
      }
    >
      <div className="grid gap-6 xl:grid-cols-2">
        <OpeningBars title="As White" rows={openings.white} />
        <OpeningBars title="As Black" rows={openings.black} />
      </div>
    </ChartCard>
  )
}
