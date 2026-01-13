/**
 * Stratum AI - Attribution API
 *
 * Handles multi-touch attribution and data-driven attribution models.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// =============================================================================
// Types
// =============================================================================

export type AttributionModel = 'first_touch' | 'last_touch' | 'linear' | 'position_based' | 'time_decay' | 'w_shaped' | 'markov' | 'shapley'
export type DataDrivenModelType = 'markov_chain' | 'shapley_value'
export type ModelStatus = 'training' | 'active' | 'archived' | 'failed'

// Multi-Touch Attribution Types
export interface AttributionResult {
  dealId: string
  dealName: string
  totalRevenue: number
  model: AttributionModel
  touchpoints: AttributedTouchpoint[]
  conversionDate: string
}

export interface AttributedTouchpoint {
  touchpointId: string
  channel: string
  source: string
  medium?: string
  campaign?: string
  platform?: string
  timestamp: string
  position: number
  weight: number
  attributedRevenue: number
}

export interface AttributionSummary {
  channel: string
  platform?: string
  campaign?: string
  touchpoints: number
  conversions: number
  attributedRevenue: number
  avgWeight: number
  firstTouchCount: number
  lastTouchCount: number
  assistedConversions: number
}

export interface DailyAttributedRevenue {
  date: string
  model: AttributionModel
  channel: string
  platform?: string
  attributedRevenue: number
  conversions: number
  touchpoints: number
}

export interface ConversionPath {
  path: string
  conversions: number
  revenue: number
  avgTouchpoints: number
  avgDaysToConvert: number
  conversionRate: number
}

export interface ChannelInteraction {
  fromChannel: string
  toChannel: string
  transitions: number
  conversionRate: number
}

export interface JourneyVisualization {
  contact: {
    id: string
    email?: string
    name?: string
  }
  touchpoints: {
    id: string
    channel: string
    source: string
    timestamp: string
    isConverting: boolean
  }[]
  deals: {
    id: string
    name: string
    amount: number
    stage: string
    closeDate?: string
  }[]
  timeline: {
    date: string
    events: Array<{
      type: 'touchpoint' | 'deal_created' | 'deal_won'
      data: any
    }>
  }[]
}

export interface AttributionComparison {
  models: AttributionModel[]
  channels: Array<{
    channel: string
    byModel: Record<AttributionModel, {
      revenue: number
      conversions: number
      share: number
    }>
  }>
  totalRevenue: number
  insight: string
}

// Data-Driven Attribution Types
export interface TrainedAttributionModel {
  id: string
  tenantId: number
  modelName: string
  modelType: DataDrivenModelType
  channelType: string
  status: ModelStatus
  isActive: boolean
  trainingStart: string
  trainingEnd: string
  journeyCount: number
  convertingJourneys: number
  uniqueChannels: number
  attributionWeights: Record<string, number>
  removalEffects?: Record<string, number>
  shapleyValues?: Record<string, number>
  baselineConversionRate?: number
  validationAccuracy?: number
  createdAt: string
  updatedAt: string
}

export interface ModelTrainingRun {
  id: string
  tenantId: number
  modelId?: string
  modelType: DataDrivenModelType
  channelType: string
  status: ModelStatus
  trainingStart: string
  trainingEnd: string
  startedAt: string
  completedAt?: string
  durationSeconds?: number
  journeyCount?: number
  convertingJourneys?: number
  uniqueChannels?: number
  errorMessage?: string
}

export interface MarkovModelResult {
  modelId: string
  transitionMatrix: Record<string, Record<string, number>>
  removalEffects: Record<string, number>
  attributionWeights: Record<string, number>
  baselineConversionRate: number
  channelImportance: Array<{
    channel: string
    removalEffect: number
    attributionWeight: number
  }>
}

export interface ShapleyModelResult {
  modelId: string
  shapleyValues: Record<string, number>
  attributionWeights: Record<string, number>
  channelContributions: Array<{
    channel: string
    shapleyValue: number
    normalizedWeight: number
  }>
}

export interface ModelComparison {
  ruleBasedModels: Record<AttributionModel, Record<string, number>>
  dataDrivenModels: Record<DataDrivenModelType, Record<string, number>>
  recommendation: {
    bestModel: string
    reason: string
    confidenceScore: number
  }
}

// =============================================================================
// API Functions
// =============================================================================

export const attributionApi = {
  // Multi-Touch Attribution
  attributeDeal: async (dealId: string, model: AttributionModel) => {
    const response = await apiClient.get<ApiResponse<AttributionResult>>(`/attribution/deals/${dealId}`, {
      params: { model },
    })
    return response.data.data
  },

  batchAttributeDeals: async (params: { startDate: string; endDate: string; model: AttributionModel }) => {
    const response = await apiClient.post<ApiResponse<{ processed: number; results: AttributionResult[] }>>(
      '/attribution/batch',
      params
    )
    return response.data.data
  },

  getAttributionSummary: async (params: {
    startDate: string
    endDate: string
    model: AttributionModel
    groupBy?: 'channel' | 'platform' | 'campaign'
  }) => {
    const response = await apiClient.get<ApiResponse<AttributionSummary[]>>('/attribution/summary', { params })
    return response.data.data
  },

  getDailyAttributedRevenue: async (params: {
    startDate: string
    endDate: string
    model: AttributionModel
    channel?: string
  }) => {
    const response = await apiClient.get<ApiResponse<DailyAttributedRevenue[]>>('/attribution/daily', { params })
    return response.data.data
  },

  compareModels: async (params: { startDate: string; endDate: string; models: AttributionModel[] }) => {
    const response = await apiClient.get<ApiResponse<AttributionComparison>>('/attribution/compare', { params })
    return response.data.data
  },

  // Journey Analysis
  getContactJourney: async (contactId: string) => {
    const response = await apiClient.get<ApiResponse<JourneyVisualization>>(`/attribution/journeys/${contactId}`)
    return response.data.data
  },

  getTopConversionPaths: async (params: { startDate: string; endDate: string; limit?: number; minConversions?: number }) => {
    const response = await apiClient.get<ApiResponse<ConversionPath[]>>('/attribution/journeys/top-paths', { params })
    return response.data.data
  },

  getChannelTransitions: async (params: { startDate: string; endDate: string }) => {
    const response = await apiClient.get<ApiResponse<{
      transitions: ChannelInteraction[]
      sankeyData: { nodes: any[]; links: any[] }
    }>>('/attribution/journeys/transitions', { params })
    return response.data.data
  },

  getAssistedConversions: async (params: { startDate: string; endDate: string; groupBy?: 'channel' | 'platform' }) => {
    const response = await apiClient.get<ApiResponse<Array<{
      channel: string
      directConversions: number
      assistedConversions: number
      assistRatio: number
    }>>>('/attribution/journeys/assisted', { params })
    return response.data.data
  },

  getTimeLagReport: async (params: { startDate: string; endDate: string }) => {
    const response = await apiClient.get<ApiResponse<{
      avgDaysToConvert: number
      medianDaysToConvert: number
      distribution: Array<{ days: string; conversions: number; revenue: number }>
    }>>('/attribution/journeys/time-lag', { params })
    return response.data.data
  },

  // Data-Driven Attribution
  trainMarkovModel: async (params: {
    startDate: string
    endDate: string
    channelType?: string
    includeNonConverting?: boolean
    minJourneys?: number
  }) => {
    const response = await apiClient.post<ApiResponse<TrainedAttributionModel>>('/attribution/data-driven/markov/train', params)
    return response.data.data
  },

  trainShapleyModel: async (params: {
    startDate: string
    endDate: string
    channelType?: string
    maxChannels?: number
    sampleSize?: number
  }) => {
    const response = await apiClient.post<ApiResponse<TrainedAttributionModel>>('/attribution/data-driven/shapley/train', params)
    return response.data.data
  },

  getTrainedModels: async (params?: { modelType?: DataDrivenModelType; status?: ModelStatus; isActive?: boolean }) => {
    const response = await apiClient.get<ApiResponse<TrainedAttributionModel[]>>('/attribution/data-driven/models', { params })
    return response.data.data
  },

  getTrainedModel: async (modelId: string) => {
    const response = await apiClient.get<ApiResponse<TrainedAttributionModel>>(`/attribution/data-driven/models/${modelId}`)
    return response.data.data
  },

  activateModel: async (modelId: string) => {
    const response = await apiClient.post<ApiResponse<TrainedAttributionModel>>(`/attribution/data-driven/models/${modelId}/activate`)
    return response.data.data
  },

  archiveModel: async (modelId: string) => {
    const response = await apiClient.post<ApiResponse<TrainedAttributionModel>>(`/attribution/data-driven/models/${modelId}/archive`)
    return response.data.data
  },

  getTrainingRuns: async (params?: { modelType?: DataDrivenModelType; status?: ModelStatus }) => {
    const response = await apiClient.get<ApiResponse<ModelTrainingRun[]>>('/attribution/data-driven/training-runs', { params })
    return response.data.data
  },

  getMarkovResults: async (modelId: string) => {
    const response = await apiClient.get<ApiResponse<MarkovModelResult>>(`/attribution/data-driven/markov/${modelId}/results`)
    return response.data.data
  },

  getShapleyResults: async (modelId: string) => {
    const response = await apiClient.get<ApiResponse<ShapleyModelResult>>(`/attribution/data-driven/shapley/${modelId}/results`)
    return response.data.data
  },

  getModelRecommendation: async (params: { startDate: string; endDate: string }) => {
    const response = await apiClient.get<ApiResponse<{
      recommendedModel: string
      confidence: number
      reason: string
      comparison: ModelComparison
    }>>('/attribution/data-driven/recommend', { params })
    return response.data.data
  },

  attributeWithDataDriven: async (dealId: string, modelId: string) => {
    const response = await apiClient.get<ApiResponse<AttributionResult>>(`/attribution/data-driven/attribute/${dealId}`, {
      params: { model_id: modelId },
    })
    return response.data.data
  },

  compareWithRuleBased: async (modelId: string, params: { startDate: string; endDate: string }) => {
    const response = await apiClient.get<ApiResponse<ModelComparison>>(`/attribution/data-driven/models/${modelId}/compare`, { params })
    return response.data.data
  },
}

// =============================================================================
// React Query Hooks
// =============================================================================

// Multi-Touch Attribution
export function useAttributeDeal(dealId: string, model: AttributionModel) {
  return useQuery({
    queryKey: ['attribution', 'deals', dealId, model],
    queryFn: () => attributionApi.attributeDeal(dealId, model),
    enabled: !!dealId,
  })
}

export function useBatchAttributeDeals() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: attributionApi.batchAttributeDeals,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attribution'] })
    },
  })
}

export function useAttributionSummary(params: {
  startDate: string
  endDate: string
  model: AttributionModel
  groupBy?: 'channel' | 'platform' | 'campaign'
}) {
  return useQuery({
    queryKey: ['attribution', 'summary', params],
    queryFn: () => attributionApi.getAttributionSummary(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

export function useDailyAttributedRevenue(params: {
  startDate: string
  endDate: string
  model: AttributionModel
  channel?: string
}) {
  return useQuery({
    queryKey: ['attribution', 'daily', params],
    queryFn: () => attributionApi.getDailyAttributedRevenue(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

export function useCompareModels(params: { startDate: string; endDate: string; models: AttributionModel[] }) {
  return useQuery({
    queryKey: ['attribution', 'compare', params],
    queryFn: () => attributionApi.compareModels(params),
    enabled: !!params.startDate && !!params.endDate && params.models.length > 0,
  })
}

// Journey Analysis
export function useContactJourney(contactId: string) {
  return useQuery({
    queryKey: ['attribution', 'journeys', contactId],
    queryFn: () => attributionApi.getContactJourney(contactId),
    enabled: !!contactId,
  })
}

export function useTopConversionPaths(params: { startDate: string; endDate: string; limit?: number; minConversions?: number }) {
  return useQuery({
    queryKey: ['attribution', 'journeys', 'top-paths', params],
    queryFn: () => attributionApi.getTopConversionPaths(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

export function useChannelTransitions(params: { startDate: string; endDate: string }) {
  return useQuery({
    queryKey: ['attribution', 'journeys', 'transitions', params],
    queryFn: () => attributionApi.getChannelTransitions(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

export function useAssistedConversions(params: { startDate: string; endDate: string; groupBy?: 'channel' | 'platform' }) {
  return useQuery({
    queryKey: ['attribution', 'journeys', 'assisted', params],
    queryFn: () => attributionApi.getAssistedConversions(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

export function useTimeLagReport(params: { startDate: string; endDate: string }) {
  return useQuery({
    queryKey: ['attribution', 'journeys', 'time-lag', params],
    queryFn: () => attributionApi.getTimeLagReport(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

// Data-Driven Attribution
export function useTrainMarkovModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: attributionApi.trainMarkovModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attribution', 'data-driven'] })
    },
  })
}

export function useTrainShapleyModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: attributionApi.trainShapleyModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attribution', 'data-driven'] })
    },
  })
}

export function useTrainedModels(params?: { modelType?: DataDrivenModelType; status?: ModelStatus; isActive?: boolean }) {
  return useQuery({
    queryKey: ['attribution', 'data-driven', 'models', params],
    queryFn: () => attributionApi.getTrainedModels(params),
  })
}

export function useTrainedModel(modelId: string) {
  return useQuery({
    queryKey: ['attribution', 'data-driven', 'models', modelId],
    queryFn: () => attributionApi.getTrainedModel(modelId),
    enabled: !!modelId,
  })
}

export function useActivateModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: attributionApi.activateModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attribution', 'data-driven', 'models'] })
    },
  })
}

export function useArchiveModel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: attributionApi.archiveModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['attribution', 'data-driven', 'models'] })
    },
  })
}

export function useTrainingRuns(params?: { modelType?: DataDrivenModelType; status?: ModelStatus }) {
  return useQuery({
    queryKey: ['attribution', 'data-driven', 'training-runs', params],
    queryFn: () => attributionApi.getTrainingRuns(params),
  })
}

export function useMarkovResults(modelId: string) {
  return useQuery({
    queryKey: ['attribution', 'data-driven', 'markov', modelId, 'results'],
    queryFn: () => attributionApi.getMarkovResults(modelId),
    enabled: !!modelId,
  })
}

export function useShapleyResults(modelId: string) {
  return useQuery({
    queryKey: ['attribution', 'data-driven', 'shapley', modelId, 'results'],
    queryFn: () => attributionApi.getShapleyResults(modelId),
    enabled: !!modelId,
  })
}

export function useModelRecommendation(params: { startDate: string; endDate: string }) {
  return useQuery({
    queryKey: ['attribution', 'data-driven', 'recommend', params],
    queryFn: () => attributionApi.getModelRecommendation(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

export function useAttributeWithDataDriven(dealId: string, modelId: string) {
  return useQuery({
    queryKey: ['attribution', 'data-driven', 'attribute', dealId, modelId],
    queryFn: () => attributionApi.attributeWithDataDriven(dealId, modelId),
    enabled: !!dealId && !!modelId,
  })
}

export function useCompareWithRuleBased(modelId: string, params: { startDate: string; endDate: string }) {
  return useQuery({
    queryKey: ['attribution', 'data-driven', 'models', modelId, 'compare', params],
    queryFn: () => attributionApi.compareWithRuleBased(modelId, params),
    enabled: !!modelId && !!params.startDate && !!params.endDate,
  })
}
