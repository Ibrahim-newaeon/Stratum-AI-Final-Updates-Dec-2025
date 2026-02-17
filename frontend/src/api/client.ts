/**
 * Stratum AI - API Client
 *
 * Centralized axios client with tenant context and authentication.
 * Re-exports the existing api client with tenant-aware features.
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token management
let accessToken: string | null = null

export const setAccessToken = (token: string | null) => {
  accessToken = token
  if (token) {
    localStorage.setItem('access_token', token)
  } else {
    localStorage.removeItem('access_token')
  }
}

export const getAccessToken = (): string | null => {
  if (!accessToken) {
    accessToken = localStorage.getItem('access_token')
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

// Super admin bypass header management
let superAdminBypass = false

export const setSuperAdminBypass = (bypass: boolean) => {
  superAdminBypass = bypass
}

export const getSuperAdminBypass = (): boolean => {
  return superAdminBypass
}

// Request interceptor - add auth token, tenant ID, and super admin bypass
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

    // Add super admin bypass header if enabled
    if (superAdminBypass && config.headers) {
      config.headers['X-Superadmin-Bypass'] = 'true'
    }

    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor - handle errors and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    // Handle 401 - try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          const { access_token } = response.data
          setAccessToken(access_token)

          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`
          }
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed - logout user
        setAccessToken(null)
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
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
