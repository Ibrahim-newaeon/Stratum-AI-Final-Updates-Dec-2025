/**
 * Stratum AI - Tenant Dashboard Hooks
 *
 * React Query hooks for tenant-scoped dashboard data.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse } from '../client';

// =============================================================================
// Types
// =============================================================================

export interface DashboardOverview {
  total_spend: number;
  total_revenue: number;
  spend_delta_pct: number;
  revenue_delta_pct: number;
  portfolio_roas: number;
  roas_delta_pct: number;
  avg_cpa: number;
  cpa_delta_pct: number;
  avg_ctr: number;
  ctr_delta_pct: number;
  total_impressions: number;
  total_clicks: number;
  total_conversions: number;
  total_campaigns: number;
  active_campaigns: number;
  paused_campaigns: number;
  scaling_candidates: number;
  watch_campaigns: number;
  fix_candidates: number;
  avg_emq_score: number | null;
  signal_health_status: string;
  open_alerts_count: number;
  platform_breakdown: Record<string, { campaigns: number; spend: number; revenue: number }>;
}

export interface Recommendation {
  id: string;
  type: 'scale' | 'watch' | 'fix' | 'pause' | 'creative_refresh' | 'budget_shift';
  priority: number;
  entity_type: string;
  entity_id: string;
  entity_name: string;
  title: string;
  description: string;
  impact_estimate: string | null;
  roas_impact: number | null;
  confidence: number;
  actions: Array<{ action: string; label: string; params?: Record<string, any> }>;
  created_at: string;
}

export interface Alert {
  id: number;
  type: 'anomaly' | 'fatigue' | 'budget' | 'signal' | 'system';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: string | null;
  entity_name: string | null;
  metric: string | null;
  current_value: number | null;
  expected_value: number | null;
  is_acknowledged: boolean;
  is_resolved: boolean;
  acknowledged_by: number | null;
  acknowledged_at: string | null;
  resolved_by: number | null;
  resolved_at: string | null;
  created_at: string;
}

export interface TenantSettings {
  currency: string;
  timezone: string;
  date_format: string;
  fiscal_year_start: number;
  alert_roas_drop_pct: number;
  alert_cpa_increase_pct: number;
  alert_spend_anomaly_threshold: number;
  alert_emq_min_score: number;
  email_notifications: boolean;
  whatsapp_notifications: boolean;
  slack_notifications: boolean;
  notification_frequency: string;
  connected_platforms: string[];
  feature_flags: Record<string, boolean>;
}

export interface CommandCenterItem {
  campaign_id: number;
  campaign_name: string;
  platform: string;
  status: string;
  spend: number;
  revenue: number;
  roas: number;
  cpa: number;
  ctr: number;
  conversions: number;
  scaling_score: number;
  action: 'scale' | 'watch' | 'fix';
  signals: {
    roas_momentum: number;
    spend_efficiency: number;
    conversion_trend: number;
  };
  recommendation: string;
}

export interface CommandCenterResponse {
  items: CommandCenterItem[];
  summary: {
    total: number;
    scale: number;
    watch: number;
    fix: number;
  };
}

// =============================================================================
// Query Keys
// =============================================================================

export const tenantQueryKeys = {
  all: ['tenant'] as const,
  overview: (tenantId: number, date?: string) =>
    [...tenantQueryKeys.all, 'overview', tenantId, date] as const,
  recommendations: (tenantId: number, date?: string) =>
    [...tenantQueryKeys.all, 'recommendations', tenantId, date] as const,
  alerts: (tenantId: number, filters?: Record<string, any>) =>
    [...tenantQueryKeys.all, 'alerts', tenantId, filters] as const,
  settings: (tenantId: number) => [...tenantQueryKeys.all, 'settings', tenantId] as const,
  commandCenter: (tenantId: number, filters?: Record<string, any>) =>
    [...tenantQueryKeys.all, 'commandCenter', tenantId, filters] as const,
};

// =============================================================================
// API Functions
// =============================================================================

const fetchDashboardOverview = async (
  tenantId: number,
  date?: string,
  period?: string
): Promise<DashboardOverview> => {
  const params = new URLSearchParams();
  if (date) params.append('date', date);
  if (period) params.append('period', period);

  const response = await apiClient.get<ApiResponse<DashboardOverview>>(
    `/tenant/${tenantId}/dashboard/overview?${params.toString()}`
  );
  return response.data.data;
};

const fetchRecommendations = async (
  tenantId: number,
  date?: string,
  limit?: number
): Promise<Recommendation[]> => {
  const params = new URLSearchParams();
  if (date) params.append('date', date);
  if (limit) params.append('limit', String(limit));

  const response = await apiClient.get<ApiResponse<Recommendation[]>>(
    `/tenant/${tenantId}/recommendations?${params.toString()}`
  );
  return response.data.data;
};

const fetchAlerts = async (
  tenantId: number,
  filters?: {
    severity?: string;
    type?: string;
    include_resolved?: boolean;
    skip?: number;
    limit?: number;
  }
): Promise<Alert[]> => {
  const params = new URLSearchParams();
  if (filters?.severity) params.append('severity', filters.severity);
  if (filters?.type) params.append('type', filters.type);
  if (filters?.include_resolved) params.append('include_resolved', 'true');
  if (filters?.skip) params.append('skip', String(filters.skip));
  if (filters?.limit) params.append('limit', String(filters.limit));

  const response = await apiClient.get<ApiResponse<Alert[]>>(
    `/tenant/${tenantId}/alerts?${params.toString()}`
  );
  return response.data.data;
};

const fetchSettings = async (tenantId: number): Promise<TenantSettings> => {
  const response = await apiClient.get<ApiResponse<TenantSettings>>(`/tenant/${tenantId}/settings`);
  return response.data.data;
};

const updateSettings = async (
  tenantId: number,
  settings: Partial<TenantSettings>
): Promise<TenantSettings> => {
  const response = await apiClient.put<ApiResponse<TenantSettings>>(
    `/tenant/${tenantId}/settings`,
    settings
  );
  return response.data.data;
};

const acknowledgeAlert = async (
  tenantId: number,
  alertId: number
): Promise<{ alert_id: number; acknowledged_by: number; acknowledged_at: string }> => {
  const response = await apiClient.post<ApiResponse<any>>(
    `/tenant/${tenantId}/alerts/${alertId}/ack`
  );
  return response.data.data;
};

const resolveAlert = async (
  tenantId: number,
  alertId: number,
  notes?: string
): Promise<{ alert_id: number; resolved_by: number; resolved_at: string }> => {
  const params = notes ? `?resolution_notes=${encodeURIComponent(notes)}` : '';
  const response = await apiClient.post<ApiResponse<any>>(
    `/tenant/${tenantId}/alerts/${alertId}/resolve${params}`
  );
  return response.data.data;
};

const fetchCommandCenter = async (
  tenantId: number,
  filters?: {
    action?: string;
    platform?: string;
    limit?: number;
  }
): Promise<CommandCenterResponse> => {
  const params = new URLSearchParams();
  if (filters?.action) params.append('action_filter', filters.action);
  if (filters?.platform) params.append('platform', filters.platform);
  if (filters?.limit) params.append('limit', String(filters.limit));

  const response = await apiClient.get<ApiResponse<CommandCenterResponse>>(
    `/tenant/${tenantId}/command-center?${params.toString()}`
  );
  return response.data.data;
};

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to fetch tenant dashboard overview data.
 */
