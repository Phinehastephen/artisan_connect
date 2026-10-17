import { createContext, useContext, useEffect, useState } from 'react'
import { apiRequest, tokenStorage } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => tokenStorage.getUser())
  const [loading, setLoading] = useState(Boolean(tokenStorage.getAccessToken()))

  useEffect(() => {
    let active = true
    const accessToken = tokenStorage.getAccessToken()

    const handleExpired = () => {
      tokenStorage.clear()
      setUser(null)
      setLoading(false)
    }
    window.addEventListener('artisan-auth-expired', handleExpired)

    if (!accessToken) {
      setLoading(false)
      return () => window.removeEventListener('artisan-auth-expired', handleExpired)
    }

    apiRequest('/accounts/auth/me')
      .then((profile) => {
        if (!active) return
        tokenStorage.save({
          access: tokenStorage.getAccessToken(),
          refresh: tokenStorage.getRefreshToken(),
          user: profile,
        })
        setUser(profile)
      })
      .catch(() => {
        if (!active) return
        tokenStorage.clear()
        setUser(null)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
      window.removeEventListener('artisan-auth-expired', handleExpired)
    }
  }, [])

  async function login(username, password) {
    const data = await apiRequest('/accounts/auth/login', {
      method: 'POST',
      body: { username, password },
    })
    const profile = {
      username: data.username,
      email: data.email,
      role: data.role,
    }
    tokenStorage.save({ ...data, user: profile })
    setUser(profile)
    return profile
  }

  async function logout() {
    const refresh = tokenStorage.getRefreshToken()
    try {
      if (refresh) {
        await apiRequest('/accounts/auth/logout', {
          method: 'POST',
          body: { refresh },
        })
      }
    } finally {
      tokenStorage.clear()
      setUser(null)
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider.')
  return context
}

export function homeForRole(role) {
  return {
    CUSTOMER: '/customer',
    ARTISAN: '/artisan',
    ADMIN: '/admin',
  }[role] || '/login'
}