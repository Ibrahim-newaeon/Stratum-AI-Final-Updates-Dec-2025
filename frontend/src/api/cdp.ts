/**
 * Stratum AI - CDP (Customer Data Platform) API Client
 *
 * API client with TypeScript types and React Query hooks for CDP endpoints.
 * Handles event ingestion, profile lookups, and source management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// =============================================================================
// TypeScript Types
// =============================================================================

// Identifier Types
export type IdentifierType = 'email' | 'phone' | 'device_id' | 'anonymous_id' | 'external_id'

export interface IdentifierInput {
  type: IdentifierType
  value: string
}

export interface Identifier {
  id: string
  identifier_type: IdentifierType
  identifier_value?: string
  identifier_hash: string
  is_primary: boolean
  confidence_score: number
  verified_at?: string
  first_seen_at: string
  last_seen_at: string
}

// Event Types
export interface EventContext {
  user_agent?: string
  ip?: string
  locale?: string
  timezone?: string
  screen?: { width: number; height: number }
  campaign?: Record<string, string>
}

export interface EventConsent {
  analytics?: boolean
  ads?: boolean
  email?: boolean
  sms?: boolean
}

export interface EventInput {
  event_name: string
  event_time: string
  idempotency_key?: string
  identifiers: IdentifierInput[]
  properties?: Record<string, unknown>
  context?: EventContext
  consent?: EventConsent
}

export interface EventBatchInput {
  events: EventInput[]
}

export interface EventIngestResult {
  event_id?: string
  status: 'accepted' | 'rejected' | 'duplicate'
  profile_id?: string
  error?: string
}

export interface EventBatchResponse {
  accepted: number
  rejected: number
  duplicates: number
  results: EventIngestResult[]
}

export interface CDPEvent {
  id: string
  event_name: string
  event_time: string
  received_at: string
  properties: Record<string, unknown>
  context: Record<string, unknown>
  emq_score?: number
  processed: boolean
}

// Profile Types
export type LifecycleStage = 'anonymous' | 'known' | 'customer' | 'churned'

export interface CDPProfile {
  id: string
  tenant_id: number
  external_id?: string
  first_seen_at: string
  last_seen_at: string
  profile_data: Record<string, unknown>
  computed_traits: Record<string, unknown>
  lifecycle_stage: LifecycleStage
  total_events: number
  total_sessions: number
  total_purchases: number
  total_revenue: number
  identifiers: Identifier[]
  created_at: string
  updated_at: string
}

export interface ProfileListResponse {
  profiles: CDPProfile[]
  total: number
  page: number
  page_size: number
}

// Source Types
export type SourceType = 'website' | 'server' | 'sgtm' | 'import' | 'crm'

export interface SourceCreate {
  name: string
  source_type: SourceType
  config?: Record<string, unknown>
}

export interface CDPSource {
  id: string
  name: string
  source_type: SourceType
  source_key: string
  config: Record<string, unknown>
  is_active: boolean
  event_count: number
  last_event_at?: string
  created_at: string
  updated_at: string
}

export interface SourceListResponse {
  sources: CDPSource[]
  total: number
}

// Consent Types
export type ConsentType = 'analytics' | 'ads' | 'email' | 'sms' | 'all'

export interface ConsentUpdate {
  consent_type: ConsentType
  granted: boolean
  source?: string
  consent_text?: string
  consent_version?: string
}

export interface CDPConsent {
  id: string
  consent_type: ConsentType
  granted: boolean
  granted_at?: string
  revoked_at?: string
  source?: string
  consent_version?: string
  created_at: string
  updated_at: string
}

// EMQ Score Types
export interface EMQScore {
  overall_score: number
  identifier_quality: number
  data_completeness: number
  timeliness: number
  context_richness: number
}

// Health Check Response
export interface CDPHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  module: string
  version: string
}

// Webhook Types
export type WebhookEventType =
  | 'event.received'
  | 'profile.created'
  | 'profile.updated'
  | 'profile.merged'
  | 'consent.updated'
  | 'all'

export interface WebhookCreate {
  name: string
  url: string
  event_types: WebhookEventType[]
  max_retries?: number
  timeout_seconds?: number
}

export interface WebhookUpdate {
  name?: string
  url?: string
  event_types?: WebhookEventType[]
  is_active?: boolean
  max_retries?: number
  timeout_seconds?: number
}

export interface CDPWebhook {
  id: string
  name: string
  url: string
  event_types: WebhookEventType[]
  secret_key?: string // Only returned on create/rotate
  is_active: boolean
  last_triggered_at?: string
  last_success_at?: string
  last_failure_at?: string
  failure_count: number
  max_retries: number
  timeout_seconds: number
  created_at: string
  updated_at: string
}

export interface WebhookListResponse {
  webhooks: CDPWebhook[]
  total: number
}

export interface WebhookTestResult {
  success: boolean
  status_code?: number
  response_time_ms?: number
  error?: string
}

// Anomaly Detection Types
export type AnomalySeverity = 'low' | 'medium' | 'high' | 'critical'
export type AnomalyDirection = 'high' | 'low'

export interface EventAnomaly {
  source_id?: string
  source_name: string
  metric: string
  zscore: number
  severity: AnomalySeverity
  current_value: number
  baseline_mean: number
  baseline_std: number
  direction: AnomalyDirection
  pct_change: number
}

export interface AnomalyDetectionResponse {
  anomalies: EventAnomaly[]
  anomaly_count: number
  has_critical: boolean
  has_high: boolean
  analysis_period_days: number
  zscore_threshold: number
  total_sources_analyzed: number
}

export interface AnomalyDetectionParams {
  window_days?: number
  zscore_threshold?: number
}

export type HealthStatus = 'healthy' | 'fair' | 'degraded' | 'critical' | 'unknown'
export type VolumeTrend = 'increasing' | 'stable' | 'decreasing'

export interface AnomalySummaryResponse {
  health_status: HealthStatus
  events_today: number
  events_7d: number
  events_prev_7d: number
  wow_change_pct: number
  volume_trend: VolumeTrend
  avg_emq_score?: number
  as_of: string
}

// Export Types
export type ExportFormat = 'json' | 'csv'

export interface ExportProfilesParams {
  format?: ExportFormat
  limit?: number
  offset?: number
}

export interface ExportEventsParams {
  format?: ExportFormat
  limit?: number
  offset?: number
  start_date?: string
  end_date?: string
  event_name?: string
}

export interface ExportResponse<T> {
  format: string
  count: number
  offset: number
  limit: number
  data: T[]
  filters?: Record<string, string | null>
}

// =============================================================================
// API Functions
// =============================================================================

export const cdpApi = {
  // Event Endpoints
  /**
   * Ingest events into CDP
   * @param events Array of events to ingest
   * @param sourceKey Optional source API key for authentication
   */
  ingestEvents: async (
    events: EventInput[],
    sourceKey?: string
  ): Promise<EventBatchResponse> => {
    const params = sourceKey ? { source_key: sourceKey } : {}
    const response = await apiClient.post<ApiResponse<EventBatchResponse>>(
      '/cdp/events',
      { events },
      { params }
    )
    return response.data.data
  },

  /**
   * Ingest a single event
   * @param event Event to ingest
   * @param sourceKey Optional source API key
   */
  ingestEvent: async (
    event: EventInput,
    sourceKey?: string
  ): Promise<EventIngestResult> => {
    const response = await cdpApi.ingestEvents([event], sourceKey)
    return response.results[0]
  },

  // Profile Endpoints
  /**
   * Get a profile by ID
   * @param profileId UUID of the profile
   */
  getProfile: async (profileId: string): Promise<CDPProfile> => {
    const response = await apiClient.get<ApiResponse<CDPProfile>>(
      `/cdp/profiles/${profileId}`
    )
    return response.data.data
  },

  /**
   * Lookup a profile by identifier
   * @param identifierType Type of identifier (email, phone, etc.)
   * @param identifierValue Value to look up
   */
  lookupProfile: async (
    identifierType: IdentifierType,
    identifierValue: string
  ): Promise<CDPProfile> => {
    const response = await apiClient.get<ApiResponse<CDPProfile>>(
      '/cdp/profiles',
      {
        params: {
          identifier_type: identifierType,
          identifier_value: identifierValue,
        },
      }
    )
    return response.data.data
  },

  // Source Endpoints
  /**
   * List all data sources
   */
  listSources: async (): Promise<SourceListResponse> => {
    const response = await apiClient.get<ApiResponse<SourceListResponse>>(
      '/cdp/sources'
    )
    return response.data.data
  },

  /**
   * Create a new data source
   * @param source Source configuration
   */
  createSource: async (source: SourceCreate): Promise<CDPSource> => {
    const response = await apiClient.post<ApiResponse<CDPSource>>(
      '/cdp/sources',
      source
    )
    return response.data.data
  },

  // Health Check
  /**
   * Check CDP module health
   */
  health: async (): Promise<CDPHealthResponse> => {
    const response = await apiClient.get<CDPHealthResponse>('/cdp/health')
    return response.data
  },

  // Webhook Endpoints
  /**
   * List all webhooks
   */
  listWebhooks: async (): Promise<WebhookListResponse> => {
    const response = await apiClient.get<ApiResponse<WebhookListResponse>>(
      '/cdp/webhooks'
    )
    return response.data.data
  },

  /**
   * Create a new webhook
   * @param webhook Webhook configuration
   */
  createWebhook: async (webhook: WebhookCreate): Promise<CDPWebhook> => {
    const response = await apiClient.post<ApiResponse<CDPWebhook>>(
      '/cdp/webhooks',
      webhook
    )
    return response.data.data
  },

  /**
   * Get a webhook by ID
   * @param webhookId UUID of the webhook
   */
  getWebhook: async (webhookId: string): Promise<CDPWebhook> => {
    const response = await apiClient.get<ApiResponse<CDPWebhook>>(
      `/cdp/webhooks/${webhookId}`
    )
    return response.data.data
  },

  /**
   * Update a webhook
   * @param webhookId UUID of the webhook
   * @param update Fields to update
   */
  updateWebhook: async (
    webhookId: string,
    update: WebhookUpdate
  ): Promise<CDPWebhook> => {
    const response = await apiClient.patch<ApiResponse<CDPWebhook>>(
      `/cdp/webhooks/${webhookId}`,
      update
    )
    return response.data.data
  },

  /**
   * Delete a webhook
   * @param webhookId UUID of the webhook
   */
  deleteWebhook: async (webhookId: string): Promise<void> => {
    await apiClient.delete(`/cdp/webhooks/${webhookId}`)
  },

  /**
   * Test a webhook
   * @param webhookId UUID of the webhook
   */
  testWebhook: async (webhookId: string): Promise<WebhookTestResult> => {
    const response = await apiClient.post<ApiResponse<WebhookTestResult>>(
      `/cdp/webhooks/${webhookId}/test`
    )
    return response.data.data
  },

  /**
   * Rotate webhook secret
   * @param webhookId UUID of the webhook
   */
  rotateWebhookSecret: async (webhookId: string): Promise<CDPWebhook> => {
    const response = await apiClient.post<ApiResponse<CDPWebhook>>(
      `/cdp/webhooks/${webhookId}/rotate-secret`
    )
    return response.data.data
  },

  // Anomaly Detection Endpoints
  /**
   * Detect event volume anomalies
   * @param params Optional parameters for analysis
   */
  detectEventAnomalies: async (
    params?: AnomalyDetectionParams
  ): Promise<AnomalyDetectionResponse> => {
    const response = await apiClient.get<AnomalyDetectionResponse>(
      '/cdp/anomalies/events',
      { params }
    )
    return response.data
  },

  /**
   * Get anomaly detection summary
   */
  getAnomalySummary: async (): Promise<AnomalySummaryResponse> => {
    const response = await apiClient.get<AnomalySummaryResponse>(
      '/cdp/anomalies/summary'
    )
    return response.data
  },

  // Export Endpoints
  /**
   * Export profiles in JSON or CSV format
   * @param params Export parameters (format, limit, offset)
   */
  exportProfiles: async (
    params?: ExportProfilesParams
  ): Promise<ExportResponse<CDPProfile> | Blob> => {
    const format = params?.format || 'json'

    if (format === 'csv') {
      const response = await apiClient.get('/cdp/export/profiles', {
        params: { ...params, format: 'csv' },
        responseType: 'blob',
      })
      return response.data
    }

    const response = await apiClient.get<ExportResponse<CDPProfile>>(
      '/cdp/export/profiles',
      { params }
    )
    return response.data
  },

  /**
   * Export events in JSON or CSV format
   * @param params Export parameters (format, limit, offset, date filters)
   */
  exportEvents: async (
    params?: ExportEventsParams
  ): Promise<ExportResponse<CDPEvent> | Blob> => {
    const format = params?.format || 'json'

    if (format === 'csv') {
      const response = await apiClient.get('/cdp/export/events', {
        params: { ...params, format: 'csv' },
        responseType: 'blob',
      })
      return response.data
    }

    const response = await apiClient.get<ExportResponse<CDPEvent>>(
      '/cdp/export/events',
      { params }
    )
    return response.data
  },
}