export function useTenantOverview(
  tenantId: number,
  date?: string,
  options?: {
    period?: string;
    enabled?: boolean;
    refetchInterval?: number;
  }
) {
  return useQuery({
    queryKey: tenantQueryKeys.overview(tenantId, date),
    queryFn: () => fetchDashboardOverview(tenantId, date, options?.period),
    enabled: options?.enabled !== false && !!tenantId,
    refetchInterval: options?.refetchInterval,
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}

/**
 * Hook to fetch tenant recommendations.
 */
export function useTenantRecommendations(
  tenantId: number,
  date?: string,
  options?: {
    limit?: number;
    enabled?: boolean;
  }
) {
  return useQuery({
    queryKey: tenantQueryKeys.recommendations(tenantId, date),
    queryFn: () => fetchRecommendations(tenantId, date, options?.limit),
    enabled: options?.enabled !== false && !!tenantId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Hook to fetch tenant alerts.
 */
export function useTenantAlerts(
  tenantId: number,
  filters?: {
    severity?: string;
    type?: string;
    include_resolved?: boolean;
    skip?: number;
    limit?: number;
  },
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
  }
) {
  return useQuery({
    queryKey: tenantQueryKeys.alerts(tenantId, filters),
    queryFn: () => fetchAlerts(tenantId, filters),
    enabled: options?.enabled !== false && !!tenantId,
    refetchInterval: options?.refetchInterval,
    staleTime: 1000 * 30, // 30 seconds
  });
}

/**
 * Hook to fetch tenant settings.
 */
export function useTenantSettings(tenantId: number, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: tenantQueryKeys.settings(tenantId),
    queryFn: () => fetchSettings(tenantId),
    enabled: options?.enabled !== false && !!tenantId,
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

/**
 * Hook to update tenant settings.
 */
export function useUpdateTenantSettings(tenantId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (settings: Partial<TenantSettings>) => updateSettings(tenantId, settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantQueryKeys.settings(tenantId) });
    },
  });
}

/**
 * Hook to acknowledge an alert.
 */
export function useAcknowledgeAlert(tenantId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (alertId: number) => acknowledgeAlert(tenantId, alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantQueryKeys.alerts(tenantId) });
    },
  });
}

/**
 * Hook to resolve an alert.
 */
export function useResolveAlert(tenantId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ alertId, notes }: { alertId: number; notes?: string }) =>
      resolveAlert(tenantId, alertId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tenantQueryKeys.alerts(tenantId) });
    },
  });
}

/**
 * Hook to fetch command center data.
 */
export function useCommandCenter(
  tenantId: number,
  filters?: {
    action?: string;
    platform?: string;
    limit?: number;
  },
  options?: {
    enabled?: boolean;
    refetchInterval?: number;
  }
) {
  return useQuery({
    queryKey: tenantQueryKeys.commandCenter(tenantId, filters),
    queryFn: () => fetchCommandCenter(tenantId, filters),
    enabled: options?.enabled !== false && !!tenantId,
    refetchInterval: options?.refetchInterval,
    staleTime: 1000 * 60, // 1 minute
  });
}

/**
 * Hook to test Slack webhook connection.
 */
export function useTestSlackWebhook() {
  return useMutation({
    mutationFn: async ({ webhookUrl }: { webhookUrl: string }) => {
      const response = await apiClient.post<ApiResponse<{ success: boolean; message: string }>>(
        '/integrations/slack/test',
        { webhook_url: webhookUrl }
      );
      return response.data.data;
    },
  });
}
