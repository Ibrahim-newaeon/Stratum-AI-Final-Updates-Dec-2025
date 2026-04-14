/**
 * Stratum AI - Dashboard API
 *
 * Unified dashboard endpoints for the main application dashboard.
 * Provides consolidated data for metrics, campaigns, recommendations,
 * activity feed, and signal health.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse } from './client';

// =============================================================================
// Types
// =============================================================================

export type TimePeriod = 'today' | 'yesterday' | '7d' | '30d' | '90d' | 'this_month' | 'last_month' | 'custom';

export type TrendDirection = 'up' | 'down' | 'stable';

export type RecommendationType = 'scale' | 'watch' | 'fix' | 'pause';

export type RecommendationStatus = 'pending' | 'approved' | 'rejected' | 'executed';

// Metric with value, change, and trend
export interface MetricValue {
  value: number;
  previous_value: number | null;
  change_percent: number | null;
  trend: TrendDirection;
  formatted: string;
}

// Key performance metrics
export interface OverviewMetrics {
  spend: MetricValue;
  revenue: MetricValue;
  roas: MetricValue;
  conversions: MetricValue;
  cpa: MetricValue;
  impressions: MetricValue;
  clicks: MetricValue;
  ctr: MetricValue;
}

// Signal health status
export interface SignalHealthSummary {
  overall_score: number;
  status: 'healthy' | 'degraded' | 'critical' | 'unknown';
  emq_score: number | null;
  data_freshness_minutes: number | null;
  api_health: boolean;
  issues: string[];
  autopilot_enabled: boolean;
}

// Platform performance summary
export interface PlatformSummary {
  platform: string;
  status: 'connected' | 'disconnected' | 'error';
  spend: number;
  revenue: number;
  roas: number | null;
  campaigns_count: number;
  last_synced_at: string | null;
}

// Campaign summary item
export interface CampaignSummaryItem {
  id: number;
  name: string;
  platform: string;
  status: string;
  spend: number;
  revenue: number;
  roas: number | null;
  conversions: number;
  trend: TrendDirection;
  scaling_score: number | null;
  recommendation: string | null;
}

// AI recommendation
export interface RecommendationItem {
  id: string;
  type: RecommendationType;
  entity_type: string;
  entity_id: number;
  entity_name: string;
  platform: string;
  title: string;
  description: string;
  impact_estimate: string | null;
  confidence: number;
  status: RecommendationStatus;
  created_at: string;
}

// Activity/event item
export interface ActivityItem {
  id: number;
  type: 'action' | 'alert' | 'auth' | 'system';
  title: string;
  description: string | null;
  severity: 'info' | 'warning' | 'error' | 'success' | null;
  timestamp: string;
  entity_type: string | null;
  entity_id: string | null;
}

// Quick action button
export interface QuickAction {
  id: string;
  label: string;
  icon: string;
  action: string;
  count: number | null;
}

// Response types
export interface DashboardOverviewResponse {
  onboarding_complete: boolean;
  has_connected_platforms: boolean;
  has_campaigns: boolean;
  period: string;
  period_label: string;
  date_range: {
    start: string;
    end: string;
  };
  metrics: OverviewMetrics;
  signal_health: SignalHealthSummary;
  platforms: PlatformSummary[];
  total_campaigns: number;
  active_campaigns: number;
  pending_recommendations: number;
  active_alerts: number;
  hidden_metrics: string[];
}

// Metric visibility types
// Backend may return available_metrics as string[] or {key, label}[]
export interface MetricVisibilityResponse {
  hidden_metrics: string[];
  available_metrics: (string | { key: string; label: string })[];
}

// Sync response
export interface SyncTriggerResponse {
  status: string;
  platform: string;
}

export interface CampaignPerformanceResponse {
  campaigns: CampaignSummaryItem[];
  total: number;
  page: number;
  page_size: number;
  sort_by: string;
  sort_order: string;
}

export interface RecommendationsResponse {
  recommendations: RecommendationItem[];
  total: number;
  by_type: Record<RecommendationType, number>;
}

export interface ActivityFeedResponse {
  activities: ActivityItem[];
  total: number;
  has_more: boolean;
}

export interface QuickActionsResponse {
  actions: QuickAction[];
}

// Account breakdown item
export interface AccountBreakdownItem {
  platform: string;
  account_id: string;
  account_name: string;
  business_name: string | null;
  currency: string;
  is_enabled: boolean;
  spend: number;
  revenue: number;
  roas: number;
  impressions: number;
  clicks: number;
  conversions: number;
  ctr: number;
  campaign_count: number;
}

// Account signal health item
export interface AccountSignalHealthItem {
  platform: string;
  account_id: string;
  account_name: string;
  business_name: string | null;
  status: string;
  emq_score: number | null;
  event_loss_pct: number | null;
  freshness_minutes: number | null;
  api_error_rate: number | null;
  issues: string | null;
  actions: string | null;
  notes: string | null;
}

export interface AccountSignalHealthResponse {
  date: string;
  overall_status: string;
  status_counts: Record<string, number>;
  total_accounts: number;
  accounts: AccountSignalHealthItem[];
}

// Export format types
export type ExportFormat = 'csv' | 'json';

// Export request
export interface DashboardExportRequest {
  format: ExportFormat;
  period?: TimePeriod;
  include_campaigns?: boolean;
  include_metrics?: boolean;
  include_recommendations?: boolean;
}

// Morning Briefing types
export interface BriefingChangeItem {
  metric: string;
  entity_name: string;
  platform: string;
  direction: 'up' | 'down';
  change_percent: number;
  current_value: number;
  severity: 'info' | 'warning' | 'critical';
  narrative: string;
}

export interface BriefingActionItem {
  priority: 'critical' | 'high' | 'medium';
  title: string;
  description: string;
  action_type: 'budget' | 'creative' | 'signal' | 'campaign';
  entity_name: string;
  impact_estimate: string;
}

export interface MorningBriefingResponse {
  date: string;
  greeting: string;
  summary_narrative: string;
  portfolio_health: 'strong' | 'steady' | 'needs_attention' | 'critical';
  total_spend: number;
  total_revenue: number;
  roas: number;
  total_conversions: number;
  spend_change_pct: number;
  revenue_change_pct: number;
  roas_change_pct: number;
  signal_status: 'healthy' | 'risk' | 'degraded' | 'critical';
  signal_score: number;
  autopilot_enabled: boolean;
  top_changes: BriefingChangeItem[];
  actions_today: BriefingActionItem[];
  active_campaigns: number;
  pending_recommendations: number;
  active_alerts: number;
  scale_candidates: number;
  fix_candidates: number;
}

// Request types
export interface CampaignPerformanceRequest {
  period?: TimePeriod;
  platform?: string;
  status?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface RecommendationsRequest {
  type?: RecommendationType;
  status?: RecommendationStatus;
  limit?: number;
}

export interface ActivityFeedRequest {
  limit?: number;
  offset?: number;
}

// =============================================================================
// API Functions
// =============================================================================

export const dashboardApi = {
  /**
   * Get dashboard overview with metrics and status
   */
  getOverview: async (
    period: TimePeriod = '7d',
    startDate?: string,
    endDate?: string,
  ): Promise<DashboardOverviewResponse> => {
    const params: Record<string, string> = { period };
    if (period === 'custom' && startDate && endDate) {
      params.start_date = startDate;
      params.end_date = endDate;
    }
    const response = await apiClient.get<ApiResponse<DashboardOverviewResponse>>(
      '/dashboard/overview',
      { params }
    );
    return response.data.data;
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
    );
    return response.data.data;
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
    );
    return response.data.data;
  },

  /**
   * Approve a recommendation
   */
  approveRecommendation: async (
    recommendationId: string
  ): Promise<{ message: string; status: string }> => {
    const response = await apiClient.post<ApiResponse<{ message: string; status: string }>>(
      `/dashboard/recommendations/${recommendationId}/approve`
    );
    return response.data.data;
  },

  /**
   * Reject a recommendation
   */
  rejectRecommendation: async (
    recommendationId: string
  ): Promise<{ message: string; status: string }> => {
    const response = await apiClient.post<ApiResponse<{ message: string; status: string }>>(
      `/dashboard/recommendations/${recommendationId}/reject`
    );
    return response.data.data;
  },

  /**
   * Get activity feed
   */
  getActivityFeed: async (params: ActivityFeedRequest = {}): Promise<ActivityFeedResponse> => {
    const response = await apiClient.get<ApiResponse<ActivityFeedResponse>>('/dashboard/activity', {
      params,
    });
    return response.data.data;
  },

  /**
   * Get quick actions
   */
  getQuickActions: async (): Promise<QuickActionsResponse> => {
    const response = await apiClient.get<ApiResponse<QuickActionsResponse>>(
      '/dashboard/quick-actions'
    );
    return response.data.data;
  },

  /**
   * Get detailed signal health
   */
  getSignalHealth: async (): Promise<SignalHealthSummary> => {
    const response = await apiClient.get<ApiResponse<SignalHealthSummary>>(
      '/dashboard/signal-health'
    );
    return response.data.data;
  },

  /**
   * Get performance breakdown by ad account
   */
  getAccountBreakdown: async (platform?: string): Promise<AccountBreakdownItem[]> => {
    const params: Record<string, string> = {};
    if (platform) params.platform = platform;
    const response = await apiClient.get<ApiResponse<AccountBreakdownItem[]>>(
      '/analytics/account-breakdown',
      { params }
    );
    return response.data.data;
  },

  /**
   * Get signal health breakdown by ad account
   */
  getAccountSignalHealth: async (
    tenantId: number,
    platform?: string,
    date?: string,
  ): Promise<AccountSignalHealthResponse> => {
    const params: Record<string, string> = {};
    if (platform) params.platform = platform;
    if (date) params.date = date;
    const response = await apiClient.get<ApiResponse<AccountSignalHealthResponse>>(
      `/trust-layer/tenant/${tenantId}/signal-health/by-account`,
      { params }
    );
    return response.data.data;
  },

  /**
   * Export dashboard data as CSV or JSON
   */
  exportDashboard: async (params: DashboardExportRequest): Promise<Blob> => {
    const response = await apiClient.post('/dashboard/export', params, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Trigger a platform sync (Meta, TikTok, etc.)
   */
  syncPlatform: async (platform: string, daysBack = 30): Promise<SyncTriggerResponse> => {
    const response = await apiClient.post<ApiResponse<SyncTriggerResponse>>(
      `/campaigns/sync/${platform}`,
      null,
      { params: { days_back: daysBack } }
    );
    return response.data.data;
  },

  /**
   * Get morning briefing
   */
  getMorningBriefing: async (): Promise<MorningBriefingResponse> => {
    const response = await apiClient.get<ApiResponse<MorningBriefingResponse>>(
      '/dashboard/morning-briefing'
    );
    return response.data.data;
  },

  /**
   * Get metric visibility settings
   */
  getMetricVisibility: async (): Promise<MetricVisibilityResponse> => {
    const response = await apiClient.get<ApiResponse<MetricVisibilityResponse>>(
      '/dashboard/settings/metric-visibility'
    );
    return response.data.data;
  },

  /**
   * Update metric visibility settings
   */
  updateMetricVisibility: async (hiddenMetrics: string[]): Promise<MetricVisibilityResponse> => {
    const response = await apiClient.patch<ApiResponse<MetricVisibilityResponse>>(
      '/dashboard/settings/metric-visibility',
      { hidden_metrics: hiddenMetrics }
    );
    return response.data.data;
  },
};

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Get dashboard overview
 */
export function useDashboardOverview(
  period: TimePeriod = '7d',
  enabled = true,
  startDate?: string,
  endDate?: string,
) {
  return useQuery({
    queryKey: ['dashboard', 'overview', period, startDate, endDate],
    queryFn: () => dashboardApi.getOverview(period, startDate, endDate),
    enabled,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, error: Error) => {
      // Don't retry on auth errors
      const axiosError = error as { response?: { status?: number } };
      if (axiosError?.response?.status === 401 || axiosError?.response?.status === 403) return false;
      return failureCount < 2;
    },
  });
}

