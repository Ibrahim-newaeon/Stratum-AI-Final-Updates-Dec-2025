/**
 * Stratum AI - Pacing & Forecasting API
 *
 * Handles targets, pacing calculations, forecasts, and alerts.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// =============================================================================
// Types
// =============================================================================

export type TargetPeriod = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly' | 'custom'
export type TargetMetric = 'spend' | 'revenue' | 'roas' | 'conversions' | 'cpa' | 'ctr' | 'impressions' | 'clicks'
export type AlertSeverity = 'info' | 'warning' | 'critical'
export type AlertType = 'underpacing' | 'overpacing' | 'target_at_risk' | 'target_missed' | 'target_exceeded'
export type AlertStatus = 'active' | 'acknowledged' | 'resolved' | 'dismissed'

export interface Target {
  id: string
  tenantId: number
  name: string
  description?: string
  metricType: TargetMetric
  targetValue: number
  periodType: TargetPeriod
  periodStart: string
  periodEnd: string
  platform?: string
  campaignId?: string
  minValue?: number
  maxValue?: number
  warningThresholdPct: number
  criticalThresholdPct: number
  isActive: boolean
  notifySlack: boolean
  notifyEmail: boolean
  notifyWhatsapp: boolean
  notificationRecipients: string[]
  createdAt: string
  updatedAt: string
}

export interface DailyKPI {
  id: string
  tenantId: number
  date: string
  platform?: string
  campaignId?: string
  spend: number
  revenue: number
  conversions: number
  impressions: number
  clicks: number
  roas: number
  cpa: number
  ctr: number
}

export interface PacingStatus {
  targetId: string
  targetName: string
  metricType: TargetMetric
  targetValue: number
  currentValue: number
  pacingPct: number
  projectedValue: number
  projectedPct: number
  daysRemaining: number
  daysElapsed: number
  dailyTarget: number
  dailyActual: number
  status: 'on_track' | 'ahead' | 'behind' | 'at_risk' | 'missed'
  trend: 'improving' | 'declining' | 'stable'
}

export interface PacingAlert {
  id: string
  tenantId: number
  targetId: string
  target?: Target
  alertType: AlertType
  severity: AlertSeverity
  status: AlertStatus
  message: string
  currentValue: number
  expectedValue: number
  deviationPct: number
  triggeredAt: string
  acknowledgedAt?: string
  resolvedAt?: string
  acknowledgedBy?: string
  resolvedBy?: string
  notes?: string
}

export interface Forecast {
  id: string
  tenantId: number
  targetId?: string
  metricType: TargetMetric
  platform?: string
  campaignId?: string
  forecastDate: string
  generatedAt: string
  horizon: number
  predictions: ForecastPrediction[]
  modelType: string
  accuracy?: number
  confidenceLevel: number
}

export interface ForecastPrediction {
  date: string
  predicted: number
  lowerBound: number
  upperBound: number
  confidencePct: number
}

export interface PacingSummary {
  id: string
  tenantId: number
  date: string
  period: TargetPeriod
  totalTargets: number
  onTrack: number
  ahead: number
  behind: number
  atRisk: number
  missed: number
  overallHealthScore: number
  topPerformers: string[]
  needsAttention: string[]
}

export interface CreateTargetRequest {
  name: string
  description?: string
  metricType: TargetMetric
  targetValue: number
  periodType: TargetPeriod
  periodStart: string
  periodEnd: string
  platform?: string
  campaignId?: string
  minValue?: number
  maxValue?: number
  warningThresholdPct?: number
  criticalThresholdPct?: number
  notifySlack?: boolean
  notifyEmail?: boolean
  notifyWhatsapp?: boolean
  notificationRecipients?: string[]
}

// =============================================================================
// API Functions
// =============================================================================

export const pacingApi = {
  // Targets
  getTargets: async (params?: { isActive?: boolean; metricType?: TargetMetric; periodType?: TargetPeriod }) => {
    const response = await apiClient.get<ApiResponse<Target[]>>('/pacing/targets', { params })
    return response.data.data
  },

  getTarget: async (targetId: string) => {
    const response = await apiClient.get<ApiResponse<Target>>(`/pacing/targets/${targetId}`)
    return response.data.data
  },

  createTarget: async (data: CreateTargetRequest) => {
    const response = await apiClient.post<ApiResponse<Target>>('/pacing/targets', data)
    return response.data.data
  },

  updateTarget: async (targetId: string, data: Partial<CreateTargetRequest>) => {
    const response = await apiClient.patch<ApiResponse<Target>>(`/pacing/targets/${targetId}`, data)
    return response.data.data
  },

  deleteTarget: async (targetId: string) => {
    const response = await apiClient.delete<ApiResponse<void>>(`/pacing/targets/${targetId}`)
    return response.data
  },

  // Pacing
  getPacingStatus: async (targetId: string) => {
    const response = await apiClient.get<ApiResponse<PacingStatus>>(`/pacing/targets/${targetId}/pacing`)
    return response.data.data
  },

  getAllPacingStatus: async () => {
    const response = await apiClient.get<ApiResponse<PacingStatus[]>>('/pacing/status')
    return response.data.data
  },

  getPacingSummary: async (period?: TargetPeriod) => {
    const response = await apiClient.get<ApiResponse<PacingSummary>>('/pacing/summary', { params: { period } })
    return response.data.data
  },

  // Daily KPIs
  getDailyKPIs: async (params: { startDate: string; endDate: string; platform?: string; campaignId?: string }) => {
    const response = await apiClient.get<ApiResponse<DailyKPI[]>>('/pacing/kpis/daily', { params })
    return response.data.data
  },

  // Forecasts
  getForecast: async (targetId: string, horizon?: number) => {
    const response = await apiClient.get<ApiResponse<Forecast>>(`/pacing/targets/${targetId}/forecast`, {
      params: { horizon },
    })
    return response.data.data
  },

  getMetricForecast: async (params: { metricType: TargetMetric; platform?: string; horizon?: number }) => {
    const response = await apiClient.get<ApiResponse<Forecast>>('/pacing/forecast', { params })
    return response.data.data
  },

  generateForecast: async (targetId: string, horizon?: number) => {
    const response = await apiClient.post<ApiResponse<Forecast>>(`/pacing/targets/${targetId}/forecast/generate`, {
      horizon,
    })
    return response.data.data
  },

  // Alerts
  getAlerts: async (params?: { status?: AlertStatus; severity?: AlertSeverity; targetId?: string }) => {
    const response = await apiClient.get<ApiResponse<PacingAlert[]>>('/pacing/alerts', { params })
    return response.data.data
  },

  getAlert: async (alertId: string) => {
    const response = await apiClient.get<ApiResponse<PacingAlert>>(`/pacing/alerts/${alertId}`)
    return response.data.data
  },

  acknowledgeAlert: async (alertId: string, notes?: string) => {
    const response = await apiClient.post<ApiResponse<PacingAlert>>(`/pacing/alerts/${alertId}/acknowledge`, { notes })
    return response.data.data
  },

  resolveAlert: async (alertId: string, notes?: string) => {
    const response = await apiClient.post<ApiResponse<PacingAlert>>(`/pacing/alerts/${alertId}/resolve`, { notes })
    return response.data.data
  },

  dismissAlert: async (alertId: string, notes?: string) => {
    const response = await apiClient.post<ApiResponse<PacingAlert>>(`/pacing/alerts/${alertId}/dismiss`, { notes })
    return response.data.data
  },

  getAlertStats: async () => {
    const response = await apiClient.get<ApiResponse<{
      total: number
      active: number
      acknowledged: number
      bySeverity: Record<AlertSeverity, number>
      byType: Record<AlertType, number>
    }>>('/pacing/alerts/stats')
    return response.data.data
  },
}

// =============================================================================
// React Query Hooks
// =============================================================================

// Targets
export function useTargets(params?: { isActive?: boolean; metricType?: TargetMetric; periodType?: TargetPeriod }) {
  return useQuery({
    queryKey: ['pacing', 'targets', params],
    queryFn: () => pacingApi.getTargets(params),
  })
}

export function useTarget(targetId: string) {
  return useQuery({
    queryKey: ['pacing', 'targets', targetId],
    queryFn: () => pacingApi.getTarget(targetId),
    enabled: !!targetId,
  })
}

export function useCreateTarget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: pacingApi.createTarget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pacing', 'targets'] })
    },
  })
}

export function useUpdateTarget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ targetId, data }: { targetId: string; data: Partial<CreateTargetRequest> }) =>
      pacingApi.updateTarget(targetId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pacing', 'targets'] })
    },
  })
}

export function useDeleteTarget() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: pacingApi.deleteTarget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pacing', 'targets'] })
    },
  })
}

// Pacing
export function usePacingStatus(targetId: string) {
  return useQuery({
    queryKey: ['pacing', 'status', targetId],
    queryFn: () => pacingApi.getPacingStatus(targetId),
    enabled: !!targetId,
    refetchInterval: 60000, // Refresh every minute
  })
}

export function useAllPacingStatus() {
  return useQuery({
    queryKey: ['pacing', 'status', 'all'],
    queryFn: pacingApi.getAllPacingStatus,
    refetchInterval: 60000,
  })
}

export function usePacingSummary(period?: TargetPeriod) {
  return useQuery({
    queryKey: ['pacing', 'summary', period],
    queryFn: () => pacingApi.getPacingSummary(period),
    refetchInterval: 60000,
  })
}

// Daily KPIs
export function useDailyKPIs(params: { startDate: string; endDate: string; platform?: string; campaignId?: string }) {
  return useQuery({
    queryKey: ['pacing', 'kpis', 'daily', params],
    queryFn: () => pacingApi.getDailyKPIs(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

// Forecasts
export function useForecast(targetId: string, horizon?: number) {
  return useQuery({
    queryKey: ['pacing', 'forecast', targetId, horizon],
    queryFn: () => pacingApi.getForecast(targetId, horizon),
    enabled: !!targetId,
  })
}

export function useMetricForecast(params: { metricType: TargetMetric; platform?: string; horizon?: number }) {
  return useQuery({
    queryKey: ['pacing', 'forecast', 'metric', params],
    queryFn: () => pacingApi.getMetricForecast(params),
  })
}

export function useGenerateForecast() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ targetId, horizon }: { targetId: string; horizon?: number }) =>
      pacingApi.generateForecast(targetId, horizon),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pacing', 'forecast'] })
    },
  })
}

// Alerts
export function usePacingAlerts(params?: { status?: AlertStatus; severity?: AlertSeverity; targetId?: string }) {
  return useQuery({
    queryKey: ['pacing', 'alerts', params],
    queryFn: () => pacingApi.getAlerts(params),
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

export function usePacingAlert(alertId: string) {
  return useQuery({
    queryKey: ['pacing', 'alerts', alertId],
    queryFn: () => pacingApi.getAlert(alertId),
    enabled: !!alertId,
  })
}

export function useAcknowledgeAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ alertId, notes }: { alertId: string; notes?: string }) =>
      pacingApi.acknowledgeAlert(alertId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pacing', 'alerts'] })
    },
  })
}

export function useResolveAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ alertId, notes }: { alertId: string; notes?: string }) =>
      pacingApi.resolveAlert(alertId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pacing', 'alerts'] })
    },
  })
}

export function useDismissAlert() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ alertId, notes }: { alertId: string; notes?: string }) =>
      pacingApi.dismissAlert(alertId, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pacing', 'alerts'] })
    },
  })
}

export function useAlertStats() {
  return useQuery({
    queryKey: ['pacing', 'alerts', 'stats'],
    queryFn: pacingApi.getAlertStats,
    refetchInterval: 30000,
  })
}
