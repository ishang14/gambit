import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { fetchMe, loginRequest, signupRequest } from '../api/auth.js'
import { onUnauthorized, tokenStore } from '../api/client.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // With a saved token, stay in "loading" until /auth/me says who it belongs to.
  const [loading, setLoading] = useState(() => Boolean(tokenStore.get()))

  const logout = useCallback(() => {
    tokenStore.clear()
    setUser(null)
  }, [])

  useEffect(() => {
    onUnauthorized(logout)
    return () => onUnauthorized(null)
  }, [logout])

  useEffect(() => {
    if (!tokenStore.get()) return
    let cancelled = false
    fetchMe()
      .then((me) => !cancelled && setUser(me))
      .catch(() => !cancelled && tokenStore.clear())
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  const startSession = useCallback((response) => {
    tokenStore.set(response.access_token)
    setUser(response.user)
  }, [])

  const login = useCallback(
    async (credentials) => startSession(await loginRequest(credentials)),
    [startSession],
  )

  const signup = useCallback(
    async (details) => startSession(await signupRequest(details)),
    [startSession],
  )

  const value = useMemo(
    () => ({ user, loading, login, signup, logout }),
    [user, loading, login, signup, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