// =============================================================================
// React Query Hooks
// =============================================================================

// Query Keys
export const cdpQueryKeys = {
  all: ['cdp'] as const,
  profiles: () => [...cdpQueryKeys.all, 'profiles'] as const,
  profile: (id: string) => [...cdpQueryKeys.profiles(), id] as const,
  profileByIdentifier: (type: IdentifierType, value: string) =>
    [...cdpQueryKeys.profiles(), 'lookup', type, value] as const,
  sources: () => [...cdpQueryKeys.all, 'sources'] as const,
  health: () => [...cdpQueryKeys.all, 'health'] as const,
  webhooks: () => [...cdpQueryKeys.all, 'webhooks'] as const,
  webhook: (id: string) => [...cdpQueryKeys.webhooks(), id] as const,
  anomalies: () => [...cdpQueryKeys.all, 'anomalies'] as const,
  anomalySummary: () => [...cdpQueryKeys.anomalies(), 'summary'] as const,
}

/**
 * Hook to get a profile by ID
 */
export function useCDPProfile(profileId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.profile(profileId),
    queryFn: () => cdpApi.getProfile(profileId),
    staleTime: 30 * 1000, // 30 seconds
    enabled: options?.enabled ?? !!profileId,
  })
}

/**
 * Hook to lookup a profile by identifier
 */
