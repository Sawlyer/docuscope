import { createContext, useCallback, useContext, useEffect, useState } from "react"
import { Navigate, useLocation } from "react-router-dom"

import { api, setUnauthorizedHandler } from "@/lib/api"
import type { User } from "@/lib/types"

interface AuthValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    localStorage.removeItem("docuscope.token")
    for (let index = localStorage.length - 1; index >= 0; index -= 1) {
      const key = localStorage.key(index)
      if (key?.startsWith("docuscope.conversations.")) localStorage.removeItem(key)
    }
    setUnauthorizedHandler(() => setUser(null))
    api
      .get<User>("/api/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const result = await api.post<{ user: User }>("/api/auth/login", { email, password })
    setUser(result.user)
    return result.user
  }, [])

  const logout = useCallback(async () => {
    await api.post<void>("/api/auth/logout")
    setUser(null)
  }, [])

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth must be used inside AuthProvider")
  return value
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return null
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  return <>{children}</>
}

/** Admin routes guard on mount too, so typing the URL cannot render a broken page. */
export function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user?.role !== "ADMIN") return <Navigate to="/" replace />
  return <>{children}</>
}
