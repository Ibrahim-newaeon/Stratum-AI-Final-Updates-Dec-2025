/**
 * Stratum AI - Simulator API
 *
 * What-If simulator, ROAS forecasting, and conversion predictions.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface SimulationRequest {
  campaign_id?: number
  budget_change_percent: number
  days_ahead?: number
  include_confidence_interval?: boolean
}

export interface SimulationResponse {
  campaign_id?: number
  current_metrics: Record<string, unknown>
  predicted_metrics: Record<string, unknown>
  budget_change_percent: number
  confidence_interval?: Record<string, unknown>
  feature_importances?: Record<string, unknown>
  model_version: string
}

export interface ROASForecastRequest {
  campaign_ids?: number[]
  days_ahead?: number
  granularity?: string
}

export interface ROASForecastResponse {
  forecasts: Record<string, unknown>[]
  model_version: string
  generated_at: string
}

export interface ConversionPredictionRequest {
  campaign_id: number
  features: Record<string, unknown>
}

export interface ConversionPredictionResponse {
  campaign_id: number
  predicted_conversions: number
  predicted_conversion_rate: number
  confidence: number
  factors: Record<string, unknown>[]
}

export interface ModelStatus {
  ml_provider: string
  models: Record<string, unknown>
  is_healthy: boolean
}

// API Functions
export const simulatorApi = {
  simulateScenario: async (data: SimulationRequest): Promise<SimulationResponse> => {
    const response = await apiClient.post<ApiResponse<SimulationResponse>>('/simulator', data)
    return response.data.data
  },

  forecastRoas: async (data: ROASForecastRequest): Promise<ROASForecastResponse> => {
    const response = await apiClient.post<ApiResponse<ROASForecastResponse>>('/simulator/forecast/roas', data)
    return response.data.data
  },

  predictConversions: async (data: ConversionPredictionRequest): Promise<ConversionPredictionResponse> => {
    const response = await apiClient.post<ApiResponse<ConversionPredictionResponse>>(
      '/simulator/predict/conversions',
      data
    )
    return response.data.data
  },

  getModelStatus: async (): Promise<ModelStatus> => {
    const response = await apiClient.get<ApiResponse<ModelStatus>>('/simulator/models/status')
    return response.data.data
  },
}

// React Query Hooks
export function useSimulateScenario() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: simulatorApi.simulateScenario,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['simulator'] })
    },
  })
}

export function useForecastRoas() {
  return useMutation({
    mutationFn: simulatorApi.forecastRoas,
  })
}

export function usePredictConversions() {
  return useMutation({
    mutationFn: simulatorApi.predictConversions,
  })
}

export function useModelStatus() {
  return useQuery({
    queryKey: ['simulator', 'models', 'status'],
    queryFn: simulatorApi.getModelStatus,
    staleTime: 60 * 1000,
  })
}
