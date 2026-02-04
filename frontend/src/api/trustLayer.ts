/**
 * Stratum AI - Trust Layer API Hooks
 *
 * React Query hooks for Trust Layer features:
 * - Signal health monitoring
 * - Attribution variance tracking
 * - Combined trust status
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

// =============================================================================
// Types
// =============================================================================

export type SignalHealthStatus = 'ok' | 'risk' | 'degraded' | 'critical' | 'no_data';
export type AttributionVarianceStatus =
  | 'healthy'
  | 'minor_variance'
  | 'moderate_variance'
  | 'high_variance'
  | 'no_data';

export interface MetricCard {
  title: string;
  value: string;
  status: 'ok' | 'risk' | 'degraded' | 'neutral';
  description?: string;
}

export interface TrustBanner {
  type: 'info' | 'warning' | 'error';
  title: string;
  message: string;
  actions: string[];
}

export interface PlatformHealthRow {
  platform: string;
  account_id?: string;
  emq_score?: number;
  event_loss_pct?: number;
  freshness_minutes?: number;
  api_error_rate?: number;
  status: SignalHealthStatus;
}

export interface SignalHealthData {
  date: string;
  status: SignalHealthStatus;
  automation_blocked: boolean;
  cards: MetricCard[];
  platform_rows: PlatformHealthRow[];
  banners: TrustBanner[];
  issues: string[];
  actions: string[];
}

export interface PlatformVarianceRow {
  platform: string;
  ga4_revenue: number;
  platform_revenue: number;
  revenue_delta_pct: number;
  ga4_conversions: number;
  platform_conversions: number;
  conversion_delta_pct: number;
  confidence: number;
  status: AttributionVarianceStatus;
}

export interface AttributionVarianceData {
  date: string;
  status: AttributionVarianceStatus;
  overall_revenue_variance_pct: number;
  overall_conversion_variance_pct: number;
  cards: MetricCard[];
  platform_rows: PlatformVarianceRow[];
  banners: TrustBanner[];
}

export interface TrustStatusData {
  date: string;
  overall_status: SignalHealthStatus;
  automation_allowed: boolean;
  signal_health: SignalHealthData | null;
  attribution_variance: AttributionVarianceData | null;
  banners: TrustBanner[];
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch signal health data for a tenant.
 */
