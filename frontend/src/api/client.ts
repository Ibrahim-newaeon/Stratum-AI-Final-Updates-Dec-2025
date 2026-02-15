/**
 * Stratum AI - API Client
 *
 * Centralized axios client with tenant context and authentication.
 * Re-exports the existing api client with tenant-aware features.
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';

const runtimeUrl = (window as unknown as { __RUNTIME_CONFIG__?: { VITE_API_URL?: string } }).__RUNTIME_CONFIG__?.VITE_API_URL;
const API_BASE_URL = runtimeUrl || import.meta.env.VITE_API_URL || '/api/v1';

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management
let accessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  accessToken = token;
  if (token) {
    localStorage.setItem('access_token', token);
  } else {
    localStorage.removeItem('access_token');
  }
};

export const getAccessToken = (): string | null => {
  if (!accessToken) {
    accessToken = localStorage.getItem('access_token');
  }
  return accessToken;
};

// Tenant ID management
let currentTenantId: number | null = null;

export const setTenantId = (tenantId: number | null) => {
  currentTenantId = tenantId;
  if (tenantId) {
    localStorage.setItem('tenant_id', String(tenantId));
  } else {
    localStorage.removeItem('tenant_id');
  }
};

// BUG-020: Don't hardcode default tenant ID — return 0 (no tenant) instead of 1
// The actual tenant ID should come from the user's JWT / session, not a magic default.
export const getTenantId = (): number => {
  if (!currentTenantId) {
    const stored = localStorage.getItem('tenant_id');
    currentTenantId = stored ? parseInt(stored, 10) : 0;
  }
  return currentTenantId;
};

// BUG-022: Super admin bypass header management — read persisted state on init
let superAdminBypass = (() => {
  try {
    const stored = localStorage.getItem('stratum-tenant-store');
    if (stored) {
      const parsed = JSON.parse(stored);
      return parsed?.state?.superAdminBypass === true;
    }
  } catch { /* ignore */ }
  return false;
})();

export const setSuperAdminBypass = (bypass: boolean) => {
  superAdminBypass = bypass;
};

export const getSuperAdminBypass = (): boolean => {
  return superAdminBypass;
};

// Request interceptor - add auth token, tenant ID, and super admin bypass
apiClient.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Add tenant ID header
    const tenantId = getTenantId();
    if (tenantId && config.headers) {
      config.headers['X-Tenant-ID'] = String(tenantId);
    }

    // Add super admin bypass header if enabled
    if (superAdminBypass && config.headers) {
      config.headers['X-Superadmin-Bypass'] = 'true';
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Handle 401 - try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // BUG-004: In demo mode, don't attempt token refresh or redirect — just reject
      const isDemoMode = localStorage.getItem('stratum_demo_mode') === 'true';
      if (isDemoMode) {
        return Promise.reject(error);
      }

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token } = response.data;
          setAccessToken(access_token);

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed - clear tokens gracefully
        setAccessToken(null);
        localStorage.removeItem('refresh_token');

        // BUG-004: Only redirect if not already on login page to prevent redirect loops
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }

    return Promise.reject(error);
  }
);

// API Response types
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  meta?: Record<string, any>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export default apiClient;