export function useCDPProfileLookup(
  identifierType: IdentifierType,
  identifierValue: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: cdpQueryKeys.profileByIdentifier(identifierType, identifierValue),
    queryFn: () => cdpApi.lookupProfile(identifierType, identifierValue),
    staleTime: 30 * 1000,
    enabled: options?.enabled ?? (!!identifierType && !!identifierValue),
    retry: false, // Don't retry 404s
  })
}

/**
 * Hook to list all data sources
 */
export function useCDPSources() {
  return useQuery({
    queryKey: cdpQueryKeys.sources(),
    queryFn: () => cdpApi.listSources(),
    staleTime: 60 * 1000, // 1 minute
  })
}

/**
 * Hook to ingest events
 */
export function useIngestEvents(options?: { sourceKey?: string }) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (events: EventInput[]) =>
      cdpApi.ingestEvents(events, options?.sourceKey),
    onSuccess: () => {
      // Invalidate profiles as they may have been updated
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profiles() })
    },
  })
}

/**
 * Hook to ingest a single event
 */
export function useIngestEvent(options?: { sourceKey?: string }) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (event: EventInput) =>
      cdpApi.ingestEvent(event, options?.sourceKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profiles() })
    },
  })
}

/**
 * Hook to create a new data source
 */
export function useCreateSource() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (source: SourceCreate) => cdpApi.createSource(source),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.sources() })
    },
  })
}

