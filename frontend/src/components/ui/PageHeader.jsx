/** Page title block: one h1 per page, an optional description, and optional actions on the right. */
export default function PageHeader({ title, description, actions, children }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 space-y-1">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">{title}</h1>
        {description && <p className="max-w-2xl text-ink-2">{description}</p>}
        {children}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
    </header>
  )
}
