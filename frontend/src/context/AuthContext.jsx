import { useCallback, useEffect, useMemo, useState } from 'react'
import { clearToken, getMe, getToken, loginUser, registerUser, setToken } from '../api'
import { AuthContext } from './AuthContextObject'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshMe = useCallback(async () => {
    const token = getToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const res = await getMe()
      setUser(res.data)
    } catch {
      clearToken()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshMe()
  }, [refreshMe])

  const login = useCallback(async (user_id, password) => {
    const res = await loginUser({ user_id, password })
    setToken(res.data.access_token)
    await refreshMe()
  }, [refreshMe])

  const register = useCallback(async (user_id, password, initial_balance) => {
    const res = await registerUser({ user_id, password, initial_balance })
    setToken(res.data.access_token)
    await refreshMe()
  }, [refreshMe])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshMe }),
    [user, loading, login, register, logout, refreshMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