/**
 * Get campaign performance
 */
export function useDashboardCampaigns(params: CampaignPerformanceRequest = {}, enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'campaigns', params],
    queryFn: () => dashboardApi.getCampaigns(params),
    enabled,
    staleTime: 60 * 1000,
  });
}

/**
 * Get recommendations
 */
export function useDashboardRecommendations(params: RecommendationsRequest = {}, enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'recommendations', params],
    queryFn: () => dashboardApi.getRecommendations(params),
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

/**
 * Approve recommendation
 */
export function useApproveRecommendation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dashboardApi.approveRecommendation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'recommendations'] });
    },
  });
}

/**
 * Reject recommendation
 */
export function useRejectRecommendation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dashboardApi.rejectRecommendation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'recommendations'] });
    },
  });
}

/**
 * Get activity feed
 */
export function useDashboardActivity(params: ActivityFeedRequest = {}, enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'activity', params],
    queryFn: () => dashboardApi.getActivityFeed(params),
    enabled,
    staleTime: 30 * 1000, // 30 seconds
  });
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
  });
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
    retry: (failureCount, error: Error) => {
      const axiosError = error as { response?: { status?: number } };
      if (axiosError?.response?.status === 401 || axiosError?.response?.status === 403) return false;
      return failureCount < 2;
    },
  });
}

