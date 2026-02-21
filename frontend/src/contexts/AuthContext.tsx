/**
 * Authentication Context
 * Manages user authentication state across the application
 */

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useTenantStore } from '@/stores/tenantStore';
import { useIdleTimeout } from '@/hooks/useIdleTimeout';
import IdleTimeoutWarning from '@/components/auth/IdleTimeoutWarning';

const API_BASE = window.__RUNTIME_CONFIG__?.VITE_API_URL || import.meta.env.VITE_API_URL || '/api/v1';

/**
 * Demo credentials for client-side fallback when backend is unavailable.
 * SECURITY: Never include real credentials here. These are demo-only placeholders.
 * In production, demo mode should be disabled via environment variable.
 */
const DEMO_CREDENTIALS: Record<string, { email: string; password: string; user: User }> = {
  superadmin: {
    email: 'demo-superadmin@stratum.ai',
    password: 'demo-only-not-real',
    user: {
      id: 'demo-sa-001',
      email: 'demo-superadmin@stratum.ai',
      name: 'Demo Super Admin',
      role: 'superadmin',
      organization: 'Demo Organization',
      permissions: ['all'],
      tenant_id: 1,
      user_type: 'agency',
      cms_role: 'super_admin',
    },
  },
  admin: {
    email: 'demo-admin@stratum.ai',
    password: 'demo-only-not-real',
    user: {
      id: 'demo-admin-001',
      email: 'demo-admin@stratum.ai',
      name: 'Demo Admin',
      role: 'admin',
      organization: 'Demo Commerce',
      permissions: ['all'],
      tenant_id: 1,
      user_type: 'agency',
      cms_role: 'admin',
    },
  },
  manager: {
    email: 'demo-manager@stratum.ai',
    password: 'demo-only-not-real',
    user: {
      id: 'demo-mgr-001',
      email: 'demo-manager@stratum.ai',
      name: 'Demo Manager',
      role: 'manager',
      organization: 'Demo Commerce',
      permissions: ['read'],
      tenant_id: 1,
      user_type: 'agency',
    },
  },
  analyst: {
    email: 'demo-analyst@stratum.ai',
    password: 'demo-only-not-real',
    user: {
      id: 'demo-analyst-001',
      email: 'demo-analyst@stratum.ai',
      name: 'Demo Analyst',
      role: 'analyst',
      organization: 'Demo Commerce',
      permissions: ['read'],
      tenant_id: 1,
      user_type: 'agency',
    },
  },
  viewer: {
    email: 'demo-viewer@stratum.ai',
    password: 'demo-only-not-real',
    user: {
      id: 'demo-viewer-001',
      email: 'demo-viewer@stratum.ai',
      name: 'Demo Client Viewer',
      role: 'viewer',
      organization: 'Demo Commerce',
      permissions: ['read'],
      tenant_id: 1,
      user_type: 'portal',
      client_id: 1,
    },
  },
};

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
  role: 'superadmin' | 'admin' | 'manager' | 'analyst' | 'viewer';
  avatar?: string;
  organization?: string;
  permissions: string[];
  tenant_id?: number | null;
  /** "agency" (default) or "portal" (client viewer) */
  user_type?: 'agency' | 'portal';
  /** Client ID for portal (VIEWER) users */
  client_id?: number | null;
  /** CMS-specific role (separate from platform role) */
  cms_role?: string | null;
  /** CMS permission map fetched from the backend */
  cms_permissions?: Record<string, boolean>;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isDemoSession: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string; lockoutSeconds?: number }>;
  demoLogin: (role: 'superadmin' | 'admin' | 'manager' | 'analyst' | 'viewer') => Promise<{ success: boolean; error?: string; lockoutSeconds?: number }>;
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
  const [isDemoSession, setIsDemoSession] = useState(false);

  // Check for existing session on mount and sync tenant store
  useEffect(() => {
    const isDemo = localStorage.getItem('stratum_demo_mode') === 'true';
    setIsDemoSession(isDemo);

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
  ): Promise<{ success: boolean; error?: string; lockoutSeconds?: number }> => {
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
        // Handle 429 Too Many Requests — account lockout
        if (response.status === 429) {
          const retryAfter = response.headers.get('Retry-After');
          let lockoutSeconds = 900; // default 15 minutes
          if (retryAfter) {
            const parsed = parseInt(retryAfter, 10);
            if (!isNaN(parsed) && parsed > 0) lockoutSeconds = parsed;
          } else if (typeof data.detail === 'string') {
            // Try to extract seconds from detail message: "Try again in 123 seconds."
            const match = data.detail.match(/(\d+)\s*seconds?/i);
            if (match) lockoutSeconds = parseInt(match[1], 10);
          }
          return {
            success: false,
            error: 'Too many failed login attempts.',
            lockoutSeconds,
          };
        }

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
        // Map backend role to valid frontend role (fallback to 'analyst')
        const backendRole = userData.data.role || 'analyst';
        const validRoles = ['superadmin', 'admin', 'manager', 'analyst', 'viewer'];
        const mappedRole = validRoles.includes(backendRole) ? backendRole : 'analyst';
        userInfo = {
          id: String(userData.data.id),
          email: userData.data.email,
          name: userData.data.full_name || userData.data.email,
          role: mappedRole as User['role'],
          permissions: ['all'],
          tenant_id: tenantId,
          user_type: userData.data.user_type || 'agency',
          client_id: userData.data.client_id ?? null,
          cms_role: userData.data.cms_role ?? null,
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
          user_type: 'agency',
          cms_role: (jwtPayload.cms_role as string) ?? null,
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

  /** Client-side demo login — creates a mock session without hitting the backend */
  const demoLogin = useCallback(
    async (role: 'superadmin' | 'admin' | 'manager' | 'analyst' | 'viewer'): Promise<{ success: boolean; error?: string }> => {
      const demo = DEMO_CREDENTIALS[role];
      if (!demo) return { success: false, error: 'Unknown demo role' };

      // First try the real backend
      try {
        const result = await login(demo.email, demo.password);
        if (result.success) return result;
      } catch {
        // Backend unavailable — fall through to client-side fallback
      }

      // Client-side fallback: set user directly without API
      const demoUser = { ...demo.user };

      setUser(demoUser);
      setIsDemoSession(true);
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(demoUser));
      localStorage.setItem('stratum_demo_mode', 'true');

      // Set a placeholder token so the API interceptor doesn't redirect
      localStorage.setItem(ACCESS_TOKEN_KEY, 'demo-token');
      localStorage.setItem(REFRESH_TOKEN_KEY, 'demo-refresh-token');

      // Sync tenant store
      const tenantStore = useTenantStore.getState();
      if (demoUser.tenant_id) {
        tenantStore.setTenantId(demoUser.tenant_id);
      }
      tenantStore.setUser({
        id: Number(demoUser.id.replace(/\D/g, '')) || 1,
        email: demoUser.email,
        full_name: demoUser.name,
        role: demoUser.role,
        avatar_url: null,
        locale: 'en',
        timezone: 'UTC',
        is_active: true,
        is_verified: true,
        last_login_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
      });

      return { success: true };
    },
    [login]
  );

  const logout = () => {
    setUser(null);
    setIsDemoSession(false);
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem('stratum_demo_mode');
    // BUG-023: Clean up all onboarding-related localStorage keys on logout
    localStorage.removeItem('stratum_onboarding_progress');
    localStorage.removeItem('stratum_onboarding_dismissed');
    localStorage.removeItem('stratum_onboarding_skipped');
    localStorage.removeItem('stratum_onboarding_demo_dismissed');
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

  // BUG-014: Session idle timeout — auto-logout after 30 min of inactivity
  const { isWarning, secondsLeft, resetTimer } = useIdleTimeout({
    timeout: 30 * 60 * 1000, // 30 minutes
    warningDuration: 60 * 1000, // 60-second warning
    onTimeout: () => {
      logout();
      window.location.href = '/login?reason=idle';
    },
    enabled: !!user, // Only active when logged in
  });

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      isDemoSession,
      login,
      demoLogin,
      logout,
      updateUser,
    }),
    [user, isLoading, isDemoSession, login, demoLogin, logout, updateUser]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
      {isWarning && (
        <IdleTimeoutWarning secondsLeft={secondsLeft} onStay={resetTimer} />
      )}
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
