/**
 * Stratum AI - Trust Layer API Hooks
 *
 * React Query hooks for Trust Layer features:
 * - Signal health monitoring
 * - Attribution variance tracking
 * - Combined trust status
 */

import { useQuery } from '@tanstack/react-query'
import { api } from './client'

// =============================================================================
// Types
// =============================================================================

export type SignalHealthStatus = 'ok' | 'risk' | 'degraded' | 'critical' | 'no_data'
export type AttributionVarianceStatus = 'healthy' | 'minor_variance' | 'moderate_variance' | 'high_variance' | 'no_data'

export interface MetricCard {
  title: string
  value: string
  status: 'ok' | 'risk' | 'degraded' | 'neutral'
  description?: string
}

export interface TrustBanner {
  type: 'info' | 'warning' | 'error'
  title: string
  message: string
  actions: string[]
}

export interface PlatformHealthRow {
  platform: string
  account_id?: string
  emq_score?: number
  event_loss_pct?: number
  freshness_minutes?: number
  api_error_rate?: number
  status: SignalHealthStatus
}

export interface SignalHealthData {
  date: string
  status: SignalHealthStatus
  automation_blocked: boolean
  cards: MetricCard[]
  platform_rows: PlatformHealthRow[]
  banners: TrustBanner[]
  issues: string[]
  actions: string[]
}

export interface PlatformVarianceRow {
  platform: string
  ga4_revenue: number
  platform_revenue: number
  revenue_delta_pct: number
  ga4_conversions: number
  platform_conversions: number
  conversion_delta_pct: number
  confidence: number
  status: AttributionVarianceStatus
}

export interface AttributionVarianceData {
  date: string
  status: AttributionVarianceStatus
  overall_revenue_variance_pct: number
  overall_conversion_variance_pct: number
  cards: MetricCard[]
  platform_rows: PlatformVarianceRow[]
  banners: TrustBanner[]
}

export interface TrustStatusData {
  date: string
  overall_status: SignalHealthStatus
  automation_allowed: boolean
  signal_health: SignalHealthData | null
  attribution_variance: AttributionVarianceData | null
  banners: TrustBanner[]
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
      const params = date ? `?date=${date}` : ''
      const response = await api.get<{ data: SignalHealthData }>(
        `/trust-layer/tenant/${tenantId}/signal-health${params}`
      )
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  })
}

/**
 * Fetch signal health history for trend analysis.
 */
export function useSignalHealthHistory(
  tenantId: number,
  days: number = 7,
  platform?: string
) {
  return useQuery({
    queryKey: ['signal-health-history', tenantId, days, platform],
    queryFn: async () => {
      const params = new URLSearchParams({ days: days.toString() })
      if (platform) params.append('platform', platform)

      const response = await api.get<{ data: { history: SignalHealthData[] } }>(
        `/trust-layer/tenant/${tenantId}/signal-health/history?${params}`
      )
      return response.data.data.history
    },
    enabled: !!tenantId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Fetch attribution variance data for a tenant.
 */
export function useAttributionVariance(tenantId: number, date?: string) {
  return useQuery({
    queryKey: ['attribution-variance', tenantId, date],
    queryFn: async () => {
      const params = date ? `?date=${date}` : ''
      const response = await api.get<{ data: AttributionVarianceData }>(
        `/trust-layer/tenant/${tenantId}/attribution-variance${params}`
      )
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  })
}

/**
 * Fetch combined trust status for a tenant.
 * This is the main endpoint for the Trust Layer banner.
 */
export function useTrustStatus(tenantId: number, date?: string) {
  return useQuery({
    queryKey: ['trust-status', tenantId, date],
    queryFn: async () => {
      const params = date ? `?date=${date}` : ''
      const response = await api.get<{ data: TrustStatusData }>(
        `/trust-layer/tenant/${tenantId}/trust-status${params}`
      )
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  })
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
  }
  return colors[status] || 'gray'
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
  }
  return labels[status] || status
}

/**
 * Get banner icon based on type.
 */
export function getBannerIcon(type: 'info' | 'warning' | 'error'): string {
  const icons: Record<string, string> = {
    info: 'ℹ️',
    warning: '⚠️',
    error: '🚨',
  }
  return icons[type] || 'ℹ️'
}
