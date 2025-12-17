/**
 * Authentication Context
 * Manages user authentication state across the application
 */

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface User {
  id: string
  email: string
  name: string
  role: 'superadmin' | 'admin' | 'user'
  avatar?: string
  organization?: string
  permissions: string[]
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>
  logout: () => void
  updateUser: (userData: Partial<User>) => void
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
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1000))

    const mockUser = MOCK_USERS[email.toLowerCase()]

    if (!mockUser) {
      return { success: false, error: 'User not found' }
    }

    if (mockUser.password !== password) {
      return { success: false, error: 'Invalid password' }
    }

    setUser(mockUser.user)
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(mockUser.user))
    return { success: true }
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

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        updateUser,
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
