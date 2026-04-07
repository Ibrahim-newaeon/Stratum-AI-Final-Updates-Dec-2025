/**
 * Stratum AI - EMQ v2 Enhanced API
 *
 * Event Measurement Quality endpoints with Trust Layer integration
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface EmqDriver {
  name: string
  value: number
  weight: number
  status: 'good' | 'warning' | 'critical'
  trend: 'up' | 'down' | 'flat'
}

export interface EmqScore {
  score: number
  previousScore: number
  confidenceBand: 'reliable' | 'directional' | 'unsafe'
  drivers: EmqDriver[]
  lastUpdated: string
}

export interface ConfidenceData {
  band: 'reliable' | 'directional' | 'unsafe'
  score: number
  thresholds: {
    reliable: number
    directional: number
  }
  factors: {
    name: string
    contribution: number
    status: 'positive' | 'negative' | 'neutral'
  }[]
}

export interface PlaybookItem {
  id: string
  title: string
  description: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  owner: string | null
  estimatedImpact: number
  estimatedTime: string | null
  platform: string | null
  status: 'pending' | 'in_progress' | 'completed'
  actionUrl: string | null
}

export interface EmqIncident {
  id: string
  type: 'incident_opened' | 'incident_closed' | 'degradation' | 'recovery'
  title: string
  description: string | null
  timestamp: string
  platform: string | null
  severity: 'critical' | 'high' | 'medium' | 'low'
  recoveryHours: number | null
  emqImpact: number | null
}

export interface EmqImpact {
  totalImpact: number
  currency: string
  breakdown: {
    platform: string
    actualRoas: number
    estimatedRoas: number
    confidence: number
    revenueImpact: number
  }[]
}

export interface EmqVolatility {
  svi: number // Signal Volatility Index
  trend: 'increasing' | 'decreasing' | 'stable'
  weeklyData: {
    date: string
    value: number
  }[]
}

export interface EmqBenchmark {
  platform: string
  p25: number
  p50: number
  p75: number
  tenantScore: number
  percentile: number
}

export interface EmqPortfolio {
  totalTenants: number
  byBand: {
    reliable: number
    directional: number
    unsafe: number
  }
  atRiskBudget: number
  avgScore: number
  topIssues: {
    driver: string
    affectedTenants: number
  }[]
}

export type AutopilotMode = 'normal' | 'limited' | 'cuts_only' | 'frozen'

export interface AutopilotState {
  mode: AutopilotMode
  reason: string | null
  budgetAtRisk: number
  allowedActions: string[]
  restrictedActions: string[]
}

// API Functions
export const emqV2Api = {
  /**
   * Get current EMQ score for a tenant
   */
  getEmqScore: async (tenantId: number, date?: string): Promise<EmqScore> => {
    const params = date ? { date } : {}
    const response = await apiClient.get<ApiResponse<EmqScore>>(
      `/emq/v2/tenants/${tenantId}/score`,
      { params }
    )
    return response.data.data
  },

  /**
   * Get confidence band details
   */
  getConfidence: async (tenantId: number, date?: string): Promise<ConfidenceData> => {
    const params = date ? { date } : {}
    const response = await apiClient.get<ApiResponse<ConfidenceData>>(
      `/emq/v2/tenants/${tenantId}/confidence`,
      { params }
    )
    return response.data.data
  },

  /**
   * Get fix playbook items
   */
  getPlaybook: async (tenantId: number): Promise<PlaybookItem[]> => {
    const response = await apiClient.get<ApiResponse<PlaybookItem[]>>(
      `/emq/v2/tenants/${tenantId}/playbook`
    )
    return response.data.data
  },

  /**
   * Update playbook item status
   */
  updatePlaybookItem: async (
    tenantId: number,
    itemId: string,
    updates: Partial<Pick<PlaybookItem, 'status' | 'owner'>>
  ): Promise<PlaybookItem> => {
    const response = await apiClient.patch<ApiResponse<PlaybookItem>>(
      `/emq/v2/tenants/${tenantId}/playbook/${itemId}`,
      updates
    )
    return response.data.data
  },

  /**
   * Get incident timeline
   */
  getIncidents: async (
    tenantId: number,
    startDate: string,
    endDate: string
  ): Promise<EmqIncident[]> => {
    const response = await apiClient.get<ApiResponse<EmqIncident[]>>(
      `/emq/v2/tenants/${tenantId}/incidents`,
      { params: { start_date: startDate, end_date: endDate } }
    )
    return response.data.data
  },

  /**
   * Get ROAS impact estimate
   */
  getImpact: async (tenantId: number, startDate: string, endDate: string): Promise<EmqImpact> => {
    const response = await apiClient.get<ApiResponse<EmqImpact>>(
      `/emq/v2/tenants/${tenantId}/impact`,
      { params: { start_date: startDate, end_date: endDate } }
    )
    return response.data.data
  },

  /**
   * Get signal volatility data
   */
  getVolatility: async (tenantId: number, week?: string): Promise<EmqVolatility> => {
    const params = week ? { week } : {}
    const response = await apiClient.get<ApiResponse<EmqVolatility>>(
      `/emq/v2/tenants/${tenantId}/volatility`,
      { params }
    )
    return response.data.data
  },

  /**
   * Get autopilot state
   */
  getAutopilotState: async (tenantId: number): Promise<AutopilotState> => {
    const response = await apiClient.get<ApiResponse<AutopilotState>>(
      `/emq/v2/tenants/${tenantId}/autopilot`
    )
    return response.data.data
  },

  /**
   * Update autopilot mode (manual override)
   */
  updateAutopilotMode: async (
    tenantId: number,
    mode: AutopilotMode,
    reason?: string
  ): Promise<AutopilotState> => {
    const response = await apiClient.put<ApiResponse<AutopilotState>>(
      `/emq/v2/tenants/${tenantId}/autopilot`,
      { mode, reason }
    )
    return response.data.data
  },

  // Super Admin endpoints
  /**
   * Get EMQ benchmarks across platform (super admin)
   */
  getBenchmarks: async (date?: string, platform?: string): Promise<EmqBenchmark[]> => {
    const params: Record<string, string> = {}
    if (date) params.date = date
    if (platform) params.platform = platform
    const response = await apiClient.get<ApiResponse<EmqBenchmark[]>>(
      '/emq/v2/benchmarks',
      { params }
    )
    return response.data.data
  },

  /**
   * Get portfolio overview (super admin)
   */
  getPortfolio: async (date?: string): Promise<EmqPortfolio> => {
    const params = date ? { date } : {}
    const response = await apiClient.get<ApiResponse<EmqPortfolio>>(
      '/emq/v2/portfolio',
      { params }
    )
    return response.data.data
  },
}

