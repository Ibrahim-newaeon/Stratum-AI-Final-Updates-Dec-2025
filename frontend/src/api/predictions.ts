/**
 * Stratum AI - Predictions & Optimization API
 *
 * ML-powered predictions and budget optimization
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export type PredictionType = 'roas' | 'conversions' | 'spend' | 'cpa'
export type AlertSeverity = 'info' | 'warning' | 'critical'

export interface Prediction {
  id: string
  type: PredictionType
  campaignId: string
  campaignName: string
  platform: string
  currentValue: number
  predictedValue: number
  confidence: number
  timeframe: string
  trend: 'up' | 'down' | 'flat'
  factors: {
    name: string
    impact: number
    direction: 'positive' | 'negative'
  }[]
  createdAt: string
}

export interface PredictionAlert {
  id: string
  predictionId: string
  severity: AlertSeverity
  title: string
  message: string
  campaignId: string
  platform: string
  suggestedAction: string | null
  isRead: boolean
  createdAt: string
}

export interface BudgetOptimization {
  id: string
  totalBudget: number
  optimizedAllocation: {
    campaignId: string
    campaignName: string
    platform: string
    currentBudget: number
    recommendedBudget: number
    expectedRoasChange: number
    confidence: number
  }[]
  estimatedImpact: {
    currentRoas: number
    projectedRoas: number
    revenueChange: number
  }
  createdAt: string
}

export interface Scenario {
  id: string
  name: string
  description: string | null
  budgetChange: number
  parameters: Record<string, unknown>
  results: {
    metric: string
    currentValue: number
    projectedValue: number
    change: number
    confidence: number
  }[]
  createdAt: string
}

export interface CreateScenarioRequest {
  name: string
  description?: string
  budgetChange: number
  parameters?: Record<string, unknown>
}

// API Functions
export const predictionsApi = {
  /**
   * Get live predictions
   */
  getLivePredictions: async (): Promise<Prediction[]> => {
    const response = await apiClient.get<ApiResponse<Prediction[]>>('/predictions/live')
    return response.data.data
  },

  /**
   * Get predictions for a campaign
   */
  getCampaignPredictions: async (campaignId: string): Promise<Prediction[]> => {
    const response = await apiClient.get<ApiResponse<Prediction[]>>(
      `/predictions/campaigns/${campaignId}`
    )
    return response.data.data
  },

  /**
   * Get prediction alerts
   */
  getPredictionAlerts: async (unreadOnly: boolean = false): Promise<PredictionAlert[]> => {
    const response = await apiClient.get<ApiResponse<PredictionAlert[]>>(
      '/predictions/alerts',
      { params: { unread_only: unreadOnly } }
    )
    return response.data.data
  },

  /**
   * Mark alert as read
   */
  markAlertRead: async (id: string): Promise<void> => {
    await apiClient.post(`/predictions/alerts/${id}/read`)
  },

  /**
   * Refresh predictions
   */
  refreshPredictions: async (): Promise<{ success: boolean }> => {
    const response = await apiClient.post<ApiResponse<{ success: boolean }>>(
      '/predictions/refresh'
    )
    return response.data.data
  },

  /**
   * Get budget optimization recommendations
   */
  getBudgetOptimization: async (totalBudget?: number): Promise<BudgetOptimization> => {
    const params = totalBudget ? { total_budget: totalBudget } : {}
    const response = await apiClient.get<ApiResponse<BudgetOptimization>>(
      '/predictions/budget-optimization',
      { params }
    )
    return response.data.data
  },

  /**
   * Apply budget optimization
   */
  applyBudgetOptimization: async (optimizationId: string): Promise<{ success: boolean }> => {
    const response = await apiClient.post<ApiResponse<{ success: boolean }>>(
      `/predictions/budget-optimization/${optimizationId}/apply`
    )
    return response.data.data
  },

  /**
   * Get all scenarios
   */
  getScenarios: async (): Promise<Scenario[]> => {
    const response = await apiClient.get<ApiResponse<Scenario[]>>('/predictions/scenarios')
    return response.data.data
  },

  /**
   * Create a scenario
   */
  createScenario: async (data: CreateScenarioRequest): Promise<Scenario> => {
    const response = await apiClient.post<ApiResponse<Scenario>>(
      '/predictions/scenarios',
      data
    )
    return response.data.data
  },

  /**
   * Get scenario by ID
   */
  getScenario: async (id: string): Promise<Scenario> => {
    const response = await apiClient.get<ApiResponse<Scenario>>(
      `/predictions/scenarios/${id}`
    )
    return response.data.data
  },

  /**
   * Delete a scenario
   */
  deleteScenario: async (id: string): Promise<void> => {
    await apiClient.delete(`/predictions/scenarios/${id}`)
  },
}

// React Query Hooks

export function useLivePredictions() {
  return useQuery({
    queryKey: ['predictions', 'live'],
    queryFn: predictionsApi.getLivePredictions,
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  })
}

export function useCampaignPredictions(campaignId: string) {
  return useQuery({
    queryKey: ['predictions', 'campaigns', campaignId],
    queryFn: () => predictionsApi.getCampaignPredictions(campaignId),
    enabled: !!campaignId,
  })
}

export function usePredictionAlerts(unreadOnly: boolean = false) {
  return useQuery({
    queryKey: ['predictions', 'alerts', unreadOnly],
    queryFn: () => predictionsApi.getPredictionAlerts(unreadOnly),
    staleTime: 30 * 1000,
  })
}

export function useMarkAlertRead() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: predictionsApi.markAlertRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions', 'alerts'] })
    },
  })
}

export function useRefreshPredictions() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: predictionsApi.refreshPredictions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions'] })
    },
  })
}

export function useBudgetOptimization(totalBudget?: number) {
  return useQuery({
    queryKey: ['predictions', 'budget-optimization', totalBudget],
    queryFn: () => predictionsApi.getBudgetOptimization(totalBudget),
    staleTime: 5 * 60 * 1000,
  })
}

export function useApplyBudgetOptimization() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: predictionsApi.applyBudgetOptimization,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions', 'budget-optimization'] })
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    },
  })
}

export function useScenarios() {
  return useQuery({
    queryKey: ['predictions', 'scenarios'],
    queryFn: predictionsApi.getScenarios,
  })
}

export function useScenario(id: string) {
  return useQuery({
    queryKey: ['predictions', 'scenarios', id],
    queryFn: () => predictionsApi.getScenario(id),
    enabled: !!id,
  })
}

export function useCreateScenario() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: predictionsApi.createScenario,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions', 'scenarios'] })
    },
  })
}

export function useDeleteScenario() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: predictionsApi.deleteScenario,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions', 'scenarios'] })
    },
  })
}
