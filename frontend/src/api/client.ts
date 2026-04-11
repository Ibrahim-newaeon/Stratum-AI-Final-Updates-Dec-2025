/**
 * Stratum AI - API Client
 *
 * Centralized axios client with tenant context and authentication.
 * Re-exports the existing api client with tenant-aware features.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios'

// Runtime config (injected in index.html) takes priority over build-time env
const API_BASE_URL =
  (window as any).__RUNTIME_CONFIG__?.VITE_API_URL ||
  import.meta.env.VITE_API_URL ||
  '/api/v1'

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token management — use in-memory + sessionStorage to reduce XSS persistence
// (sessionStorage is cleared when the tab closes, unlike localStorage)
let accessToken: string | null = null

export const setAccessToken = (token: string | null) => {
  accessToken = token
  if (token) {
    sessionStorage.setItem('access_token', token)
  } else {
    sessionStorage.removeItem('access_token')
  }
}

export const getAccessToken = (): string | null => {
  if (!accessToken) {
    accessToken = sessionStorage.getItem('access_token')
  }
  return accessToken
}

// Tenant ID management
let currentTenantId: number | null = null

export const setTenantId = (tenantId: number | null) => {
  currentTenantId = tenantId
  if (tenantId) {
    localStorage.setItem('tenant_id', String(tenantId))
  } else {
    localStorage.removeItem('tenant_id')
  }
}

export const getTenantId = (): number => {
  if (!currentTenantId) {
    const stored = localStorage.getItem('tenant_id')
    currentTenantId = stored ? parseInt(stored, 10) : 1
  }
  return currentTenantId
}

// Request interceptor - add auth token and tenant ID
// NOTE: X-Superadmin-Bypass removed — bypass must be validated server-side only
apiClient.interceptors.request.use(
  (config) => {
    const token = getAccessToken()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Add tenant ID header
    const tenantId = getTenantId()
    if (tenantId && config.headers) {
      config.headers['X-Tenant-ID'] = String(tenantId)
    }

    return config
  },
  (error) => Promise.reject(error)
)

// Token refresh mutex — prevents multiple concurrent 401s from each
// attempting their own refresh.  The first 401 triggers the refresh;
// subsequent 401s wait for the same promise to resolve.
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

function onTokenRefreshed(newToken: string) {
  refreshSubscribers.forEach((cb) => cb(newToken))
  refreshSubscribers = []
}

// Response interceptor - handle errors and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    // Handle 401 - try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // If a refresh is already in progress, queue this request
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((newToken: string) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${newToken}`
            }
            resolve(apiClient(originalRequest))
          })
        })
      }

      isRefreshing = true

      try {
        const refreshToken = sessionStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })

          // Backend returns APIResponse wrapper: { success, data: { access_token, refresh_token, ... } }
          const tokenData = response.data?.data ?? response.data
          const newAccessToken = tokenData.access_token
          const newRefreshToken = tokenData.refresh_token

          if (!newAccessToken) {
            throw new Error('No access_token in refresh response')
          }

          setAccessToken(newAccessToken)

          // Persist the rotated refresh token so future refreshes work
          if (newRefreshToken) {
            sessionStorage.setItem('refresh_token', newRefreshToken)
          }

          isRefreshing = false
          onTokenRefreshed(newAccessToken)

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
          }
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        isRefreshing = false
        refreshSubscribers = []
        // Refresh failed - logout user
        setAccessToken(null)
        sessionStorage.removeItem('refresh_token')
        window.location.href = '/login?reason=session_expired'
      }
    }

    return Promise.reject(error)
  }
)

// API Response types
export interface ApiResponse<T> {
  success: boolean
  data: T
  message?: string
  meta?: Record<string, any>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

export default apiClient
