import { useCallback, useState } from 'react'

const KEY = 'gambit_theme'

function currentTheme() {
  return document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'
}

/** Light/dark theme. index.html sets the first value before paint; this toggles and remembers it. */
export function useTheme() {
  const [theme, setTheme] = useState(currentTheme)

  const toggle = useCallback(() => {
    const next = currentTheme() === 'light' ? 'dark' : 'light'
    document.documentElement.dataset.theme = next
    try {
      localStorage.setItem(KEY, next)
    } catch {
      // Storage can be blocked; the theme still applies for this visit.
    }
    setTheme(next)
  }, [])

  return { theme, toggle }
}