export function useSignalHealth(tenantId: number, date?: string) {
  return useQuery({
    queryKey: ['signal-health', tenantId, date],
    queryFn: async () => {
      const params = date ? `?date=${date}` : '';
      const response = await apiClient.get<{ data: SignalHealthData }>(
        `/trust-layer/tenant/${tenantId}/signal-health${params}`
      );
      return response.data.data;
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

/**
 * Fetch signal health history for trend analysis.
 */
export function useSignalHealthHistory(tenantId: number, days: number = 7, platform?: string) {
  return useQuery({
    queryKey: ['signal-health-history', tenantId, days, platform],
    queryFn: async () => {
      const params = new URLSearchParams({ days: days.toString() });
      if (platform) params.append('platform', platform);

      const response = await apiClient.get<{ data: { history: SignalHealthData[] } }>(
        `/trust-layer/tenant/${tenantId}/signal-health/history?${params}`
      );
      return response.data.data.history;
    },
    enabled: !!tenantId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Fetch attribution variance data for a tenant.
 */
export function useAttributionVariance(tenantId: number, date?: string) {
  return useQuery({
    queryKey: ['attribution-variance', tenantId, date],
    queryFn: async () => {
      const params = date ? `?date=${date}` : '';
      const response = await apiClient.get<{ data: AttributionVarianceData }>(
        `/trust-layer/tenant/${tenantId}/attribution-variance${params}`
      );
      return response.data.data;
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

/**
 * Fetch combined trust status for a tenant.
 * This is the main endpoint for the Trust Layer banner.
 */
export function useTrustStatus(tenantId: number, date?: string) {
  return useQuery({
    queryKey: ['trust-status', tenantId, date],
    queryFn: async () => {
      const params = date ? `?date=${date}` : '';
      const response = await apiClient.get<{ data: TrustStatusData }>(
        `/trust-layer/tenant/${tenantId}/trust-status${params}`
      );
      return response.data.data;
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get status color for UI rendering.
 */
export function getStatusColor(status: SignalHealthStatus | AttributionVarianceStatus): string {
  const colors: Record<string, string> = {
    ok: 'green',
    healthy: 'green',
    risk: 'yellow',
    minor_variance: 'yellow',
    degraded: 'orange',
    moderate_variance: 'orange',
    critical: 'red',
    high_variance: 'red',
    no_data: 'gray',
  };
  return colors[status] || 'gray';
}

/**
 * Get status label for display.
 */
export function getStatusLabel(status: SignalHealthStatus | AttributionVarianceStatus): string {
  const labels: Record<string, string> = {
    ok: 'Healthy',
    healthy: 'Healthy',
    risk: 'At Risk',
    minor_variance: 'Minor Variance',
    degraded: 'Degraded',
    moderate_variance: 'Moderate Variance',
    critical: 'Critical',
    high_variance: 'High Variance',
    no_data: 'No Data',
  };
  return labels[status] || status;
}

/**
 * Get banner icon based on type.
 */
export function getBannerIcon(type: 'info' | 'warning' | 'error'): string {
  const icons: Record<string, string> = {
    info: 'ℹ️',
    warning: '⚠️',
    error: '🚨',
  };
  return icons[type] || 'ℹ️';
}

// =============================================================================
// Trust Gate Audit Log Types
// =============================================================================

export interface TrustGateAuditLog {
  id: string;
  created_at: string;
  decision_type: 'execute' | 'hold' | 'block';
  action_type: string;
  entity_type: string;
  entity_id: string;
  entity_name?: string;
  platform?: string;
  signal_health_score?: number;
  signal_health_status?: string;
  gate_passed: boolean;
  gate_reason?: Record<string, unknown>;
  is_dry_run: boolean;
  healthy_threshold?: number;
  degraded_threshold?: number;
  triggered_by_system: boolean;
}

export interface TrustGateAuditLogsResponse {
  logs: TrustGateAuditLog[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
  summary: {
    total_decisions: number;
    executed: number;
    held: number;
    blocked: number;
    pass_rate: number;
  };
  date_range: {
    start: string;
    end: string;
  };
}

export interface SignalHealthHistoryRecord {
  date: string;
  overall_score: number;
  status: SignalHealthStatus;
  emq_score_avg?: number;
  event_loss_pct_avg?: number;
  freshness_minutes_avg?: number;
  api_error_rate_avg?: number;
  platforms_ok: number;
  platforms_risk: number;
  platforms_degraded: number;
  platforms_critical: number;
  automation_blocked: boolean;
}

export interface SignalHealthHistoryResponse {
  days: number;
  platform?: string;
  start_date: string;
  end_date: string;
  history: SignalHealthHistoryRecord[];
  total_records: number;
}

// =============================================================================
// Trust Gate Audit Log Hooks
// =============================================================================

/**
 * Fetch trust gate audit logs for a tenant.
 */
export function useTrustGateAuditLogs(
  tenantId: number,
  options?: {
    days?: number;
    decisionType?: string;
    entityType?: string;
    limit?: number;
    offset?: number;
  }
) {
  return useQuery({
    queryKey: ['trust-gate-audit-logs', tenantId, options],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (options?.days) params.append('days', options.days.toString());
      if (options?.decisionType) params.append('decision_type', options.decisionType);
      if (options?.entityType) params.append('entity_type', options.entityType);
      if (options?.limit) params.append('limit', options.limit.toString());
      if (options?.offset) params.append('offset', options.offset.toString());

      const response = await apiClient.get<{ data: TrustGateAuditLogsResponse }>(
        `/trust-layer/tenant/${tenantId}/trust-gate/audit-logs?${params}`
      );
      return response.data.data;
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000,
  });
}

/**
 * Fetch detailed signal health history for trend charts.
 */
export function useSignalHealthHistoryDetailed(
  tenantId: number,
  days: number = 7,
  platform?: string
) {
  return useQuery({
    queryKey: ['signal-health-history-detailed', tenantId, days, platform],
    queryFn: async () => {
      const params = new URLSearchParams({ days: days.toString() });
      if (platform) params.append('platform', platform);

      const response = await apiClient.get<{ data: SignalHealthHistoryResponse }>(
        `/trust-layer/tenant/${tenantId}/signal-health/history?${params}`
      );
      return response.data.data;
    },
    enabled: !!tenantId,
    staleTime: 5 * 60 * 1000,
  });
}
