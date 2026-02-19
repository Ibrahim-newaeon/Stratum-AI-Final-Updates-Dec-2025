/**
 * Service-layer API namespaces.
 *
 * IMPORTANT: This module re-uses the canonical axios client from `@/api/client`
 * so there is a single source of truth for auth tokens, tenant headers, and
 * token refresh logic. Do NOT create a separate axios instance here.
 */

import { apiClient, setAccessToken, getAccessToken } from '@/api/client'

export { setAccessToken, getAccessToken }

// API Response types
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

// Auth API
export const authApi = {
  login: async (email: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', email)
    formData.append('password', password)

    const response = await apiClient.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    return response.data
  },

  register: async (data: { email: string; password: string; full_name: string }) => {
    const response = await apiClient.post('/auth/register', data)
    return response.data
  },

  logout: async () => {
    const response = await apiClient.post('/auth/logout')
    setAccessToken(null)
    localStorage.removeItem('refresh_token')
    return response.data
  },

  refreshToken: async (refreshToken: string) => {
    const response = await apiClient.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },
}

// Campaigns API
export const campaignsApi = {
  list: async (params?: { page?: number; page_size?: number; status?: string; platform?: string }) => {
    const response = await apiClient.get('/campaigns', { params })
    return response.data
  },

  get: async (id: number) => {
    const response = await apiClient.get(`/campaigns/${id}`)
    return response.data
  },

  create: async (data: any) => {
    const response = await apiClient.post('/campaigns', data)
    return response.data
  },

  update: async (id: number, data: any) => {
    const response = await apiClient.put(`/campaigns/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    const response = await apiClient.delete(`/campaigns/${id}`)
    return response.data
  },

  getMetrics: async (id: number, params?: { start_date?: string; end_date?: string }) => {
    const response = await apiClient.get(`/campaigns/${id}/metrics`, { params })
    return response.data
  },
}

// Assets API
export const assetsApi = {
  list: async (params?: { page?: number; page_size?: number; type?: string }) => {
    const response = await apiClient.get('/assets', { params })
    return response.data
  },

  get: async (id: number) => {
    const response = await apiClient.get(`/assets/${id}`)
    return response.data
  },

  upload: async (file: File, metadata?: any) => {
    const formData = new FormData()
    formData.append('file', file)
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata))
    }

    const response = await apiClient.post('/assets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  delete: async (id: number) => {
    const response = await apiClient.delete(`/assets/${id}`)
    return response.data
  },

  getFatigueScores: async () => {
    const response = await apiClient.get('/assets/fatigue')
    return response.data
  },
}

// Rules API
export const rulesApi = {
  list: async (params?: { page?: number; page_size?: number; status?: string }) => {
    const response = await apiClient.get('/rules', { params })
    return response.data
  },

  get: async (id: number) => {
    const response = await apiClient.get(`/rules/${id}`)
    return response.data
  },

  create: async (data: any) => {
    const response = await apiClient.post('/rules', data)
    return response.data
  },

  update: async (id: number, data: any) => {
    const response = await apiClient.put(`/rules/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    const response = await apiClient.delete(`/rules/${id}`)
    return response.data
  },

  test: async (id: number) => {
    const response = await apiClient.post(`/rules/${id}/test`)
    return response.data
  },

  getExecutions: async (id: number, params?: { page?: number; page_size?: number }) => {
    const response = await apiClient.get(`/rules/${id}/executions`, { params })
    return response.data
  },
}

// Analytics API
export const analyticsApi = {
  getKPIs: async (params?: { start_date?: string; end_date?: string }) => {
    const response = await apiClient.get('/analytics/kpis', { params })
    return response.data
  },

  getDemographics: async (params?: { start_date?: string; end_date?: string }) => {
    const response = await apiClient.get('/analytics/demographics', { params })
    return response.data
  },

  getHeatmap: async (params?: { start_date?: string; end_date?: string }) => {
    const response = await apiClient.get('/analytics/heatmap', { params })
    return response.data
  },

  getPlatformBreakdown: async (params?: { start_date?: string; end_date?: string }) => {
    const response = await apiClient.get('/analytics/platforms', { params })
    return response.data
  },

  // New template-based endpoints
  getPerformanceData: async (filters: {
    date_range: { start: string; end: string }
    platforms: string[]
    regions: string[]
    campaign_types: string[]
  }) => {
    const response = await apiClient.post('/analytics/performance', filters)
    return response.data
  },

  getCampaignDetails: async (campaignId: string) => {
    const response = await apiClient.get(`/analytics/campaigns/${campaignId}`)
    return response.data
  },

  getAlerts: async (unreadOnly: boolean = false) => {
    const response = await apiClient.get('/analytics/alerts', {
      params: { unread_only: unreadOnly },
    })
    return response.data
  },

  markAlertAsRead: async (alertId: string) => {
    const response = await apiClient.patch(`/analytics/alerts/${alertId}/read`)
    return response.data
  },

  optimizeBudget: async (data: {
    total_budget: number
    optimization_goal: string
    filters: {
      date_range: { start: string; end: string }
      platforms: string[]
      regions: string[]
      campaign_types: string[]
    }
  }) => {
    const response = await apiClient.post('/analytics/budget/optimize', data)
    return response.data
  },

  requestExport: async (data: {
    format: 'csv' | 'excel' | 'pdf'
    filters: {
      date_range: { start: string; end: string }
      platforms: string[]
      regions: string[]
      campaign_types: string[]
    }
  }) => {
    const response = await apiClient.post('/analytics/export', data)
    return response.data
  },

  checkExportStatus: async (taskId: string) => {
    const response = await apiClient.get(`/analytics/export/${taskId}/status`)
    return response.data
  },

  triggerPlatformSync: async (platforms: string[]) => {
    const response = await apiClient.post('/analytics/sync', { platforms })
    return response.data
  },

  getSyncStatus: async (taskId: string) => {
    const response = await apiClient.get(`/analytics/sync/${taskId}/status`)
    return response.data
  },

  // New endpoints for Dashboard v2
  getTenantOverview: async () => {
    const response = await apiClient.get('/analytics/tenant-overview')
    return response.data
  },

  getExecutiveSummary: async () => {
    const response = await apiClient.get('/analytics/executive-summary')
    return response.data
  },

  getTrends: async (params?: { metric?: string; days?: number }) => {
    const response = await apiClient.get('/analytics/trends', { params })
    return response.data
  },
}

// Simulator API
export const simulatorApi = {
  simulate: async (data: {
    campaign_id?: number
    budget_change: number
    bid_change: number
    audience_change: number
  }) => {
    const response = await apiClient.post('/simulator/what-if', data)
    return response.data
  },

  getForecast: async (params?: { days?: number }) => {
    const response = await apiClient.get('/simulator/forecast', { params })
    return response.data
  },
}

// Competitors API
export const competitorsApi = {
  list: async () => {
    const response = await apiClient.get('/competitors')
    return response.data
  },

  getBenchmarks: async (params?: { industry?: string }) => {
    const response = await apiClient.get('/competitors/benchmarks', { params })
    return response.data
  },

  getMarketShare: async () => {
    const response = await apiClient.get('/competitors/market-share')
    return response.data
  },

  refreshData: async () => {
    const response = await apiClient.post('/competitors/refresh')
    return response.data
  },
}

// GDPR API
export const gdprApi = {
  requestExport: async () => {
    const response = await apiClient.post('/gdpr/export')
    return response.data
  },

  getExportStatus: async (exportId: string) => {
    const response = await apiClient.get(`/gdpr/export/${exportId}`)
    return response.data
  },

  downloadExport: async (exportId: string) => {
    const response = await apiClient.get(`/gdpr/export/${exportId}/download`, {
      responseType: 'blob',
    })
    return response.data
  },

  requestDeletion: async () => {
    const response = await apiClient.post('/gdpr/anonymize')
    return response.data
  },
}

// User API
export const userApi = {
  getProfile: async () => {
    const response = await apiClient.get('/users/me')
    return response.data
  },

  updateProfile: async (data: any) => {
    const response = await apiClient.put('/users/me', data)
    return response.data
  },

  updatePassword: async (data: { current_password: string; new_password: string }) => {
    const response = await apiClient.put('/users/me/password', data)
    return response.data
  },

  getNotificationPreferences: async () => {
    const response = await apiClient.get('/users/me/notifications')
    return response.data
  },

  updateNotificationPreferences: async (data: any) => {
    const response = await apiClient.put('/users/me/notifications', data)
    return response.data
  },
}

// WhatsApp API
export const whatsappApi = {
  // Contacts
  listContacts: async (params?: {
    page?: number
    page_size?: number
    opt_in_status?: string
    search?: string
  }) => {
    const response = await apiClient.get('/whatsapp/contacts', { params })
    return response.data
  },

  createContact: async (data: {
    phone_number: string
    country_code: string
    display_name?: string
    opt_in_method?: string
  }) => {
    const response = await apiClient.post('/whatsapp/contacts', data)
    return response.data
  },

  verifyContact: async (contactId: number) => {
    const response = await apiClient.post(`/whatsapp/contacts/${contactId}/verify`)
    return response.data
  },

  optInContact: async (contactId: number, method: string = 'web_form') => {
    const response = await apiClient.post(`/whatsapp/contacts/${contactId}/opt-in`, null, {
      params: { method },
    })
    return response.data
  },

  optOutContact: async (contactId: number) => {
    const response = await apiClient.post(`/whatsapp/contacts/${contactId}/opt-out`)
    return response.data
  },

  // Templates
  listTemplates: async (params?: {
    page?: number
    page_size?: number
    status?: string
    category?: string
  }) => {
    const response = await apiClient.get('/whatsapp/templates', { params })
    return response.data
  },

  createTemplate: async (data: {
    name: string
    language: string
    category: string
    body_text: string
    header_type?: string
    header_content?: string
    footer_text?: string
    header_variables?: string[]
    body_variables?: string[]
    buttons?: any[]
  }) => {
    const response = await apiClient.post('/whatsapp/templates', data)
    return response.data
  },

  // Messages
  sendMessage: async (data: {
    contact_id: number
    message_type: string
    template_name?: string
    template_variables?: Record<string, any>
    content?: string
    media_url?: string
    scheduled_at?: string
  }) => {
    const response = await apiClient.post('/whatsapp/messages/send', data)
    return response.data
  },

  listMessages: async (params?: {
    contact_id?: number
    status?: string
    page?: number
    page_size?: number
  }) => {
    const response = await apiClient.get('/whatsapp/messages', { params })
    return response.data
  },

  getMessage: async (messageId: number) => {
    const response = await apiClient.get(`/whatsapp/messages/${messageId}`)
    return response.data
  },

  // Conversations
  listConversations: async (params?: {
    contact_id?: number
    active_only?: boolean
    page?: number
    page_size?: number
  }) => {
    const response = await apiClient.get('/whatsapp/conversations', { params })
    return response.data
  },
}

// SSE Events
export const createEventSource = (endpoint: string): EventSource => {
  const token = getAccessToken()
  const baseURL = apiClient.defaults.baseURL || '/api/v1'
  const url = new URL(`${baseURL}${endpoint}`, window.location.origin)
  if (token) {
    url.searchParams.set('token', token)
  }
  return new EventSource(url.toString())
}

export default apiClient