// React Query Hooks

export function useEmqScore(tenantId: number, date?: string) {
  return useQuery({
    queryKey: ['emq', 'score', tenantId, date],
    queryFn: () => emqV2Api.getEmqScore(tenantId, date),
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  })
}

export function useConfidence(tenantId: number, date?: string) {
  return useQuery({
    queryKey: ['emq', 'confidence', tenantId, date],
    queryFn: () => emqV2Api.getConfidence(tenantId, date),
    staleTime: 60 * 1000,
  })
}

export function useEmqPlaybook(tenantId: number) {
  return useQuery({
    queryKey: ['emq', 'playbook', tenantId],
    queryFn: () => emqV2Api.getPlaybook(tenantId),
    staleTime: 30 * 1000,
  })
}

export function useUpdatePlaybookItem(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ itemId, updates }: { itemId: string; updates: Partial<Pick<PlaybookItem, 'status' | 'owner'>> }) =>
      emqV2Api.updatePlaybookItem(tenantId, itemId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emq', 'playbook', tenantId] })
    },
  })
}

export function useEmqIncidents(tenantId: number, startDate: string, endDate: string) {
  return useQuery({
    queryKey: ['emq', 'incidents', tenantId, startDate, endDate],
    queryFn: () => emqV2Api.getIncidents(tenantId, startDate, endDate),
    staleTime: 60 * 1000,
  })
}

export function useEmqImpact(tenantId: number, startDate: string, endDate: string) {
  return useQuery({
    queryKey: ['emq', 'impact', tenantId, startDate, endDate],
    queryFn: () => emqV2Api.getImpact(tenantId, startDate, endDate),
    staleTime: 5 * 60 * 1000,
  })
}

export function useEmqVolatility(tenantId: number, week?: string) {
  return useQuery({
    queryKey: ['emq', 'volatility', tenantId, week],
    queryFn: () => emqV2Api.getVolatility(tenantId, week),
    staleTime: 60 * 1000,
  })
}

export function useAutopilotState(tenantId: number) {
  return useQuery({
    queryKey: ['emq', 'autopilot', tenantId],
    queryFn: () => emqV2Api.getAutopilotState(tenantId),
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  })
}

export function useUpdateAutopilotMode(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ mode, reason }: { mode: AutopilotMode; reason?: string }) =>
      emqV2Api.updateAutopilotMode(tenantId, mode, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emq', 'autopilot', tenantId] })
    },
  })
}

// Super Admin hooks
export function useEmqBenchmarks(date?: string, platform?: string) {
  return useQuery({
    queryKey: ['emq', 'benchmarks', date, platform],
    queryFn: () => emqV2Api.getBenchmarks(date, platform),
    staleTime: 5 * 60 * 1000,
  })
}

export function useEmqPortfolio(date?: string) {
  return useQuery({
    queryKey: ['emq', 'portfolio', date],
    queryFn: () => emqV2Api.getPortfolio(date),
    staleTime: 5 * 60 * 1000,
  })
}
