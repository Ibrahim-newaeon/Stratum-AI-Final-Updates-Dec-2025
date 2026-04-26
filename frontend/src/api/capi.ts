/**
 * Stratum AI - CAPI (Conversion API) Client
 *
 * Server-side event streaming and data quality.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface ConversionEvent {
  event_name: string
  user_data: Record<string, unknown>
  parameters?: Record<string, unknown>
  event_time?: number
  event_source_url?: string
  event_id?: string
}

export interface StreamEventResponse {
  total_events: number
  platforms_sent: number
  failed_platforms: string[]
  data_quality_score: number
  platform_results: Record<string, unknown>
}

export interface DataQualityReport {
  overall_score: number
  estimated_roas_improvement: number
  data_gaps_summary: Record<string, unknown>
  trend: string
  generated_at: string
  platform_scores: Record<string, unknown>
  top_recommendations: string[]
}

export interface PlatformCredentials {
  platform: string
  credentials: Record<string, string>
}

export interface PlatformStatus {
  connected_platforms: string[]
  setup_status: Record<string, unknown>
}

// API Functions
export const capiApi = {
  streamEvent: async (event: ConversionEvent, platforms?: string[]): Promise<StreamEventResponse> => {
    const response = await apiClient.post<ApiResponse<StreamEventResponse>>('/capi/events/stream', event, {
      params: platforms ? { platforms: platforms.join(',') } : undefined,
    })
    return response.data.data
  },

  streamBatchEvents: async (events: ConversionEvent[], platforms?: string[]): Promise<StreamEventResponse> => {
    const response = await apiClient.post<ApiResponse<StreamEventResponse>>('/capi/events/batch', {
      events,
      platforms,
    })
    return response.data.data
  },

  getDataQualityReport: async (platforms?: string[]): Promise<DataQualityReport> => {
    const response = await apiClient.get<ApiResponse<DataQualityReport>>('/capi/quality/report', {
      params: platforms ? { platforms: platforms.join(',') } : undefined,
    })
    return response.data.data
  },

  connectPlatform: async (data: PlatformCredentials): Promise<Record<string, unknown>> => {
    const response = await apiClient.post<ApiResponse<Record<string, unknown>>>('/capi/platforms/connect', data)
    return response.data.data
  },

  disconnectPlatform: async (platform: string): Promise<Record<string, unknown>> => {
    const response = await apiClient.delete<ApiResponse<Record<string, unknown>>>(`/capi/platforms/${platform}/disconnect`)
    return response.data.data
  },

  getPlatformsStatus: async (): Promise<PlatformStatus> => {
    const response = await apiClient.get<ApiResponse<PlatformStatus>>('/capi/platforms/status')
    return response.data.data
  },
}

// React Query Hooks
export function useStreamEvent() {
  return useMutation({
    mutationFn: ({ event, platforms }: { event: ConversionEvent; platforms?: string[] }) =>
      capiApi.streamEvent(event, platforms),
  })
}

export function useStreamBatchEvents() {
  return useMutation({
    mutationFn: ({ events, platforms }: { events: ConversionEvent[]; platforms?: string[] }) =>
      capiApi.streamBatchEvents(events, platforms),
  })
}

export function useCapiDataQualityReport(platforms?: string[]) {
  return useQuery({
    queryKey: ['capi', 'data-quality', platforms],
    queryFn: () => capiApi.getDataQualityReport(platforms),
    staleTime: 60 * 1000,
  })
}

export function useConnectPlatform() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: capiApi.connectPlatform,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['capi', 'platforms'] })
    },
  })
}

export function useDisconnectPlatform() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: capiApi.disconnectPlatform,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['capi', 'platforms'] })
    },
  })
}

export function usePlatformsStatus() {
  return useQuery({
    queryKey: ['capi', 'platforms', 'status'],
    queryFn: capiApi.getPlatformsStatus,
    staleTime: 60 * 1000,
  })
}
