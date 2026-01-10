/**
 * Stratum AI - Dashboard API
 *
 * Unified dashboard endpoints for the main application dashboard.
 * Provides consolidated data for metrics, campaigns, recommendations,
 * activity feed, and signal health.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// =============================================================================
// Types
// =============================================================================

export type TimePeriod =
  | 'today'
  | 'yesterday'
  | '7d'
  | '30d'
  | '90d'
  | 'this_month'
  | 'last_month'

export type TrendDirection = 'up' | 'down' | 'stable'

export type RecommendationType = 'scale' | 'watch' | 'fix' | 'pause'

export type RecommendationStatus = 'pending' | 'approved' | 'rejected' | 'executed'

// Metric with value, change, and trend
export interface MetricValue {
  value: number
  previous_value: number | null
  change_percent: number | null
  trend: TrendDirection
  formatted: string
}

// Key performance metrics
export interface OverviewMetrics {
  spend: MetricValue
  revenue: MetricValue
  roas: MetricValue
  conversions: MetricValue
  cpa: MetricValue
  impressions: MetricValue
  clicks: MetricValue
  ctr: MetricValue
}

// Signal health status
export interface SignalHealthSummary {
  overall_score: number
  status: 'healthy' | 'degraded' | 'critical' | 'unknown'
  emq_score: number | null
  data_freshness_minutes: number | null
  api_health: boolean
  issues: string[]
  autopilot_enabled: boolean
}

// Platform performance summary
export interface PlatformSummary {
  platform: string
  status: 'connected' | 'disconnected' | 'error'
  spend: number
  revenue: number
  roas: number | null
  campaigns_count: number
  last_synced_at: string | null
}

// Campaign summary item
export interface CampaignSummaryItem {
  id: number
  name: string
  platform: string
  status: string
  spend: number
  revenue: number
  roas: number | null
  conversions: number
  trend: TrendDirection
  scaling_score: number | null
  recommendation: string | null
}

// AI recommendation
export interface RecommendationItem {
  id: string
  type: RecommendationType
  entity_type: string
  entity_id: number
  entity_name: string
  platform: string
  title: string
  description: string
  impact_estimate: string | null
  confidence: number
  status: RecommendationStatus
  created_at: string
}

// Activity/event item
export interface ActivityItem {
  id: number
  type: 'action' | 'alert' | 'auth' | 'system'
  title: string
  description: string | null
  severity: 'info' | 'warning' | 'error' | 'success' | null
  timestamp: string
  entity_type: string | null
  entity_id: string | null
}

// Quick action button
export interface QuickAction {
  id: string
  label: string
  icon: string
  action: string
  count: number | null
}

// Response types
export interface DashboardOverviewResponse {
  onboarding_complete: boolean
  has_connected_platforms: boolean
  has_campaigns: boolean
  period: string
  period_label: string
  date_range: {
    start: string
    end: string
  }
  metrics: OverviewMetrics
  signal_health: SignalHealthSummary
  platforms: PlatformSummary[]
  total_campaigns: number
  active_campaigns: number
  pending_recommendations: number
  active_alerts: number
}

export interface CampaignPerformanceResponse {
  campaigns: CampaignSummaryItem[]
  total: number
  page: number
  page_size: number
  sort_by: string
  sort_order: string
}

export interface RecommendationsResponse {
  recommendations: RecommendationItem[]
  total: number
  by_type: Record<RecommendationType, number>
}

export interface ActivityFeedResponse {
  activities: ActivityItem[]
  total: number
  has_more: boolean
}

export interface QuickActionsResponse {
  actions: QuickAction[]
}

// Request types
export interface CampaignPerformanceRequest {
  period?: TimePeriod
  platform?: string
  status?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface RecommendationsRequest {
  type?: RecommendationType
  status?: RecommendationStatus
  limit?: number
}

export interface ActivityFeedRequest {
  limit?: number
  offset?: number
}

// =============================================================================
// API Functions
// =============================================================================

export const dashboardApi = {
  /**
   * Get dashboard overview with metrics and status
   */
  getOverview: async (period: TimePeriod = '7d'): Promise<DashboardOverviewResponse> => {
    const response = await apiClient.get<ApiResponse<DashboardOverviewResponse>>(
      '/dashboard/overview',
      { params: { period } }
    )
    return response.data.data
  },

  /**
   * Get campaign performance list
   */
  getCampaigns: async (
    params: CampaignPerformanceRequest = {}
  ): Promise<CampaignPerformanceResponse> => {
    const response = await apiClient.get<ApiResponse<CampaignPerformanceResponse>>(
      '/dashboard/campaigns',
      { params }
    )
    return response.data.data
  },

  /**
   * Get AI recommendations
   */
  getRecommendations: async (
    params: RecommendationsRequest = {}
  ): Promise<RecommendationsResponse> => {
    const response = await apiClient.get<ApiResponse<RecommendationsResponse>>(
      '/dashboard/recommendations',
      { params }
    )
    return response.data.data
  },

  /**
   * Approve a recommendation
   */
  approveRecommendation: async (
    recommendationId: string
  ): Promise<{ message: string; status: string }> => {
    const response = await apiClient.post<
      ApiResponse<{ message: string; status: string }>
    >(`/dashboard/recommendations/${recommendationId}/approve`)
    return response.data.data
  },

  /**
   * Reject a recommendation
   */
  rejectRecommendation: async (
    recommendationId: string
  ): Promise<{ message: string; status: string }> => {
    const response = await apiClient.post<
      ApiResponse<{ message: string; status: string }>
    >(`/dashboard/recommendations/${recommendationId}/reject`)
    return response.data.data
  },

  /**
   * Get activity feed
   */
  getActivityFeed: async (
    params: ActivityFeedRequest = {}
  ): Promise<ActivityFeedResponse> => {
    const response = await apiClient.get<ApiResponse<ActivityFeedResponse>>(
      '/dashboard/activity',
      { params }
    )
    return response.data.data
  },

  /**
   * Get quick actions
   */
  getQuickActions: async (): Promise<QuickActionsResponse> => {
    const response = await apiClient.get<ApiResponse<QuickActionsResponse>>(
      '/dashboard/quick-actions'
    )
    return response.data.data
  },

  /**
   * Get detailed signal health
   */
  getSignalHealth: async (): Promise<SignalHealthSummary> => {
    const response = await apiClient.get<ApiResponse<SignalHealthSummary>>(
      '/dashboard/signal-health'
    )
    return response.data.data
  },
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Get dashboard overview
 */
