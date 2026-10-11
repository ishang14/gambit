/** A friendly empty state: a glyph, a headline, and what to do next. */
export default function EmptyState({ title, children, glyph = '♞' }) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-12 text-center">
      <span aria-hidden="true" className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand/15 text-3xl text-brand">
        {glyph}
      </span>
      <p className="text-lg font-semibold text-ink">{title}</p>
      {children && <div className="max-w-md text-sm text-ink-2">{children}</div>}
    </div>
  )
}
