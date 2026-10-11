import { useEffect, useId, useRef, useState } from 'react'
import Icon from './Icon.jsx'

/** The avatar button in the header. Click it for a menu with the account email and Log out. */
export default function UserMenu({ email, onLogout }) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const buttonRef = useRef(null)
  const menuId = useId()

  useEffect(() => {
    if (!open) return

    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false)
    }
    function onKeyDown(event) {
      if (event.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div
      ref={rootRef}
      className="relative"
      // Tabbing out of the menu closes it.
      onBlur={(event) => {
        if (open && !rootRef.current?.contains(event.relatedTarget)) setOpen(false)
      }}
    >
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-label="Account menu"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        className="flex h-9 w-9 items-center justify-center rounded-full bg-brand/20 text-sm font-bold text-brand outline-none transition hover:bg-brand/30 focus-visible:ring-2 focus-visible:ring-brand/60"
      >
        {email[0].toUpperCase()}
      </button>

      {open && (
        <div
          id={menuId}
          role="menu"
          aria-label="Account"
          className="absolute right-0 top-full z-40 mt-2 w-64 overflow-hidden rounded-xl border border-line bg-panel shadow-lg"
        >
          <div className="border-b border-line px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted">Signed in as</p>
            <p className="mt-0.5 break-all text-sm font-semibold text-ink">{email}</p>
          </div>
          <div className="p-1.5">
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false)
                onLogout()
              }}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-semibold text-ink-2 transition hover:bg-raised hover:text-ink focus-visible:bg-raised focus-visible:outline-none"
            >
              <Icon name="logout" className="h-4 w-4" />
              Log out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
