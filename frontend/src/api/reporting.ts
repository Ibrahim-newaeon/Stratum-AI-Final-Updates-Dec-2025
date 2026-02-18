/**
 * Stratum AI - Automated Reporting API
 *
 * Handles report templates, scheduling, generation, and delivery.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// =============================================================================
// Types
// =============================================================================

export type ReportType = 'campaign_performance' | 'attribution_summary' | 'pacing_status' | 'profit_roas' | 'pipeline_metrics' | 'executive_summary' | 'custom'
export type ReportFormat = 'pdf' | 'csv' | 'excel' | 'json' | 'html'
export type ScheduleFrequency = 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'custom'
export type DeliveryChannel = 'email' | 'slack' | 'teams' | 'webhook' | 's3'
export type ExecutionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type DeliveryStatus = 'pending' | 'sent' | 'delivered' | 'failed' | 'bounced'

export interface ReportTemplate {
  id: string
  tenantId: number
  name: string
  description?: string
  reportType: ReportType
  config: ReportConfig
  defaultFormat: ReportFormat
  availableFormats: ReportFormat[]
  templateHtml?: string
  chartConfig?: Record<string, any>
  isActive: boolean
  isSystem: boolean
  createdAt: string
  updatedAt: string
}

export interface ReportConfig {
  metrics?: string[]
  dimensions?: string[]
  filters?: Record<string, any>
  dateRange?: { type: string; start?: string; end?: string }
  comparison?: { enabled: boolean; period: string }
  sections?: string[]
  branding?: { logoUrl?: string; primaryColor?: string }
}

export interface ScheduledReport {
  id: string
  tenantId: number
  templateId: string
  template?: ReportTemplate
  name: string
  description?: string
  frequency: ScheduleFrequency
  timezone: string
  dayOfWeek?: number
  dayOfMonth?: number
  hour: number
  minute: number
  cronExpression?: string
  formatOverride?: ReportFormat
  configOverride?: Record<string, any>
  dateRangeType: string
  deliveryChannels: DeliveryChannel[]
  deliveryConfig: DeliveryConfig
  isActive: boolean
  isPaused: boolean
  lastRunAt?: string
  lastRunStatus?: ExecutionStatus
  nextRunAt?: string
  runCount: number
  failureCount: number
  createdAt: string
  updatedAt: string
}

export interface DeliveryConfig {
  email?: {
    recipients: string[]
    cc?: string[]
    subjectTemplate?: string
    bodyTemplate?: string
  }
  slack?: {
    channel: string
    webhookUrl?: string
  }
  teams?: {
    webhookUrl: string
  }
  webhook?: {
    webhookUrl: string
    headers?: Record<string, string>
    authHeader?: string
  }
  s3?: {
    bucket: string
    prefix?: string
    region?: string
  }
}

export interface ReportExecution {
  id: string
  tenantId: number
  templateId?: string
  scheduleId?: string
  executionType: 'scheduled' | 'manual' | 'api'
  status: ExecutionStatus
  startedAt: string
  completedAt?: string
  durationSeconds?: number
  reportType: ReportType
  format: ReportFormat
  dateRangeStart: string
  dateRangeEnd: string
  configUsed?: Record<string, any>
  filePath?: string
  fileSizeBytes?: number
  fileUrl?: string
  fileUrlExpiresAt?: string
  rowCount?: number
  metricsSummary?: Record<string, any>
  errorMessage?: string
  errorDetails?: Record<string, any>
  triggeredByUserId?: number
}

export interface ReportDelivery {
  id: string
  executionId: string
  channel: DeliveryChannel
  recipient: string
  status: DeliveryStatus
  sentAt?: string
  deliveredAt?: string
  errorMessage?: string
  retryCount: number
}

export interface DeliveryChannelConfig {
  id: string
  tenantId: number
  channel: DeliveryChannel
  name: string
  isActive: boolean
  isVerified: boolean
  config: Record<string, any>
  createdAt: string
  updatedAt: string
}

export interface CreateTemplateRequest {
  name: string
  description?: string
  reportType: ReportType
  config?: ReportConfig
  defaultFormat?: ReportFormat
  availableFormats?: ReportFormat[]
  templateHtml?: string
  chartConfig?: Record<string, any>
}

export interface CreateScheduleRequest {
  templateId: string
  name: string
  description?: string
  frequency: ScheduleFrequency
  timezone?: string
  dayOfWeek?: number
  dayOfMonth?: number
  hour?: number
  minute?: number
  cronExpression?: string
  formatOverride?: ReportFormat
  configOverride?: Record<string, any>
  dateRangeType?: string
  deliveryChannels: DeliveryChannel[]
  deliveryConfig: DeliveryConfig
}

export interface GenerateReportRequest {
  templateId: string
  startDate: string
  endDate: string
  format?: ReportFormat
  configOverride?: Record<string, any>
  deliverTo?: DeliveryChannel[]
  deliveryConfig?: DeliveryConfig
}

export interface ReportTypeInfo {
  type: ReportType
  name: string
  description: string
  defaultMetrics?: string[]
  availableDimensions?: string[]
  availableModels?: string[]
  sections?: string[]
}

// =============================================================================
// API Functions
// =============================================================================

export const reportingApi = {
  // Templates
  getTemplates: async (params?: { reportType?: ReportType; isActive?: boolean }) => {
    const response = await apiClient.get<ApiResponse<ReportTemplate[]>>('/reporting/templates', { params })
    return response.data.data
  },

  getTemplate: async (templateId: string) => {
    const response = await apiClient.get<ApiResponse<ReportTemplate>>(`/reporting/templates/${templateId}`)
    return response.data.data
  },

  createTemplate: async (data: CreateTemplateRequest) => {
    const response = await apiClient.post<ApiResponse<ReportTemplate>>('/reporting/templates', data)
    return response.data.data
  },

  updateTemplate: async (templateId: string, data: Partial<CreateTemplateRequest>) => {
    const response = await apiClient.patch<ApiResponse<ReportTemplate>>(`/reporting/templates/${templateId}`, data)
    return response.data.data
  },

  deleteTemplate: async (templateId: string) => {
    const response = await apiClient.delete<ApiResponse<void>>(`/reporting/templates/${templateId}`)
    return response.data
  },

  // Schedules
  getSchedules: async (params?: { isActive?: boolean; templateId?: string }) => {
    const response = await apiClient.get<ApiResponse<ScheduledReport[]>>('/reporting/schedules', { params })
    return response.data.data
  },

  getSchedule: async (scheduleId: string) => {
    const response = await apiClient.get<ApiResponse<ScheduledReport>>(`/reporting/schedules/${scheduleId}`)
    return response.data.data
  },

  createSchedule: async (data: CreateScheduleRequest) => {
    const response = await apiClient.post<ApiResponse<ScheduledReport>>('/reporting/schedules', data)
    return response.data.data
  },

  updateSchedule: async (scheduleId: string, data: Partial<CreateScheduleRequest>) => {
    const response = await apiClient.patch<ApiResponse<ScheduledReport>>(`/reporting/schedules/${scheduleId}`, data)
    return response.data.data
  },

  deleteSchedule: async (scheduleId: string) => {
    const response = await apiClient.delete<ApiResponse<void>>(`/reporting/schedules/${scheduleId}`)
    return response.data
  },

  pauseSchedule: async (scheduleId: string) => {
    const response = await apiClient.post<ApiResponse<ScheduledReport>>(`/reporting/schedules/${scheduleId}/pause`)
    return response.data.data
  },

  resumeSchedule: async (scheduleId: string) => {
    const response = await apiClient.post<ApiResponse<ScheduledReport>>(`/reporting/schedules/${scheduleId}/resume`)
    return response.data.data
  },

  runScheduleNow: async (scheduleId: string) => {
    const response = await apiClient.post<ApiResponse<ReportExecution>>(`/reporting/schedules/${scheduleId}/run-now`)
    return response.data.data
  },

  getScheduleHistory: async (scheduleId: string, limit?: number) => {
    const response = await apiClient.get<ApiResponse<ReportExecution[]>>(`/reporting/schedules/${scheduleId}/history`, {
      params: { limit },
    })
    return response.data.data
  },

  // Report Generation
  generateReport: async (data: GenerateReportRequest) => {
    const response = await apiClient.post<ApiResponse<ReportExecution>>('/reporting/generate', data)
    return response.data.data
  },

  // Executions
  getExecutions: async (params?: {
    status?: ExecutionStatus
    reportType?: ReportType
    startDate?: string
    endDate?: string
    limit?: number
    offset?: number
  }) => {
    const response = await apiClient.get<ApiResponse<ReportExecution[]>>('/reporting/executions', { params })
    return response.data.data
  },

  getExecution: async (executionId: string) => {
    const response = await apiClient.get<ApiResponse<ReportExecution>>(`/reporting/executions/${executionId}`)
    return response.data.data
  },

  downloadReport: async (executionId: string) => {
    const response = await apiClient.get<ApiResponse<{
      downloadUrl: string
      expiresAt?: string
      format: ReportFormat
      fileSizeBytes?: number
    }>>(`/reporting/executions/${executionId}/download`)
    return response.data.data
  },

  // Deliveries
  getDeliveryStatus: async (executionId: string) => {
    const response = await apiClient.get<ApiResponse<ReportDelivery[]>>(`/reporting/executions/${executionId}/deliveries`)
    return response.data.data
  },

  retryDelivery: async (deliveryId: string) => {
    const response = await apiClient.post<ApiResponse<{ success: boolean; error?: string }>>(`/reporting/deliveries/${deliveryId}/retry`)
    return response.data.data
  },

  // Delivery Channel Configs
  getDeliveryChannelConfigs: async () => {
    const response = await apiClient.get<ApiResponse<DeliveryChannelConfig[]>>('/reporting/delivery-channels')
    return response.data.data
  },

  createDeliveryChannelConfig: async (data: { channel: DeliveryChannel; name: string; config: Record<string, any> }) => {
    const response = await apiClient.post<ApiResponse<DeliveryChannelConfig>>('/reporting/delivery-channels', data)
    return response.data.data
  },

  updateDeliveryChannelConfig: async (configId: string, data: Partial<DeliveryChannelConfig>) => {
    const response = await apiClient.patch<ApiResponse<DeliveryChannelConfig>>(`/reporting/delivery-channels/${configId}`, data)
    return response.data.data
  },

  deleteDeliveryChannelConfig: async (configId: string) => {
    const response = await apiClient.delete<ApiResponse<void>>(`/reporting/delivery-channels/${configId}`)
    return response.data
  },

  verifyDeliveryChannel: async (configId: string) => {
    const response = await apiClient.post<ApiResponse<{ verified: boolean; error?: string }>>(`/reporting/delivery-channels/${configId}/verify`)
    return response.data.data
  },

  // Report Types Info
  getReportTypes: async () => {
    const response = await apiClient.get<ApiResponse<{
      reportTypes: ReportTypeInfo[]
      formats: ReportFormat[]
      frequencies: ScheduleFrequency[]
      deliveryChannels: DeliveryChannel[]
      dateRangeTypes: string[]
    }>>('/reporting/report-types')
    return response.data.data
  },
}

// =============================================================================
// React Query Hooks
// =============================================================================

// Templates
export function useReportTemplates(params?: { reportType?: ReportType; isActive?: boolean }) {
  return useQuery({
    queryKey: ['reporting', 'templates', params],
    queryFn: () => reportingApi.getTemplates(params),
  })
}

export function useReportTemplate(templateId: string) {
  return useQuery({
    queryKey: ['reporting', 'templates', templateId],
    queryFn: () => reportingApi.getTemplate(templateId),
    enabled: !!templateId,
  })
}

export function useCreateReportTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.createTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'templates'] })
    },
  })
}

export function useUpdateReportTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ templateId, data }: { templateId: string; data: Partial<CreateTemplateRequest> }) =>
      reportingApi.updateTemplate(templateId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'templates'] })
    },
  })
}

export function useDeleteReportTemplate() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.deleteTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'templates'] })
    },
  })
}

// Schedules
export function useReportSchedules(params?: { isActive?: boolean; templateId?: string }) {
  return useQuery({
    queryKey: ['reporting', 'schedules', params],
    queryFn: () => reportingApi.getSchedules(params),
  })
}

export function useReportSchedule(scheduleId: string) {
  return useQuery({
    queryKey: ['reporting', 'schedules', scheduleId],
    queryFn: () => reportingApi.getSchedule(scheduleId),
    enabled: !!scheduleId,
  })
}

export function useCreateReportSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.createSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'schedules'] })
    },
  })
}

export function useUpdateReportSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ scheduleId, data }: { scheduleId: string; data: Partial<CreateScheduleRequest> }) =>
      reportingApi.updateSchedule(scheduleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'schedules'] })
    },
  })
}

export function useDeleteReportSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.deleteSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'schedules'] })
    },
  })
}

export function usePauseReportSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.pauseSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'schedules'] })
    },
  })
}

export function useResumeReportSchedule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.resumeSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'schedules'] })
    },
  })
}

export function useRunScheduleNow() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.runScheduleNow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'executions'] })
      queryClient.invalidateQueries({ queryKey: ['reporting', 'schedules'] })
    },
  })
}

export function useScheduleHistory(scheduleId: string, limit?: number) {
  return useQuery({
    queryKey: ['reporting', 'schedules', scheduleId, 'history', limit],
    queryFn: () => reportingApi.getScheduleHistory(scheduleId, limit),
    enabled: !!scheduleId,
  })
}

// Report Generation
export function useGenerateReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.generateReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'executions'] })
    },
  })
}

// Executions
export function useReportExecutions(params?: {
  status?: ExecutionStatus
  reportType?: ReportType
  startDate?: string
  endDate?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['reporting', 'executions', params],
    queryFn: () => reportingApi.getExecutions(params),
  })
}

export function useReportExecution(executionId: string) {
  return useQuery({
    queryKey: ['reporting', 'executions', executionId],
    queryFn: () => reportingApi.getExecution(executionId),
    enabled: !!executionId,
  })
}

export function useDownloadReport(executionId: string) {
  return useQuery({
    queryKey: ['reporting', 'executions', executionId, 'download'],
    queryFn: () => reportingApi.downloadReport(executionId),
    enabled: !!executionId,
  })
}

// Deliveries
export function useDeliveryStatus(executionId: string) {
  return useQuery({
    queryKey: ['reporting', 'executions', executionId, 'deliveries'],
    queryFn: () => reportingApi.getDeliveryStatus(executionId),
    enabled: !!executionId,
  })
}

export function useRetryDelivery() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.retryDelivery,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'executions'] })
    },
  })
}

// Delivery Channel Configs
export function useDeliveryChannelConfigs() {
  return useQuery({
    queryKey: ['reporting', 'delivery-channels'],
    queryFn: reportingApi.getDeliveryChannelConfigs,
  })
}

export function useCreateDeliveryChannelConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.createDeliveryChannelConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'delivery-channels'] })
    },
  })
}

export function useUpdateDeliveryChannelConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ configId, data }: { configId: string; data: Partial<DeliveryChannelConfig> }) =>
      reportingApi.updateDeliveryChannelConfig(configId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'delivery-channels'] })
    },
  })
}

export function useDeleteDeliveryChannelConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.deleteDeliveryChannelConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'delivery-channels'] })
    },
  })
}

export function useVerifyDeliveryChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: reportingApi.verifyDeliveryChannel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reporting', 'delivery-channels'] })
    },
  })
}

// Report Types Info
export function useReportTypes() {
  return useQuery({
    queryKey: ['reporting', 'report-types'],
    queryFn: reportingApi.getReportTypes,
    staleTime: Infinity, // This data rarely changes
  })
}
