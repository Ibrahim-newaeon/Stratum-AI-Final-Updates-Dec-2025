/**
 * Stratum AI - Superadmin Analytics API Hooks
 *
 * React Query hooks for superadmin platform analytics:
 * - Platform overview
 * - Tenant profitability
 * - Signal health trends
 * - Actions analytics
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

// =============================================================================
// Types
// =============================================================================

export interface PlatformOverview {
  period_days: number;
  start_date: string;
  active_tenants: number;
  total_actions: number;
  applied_actions: number;
  failed_actions: number;
  success_rate: number;
  signal_health_summary: Record<string, number>;
  platform_breakdown: Array<{
    platform: string;
    record_count: number;
    avg_emq: number | null;
  }>;
}

export interface TenantProfitability {
  tenant_id: number;
  total_actions: number;
  applied_actions: number;
  active_days: number;
  action_efficiency: number;
  avg_emq_score: number;
  avg_event_loss: number;
  health_score: number;
}

export interface TenantProfitabilityResponse {
  period_days: number;
  start_date: string;
  tenants: TenantProfitability[];
  total_tenants: number;
}

export interface SignalHealthTrend {
  date: string;
  avg_emq: number | null;
  avg_event_loss: number | null;
  avg_freshness_minutes: number | null;
  avg_api_error_rate: number | null;
  record_count: number;
}

export interface SignalHealthTrendsResponse {
  period_days: number;
  trends: SignalHealthTrend[];
  trend_direction: 'improving' | 'declining' | 'stable' | 'insufficient_data';
}

export interface ActionsAnalytics {
  period_days: number;
  total_actions: number;
  type_breakdown: Record<string, number>;
  status_breakdown: Record<string, number>;
  platform_breakdown: Record<string, number>;
  daily_counts: Array<{ date: string; count: number }>;
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Get platform-wide overview metrics.
 */
export function usePlatformOverview(days: number = 7) {
  return useQuery({
    queryKey: ['superadmin-platform-overview', days],
    queryFn: async () => {
      const response = await apiClient.get<{ data: PlatformOverview }>(
        `/superadmin/platform-overview?days=${days}`
      );
      return response.data.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Get tenant profitability metrics.
 */
export function useTenantProfitability(days: number = 30) {
  return useQuery({
    queryKey: ['superadmin-tenant-profitability', days],
    queryFn: async () => {
      const response = await apiClient.get<{ data: TenantProfitabilityResponse }>(
        `/superadmin/tenant-profitability?days=${days}`
      );
      return response.data.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Get signal health trends.
 */
export function useSignalHealthTrends(days: number = 14) {
  return useQuery({
    queryKey: ['superadmin-signal-health-trends', days],
    queryFn: async () => {
      const response = await apiClient.get<{ data: SignalHealthTrendsResponse }>(
        `/superadmin/signal-health-trends?days=${days}`
      );
      return response.data.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Get actions analytics.
 */
export function useActionsAnalytics(days: number = 7) {
  return useQuery({
    queryKey: ['superadmin-actions-analytics', days],
    queryFn: async () => {
      const response = await apiClient.get<{ data: ActionsAnalytics }>(
        `/superadmin/actions-analytics?days=${days}`
      );
      return response.data.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get health score color.
 */
export function getHealthScoreColor(score: number): string {
  if (score >= 80) return 'green';
  if (score >= 60) return 'yellow';
  if (score >= 40) return 'orange';
  return 'red';
}

/**
 * Get trend direction icon.
 */
export function getTrendIcon(direction: string): string {
  const icons: Record<string, string> = {
    improving: '📈',
    declining: '📉',
    stable: '➡️',
    insufficient_data: '❓',
  };
  return icons[direction] || '❓';
}

/**
 * Format platform name.
 */
export function formatPlatformName(platform: string): string {
  const names: Record<string, string> = {
    meta: 'Meta (Facebook/Instagram)',
    google: 'Google Ads',
    tiktok: 'TikTok Ads',
    snapchat: 'Snapchat Ads',
  };
  return names[platform] || platform;
}
