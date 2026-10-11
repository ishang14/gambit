import { useCallback, useEffect, useState } from 'react'

/** Current ply (0 = start position) with arrow-key / Home / End navigation. */
export function useMoveNavigation(moveCount) {
  const [ply, setPly] = useState(0)

  const goTo = useCallback((next) => setPly(Math.max(0, Math.min(moveCount, next))), [moveCount])

  useEffect(() => {
    function onKeyDown(event) {
      if (event.target instanceof HTMLElement && ['INPUT', 'SELECT', 'TEXTAREA'].includes(event.target.tagName)) {
        return
      }
      const actions = {
        ArrowLeft: () => setPly((p) => Math.max(0, p - 1)),
        ArrowRight: () => setPly((p) => Math.min(moveCount, p + 1)),
        Home: () => setPly(0),
        End: () => setPly(moveCount),
      }
      const action = actions[event.key]
      if (action) {
        event.preventDefault()
        action()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [moveCount])

  return { ply, goTo }
}