/**
 * Hook to check CDP health
 */
export function useCDPHealth() {
  return useQuery({
    queryKey: cdpQueryKeys.health(),
    queryFn: () => cdpApi.health(),
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000, // Every 5 minutes
  })
}

/**
 * Hook to list all webhooks
 */
export function useCDPWebhooks() {
  return useQuery({
    queryKey: cdpQueryKeys.webhooks(),
    queryFn: () => cdpApi.listWebhooks(),
    staleTime: 60 * 1000, // 1 minute
  })
}

/**
 * Hook to get a webhook by ID
 */
export function useCDPWebhook(webhookId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.webhook(webhookId),
    queryFn: () => cdpApi.getWebhook(webhookId),
    staleTime: 30 * 1000,
    enabled: options?.enabled ?? !!webhookId,
  })
}

/**
 * Hook to create a new webhook
 */
export function useCreateWebhook() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (webhook: WebhookCreate) => cdpApi.createWebhook(webhook),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhooks() })
    },
  })
}

/**
 * Hook to update a webhook
 */
export function useUpdateWebhook() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ webhookId, update }: { webhookId: string; update: WebhookUpdate }) =>
      cdpApi.updateWebhook(webhookId, update),
    onSuccess: (_, { webhookId }) => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhooks() })
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhook(webhookId) })
    },
  })
}

