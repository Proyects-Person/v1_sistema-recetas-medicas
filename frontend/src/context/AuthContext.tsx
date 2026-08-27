import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react'
import { api, setToken } from '../services/api'
import type { User, UserConfig } from '../types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  setUser: (user: User | null) => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function applyUserConfig(config: Partial<UserConfig>) {
  if (config.theme) {
    document.documentElement.dataset.theme = config.theme
    localStorage.setItem('theme', config.theme)
  }
  if (config.language) {
    document.documentElement.lang = config.language
    localStorage.setItem('language', config.language)
  }
  if (typeof config.notifications === 'boolean') {
    localStorage.setItem('notifications', String(config.notifications))
  }
}

async function loadAndApplyConfig() {
  try {
    const config = await api.get<UserConfig>('/config')
    applyUserConfig(config)
  } catch (_) {
    const theme = localStorage.getItem('theme') || 'claro'
    const language = localStorage.getItem('language') || 'es'
    applyUserConfig({ theme, language })
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = async () => {
    const me = await api.get<User>('/auth/me')
    setUser(me)
    await loadAndApplyConfig()
  }

  useEffect(() => {
    const theme = localStorage.getItem('theme') || 'claro'
    const language = localStorage.getItem('language') || 'es'
    applyUserConfig({ theme, language })
    const boot = async () => {
      try {
        if (localStorage.getItem('token')) await refreshUser()
      } catch (_) {
        setToken(null)
        setUser(null)
      } finally {
        setLoading(false)
      }
    }
    boot()
  }, [])

  const login = async (email: string, password: string) => {
    const response = await api.post<{ access_token: string; user: User }>('/auth/login', { email, password })
    setToken(response.access_token)
    setUser(response.user)
    await loadAndApplyConfig()
  }

  const logout = async () => {
    try {
      await api.post('/auth/logout')
    } catch (_) {}
    setToken(null)
    setUser(null)
  }

  const value = useMemo(() => ({ user, loading, login, logout, refreshUser, setUser }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth debe usarse dentro de AuthProvider')
  return context
}
