import { Suspense } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'
import Icon from './ui/Icon.jsx'
import Logo from './ui/Logo.jsx'
import Spinner from './ui/Spinner.jsx'
import ThemeToggle from './ui/ThemeToggle.jsx'

const links = [
  { to: '/import', label: 'Import', icon: 'import' },
  { to: '/games', label: 'Games', icon: 'games' },
  { to: '/openings', label: 'Openings', icon: 'openings' },
  { to: '/training', label: 'Training', icon: 'training' },
  { to: '/insights', label: 'Insights', icon: 'insights' },
]

function navClass({ isActive }) {
  const base = 'flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition'
  return isActive
    ? `${base} bg-brand/15 text-brand`
    : `${base} text-ink-2 hover:bg-raised hover:text-ink`
}

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="sticky top-0 z-30 border-b border-line bg-panel/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <NavLink to="/" aria-label="Gambit home" className="rounded-lg">
            <Logo />
          </NavLink>

          <nav aria-label="Main" className="order-last -mx-1 flex w-full gap-1 overflow-x-auto px-1 md:order-none md:mx-0 md:w-auto md:px-0">
            {links.map((link) => (
              <NavLink key={link.to} to={link.to} className={navClass}>
                <Icon name={link.icon} className="h-[18px] w-[18px]" />
                <span>{link.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <span
              aria-hidden="true"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-brand/20 text-sm font-bold uppercase text-brand"
            >
              {user.email[0]}
            </span>
            <span className="hidden max-w-48 truncate text-sm text-ink-2 lg:inline">{user.email}</span>
            <button type="button" onClick={logout} className="btn btn-ghost btn-sm">
              <Icon name="logout" className="h-4 w-4" />
              <span>Log out</span>
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
        <Suspense fallback={<Spinner />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}
