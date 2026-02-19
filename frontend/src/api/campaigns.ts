/**
 * Stratum AI - Campaigns API
 *
 * Campaign management endpoints for CRUD operations and metrics
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse, PaginatedResponse } from './client'

// Types
export type Platform = 'meta' | 'google' | 'tiktok' | 'snapchat' | 'linkedin'
export type CampaignStatus = 'active' | 'paused' | 'completed' | 'draft' | 'error'
export type CampaignObjective = 'awareness' | 'consideration' | 'conversion'

export interface Campaign {
  id: string
  tenantId: number
  platform: Platform
  platformCampaignId: string
  name: string
  status: CampaignStatus
  objective: CampaignObjective
  budget: number
  dailyBudget: number | null
  currency: string
  startDate: string
  endDate: string | null
  createdAt: string
  updatedAt: string
  lastSyncedAt: string | null
}

export interface CampaignMetrics {
  campaignId: string
  date: string
  spend: number
  impressions: number
  clicks: number
  conversions: number
  revenue: number
  roas: number
  ctr: number
  cpc: number
  cpa: number
  reach: number | null
  frequency: number | null
}

export interface CampaignWithMetrics extends Campaign {
  metrics: CampaignMetrics
  previousMetrics?: CampaignMetrics
}

export interface CampaignFilters {
  platform?: Platform
  status?: CampaignStatus
  objective?: CampaignObjective
  startDate?: string
  endDate?: string
  search?: string
  skip?: number
  limit?: number
}

export interface CreateCampaignRequest {
  platform: Platform
  name: string
  objective: CampaignObjective
  budget: number
  dailyBudget?: number
  currency?: string
  startDate: string
  endDate?: string
  targeting?: Record<string, unknown>
  creatives?: string[]
}

export interface UpdateCampaignRequest {
  name?: string
  status?: CampaignStatus
  budget?: number
  dailyBudget?: number
  endDate?: string
  targeting?: Record<string, unknown>
}

// API Functions
export const campaignsApi = {
  /**
   * Get all campaigns with optional filters
   */
  getCampaigns: async (filters: CampaignFilters = {}): Promise<PaginatedResponse<CampaignWithMetrics>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<CampaignWithMetrics>>>(
      '/campaigns',
      { params: filters }
    )
    return response.data.data
  },

  /**
   * Get a single campaign by ID
   */
  getCampaign: async (id: string): Promise<CampaignWithMetrics> => {
    const response = await apiClient.get<ApiResponse<CampaignWithMetrics>>(`/campaigns/${id}`)
    return response.data.data
  },

  /**
   * Create a new campaign
   */
  createCampaign: async (data: CreateCampaignRequest): Promise<Campaign> => {
    const response = await apiClient.post<ApiResponse<Campaign>>('/campaigns', data)
    return response.data.data
  },

  /**
   * Update an existing campaign
   */
  updateCampaign: async (id: string, data: UpdateCampaignRequest): Promise<Campaign> => {
    const response = await apiClient.patch<ApiResponse<Campaign>>(`/campaigns/${id}`, data)
    return response.data.data
  },

  /**
   * Delete a campaign
   */
  deleteCampaign: async (id: string): Promise<void> => {
    await apiClient.delete(`/campaigns/${id}`)
  },

  /**
   * Get campaign metrics
   */
  getCampaignMetrics: async (
    id: string,
    startDate: string,
    endDate: string,
    granularity: 'day' | 'week' | 'month' = 'day'
  ): Promise<CampaignMetrics[]> => {
    const response = await apiClient.get<ApiResponse<CampaignMetrics[]>>(
      `/campaigns/${id}/metrics`,
      { params: { start_date: startDate, end_date: endDate, granularity } }
    )
    return response.data.data
  },

  /**
   * Sync campaign from platform
   */
  syncCampaign: async (id: string): Promise<Campaign> => {
    const response = await apiClient.post<ApiResponse<Campaign>>(`/campaigns/${id}/sync`)
    return response.data.data
  },

  /**
   * Sync all campaigns from all platforms
   */
  syncAllCampaigns: async (): Promise<{ task_id: string; message: string }> => {
    const response = await apiClient.post<ApiResponse<{ task_id: string; message: string }>>('/campaigns/sync-all')
    return response.data.data
  },

  /**
   * Bulk update campaign status
   */
  bulkUpdateStatus: async (
    ids: string[],
    status: CampaignStatus
  ): Promise<Campaign[]> => {
    const response = await apiClient.post<ApiResponse<Campaign[]>>(
      '/campaigns/bulk/status',
      { ids, status }
    )
    return response.data.data
  },

  /**
   * Pause a campaign
   */
  pauseCampaign: async (id: string): Promise<Campaign> => {
    const response = await apiClient.post<ApiResponse<Campaign>>(`/campaigns/${id}/pause`)
    return response.data.data
  },

  /**
   * Activate a campaign
   */
  activateCampaign: async (id: string): Promise<Campaign> => {
    const response = await apiClient.post<ApiResponse<Campaign>>(`/campaigns/${id}/activate`)
    return response.data.data
  },
}

// React Query Hooks

export function useCampaigns(filters: CampaignFilters = {}) {
  return useQuery({
    queryKey: ['campaigns', filters],
    queryFn: () => campaignsApi.getCampaigns(filters),
    staleTime: 30 * 1000,
  })
}

export function useCampaign(id: string) {
  return useQuery({
    queryKey: ['campaigns', id],
    queryFn: () => campaignsApi.getCampaign(id),
    enabled: !!id,
  })
}

export function useCreateCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: campaignsApi.createCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    },
    onError: (error: Error) => {
      console.error('Operation failed:', error)
    },
  })
}

export function useUpdateCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateCampaignRequest }) =>
      campaignsApi.updateCampaign(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      queryClient.invalidateQueries({ queryKey: ['campaigns', variables.id] })
    },
    onError: (error: Error) => {
      console.error('Operation failed:', error)
    },
  })
}

export function useDeleteCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: campaignsApi.deleteCampaign,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    },
    onError: (error: Error) => {
      console.error('Operation failed:', error)
    },
  })
}

export function useCampaignMetrics(
  id: string,
  startDate: string,
  endDate: string,
  granularity: 'day' | 'week' | 'month' = 'day'
) {
  return useQuery({
    queryKey: ['campaigns', id, 'metrics', startDate, endDate, granularity],
    queryFn: () => campaignsApi.getCampaignMetrics(id, startDate, endDate, granularity),
    enabled: !!id && !!startDate && !!endDate,
  })
}

export function useSyncCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: campaignsApi.syncCampaign,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns', id] })
    },
  })
}

export function useSyncAllCampaigns() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: campaignsApi.syncAllCampaigns,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    },
  })
}

export function useBulkUpdateCampaignStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ ids, status }: { ids: string[]; status: CampaignStatus }) =>
      campaignsApi.bulkUpdateStatus(ids, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    },
  })
}

export function usePauseCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: campaignsApi.pauseCampaign,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      queryClient.invalidateQueries({ queryKey: ['campaigns', id] })
    },
    onError: (error: Error) => {
      console.error('Operation failed:', error)
    },
  })
}

export function useActivateCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: campaignsApi.activateCampaign,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      queryClient.invalidateQueries({ queryKey: ['campaigns', id] })
    },
    onError: (error: Error) => {
      console.error('Operation failed:', error)
    },
  })
}
