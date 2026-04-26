/**
 * Stratum AI - Meta CAPI QA API
 *
 * Meta Conversion API quality assurance.
 */

import { useQuery, useMutation } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface CAPIEventData {
  event_name: string
  event_time: number
  user_data: Record<string, unknown>
  custom_data?: Record<string, unknown>
  event_source_url?: string
  action_source?: string
}

export interface CAPIEventBatch {
  events: CAPIEventData[]
  pixel_id?: string
  test_event_code?: string
}

export interface CAPIValidationResult {
  all_valid: boolean
  total_events: number
  average_quality_score: number
  validations: Array<{
    event_name: string
    valid: boolean
    quality_score: number
    issues: string[]
    suggestions: string[]
  }>
}

export interface CAPIQualityReport {
  overall_score?: number
  platform_scores: Record<string, unknown>
  top_recommendations: string[]
  estimated_roas_improvement: number
  trend: string
  message?: string
}

// API Functions
export const metaCapiApi = {
  sendEvents: async (batch: CAPIEventBatch): Promise<Record<string, unknown>> => {
    const response = await apiClient.post<ApiResponse<Record<string, unknown>>>('/meta-capi/events', batch)
    return response.data.data
  },

  validateEvents: async (events: CAPIEventData[]): Promise<CAPIValidationResult> => {
    const response = await apiClient.post<ApiResponse<CAPIValidationResult>>('/meta-capi/events/validate', {
      events,
    })
    return response.data.data
  },

  getQualityReport: async (tenantId: number): Promise<CAPIQualityReport> => {
    const response = await apiClient.get<ApiResponse<CAPIQualityReport>>(`/meta-capi/quality/${tenantId}/report`)
    return response.data.data
  },

  getHealth: async (): Promise<{ status: string; module: string }> => {
    const response = await apiClient.get<{ status: string; module: string }>('/meta-capi/health')
    return response.data
  },
}

// React Query Hooks
export function useMetaCapiSendEvents() {
  return useMutation({
    mutationFn: metaCapiApi.sendEvents,
  })
}

export function useMetaCapiValidateEvents() {
  return useMutation({
    mutationFn: metaCapiApi.validateEvents,
  })
}

export function useMetaCapiQualityReport(tenantId: number) {
  return useQuery({
    queryKey: ['meta-capi', 'quality-report', tenantId],
    queryFn: () => metaCapiApi.getQualityReport(tenantId),
    enabled: !!tenantId,
    staleTime: 60 * 1000,
  })
}

export function useMetaCapiHealth() {
  return useQuery({
    queryKey: ['meta-capi', 'health'],
    queryFn: metaCapiApi.getHealth,
    staleTime: 5 * 60 * 1000,
  })
}