/**
 * Hook to delete a webhook
 */
export function useDeleteWebhook() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (webhookId: string) => cdpApi.deleteWebhook(webhookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhooks() })
    },
  })
}

/**
 * Hook to test a webhook
 */
export function useTestWebhook() {
  return useMutation({
    mutationFn: (webhookId: string) => cdpApi.testWebhook(webhookId),
  })
}

/**
 * Hook to rotate webhook secret
 */
export function useRotateWebhookSecret() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (webhookId: string) => cdpApi.rotateWebhookSecret(webhookId),
    onSuccess: (_, webhookId) => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhook(webhookId) })
    },
  })
}

/**
 * Hook to detect event volume anomalies
 */
export function useEventAnomalies(params?: AnomalyDetectionParams) {
  return useQuery({
    queryKey: [...cdpQueryKeys.anomalies(), params],
    queryFn: () => cdpApi.detectEventAnomalies(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Hook to get anomaly detection summary
 */
export function useAnomalySummary() {
  return useQuery({
    queryKey: cdpQueryKeys.anomalySummary(),
    queryFn: () => cdpApi.getAnomalySummary(),
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Every 5 minutes
  })
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Create a track event helper for easy event ingestion
 */
export function createTracker(sourceKey?: string) {
  return {
    track: async (
      eventName: string,
      identifiers: IdentifierInput[],
      properties?: Record<string, unknown>,
      options?: {
        idempotencyKey?: string
        context?: EventContext
        consent?: EventConsent
      }
    ): Promise<EventIngestResult> => {
      const event: EventInput = {
        event_name: eventName,
        event_time: new Date().toISOString(),
        idempotency_key: options?.idempotencyKey,
        identifiers,
        properties,
        context: options?.context,
        consent: options?.consent,
      }
      return cdpApi.ingestEvent(event, sourceKey)
    },

    identify: async (
      identifiers: IdentifierInput[],
      traits?: Record<string, unknown>
    ): Promise<EventIngestResult> => {
      const event: EventInput = {
        event_name: 'Identify',
        event_time: new Date().toISOString(),
        identifiers,
        properties: traits ? { traits } : undefined,
      }
      return cdpApi.ingestEvent(event, sourceKey)
    },

    page: async (
      identifiers: IdentifierInput[],
      pageName?: string,
      properties?: Record<string, unknown>,
      context?: EventContext
    ): Promise<EventIngestResult> => {
      const event: EventInput = {
        event_name: 'PageView',
        event_time: new Date().toISOString(),
        identifiers,
        properties: { page_name: pageName, ...properties },
        context,
      }
      return cdpApi.ingestEvent(event, sourceKey)
    },
  }
}
