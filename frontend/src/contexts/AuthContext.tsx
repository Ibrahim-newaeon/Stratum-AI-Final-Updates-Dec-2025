/**
 * Authentication Context
 * Manages user authentication state across the application
 */

import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import { useTenantStore } from '@/stores/tenantStore';

const API_BASE = (window as any).__RUNTIME_CONFIG__?.VITE_API_URL || import.meta.env.VITE_API_URL || '/api/v1';

/** Decode JWT payload without a library */
function decodeJwtPayload(token: string): Record<string, unknown> {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
  } catch {
    return {};
  }
}

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

  // Check for existing session on mount and sync tenant store
  useEffect(() => {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      try {
        const parsedUser = JSON.parse(stored) as User;
        setUser(parsedUser);

        // Sync tenant context to Zustand store on session restore
        const tenantStore = useTenantStore.getState();
        if (parsedUser.tenant_id && !tenantStore.tenantId) {
          tenantStore.setTenantId(parsedUser.tenant_id);
        }
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

      // Extract tenant_id from JWT so we can sync it to the tenant store
      const jwtPayload = data.data?.access_token
        ? decodeJwtPayload(data.data.access_token)
        : {};
      const jwtTenantId = jwtPayload.tenant_id as number | undefined;

      // Fetch user profile
      const userResponse = await fetch(`${API_BASE}/auth/me`, {
        headers: {
          Authorization: `Bearer ${data.data.access_token}`,
        },
      });

      let userInfo: User;

      if (userResponse.ok) {
        const userData = await userResponse.json();
        const tenantId = userData.data.tenant_id ?? jwtTenantId ?? null;
        userInfo = {
          id: String(userData.data.id),
          email: userData.data.email,
          name: userData.data.full_name || userData.data.email,
          role: userData.data.role || 'user',
          permissions: ['all'],
          tenant_id: tenantId,
        };
      } else {
        // Fallback if /me fails - create user from token claims
        userInfo = {
          id: String(jwtPayload.sub ?? '1'),
          email: email,
          name: email.split('@')[0],
          role: (jwtPayload.role as User['role']) ?? 'admin',
          permissions: ['all'],
          tenant_id: jwtTenantId ?? null,
        };
      }

      setUser(userInfo);
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(userInfo));

      // Sync tenant context to Zustand store so other components pick it up
      const tenantStore = useTenantStore.getState();
      if (userInfo.tenant_id) {
        tenantStore.setTenantId(userInfo.tenant_id);
      }
      // Also sync user to tenant store for role-based features
      tenantStore.setUser({
        id: Number(userInfo.id),
        email: userInfo.email,
        full_name: userInfo.name,
        role: userInfo.role,
        avatar_url: userInfo.avatar ?? null,
        locale: 'en',
        timezone: 'UTC',
        is_active: true,
        is_verified: true,
        last_login_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
      });

      return { success: true };
    } catch (error) {
      // Error returned in result object
      return { success: false, error: 'Network error. Please try again.' };
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    // Clear Zustand tenant store on logout
    useTenantStore.getState().logout();
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
