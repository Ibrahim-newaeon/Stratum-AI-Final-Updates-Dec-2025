/**
 * Stratum AI - Insights API Hooks
 *
 * React Query hooks for Intelligence Layer features:
 * - Insights (aggregated daily view)
 * - Recommendations
 * - Anomaly alerts
 * - KPIs
 */

import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'

// =============================================================================
// Types
// =============================================================================

export interface AutopilotStatus {
  level: number
  level_name: string
  blocked: boolean
  reason: string | null
}

export interface ActionRecommendation {
  type: string
  priority: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  description: string
  entity_id?: string
  entity_name?: string
  entity_type?: string
  expected_impact?: Record<string, unknown>
  action_params?: Record<string, unknown>
  confidence?: number
  guardrails?: {
    max_budget_change_pct: number
    max_daily_budget_change: number
    requires_approval: boolean
  }
}

export interface RiskAlert {
  type: string
  severity: string
  message: string
  metric?: string
  current_value?: number
  baseline?: number
}

export interface Opportunity {
  type: string
  entity_id?: string
  entity_name?: string
  title: string
  score?: number
  recommendations?: string[]
}

export interface InsightsData {
  date: string
  kpis: {
    total_spend: number
    total_revenue: number
    roas: number
    cpa: number
    trend_vs_yesterday: number
    trend_vs_last_week: number
  }
  actions: ActionRecommendation[]
  risks: RiskAlert[]
  opportunities: Opportunity[]
  autopilot: AutopilotStatus
  signal_health_status: string
  scaling_summary: {
    scale_candidates: number
    fix_candidates: number
    watch_candidates: number
  }
}

export interface RecommendationsData {
  date: string
  recommendations: ActionRecommendation[]
  total: number
  filters_applied: {
    entity_type: string | null
    priority: string | null
  }
}

export interface Anomaly {
  id: string
  detected_at: string
  metric: string
  entity_type: string
  entity_id: string
  entity_name: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  direction: 'spike' | 'drop'
  current_value: number
  expected_value: number
  zscore: number
  description: string
  possible_causes: string[]
  recommended_actions: string[]
}

export interface AnomaliesData {
  date: string
  lookback_days: number
  anomalies: Anomaly[]
  total: number
  by_severity: {
    critical: number
    high: number
    medium: number
    low: number
  }
}

export interface MetricTrend {
  value: number
  previous: number
  change_pct: number
  trend: 'up' | 'down' | 'neutral'
}

export interface KPIsData {
  date: string
  comparison_date: string
  comparison_type: string
  metrics: {
    spend: MetricTrend
    revenue: MetricTrend
    roas: MetricTrend
    cpa: MetricTrend
    conversions: MetricTrend
    ctr: MetricTrend
  }
  by_platform: Record<string, unknown>
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Fetch insights for a tenant.
 */
export function useInsights(tenantId: number, date?: string) {
  return useQuery({
    queryKey: ['insights', tenantId, date],
    queryFn: async () => {
      const params = date ? `?date=${date}` : ''
      const response = await apiClient.get<{ data: InsightsData }>(
        `/insights/tenant/${tenantId}/insights${params}`
      )
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  })
}

/**
 * Fetch detailed recommendations.
 */
export function useRecommendations(
  tenantId: number,
  options?: {
    date?: string
    entity_type?: string
    priority?: string
    limit?: number
  }
) {
  return useQuery({
    queryKey: ['recommendations', tenantId, options],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (options?.date) params.append('date', options.date)
      if (options?.entity_type) params.append('entity_type', options.entity_type)
      if (options?.priority) params.append('priority', options.priority)
      if (options?.limit) params.append('limit', options.limit.toString())

      const response = await apiClient.get<{ data: RecommendationsData }>(
        `/insights/tenant/${tenantId}/recommendations?${params}`
      )
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000,
  })
}

/**
 * Fetch anomaly alerts.
 */
export function useAnomalies(
  tenantId: number,
  options?: {
    date?: string
    days?: number
    severity?: string
  }
) {
  return useQuery({
    queryKey: ['anomalies', tenantId, options],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (options?.date) params.append('date', options.date)
      if (options?.days) params.append('days', options.days.toString())
      if (options?.severity) params.append('severity', options.severity)

      const response = await apiClient.get<{ data: AnomaliesData }>(
        `/insights/tenant/${tenantId}/anomalies?${params}`
      )
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000,
  })
}

/**
 * Fetch KPIs with trends.
 */
export function useKPIs(
  tenantId: number,
  options?: {
    date?: string
    comparison?: 'yesterday' | 'last_week' | 'last_month'
  }
) {
  return useQuery({
    queryKey: ['kpis', tenantId, options],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (options?.date) params.append('date', options.date)
      if (options?.comparison) params.append('comparison', options.comparison)

      const response = await apiClient.get<{ data: KPIsData }>(
        `/insights/tenant/${tenantId}/kpis?${params}`
      )
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000,
  })
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get priority color.
 */
export function getPriorityColor(priority: string): string {
  const colors: Record<string, string> = {
    critical: 'red',
    high: 'orange',
    medium: 'yellow',
    low: 'blue',
    info: 'gray',
  }
  return colors[priority] || 'gray'
}

/**
 * Get priority label.
 */
export function getPriorityLabel(priority: string): string {
  const labels: Record<string, string> = {
    critical: 'Critical',
    high: 'High Priority',
    medium: 'Medium Priority',
    low: 'Low Priority',
    info: 'Info',
  }
  return labels[priority] || priority
}

/**
 * Get action type icon.
 */
export function getActionTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    budget_shift: '💰',
    creative_refresh: '🎨',
    fix_campaign: '🔧',
    anomaly_investigation: '🔍',
    signal_health: '📊',
    scaling_opportunity: '📈',
  }
  return icons[type] || '📋'
}

/**
 * Get trend icon.
 */
export function getTrendIcon(trend: string): string {
  const icons: Record<string, string> = {
    up: '📈',
    down: '📉',
    neutral: '➡️',
  }
  return icons[trend] || '➡️'
}

/**
 * Format currency.
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

/**
 * Format percentage.
 */
export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`
}
