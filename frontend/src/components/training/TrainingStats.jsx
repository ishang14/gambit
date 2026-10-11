function Stat({ label, value, highlight = false }) {
  return (
    <div className={`card px-4 py-3 text-center ${highlight ? 'border-brand/40 bg-brand/10' : ''}`}>
      <div
        className={`text-2xl font-extrabold tracking-tight ${highlight ? 'text-brand' : 'text-ink'}`}
        aria-label={label}
      >
        {value}
      </div>
      <div className="mt-0.5 text-xs font-medium text-muted">{label}</div>
    </div>
  )
}

export default function TrainingStats({ stats }) {
  const accuracy = stats.accuracy_last_7d != null ? `${Math.round(stats.accuracy_last_7d * 100)}%` : '—'
  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
      <Stat label="Due now" value={stats.due_now} highlight={stats.due_now > 0} />
      <Stat label="New" value={stats.new} />
      <Stat label="Learning" value={stats.learning} />
      <Stat label="Mature" value={stats.mature} />
      <Stat label="Reviews (24h)" value={stats.reviews_last_24h} />
      <Stat label="Accuracy (7d)" value={accuracy} />
    </div>
  )
}
