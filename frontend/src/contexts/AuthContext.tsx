/**
 * Authentication Context
 * Manages user authentication state across the application
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface User {
  id: string
  email: string
  name: string
  role: 'superadmin' | 'admin' | 'user'
  avatar?: string
  organization?: string
  permissions: string[]
  plan?: string
  planExpiresAt?: string | null
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  updateUser: (userData: Partial<User>) => void
  setUser: (user: User | null) => void
  setTokens: (accessToken: string, refreshToken: string) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Mock users for demo
const MOCK_USERS: Record<string, { password: string; user: User }> = {
  'superadmin@stratum.ai': {
    password: 'admin123',
    user: {
      id: '1',
      email: 'superadmin@stratum.ai',
      name: 'Super Admin',
      role: 'superadmin',
      permissions: ['all'],
    },
  },
  'admin@company.com': {
    password: 'admin123',
    user: {
      id: '2',
      email: 'admin@company.com',
      name: 'Company Admin',
      role: 'admin',
      organization: 'Acme Corp',
      permissions: ['campaigns', 'analytics', 'users'],
    },
  },
  'user@company.com': {
    password: 'user123',
    user: {
      id: '3',
      email: 'user@company.com',
      name: 'Regular User',
      role: 'user',
      organization: 'Acme Corp',
      permissions: ['campaigns', 'analytics'],
    },
  },
}

const AUTH_STORAGE_KEY = 'stratum_auth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Check for existing session on mount
  useEffect(() => {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY)
    if (stored) {
      try {
        const parsedUser = JSON.parse(stored)
        setUser(parsedUser)
      } catch (e) {
        localStorage.removeItem(AUTH_STORAGE_KEY)
      }
    }
    setIsLoading(false)
  }, [])

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/auth/login`, {
        email,
        password,
      })

      if (response.data.success) {
        const { access_token, refresh_token } = response.data.data

        // Decode JWT to get user info (the payload is in the middle part)
        const tokenPayload = JSON.parse(atob(access_token.split('.')[1]))

        // Map to frontend User interface
        const mappedUser: User = {
          id: tokenPayload.sub,
          email: email,
          name: email.split('@')[0], // Use email prefix as name for now
          role: tokenPayload.role as 'superadmin' | 'admin' | 'user',
          permissions: tokenPayload.role === 'superadmin' ? ['all'] :
                       tokenPayload.role === 'admin' ? ['campaigns', 'analytics', 'users'] :
                       ['campaigns', 'analytics'],
        }

        // Store tokens
        localStorage.setItem('access_token', access_token)
        localStorage.setItem('refresh_token', refresh_token)

        // Set user state and persist
        setUser(mappedUser)
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(mappedUser))

        return { success: true }
      } else {
        return { success: false, error: response.data.error || 'Login failed' }
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.error || 'Invalid email or password'
      return { success: false, error: errorMessage }
    }
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem(AUTH_STORAGE_KEY)
  }

  const updateUser = (userData: Partial<User>) => {
    if (user) {
      const updatedUser = { ...user, ...userData }
      setUser(updatedUser)
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(updatedUser))
    }
  }

  const setUserAndPersist = (newUser: User | null) => {
    setUser(newUser)
    if (newUser) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(newUser))
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY)
    }
  }

  const setTokens = (accessToken: string, refreshToken: string) => {
    localStorage.setItem('access_token', accessToken)
    localStorage.setItem('refresh_token', refreshToken)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        updateUser,
        setUser: setUserAndPersist,
        setTokens,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
