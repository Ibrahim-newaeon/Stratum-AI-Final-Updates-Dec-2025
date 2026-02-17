/**
 * Stratum AI - A/B Testing API
 *
 * Handles A/B test creation, management, and statistical analysis.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// =============================================================================
// Types
// =============================================================================

export type TestStatus = 'draft' | 'running' | 'paused' | 'completed' | 'stopped'
export type TestType = 'campaign' | 'creative' | 'audience' | 'landing_page' | 'bid_strategy'
export type SignificanceLevel = 0.9 | 0.95 | 0.99

export interface ABTest {
  id: string
  tenantId: number
  name: string
  description?: string
  testType: TestType
  status: TestStatus
  hypothesis: string
  primaryMetric: string
  secondaryMetrics: string[]
  targetSampleSize: number
  currentSampleSize: number
  confidenceLevel: SignificanceLevel
  minimumDetectableEffect: number
  variants: Variant[]
  startDate?: string
  endDate?: string
  createdAt: string
  updatedAt: string
  createdBy: string
}

export interface Variant {
  id: string
  name: string
  description?: string
  isControl: boolean
  trafficAllocation: number
  entityId?: string
  entityType?: string
  sampleSize: number
  conversions: number
  revenue: number
  metrics: Record<string, number>
}

export interface TestResults {
  testId: string
  status: TestStatus
  winner?: string
  isSignificant: boolean
  pValue: number
  confidenceLevel: number
  uplift: number
  upliftRange: { lower: number; upper: number }
  powerAchieved: number
  variants: VariantResults[]
  recommendation: string
  analysisDate: string
}

export interface VariantResults {
  variantId: string
  name: string
  isControl: boolean
  sampleSize: number
  conversions: number
  conversionRate: number
  revenue: number
  revenuePerUser: number
  confidenceInterval: { lower: number; upper: number }
  relativeUplift?: number
  isWinner: boolean
}

export interface PowerAnalysis {
  requiredSampleSize: number
  estimatedDuration: number
  currentPower: number
  minimumDetectableEffect: number
  baselineConversionRate: number
  recommendations: string[]
}

export interface TestMetrics {
  testId: string
  date: string
  variantId: string
  impressions: number
  clicks: number
  conversions: number
  revenue: number
  ctr: number
  conversionRate: number
  roas: number
}

export interface CreateTestParams {
  name: string
  description?: string
  testType: TestType
  hypothesis: string
  primaryMetric: string
  secondaryMetrics?: string[]
  confidenceLevel?: SignificanceLevel
  minimumDetectableEffect?: number
  variants: {
    name: string
    description?: string
    isControl: boolean
    trafficAllocation: number
    entityId?: string
    entityType?: string
  }[]
  startDate?: string
  endDate?: string
}

// =============================================================================
// API Functions
// =============================================================================

export const abTestingApi = {
  // Test CRUD
  getTests: async (params?: { status?: TestStatus; testType?: TestType }) => {
    const response = await apiClient.get<ApiResponse<ABTest[]>>('/ab-testing/tests', { params })
    return response.data.data
  },

  getTest: async (testId: string) => {
    const response = await apiClient.get<ApiResponse<ABTest>>(`/ab-testing/tests/${testId}`)
    return response.data.data
  },

  createTest: async (params: CreateTestParams) => {
    const response = await apiClient.post<ApiResponse<ABTest>>('/ab-testing/tests', params)
    return response.data.data
  },

  updateTest: async (testId: string, params: Partial<CreateTestParams>) => {
    const response = await apiClient.put<ApiResponse<ABTest>>(`/ab-testing/tests/${testId}`, params)
    return response.data.data
  },

  deleteTest: async (testId: string) => {
    const response = await apiClient.delete<ApiResponse<void>>(`/ab-testing/tests/${testId}`)
    return response.data
  },

  // Test Actions
  startTest: async (testId: string) => {
    const response = await apiClient.post<ApiResponse<ABTest>>(`/ab-testing/tests/${testId}/start`)
    return response.data.data
  },

  pauseTest: async (testId: string) => {
    const response = await apiClient.post<ApiResponse<ABTest>>(`/ab-testing/tests/${testId}/pause`)
    return response.data.data
  },

  stopTest: async (testId: string, winnerId?: string) => {
    const response = await apiClient.post<ApiResponse<ABTest>>(`/ab-testing/tests/${testId}/stop`, { winnerId })
    return response.data.data
  },

  // Results & Analysis
  getResults: async (testId: string) => {
    const response = await apiClient.get<ApiResponse<TestResults>>(`/ab-testing/tests/${testId}/results`)
    return response.data.data
  },

  getMetrics: async (testId: string, params?: { startDate?: string; endDate?: string }) => {
    const response = await apiClient.get<ApiResponse<TestMetrics[]>>(`/ab-testing/tests/${testId}/metrics`, { params })
    return response.data.data
  },

  getPowerAnalysis: async (params: {
    baselineConversionRate: number
    minimumDetectableEffect: number
    confidenceLevel: SignificanceLevel
    dailyTraffic: number
  }) => {
    const response = await apiClient.post<ApiResponse<PowerAnalysis>>('/ab-testing/power-analysis', params)
    return response.data.data
  },

  // LTV Predictions for tests
  getLTVImpact: async (testId: string) => {
    const response = await apiClient.get<ApiResponse<{
      controlLTV: number
      variantLTV: Record<string, number>
      projectedRevenueLift: number
      confidenceLevel: number
    }>>(`/ab-testing/tests/${testId}/ltv-impact`)
    return response.data.data
  },
}

// =============================================================================
// React Query Hooks
// =============================================================================

export function useABTests(params?: { status?: TestStatus; testType?: TestType }) {
  return useQuery({
    queryKey: ['ab-testing', 'tests', params],
    queryFn: () => abTestingApi.getTests(params),
  })
}

export function useABTest(testId: string) {
  return useQuery({
    queryKey: ['ab-testing', 'tests', testId],
    queryFn: () => abTestingApi.getTest(testId),
    enabled: !!testId,
  })
}

export function useCreateABTest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: abTestingApi.createTest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ab-testing', 'tests'] })
    },
  })
}

export function useUpdateABTest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ testId, params }: { testId: string; params: Partial<CreateTestParams> }) =>
      abTestingApi.updateTest(testId, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ab-testing', 'tests'] })
    },
  })
}

export function useDeleteABTest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: abTestingApi.deleteTest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ab-testing', 'tests'] })
    },
  })
}

export function useStartABTest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: abTestingApi.startTest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ab-testing', 'tests'] })
    },
  })
}

export function usePauseABTest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: abTestingApi.pauseTest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ab-testing', 'tests'] })
    },
  })
}

export function useStopABTest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ testId, winnerId }: { testId: string; winnerId?: string }) =>
      abTestingApi.stopTest(testId, winnerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ab-testing', 'tests'] })
    },
  })
}

export function useABTestResults(testId: string) {
  return useQuery({
    queryKey: ['ab-testing', 'tests', testId, 'results'],
    queryFn: () => abTestingApi.getResults(testId),
    enabled: !!testId,
    refetchInterval: 60000, // Refresh every minute for running tests
  })
}

export function useABTestMetrics(testId: string, params?: { startDate?: string; endDate?: string }) {
  return useQuery({
    queryKey: ['ab-testing', 'tests', testId, 'metrics', params],
    queryFn: () => abTestingApi.getMetrics(testId, params),
    enabled: !!testId,
  })
}

export function usePowerAnalysis() {
  return useMutation({
    mutationFn: abTestingApi.getPowerAnalysis,
  })
}

export function useLTVImpact(testId: string) {
  return useQuery({
    queryKey: ['ab-testing', 'tests', testId, 'ltv-impact'],
    queryFn: () => abTestingApi.getLTVImpact(testId),
    enabled: !!testId,
  })
}
