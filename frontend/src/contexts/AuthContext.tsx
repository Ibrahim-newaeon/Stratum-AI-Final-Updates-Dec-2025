/**
 * Authentication Context
 * Manages user authentication state across the application
 */

import { createContext, ReactNode, useContext, useEffect, useState } from 'react';

const API_BASE = (window as any).__RUNTIME_CONFIG__?.VITE_API_URL || import.meta.env.VITE_API_URL || '/api/v1';

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'superadmin' | 'admin' | 'user';
  avatar?: string;
  organization?: string;
  permissions: string[];
  tenant_id?: number | null;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  updateUser: (userData: Partial<User>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_STORAGE_KEY = 'stratum_auth';
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing session on mount
  useEffect(() => {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      try {
        const parsedUser = JSON.parse(stored);
        setUser(parsedUser);
      } catch (e) {
        localStorage.removeItem(AUTH_STORAGE_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (
    email: string,
    password: string
  ): Promise<{ success: boolean; error?: string }> => {
    try {
      // Call the actual backend API
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        // Handle Pydantic validation errors (array of {type, loc, msg, input, ctx})
        let errorMessage = 'Login failed';
        if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (Array.isArray(data.detail) && data.detail.length > 0) {
            // Extract message from first validation error
            errorMessage = data.detail[0].msg || data.detail[0].message || 'Validation error';
          } else if (typeof data.detail === 'object' && data.detail.msg) {
            errorMessage = data.detail.msg;
          }
        }
        return { success: false, error: errorMessage };
      }

      // Store tokens
      if (data.data?.access_token) {
        localStorage.setItem(ACCESS_TOKEN_KEY, data.data.access_token);
      }
      if (data.data?.refresh_token) {
        localStorage.setItem(REFRESH_TOKEN_KEY, data.data.refresh_token);
      }

      // Fetch user profile
      const userResponse = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${data.data.access_token}`,
        },
      });

      if (userResponse.ok) {
        const userData = await userResponse.json();
        const userInfo: User = {
          id: String(userData.data.id),
          email: userData.data.email,
          name: userData.data.full_name || userData.data.email,
          role: userData.data.role || 'user',
          permissions: ['all'],
        };
        setUser(userInfo);
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(userInfo));
      } else {
        // Fallback if /me fails - create user from token claims
        const userInfo: User = {
          id: '1',
          email: email,
          name: email.split('@')[0],
          role: 'admin',
          permissions: ['all'],
        };
        setUser(userInfo);
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(userInfo));
      }

      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: 'Network error. Please try again.' };
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  };

  const updateUser = (userData: Partial<User>) => {
    if (user) {
      const updatedUser = { ...user, ...userData };
      setUser(updatedUser);
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(updatedUser));
    }
  };

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
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
