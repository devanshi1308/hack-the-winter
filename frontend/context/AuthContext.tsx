"use client"

import { createContext, useContext, useEffect, useState } from "react"
import { useRouter } from "next/navigation"

interface User {
  id: string
  email: string
  name: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    // Load user data from localStorage on mount
    if (typeof window !== "undefined") {
      const storedToken = localStorage.getItem("auth_token")
      const storedUserId = localStorage.getItem("user_id")
      const storedEmail = localStorage.getItem("user_email")
      const storedName = localStorage.getItem("user_name")

      if (storedToken && storedUserId && storedEmail) {
        setToken(storedToken)
        setUser({
          id: storedUserId,
          email: storedEmail,
          name: storedName || "",
        })
      }

      setIsLoading(false)
    }
  }, [])

  const logout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth_token")
      localStorage.removeItem("user_id")
      localStorage.removeItem("user_email")
      localStorage.removeItem("user_name")
    }
    setUser(null)
    setToken(null)
    router.push("/login")
  }

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    isAuthenticated: !!token && !!user,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuthContext() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuthContext must be used within an AuthProvider")
  }
  return context
}