/**
 * Get account performance breakdown
 */
export function useAccountBreakdown(platform?: string, enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'account-breakdown', platform],
    queryFn: () => dashboardApi.getAccountBreakdown(platform),
    enabled,
    staleTime: 60 * 1000,
  });
}

/**
 * Get account-level signal health
 */
export function useAccountSignalHealth(
  tenantId: number,
  platform?: string,
  date?: string,
  enabled = true,
) {
  return useQuery({
    queryKey: ['dashboard', 'account-signal-health', tenantId, platform, date],
    queryFn: () => dashboardApi.getAccountSignalHealth(tenantId, platform, date),
    enabled: enabled && !!tenantId,
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

/**
 * Export dashboard data
 */
export function useExportDashboard() {
  return useMutation({
    mutationFn: async (params: DashboardExportRequest) => {
      const blob = await dashboardApi.exportDashboard(params);
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `stratum-dashboard-export-${new Date().toISOString().split('T')[0]}.${params.format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      return blob;
    },
  });
}

/**
 * Trigger platform sync
 */
export function useSyncPlatform() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ platform, daysBack }: { platform: string; daysBack?: number }) =>
      dashboardApi.syncPlatform(platform, daysBack),
    onSuccess: () => {
      // Invalidate dashboard data after sync triggers
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

/**
 * Get metric visibility settings
 */
export function useMetricVisibility(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'metric-visibility'],
    queryFn: dashboardApi.getMetricVisibility,
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Get morning briefing
 */
export function useMorningBriefing(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'morning-briefing'],
    queryFn: dashboardApi.getMorningBriefing,
    enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 30 * 60 * 1000, // 30 minutes
    retry: 1,
  });
}

// =============================================================================
// Anomaly Narratives Types (Feature #2)
// =============================================================================

export interface AnomalyNarrative {
  metric: string;
  title: string;
  summary: string;
  likely_causes: string[];
  recommended_actions: string[];
  severity: 'critical' | 'high' | 'medium' | 'low';
  direction: 'up' | 'down';
  change_percent: number;
  current_value: number;
  baseline_value: number;
  zscore: number;
  category: 'spend' | 'revenue' | 'efficiency' | 'quality' | 'other';
}

export interface CorrelationInsight {
  title: string;
  description: string;
  severity: string;
  related_metrics: string[];
  pattern: string;
}

export interface AnomalyNarrativesResponse {
  executive_summary: string;
  total_anomalies: number;
  critical_count: number;
  high_count: number;
  narratives: AnomalyNarrative[];
  correlations: CorrelationInsight[];
  portfolio_risk: 'low' | 'moderate' | 'elevated' | 'high';
}

/**
 * Hook for fetching anomaly narratives
 */
export function useAnomalyNarratives(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'anomaly-narratives'],
    queryFn: async (): Promise<AnomalyNarrativesResponse> => {
      const response = await apiClient.get<ApiResponse<AnomalyNarrativesResponse>>(
        '/dashboard/anomaly-narratives'
      );
      return response.data.data;
    },
    enabled,
    staleTime: 10 * 60 * 1000,
    refetchInterval: 30 * 60 * 1000,
    retry: 1,
  });
}

// =============================================================================
// Signal Auto-Recovery Types (Feature #3)
// =============================================================================

export interface SignalIssue {
  id: string;
  type: 'emq_drop' | 'event_loss' | 'api_down' | 'data_stale' | 'tracking_gap';
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  metric_value: number | null;
  threshold: number | null;
  affected_platforms: string[];
  detected_at: string;
}

export interface RecoveryAction {
  id: string;
  issue_id: string;
  type: 'resync' | 'diagnostics' | 'check_capi' | 'check_pixel' | 'alert_team' | 'expand_params';
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  priority: 'urgent' | 'high' | 'normal';
  auto_triggered: boolean;
  estimated_minutes: number | null;
}

export interface RecoveryTimeline {
  timestamp: string;
  event: string;
  type: 'detection' | 'action' | 'progress' | 'resolution';
  details: string | null;
}

export interface SignalRecoveryResponse {
  status: 'healthy' | 'recovering' | 'degraded' | 'critical';
  summary: string;
  issues: SignalIssue[];
  recovery_actions: RecoveryAction[];
  timeline: RecoveryTimeline[];
  overall_health_score: number;
  recovery_progress_pct: number;
  has_active_recovery: boolean;
  platforms_affected: string[];
  last_healthy_at: string | null;
  estimated_recovery_minutes: number | null;
}

/**
 * Hook for fetching signal recovery status
 */
export function useSignalRecovery(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'signal-recovery'],
    queryFn: async (): Promise<SignalRecoveryResponse> => {
      const response = await apiClient.get<ApiResponse<SignalRecoveryResponse>>(
        '/dashboard/signal-recovery'
      );
      return response.data.data;
    },
    enabled,
    staleTime: 30 * 1000, // 30 seconds — signal health changes fast
    refetchInterval: 2 * 60 * 1000, // 2 minutes
    retry: 1,
  });
}

// =============================================================================
// Predictive Budget Autopilot Types (Feature #5)
// =============================================================================

export interface CampaignBudgetInsight {
  campaign_id: number;
  campaign_name: string;
  platform: string;
  current_spend: number;
  recommended_spend: number;
  change_amount: number;
  change_percent: number;
  action: 'scale' | 'reduce' | 'maintain' | 'pause';
  confidence: number;
  reasoning: string;
  metrics: Record<string, number>;
  risk_factors: string[];
}

export interface BudgetForecast {
  projected_spend: number;
  projected_revenue: number;
  projected_roas: number;
  projected_conversions: number;
  spend_change_pct: number;
  revenue_change_pct: number;
  confidence_level: 'high' | 'medium' | 'low';
}

export interface PredictiveBudgetResponse {
  summary: string;
  trust_gate_status: 'pass' | 'hold' | 'block';
  autopilot_eligible: boolean;
  total_campaigns_analyzed: number;
  recommendations: CampaignBudgetInsight[];
  scale_candidates: number;
  reduce_candidates: number;
  maintain_count: number;
  total_budget_shift: number;
  budget_shift_pct: number;
  forecast: BudgetForecast | null;
  avg_confidence: number;
  high_confidence_count: number;
}

/**
 * Hook for fetching predictive budget recommendations
 */
export function usePredictiveBudget(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'predictive-budget'],
    queryFn: async (): Promise<PredictiveBudgetResponse> => {
      const response = await apiClient.get<ApiResponse<PredictiveBudgetResponse>>(
        '/dashboard/predictive-budget'
      );
      return response.data.data;
    },
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 15 * 60 * 1000, // 15 minutes
    retry: 1,
  });
}

// =============================================================================
// Feature #6: AI-Generated Reports
// =============================================================================

export interface ReportKPI {
  label: string;
  value: number;
  formatted: string;
  change_pct: number;
  trend: 'up' | 'down' | 'flat';
  is_good: boolean;
}

export interface PlatformBreakdown {
  platform: string;
  spend: number;
  revenue: number;
  roas: number;
  conversions: number;
  campaigns: number;
  spend_share_pct: number;
  change_summary: string;
}

export interface CampaignHighlight {
  campaign_id: number;
  campaign_name: string;
  platform: string;
  metric_label: string;
  metric_value: string;
  roas: number;
  spend: number;
  insight: string;
}

export interface ReportInsight {
  category: 'trend' | 'opportunity' | 'risk' | 'milestone';
  title: string;
  narrative: string;
  severity: 'info' | 'positive' | 'warning' | 'critical';
}

export interface ReportSection {
  title: string;
  section_type: string;
  content: string;
  kpis: ReportKPI[];
  platforms: PlatformBreakdown[];
  highlights: CampaignHighlight[];
  insights: ReportInsight[];
}

export interface AIReportResponse {
  report_title: string;
  generated_at: string;
  period_label: string;
  executive_summary: string;
  health_grade: 'A' | 'B' | 'C' | 'D' | 'F';
  health_label: string;
  sections: ReportSection[];
  total_spend: number;
  total_revenue: number;
  overall_roas: number;
  total_conversions: number;
  total_campaigns: number;
  platforms_count: number;
  top_recommendations: string[];
}

/**
 * Hook for fetching AI-generated performance report
 */
export function useAIReport(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'ai-report'],
    queryFn: async (): Promise<AIReportResponse> => {
      const response = await apiClient.get<ApiResponse<AIReportResponse>>(
        '/dashboard/ai-report'
      );
      return response.data.data;
    },
    enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes
    refetchInterval: 30 * 60 * 1000, // 30 minutes
    retry: 1,
  });
}

// =============================================================================
// Feature #7: Churn Prevention Automations
// =============================================================================

export interface ChurnSignal {
  signal: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  weight: number;
}

export interface ChurnIntervention {
  action: string;
  title: string;
  description: string;
  priority: 'immediate' | 'soon' | 'monitor';
  category: 'outreach' | 'optimize' | 'budget' | 'creative' | 'technical';
  auto_eligible: boolean;
}

export interface AtRiskCampaign {
  campaign_id: number;
  campaign_name: string;
  platform: string;
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  signals: ChurnSignal[];
  interventions: ChurnIntervention[];
  days_declining: number;
  current_roas: number;
  spend: number;
}

export interface RetentionMetric {
  label: string;
  value: string;
  trend: 'improving' | 'stable' | 'declining';
  is_healthy: boolean;
}

export interface ChurnPreventionResponse {
  summary: string;
  portfolio_risk_level: 'healthy' | 'watch' | 'warning' | 'critical';
  portfolio_risk_score: number;
  total_campaigns_analyzed: number;
  at_risk_count: number;
  critical_count: number;
  healthy_count: number;
  retention_rate_pct: number;
  metrics: RetentionMetric[];
  at_risk_campaigns: AtRiskCampaign[];
  top_interventions: ChurnIntervention[];
  risk_distribution: Record<string, number>;
}

/**
 * Hook for fetching churn prevention analysis
 */
export function useChurnPrevention(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'churn-prevention'],
    queryFn: async (): Promise<ChurnPreventionResponse> => {
      const response = await apiClient.get<ApiResponse<ChurnPreventionResponse>>(
        '/dashboard/churn-prevention'
      );
      return response.data.data;
    },
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // 10 minutes
    retry: 1,
  });
}

// =============================================================================
// Feature #8: Unified Notifications with AI Priority
// =============================================================================

export interface NotificationSuggestedAction {
  action_type: string;
  label: string;
  description: string;
  url?: string;
}

export interface PrioritizedNotification {
  id: string;
  title: string;
  message: string;
  source: 'pacing' | 'signal_health' | 'campaign' | 'anomaly' | 'system' | 'trust_gate' | 'churn';
  notification_type: 'info' | 'warning' | 'error' | 'success' | 'alert';
  category: string;
  priority_score: number;
  urgency: number;
  impact: number;
  actionability: number;
  priority_label: 'critical' | 'high' | 'medium' | 'low';
  created_at: string;
  is_read: boolean;
  suggested_action?: NotificationSuggestedAction;
  context: Record<string, unknown>;
}

export interface NotificationGroup {
  category: string;
  label: string;
  count: number;
  top_priority: number;
  notifications: PrioritizedNotification[];
}

export interface UnifiedNotificationsResponse {
  summary: string;
  total_count: number;
  unread_count: number;
  critical_count: number;
  high_count: number;
  notifications: PrioritizedNotification[];
  groups: NotificationGroup[];
  top_actions: NotificationSuggestedAction[];
}

/**
 * Hook for fetching AI-prioritized notifications
 */
export function useUnifiedNotifications(enabled = true) {
  return useQuery({
    queryKey: ['dashboard', 'notifications-prioritized'],
    queryFn: async (): Promise<UnifiedNotificationsResponse> => {
      const response = await apiClient.get<ApiResponse<UnifiedNotificationsResponse>>(
        '/dashboard/notifications-prioritized'
      );
      return response.data.data;
    },
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    refetchInterval: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });
}

/**
 * Update metric visibility settings
 */
export function useUpdateMetricVisibility() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (hiddenMetrics: string[]) => dashboardApi.updateMetricVisibility(hiddenMetrics),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'metric-visibility'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'overview'] });
    },
  });
}
