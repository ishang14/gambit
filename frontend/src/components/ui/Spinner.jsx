/** Inline loading indicator with a text label (the label is what assistive tech reads). */
export default function Spinner({ children = 'Loading…', className = '' }) {
  return (
    <p aria-live="polite" className={`flex items-center gap-3 text-muted ${className}`}>
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-brand"
      />
      {children}
    </p>
  )
}
