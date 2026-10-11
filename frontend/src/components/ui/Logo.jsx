/** The Gambit mark: a pawn on a green tile, plus the wordmark. */
export function LogoMark({ className = 'h-8 w-8' }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={className}>
      <rect width="32" height="32" rx="8" fill="var(--brand)" />
      <g fill="var(--on-brand)">
        <circle cx="16" cy="9.6" r="4.2" />
        <path d="M12.4 15.4h7.2l1.8 7.2H10.6z" />
        <rect x="8.6" y="23.2" width="14.8" height="3.4" rx="1.7" />
      </g>
    </svg>
  )
}

export default function Logo({ className = '' }) {
  return (
    <span className={`flex items-center gap-2.5 ${className}`}>
      <LogoMark />
      <span className="text-lg font-extrabold tracking-tight text-ink">Gambit</span>
    </span>
  )
}