export function useDashboardOverview(period: TimePeriod = '7d', enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'overview', period],
    queryFn: () => dashboardApi.getOverview(period),
    enabled,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Get campaign performance
 */
export function useDashboardCampaigns(
  params: CampaignPerformanceRequest = {},
  enabled = true
) {
  return useQuery({
    queryKey: ['dashboard', 'campaigns', params],
    queryFn: () => dashboardApi.getCampaigns(params),
    enabled,
    staleTime: 60 * 1000,
  })
}

/**
 * Get recommendations
 */
export function useDashboardRecommendations(
  params: RecommendationsRequest = {},
  enabled = true
) {
  return useQuery({
    queryKey: ['dashboard', 'recommendations', params],
    queryFn: () => dashboardApi.getRecommendations(params),
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
  })
}

/**
 * Approve recommendation
 */
export function useApproveRecommendation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: dashboardApi.approveRecommendation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'recommendations'] })
    },
  })
}

/**
 * Reject recommendation
 */
export function useRejectRecommendation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: dashboardApi.rejectRecommendation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'recommendations'] })
    },
  })
}

/**
 * Get activity feed
 */
export function useDashboardActivity(
  params: ActivityFeedRequest = {},
  enabled = true
) {
  return useQuery({
    queryKey: ['dashboard', 'activity', params],
    queryFn: () => dashboardApi.getActivityFeed(params),
    enabled,
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Get quick actions
 */
export function useDashboardQuickActions(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'quick-actions'],
    queryFn: dashboardApi.getQuickActions,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Get signal health
 */
export function useDashboardSignalHealth(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'signal-health'],
    queryFn: dashboardApi.getSignalHealth,
    enabled,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // 1 minute
  })
}
