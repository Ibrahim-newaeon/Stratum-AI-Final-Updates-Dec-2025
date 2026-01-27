/**
 * Stratum AI - CDP (Customer Data Platform) API Client
 *
 * API client with TypeScript types and React Query hooks for CDP endpoints.
 * Handles event ingestion, profile lookups, and source management.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse } from './client';

// =============================================================================
// TypeScript Types
// =============================================================================

// Identifier Types
export type IdentifierType = 'email' | 'phone' | 'device_id' | 'anonymous_id' | 'external_id';

export interface IdentifierInput {
  type: IdentifierType;
  value: string;
}

export interface Identifier {
  id: string;
  identifier_type: IdentifierType;
  identifier_value?: string;
  identifier_hash: string;
  is_primary: boolean;
  confidence_score: number;
  verified_at?: string;
  first_seen_at: string;
  last_seen_at: string;
}

// Event Types
export interface EventContext {
  user_agent?: string;
  ip?: string;
  locale?: string;
  timezone?: string;
  screen?: { width: number; height: number };
  campaign?: Record<string, string>;
}

export interface EventConsent {
  analytics?: boolean;
  ads?: boolean;
  email?: boolean;
  sms?: boolean;
}

export interface EventInput {
  event_name: string;
  event_time: string;
  idempotency_key?: string;
  identifiers: IdentifierInput[];
  properties?: Record<string, unknown>;
  context?: EventContext;
  consent?: EventConsent;
}

export interface EventBatchInput {
  events: EventInput[];
}

export interface EventIngestResult {
  event_id?: string;
  status: 'accepted' | 'rejected' | 'duplicate';
  profile_id?: string;
  error?: string;
}

export interface EventBatchResponse {
  accepted: number;
  rejected: number;
  duplicates: number;
  results: EventIngestResult[];
}

export interface CDPEvent {
  id: string;
  event_name: string;
  event_time: string;
  received_at: string;
  properties: Record<string, unknown>;
  context: Record<string, unknown>;
  emq_score?: number;
  processed: boolean;
}

// Profile Types
export type LifecycleStage = 'anonymous' | 'known' | 'customer' | 'churned';

export interface CDPProfile {
  id: string;
  tenant_id: number;
  external_id?: string;
  first_seen_at: string;
  last_seen_at: string;
  profile_data: Record<string, unknown>;
  computed_traits: Record<string, unknown>;
  lifecycle_stage: LifecycleStage;
  total_events: number;
  total_sessions: number;
  total_purchases: number;
  total_revenue: number;
  identifiers: Identifier[];
  created_at: string;
  updated_at: string;
}

export interface ProfileListResponse {
  profiles: CDPProfile[];
  total: number;
  page: number;
  page_size: number;
}

// Source Types
export type SourceType = 'website' | 'server' | 'sgtm' | 'import' | 'crm';

export interface SourceCreate {
  name: string;
  source_type: SourceType;
  config?: Record<string, unknown>;
}

export interface CDPSource {
  id: string;
  name: string;
  source_type: SourceType;
  source_key: string;
  config: Record<string, unknown>;
  is_active: boolean;
  event_count: number;
  last_event_at?: string;
  created_at: string;
  updated_at: string;
}

export interface SourceListResponse {
  sources: CDPSource[];
  total: number;
}

// Consent Types
export type ConsentType = 'analytics' | 'ads' | 'email' | 'sms' | 'all';

export interface ConsentUpdate {
  consent_type: ConsentType;
  granted: boolean;
  source?: string;
  consent_text?: string;
  consent_version?: string;
}

export interface CDPConsent {
  id: string;
  consent_type: ConsentType;
  granted: boolean;
  granted_at?: string;
  revoked_at?: string;
  source?: string;
  consent_version?: string;
  created_at: string;
  updated_at: string;
}

// EMQ Score Types
export interface EMQScore {
  overall_score: number;
  identifier_quality: number;
  data_completeness: number;
  timeliness: number;
  context_richness: number;
}

// Health Check Response
export interface CDPHealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  module: string;
  version: string;
}

// Webhook Types
export type WebhookEventType =
  | 'event.received'
  | 'profile.created'
  | 'profile.updated'
  | 'profile.merged'
  | 'consent.updated'
  | 'all';

export interface WebhookCreate {
  name: string;
  url: string;
  event_types: WebhookEventType[];
  max_retries?: number;
  timeout_seconds?: number;
}

export interface WebhookUpdate {
  name?: string;
  url?: string;
  event_types?: WebhookEventType[];
  is_active?: boolean;
  max_retries?: number;
  timeout_seconds?: number;
}

export interface CDPWebhook {
  id: string;
  name: string;
  url: string;
  event_types: WebhookEventType[];
  secret_key?: string; // Only returned on create/rotate
  is_active: boolean;
  last_triggered_at?: string;
  last_success_at?: string;
  last_failure_at?: string;
  failure_count: number;
  max_retries: number;
  timeout_seconds: number;
  created_at: string;
  updated_at: string;
}

export interface WebhookListResponse {
  webhooks: CDPWebhook[];
  total: number;
}

export interface WebhookTestResult {
  success: boolean;
  status_code?: number;
  response_time_ms?: number;
  error?: string;
}

// Anomaly Detection Types
export type AnomalySeverity = 'low' | 'medium' | 'high' | 'critical';
export type AnomalyDirection = 'high' | 'low';

export interface EventAnomaly {
  source_id?: string;
  source_name: string;
  metric: string;
  zscore: number;
  severity: AnomalySeverity;
  current_value: number;
  baseline_mean: number;
  baseline_std: number;
  direction: AnomalyDirection;
  pct_change: number;
}

export interface AnomalyDetectionResponse {
  anomalies: EventAnomaly[];
  anomaly_count: number;
  has_critical: boolean;
  has_high: boolean;
  analysis_period_days: number;
  zscore_threshold: number;
  total_sources_analyzed: number;
}

export interface AnomalyDetectionParams {
  window_days?: number;
  zscore_threshold?: number;
}

export type HealthStatus = 'healthy' | 'fair' | 'degraded' | 'critical' | 'unknown';
export type VolumeTrend = 'increasing' | 'stable' | 'decreasing';

export interface AnomalySummaryResponse {
  health_status: HealthStatus;
  events_today: number;
  events_7d: number;
  events_prev_7d: number;
  wow_change_pct: number;
  volume_trend: VolumeTrend;
  avg_emq_score?: number;
  as_of: string;
}

// Identity Graph Types
export type IdentityLinkType =
  | 'same_session'
  | 'same_event'
  | 'login'
  | 'form_submit'
  | 'purchase'
  | 'manual'
  | 'inferred';

export type MergeReason = 'identity_match' | 'manual_merge' | 'login_event' | 'cross_device';

export interface IdentityGraphNode {
  id: string;
  type: IdentifierType;
  hash: string;
  is_primary: boolean;
  priority: number;
}

export interface IdentityGraphEdge {
  source: string;
  target: string;
  type: IdentityLinkType;
  confidence: number;
}

export interface IdentityGraphResponse {
  profile_id: string;
  nodes: IdentityGraphNode[];
  edges: IdentityGraphEdge[];
  total_identifiers: number;
  total_links: number;
}

export interface CanonicalIdentity {
  id: string;
  profile_id: string;
  canonical_type?: IdentifierType;
  canonical_value_hash?: string;
  priority_score: number;
  is_verified: boolean;
  verified_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ProfileMergeRequest {
  source_profile_id: string;
  target_profile_id: string;
  reason?: string;
}

export interface ProfileMerge {
  id: string;
  surviving_profile_id?: string;
  merged_profile_id: string;
  merge_reason: MergeReason;
  merged_event_count: number;
  merged_identifier_count: number;
  is_rolled_back: boolean;
  created_at: string;
}

export interface ProfileMergeHistoryResponse {
  merges: ProfileMerge[];
  total: number;
}

export interface IdentityLink {
  id: string;
  source_identifier_id: string;
  target_identifier_id: string;
  link_type: IdentityLinkType;
  confidence_score: number;
  is_active: boolean;
  evidence: Record<string, unknown>;
  created_at: string;
}

export interface IdentityLinksResponse {
  links: IdentityLink[];
  total: number;
  limit: number;
  offset: number;
}

// Segment Types
export type SegmentType = 'static' | 'dynamic' | 'computed';
export type SegmentStatus = 'draft' | 'computing' | 'active' | 'stale' | 'archived';

export interface SegmentCondition {
  field: string;
  operator: string;
  value: unknown;
}

export interface SegmentRules {
  logic: 'and' | 'or';
  conditions: SegmentCondition[];
  groups?: SegmentRules[];
}

export interface SegmentCreate {
  name: string;
  description?: string;
  segment_type?: SegmentType;
  rules: SegmentRules;
  tags?: string[];
  auto_refresh?: boolean;
  refresh_interval_hours?: number;
}

export interface SegmentUpdate {
  name?: string;
  description?: string;
  rules?: SegmentRules;
  tags?: string[];
  auto_refresh?: boolean;
  refresh_interval_hours?: number;
}

export interface CDPSegment {
  id: string;
  name: string;
  slug?: string;
  description?: string;
  segment_type: SegmentType;
  status: SegmentStatus;
  rules: Record<string, unknown>;
  profile_count: number;
  last_computed_at?: string;
  computation_duration_ms?: number;
  auto_refresh: boolean;
  refresh_interval_hours: number;
  next_refresh_at?: string;
  tags: string[];
  created_by_user_id?: number;
  created_at: string;
  updated_at: string;
}

export interface SegmentListResponse {
  segments: CDPSegment[];
  total: number;
}

export interface SegmentPreviewRequest {
  rules: SegmentRules;
  limit?: number;
}

export interface SegmentPreviewResponse {
  estimated_count: number;
  sample_profiles: CDPProfile[];
}

export interface SegmentProfilesResponse {
  profiles: CDPProfile[];
  total: number;
}

export interface ProfileSegmentsResponse {
  segments: CDPSegment[];
}

// Computed Traits Types
export type TraitType =
  | 'count'
  | 'sum'
  | 'average'
  | 'min'
  | 'max'
  | 'first'
  | 'last'
  | 'unique_count'
  | 'exists'
  | 'formula';

export interface ComputedTraitSourceConfig {
  event_name?: string;
  property?: string;
  time_window_days?: number;
}

export interface ComputedTraitCreate {
  name: string;
  display_name: string;
  description?: string;
  trait_type: TraitType;
  source_config: ComputedTraitSourceConfig;
  output_type?: string;
  default_value?: string;
}

export interface CDPComputedTrait {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  trait_type: TraitType;
  source_config: Record<string, unknown>;
  output_type: string;
  default_value?: string;
  is_active: boolean;
  last_computed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ComputedTraitListResponse {
  traits: CDPComputedTrait[];
  total: number;
}

export interface ComputeTraitsResponse {
  profiles_processed: number;
  errors: number;
}

// RFM Types
export type RFMSegment =
  | 'champions'
  | 'loyal_customers'
  | 'potential_loyalists'
  | 'new_customers'
  | 'promising'
  | 'need_attention'
  | 'about_to_sleep'
  | 'at_risk'
  | 'cannot_lose'
  | 'hibernating'
  | 'lost'
  | 'other';

export interface RFMConfig {
  purchase_event_name?: string;
  revenue_property?: string;
  analysis_window_days?: number;
}

export interface RFMScores {
  recency_days: number;
  frequency: number;
  monetary: number;
  recency_score: number;
  frequency_score: number;
  monetary_score: number;
  rfm_score: number;
  rfm_segment: RFMSegment;
  analysis_window_days: number;
  calculated_at: string;
}

export interface RFMBatchResponse {
  profiles_processed: number;
  segment_distribution: Record<RFMSegment, number>;
  analysis_window_days: number;
  calculated_at: string;
}

export interface RFMSummaryResponse {
  total_profiles: number;
  profiles_with_rfm: number;
  segment_distribution: Record<RFMSegment, number>;
  coverage_pct: number;
}

// Profile Deletion Types
export interface ProfileDeletionResponse {
  profile_id: string;
  deleted: boolean;
  events_deleted: number;
  identifiers_deleted: number;
  consents_deleted: number;
  segment_memberships_deleted: number;
  deletion_timestamp: string;
}

// Funnel/Journey Types
export type FunnelStatus = 'draft' | 'computing' | 'active' | 'stale' | 'archived';

export interface FunnelStepCondition {
  field: string;
  operator: string;
  value: unknown;
}

export interface FunnelStep {
  step_name: string;
  event_name: string;
  conditions?: FunnelStepCondition[];
}

export interface FunnelCreate {
  name: string;
  description?: string;
  steps: FunnelStep[];
  conversion_window_days?: number;
  step_timeout_hours?: number;
  auto_refresh?: boolean;
  refresh_interval_hours?: number;
  tags?: string[];
}

export interface FunnelUpdate {
  name?: string;
  description?: string;
  steps?: FunnelStep[];
  conversion_window_days?: number;
  step_timeout_hours?: number;
  auto_refresh?: boolean;
  refresh_interval_hours?: number;
  tags?: string[];
}

export interface FunnelStepMetrics {
  step: number;
  name: string;
  event_name: string;
  count: number;
  conversion_rate: number;
  drop_off_rate: number;
  drop_off_count: number;
}

export interface CDPFunnel {
  id: string;
  name: string;
  slug?: string;
  description?: string;
  status: FunnelStatus;
  steps: FunnelStep[];
  conversion_window_days: number;
  step_timeout_hours?: number;
  total_entered: number;
  total_converted: number;
  overall_conversion_rate?: number;
  step_metrics: FunnelStepMetrics[];
  last_computed_at?: string;
  computation_duration_ms?: number;
  auto_refresh: boolean;
  refresh_interval_hours: number;
  next_refresh_at?: string;
  tags: string[];
  created_by_user_id?: number;
  created_at: string;
  updated_at: string;
}

export interface FunnelListResponse {
  funnels: CDPFunnel[];
  total: number;
}

export interface FunnelComputeResponse {
  funnel_id: string;
  total_entered: number;
  total_converted: number;
  overall_conversion_rate: number;
  step_metrics: FunnelStepMetrics[];
  computation_duration_ms: number;
}

export interface FunnelAnalysisRequest {
  start_date?: string;
  end_date?: string;
}

export interface FunnelStepAnalysis {
  step: number;
  name: string;
  event_name: string;
  count: number;
  conversion_rate_from_start: number;
  conversion_rate_from_prev: number;
  drop_off_count: number;
}

export interface FunnelAnalysisResponse {
  funnel_id: string;
  funnel_name: string;
  total_entered: number;
  total_converted: number;
  overall_conversion_rate: number;
  step_analysis: FunnelStepAnalysis[];
  avg_conversion_time_seconds?: number;
  analysis_period: {
    start?: string;
    end?: string;
  };
}

export interface ProfileFunnelJourney {
  funnel_id: string;
  funnel_name?: string;
  entered_at: string;
  converted_at?: string;
  is_converted: boolean;
  current_step: number;
  completed_steps: number;
  total_steps?: number;
  step_timestamps: Record<string, string>;
  total_duration_seconds?: number;
}

export interface ProfileFunnelJourneysResponse {
  profile_id: string;
  journeys: ProfileFunnelJourney[];
}

export interface FunnelDropOffResponse {
  funnel_id: string;
  step: number;
  profiles: CDPProfile[];
  total: number;
}

// Audience Export Types
export interface AudienceExportParams {
  format?: 'json' | 'csv';
  limit?: number;
  offset?: number;
  segment_id?: string;
  lifecycle_stage?: LifecycleStage;
  rfm_segment?: RFMSegment;
  min_events?: number;
  max_events?: number;
  min_revenue?: number;
  max_revenue?: number;
  first_seen_after?: string;
  first_seen_before?: string;
  last_seen_after?: string;
  last_seen_before?: string;
  has_identifier_type?: IdentifierType;
  include_computed_traits?: boolean;
  include_identifiers?: boolean;
  include_rfm?: boolean;
}

export interface AudienceExportResponse {
  format: string;
  export_time: string;
  total_matching: number;
  count: number;
  offset: number;
  limit: number;
  filters_applied: Record<string, string | number | null>;
  data: CDPProfile[];
}

// Profile Search Types
export interface ProfileSearchParams {
  query?: string;
  limit?: number;
  offset?: number;
  segment_ids?: string[];
  exclude_segment_ids?: string[];
  lifecycle_stages?: LifecycleStage[];
  rfm_segments?: RFMSegment[];
  identifier_types?: IdentifierType[];
  min_events?: number;
  max_events?: number;
  min_revenue?: number;
  max_revenue?: number;
  first_seen_after?: string;
  first_seen_before?: string;
  last_seen_after?: string;
  last_seen_before?: string;
  has_email?: boolean;
  has_phone?: boolean;
  is_customer?: boolean;
  sort_by?: 'last_seen_at' | 'first_seen_at' | 'total_events' | 'total_revenue' | 'created_at';
  sort_order?: 'asc' | 'desc';
  include_identifiers?: boolean;
  include_computed_traits?: boolean;
}

export interface ProfileSearchResponse {
  profiles: CDPProfile[];
  total: number;
  offset: number;
  limit: number;
  sort_by: string;
  sort_order: string;
}

// Event Statistics Types
export interface EventByName {
  event_name: string;
  count: number;
}

export interface DailyVolume {
  date: string;
  count: number;
}

export interface EMQDistribution {
  score_range: string;
  count: number;
}

export interface EventBySource {
  source_name: string;
  count: number;
}

export interface EventStatisticsResponse {
  period_days: number;
  analysis_start: string;
  analysis_end: string;
  total_events: number;
  unique_profiles: number;
  avg_emq_score?: number;
  events_by_name: EventByName[];
  daily_volume: DailyVolume[];
  emq_distribution: EMQDistribution[];
  events_by_source: EventBySource[];
}

export interface EventTrend {
  event_name: string;
  current_count: number;
  previous_count: number;
  change_pct: number;
  trend: 'up' | 'down' | 'stable';
}

export interface EventTrendsResponse {
  period_days: number;
  current_period: {
    start: string;
    end: string;
    total_events: number;
  };
  previous_period: {
    start: string;
    end: string;
    total_events: number;
  };
  overall_change_pct: number;
  overall_trend: 'up' | 'down' | 'stable';
  event_trends: EventTrend[];
}

export interface ProfileStatisticsResponse {
  total_profiles: number;
  lifecycle_distribution: Record<LifecycleStage, number>;
  new_profiles_7d: number;
  active_profiles_30d: number;
  profiles_with_email: number;
  profiles_with_phone: number;
  email_coverage_pct: number;
  phone_coverage_pct: number;
  total_customers: number;
  customer_rate_pct: number;
  revenue: {
    total: number;
    average: number;
    max: number;
  };
  events: {
    total: number;
    average_per_profile: number;
  };
}

// Export Types
export type ExportFormat = 'json' | 'csv';

export interface ExportProfilesParams {
  format?: ExportFormat;
  limit?: number;
  offset?: number;
}

export interface ExportEventsParams {
  format?: ExportFormat;
  limit?: number;
  offset?: number;
  start_date?: string;
  end_date?: string;
  event_name?: string;
}

export interface ExportResponse<T> {
  format: string;
  count: number;
  offset: number;
  limit: number;
  data: T[];
  filters?: Record<string, string | null>;
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
  ingestEvents: async (events: EventInput[], sourceKey?: string): Promise<EventBatchResponse> => {
    const params = sourceKey ? { source_key: sourceKey } : {};
    const response = await apiClient.post<ApiResponse<EventBatchResponse>>(
      '/cdp/events',
      { events },
      { params }
    );
    return response.data.data;
  },

  /**
   * Ingest a single event
   * @param event Event to ingest
   * @param sourceKey Optional source API key
   */
  ingestEvent: async (event: EventInput, sourceKey?: string): Promise<EventIngestResult> => {
    const response = await cdpApi.ingestEvents([event], sourceKey);
    return response.results[0];
  },

  // Profile Endpoints
  /**
   * Get a profile by ID
   * @param profileId UUID of the profile
   */
  getProfile: async (profileId: string): Promise<CDPProfile> => {
    const response = await apiClient.get<ApiResponse<CDPProfile>>(`/cdp/profiles/${profileId}`);
    return response.data.data;
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
    const response = await apiClient.get<ApiResponse<CDPProfile>>('/cdp/profiles', {
      params: {
        identifier_type: identifierType,
        identifier_value: identifierValue,
      },
    });
    return response.data.data;
  },

  // Source Endpoints
  /**
   * List all data sources
   */
  listSources: async (): Promise<SourceListResponse> => {
    const response = await apiClient.get<ApiResponse<SourceListResponse>>('/cdp/sources');
    return response.data.data;
  },

  /**
   * Create a new data source
   * @param source Source configuration
   */
  createSource: async (source: SourceCreate): Promise<CDPSource> => {
    const response = await apiClient.post<ApiResponse<CDPSource>>('/cdp/sources', source);
    return response.data.data;
  },

  // Health Check
  /**
   * Check CDP module health
   */
  health: async (): Promise<CDPHealthResponse> => {
    const response = await apiClient.get<CDPHealthResponse>('/cdp/health');
    return response.data;
  },

  // Webhook Endpoints
  /**
   * List all webhooks
   */
  listWebhooks: async (): Promise<WebhookListResponse> => {
    const response = await apiClient.get<ApiResponse<WebhookListResponse>>('/cdp/webhooks');
    return response.data.data;
  },

  /**
   * Create a new webhook
   * @param webhook Webhook configuration
   */
  createWebhook: async (webhook: WebhookCreate): Promise<CDPWebhook> => {
    const response = await apiClient.post<ApiResponse<CDPWebhook>>('/cdp/webhooks', webhook);
    return response.data.data;
  },

  /**
   * Get a webhook by ID
   * @param webhookId UUID of the webhook
   */
  getWebhook: async (webhookId: string): Promise<CDPWebhook> => {
    const response = await apiClient.get<ApiResponse<CDPWebhook>>(`/cdp/webhooks/${webhookId}`);
    return response.data.data;
  },

  /**
   * Update a webhook
   * @param webhookId UUID of the webhook
   * @param update Fields to update
   */
  updateWebhook: async (webhookId: string, update: WebhookUpdate): Promise<CDPWebhook> => {
    const response = await apiClient.patch<ApiResponse<CDPWebhook>>(
      `/cdp/webhooks/${webhookId}`,
      update
    );
    return response.data.data;
  },

  /**
   * Delete a webhook
   * @param webhookId UUID of the webhook
   */
  deleteWebhook: async (webhookId: string): Promise<void> => {
    await apiClient.delete(`/cdp/webhooks/${webhookId}`);
  },

  /**
   * Test a webhook
   * @param webhookId UUID of the webhook
   */
  testWebhook: async (webhookId: string): Promise<WebhookTestResult> => {
    const response = await apiClient.post<ApiResponse<WebhookTestResult>>(
      `/cdp/webhooks/${webhookId}/test`
    );
    return response.data.data;
  },

  /**
   * Rotate webhook secret
   * @param webhookId UUID of the webhook
   */
  rotateWebhookSecret: async (webhookId: string): Promise<CDPWebhook> => {
    const response = await apiClient.post<ApiResponse<CDPWebhook>>(
      `/cdp/webhooks/${webhookId}/rotate-secret`
    );
    return response.data.data;
  },

  // Anomaly Detection Endpoints
  /**
   * Detect event volume anomalies
   * @param params Optional parameters for analysis
   */
  detectEventAnomalies: async (
    params?: AnomalyDetectionParams
  ): Promise<AnomalyDetectionResponse> => {
    const response = await apiClient.get<AnomalyDetectionResponse>('/cdp/anomalies/events', {
      params,
    });
    return response.data;
  },

  /**
   * Get anomaly detection summary
   */
  getAnomalySummary: async (): Promise<AnomalySummaryResponse> => {
    const response = await apiClient.get<AnomalySummaryResponse>('/cdp/anomalies/summary');
    return response.data;
  },

  // Export Endpoints
  /**
   * Export profiles in JSON or CSV format
   * @param params Export parameters (format, limit, offset)
   */
  exportProfiles: async (
    params?: ExportProfilesParams
  ): Promise<ExportResponse<CDPProfile> | Blob> => {
    const format = params?.format || 'json';

    if (format === 'csv') {
      const response = await apiClient.get('/cdp/export/profiles', {
        params: { ...params, format: 'csv' },
        responseType: 'blob',
      });
      return response.data;
    }

    const response = await apiClient.get<ExportResponse<CDPProfile>>('/cdp/export/profiles', {
      params,
    });
    return response.data;
  },

  /**
   * Export events in JSON or CSV format
   * @param params Export parameters (format, limit, offset, date filters)
   */
  exportEvents: async (params?: ExportEventsParams): Promise<ExportResponse<CDPEvent> | Blob> => {
    const format = params?.format || 'json';

    if (format === 'csv') {
      const response = await apiClient.get('/cdp/export/events', {
        params: { ...params, format: 'csv' },
        responseType: 'blob',
      });
      return response.data;
    }

    const response = await apiClient.get<ExportResponse<CDPEvent>>('/cdp/export/events', {
      params,
    });
    return response.data;
  },

  // Identity Graph Endpoints
  /**
   * Get identity graph for a profile
   * @param profileId UUID of the profile
   */
  getIdentityGraph: async (profileId: string): Promise<IdentityGraphResponse> => {
    const response = await apiClient.get<ApiResponse<IdentityGraphResponse>>(
      `/cdp/profiles/${profileId}/identity-graph`
    );
    return response.data.data;
  },

  /**
   * Get canonical identity for a profile
   * @param profileId UUID of the profile
   */
  getCanonicalIdentity: async (profileId: string): Promise<CanonicalIdentity> => {
    const response = await apiClient.get<ApiResponse<CanonicalIdentity>>(
      `/cdp/profiles/${profileId}/canonical-identity`
    );
    return response.data.data;
  },

  /**
   * Get merge history for a profile
   * @param profileId UUID of the profile
   */
  getProfileMergeHistory: async (profileId: string): Promise<ProfileMergeHistoryResponse> => {
    const response = await apiClient.get<ApiResponse<ProfileMergeHistoryResponse>>(
      `/cdp/profiles/${profileId}/merge-history`
    );
    return response.data.data;
  },

  /**
   * Manually merge two profiles
   * @param request Merge request with source and target profile IDs
   */
  mergeProfiles: async (request: ProfileMergeRequest): Promise<ProfileMerge> => {
    const response = await apiClient.post<ApiResponse<ProfileMerge>>(
      '/cdp/profiles/merge',
      request
    );
    return response.data.data;
  },

  /**
   * List all profile merges for the tenant
   * @param params Pagination parameters
   */
  listMergeHistory: async (params?: {
    limit?: number;
    offset?: number;
  }): Promise<ProfileMergeHistoryResponse> => {
    const response = await apiClient.get<ApiResponse<ProfileMergeHistoryResponse>>(
      '/cdp/merge-history',
      { params }
    );
    return response.data.data;
  },

  /**
   * List identity links for the tenant
   * @param params Filter and pagination parameters
   */
  listIdentityLinks: async (params?: {
    limit?: number;
    offset?: number;
    link_type?: IdentityLinkType;
  }): Promise<IdentityLinksResponse> => {
    const response = await apiClient.get<IdentityLinksResponse>('/cdp/identity-links', { params });
    return response.data;
  },

  // Segment Endpoints
  /**
   * Create a new segment
   */
  createSegment: async (segment: SegmentCreate): Promise<CDPSegment> => {
    const response = await apiClient.post<ApiResponse<CDPSegment>>('/cdp/segments', segment);
    return response.data.data;
  },

  /**
   * List all segments
   */
  listSegments: async (params?: {
    status?: SegmentStatus;
    segment_type?: SegmentType;
    limit?: number;
    offset?: number;
  }): Promise<SegmentListResponse> => {
    const response = await apiClient.get<ApiResponse<SegmentListResponse>>('/cdp/segments', {
      params,
    });
    return response.data.data;
  },

  /**
   * Get a segment by ID
   */
  getSegment: async (segmentId: string): Promise<CDPSegment> => {
    const response = await apiClient.get<ApiResponse<CDPSegment>>(`/cdp/segments/${segmentId}`);
    return response.data.data;
  },

  /**
   * Update a segment
   */
  updateSegment: async (segmentId: string, update: SegmentUpdate): Promise<CDPSegment> => {
    const response = await apiClient.patch<ApiResponse<CDPSegment>>(
      `/cdp/segments/${segmentId}`,
      update
    );
    return response.data.data;
  },

  /**
   * Delete a segment
   */
  deleteSegment: async (segmentId: string): Promise<void> => {
    await apiClient.delete(`/cdp/segments/${segmentId}`);
  },

  /**
   * Compute segment membership
   */
  computeSegment: async (segmentId: string): Promise<CDPSegment> => {
    const response = await apiClient.post<ApiResponse<CDPSegment>>(
      `/cdp/segments/${segmentId}/compute`
    );
    return response.data.data;
  },

  /**
   * Preview segment membership
   */
  previewSegment: async (request: SegmentPreviewRequest): Promise<SegmentPreviewResponse> => {
    const response = await apiClient.post<ApiResponse<SegmentPreviewResponse>>(
      '/cdp/segments/preview',
      request
    );
    return response.data.data;
  },

  /**
   * Get profiles in a segment
   */
  getSegmentProfiles: async (
    segmentId: string,
    params?: {
      limit?: number;
      offset?: number;
    }
  ): Promise<SegmentProfilesResponse> => {
    const response = await apiClient.get<ApiResponse<SegmentProfilesResponse>>(
      `/cdp/segments/${segmentId}/profiles`,
      { params }
    );
    return response.data.data;
  },

  /**
   * Get segments a profile belongs to
   */
  getProfileSegments: async (profileId: string): Promise<ProfileSegmentsResponse> => {
    const response = await apiClient.get<ApiResponse<ProfileSegmentsResponse>>(
      `/cdp/profiles/${profileId}/segments`
    );
    return response.data.data;
  },

  /**
   * Delete a profile (GDPR)
   */
  deleteProfile: async (
    profileId: string,
    params?: {
      delete_events?: boolean;
      reason?: string;
    }
  ): Promise<ProfileDeletionResponse> => {
    const response = await apiClient.delete<ApiResponse<ProfileDeletionResponse>>(
      `/cdp/profiles/${profileId}`,
      { params }
    );
    return response.data.data;
  },

  // Computed Traits Endpoints
  /**
   * Create a computed trait
   */
  createTrait: async (trait: ComputedTraitCreate): Promise<CDPComputedTrait> => {
    const response = await apiClient.post<ApiResponse<CDPComputedTrait>>('/cdp/traits', trait);
    return response.data.data;
  },

  /**
   * List computed traits
   */
  listTraits: async (params?: {
    active_only?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<ComputedTraitListResponse> => {
    const response = await apiClient.get<ApiResponse<ComputedTraitListResponse>>('/cdp/traits', {
      params,
    });
    return response.data.data;
  },

  /**
   * Get a computed trait by ID
   */
  getTrait: async (traitId: string): Promise<CDPComputedTrait> => {
    const response = await apiClient.get<ApiResponse<CDPComputedTrait>>(`/cdp/traits/${traitId}`);
    return response.data.data;
  },

  /**
   * Delete a computed trait
   */
  deleteTrait: async (traitId: string): Promise<void> => {
    await apiClient.delete(`/cdp/traits/${traitId}`);
  },

  /**
   * Compute all traits for all profiles
   */
  computeAllTraits: async (): Promise<ComputeTraitsResponse> => {
    const response =
      await apiClient.post<ApiResponse<ComputeTraitsResponse>>('/cdp/traits/compute');
    return response.data.data;
  },

  /**
   * Compute traits for a specific profile
   */
  computeProfileTraits: async (
    profileId: string
  ): Promise<{ profile_id: string; computed_traits: Record<string, unknown> }> => {
    const response = await apiClient.post<
      ApiResponse<{ profile_id: string; computed_traits: Record<string, unknown> }>
    >(`/cdp/profiles/${profileId}/compute-traits`);
    return response.data.data;
  },

  // RFM Endpoints
  /**
   * Get RFM scores for a profile
   */
  getProfileRFM: async (profileId: string, params?: RFMConfig): Promise<RFMScores> => {
    const response = await apiClient.get<ApiResponse<RFMScores>>(`/cdp/profiles/${profileId}/rfm`, {
      params,
    });
    return response.data.data;
  },

  /**
   * Compute RFM for all profiles
   */
  computeRFMBatch: async (config?: RFMConfig): Promise<RFMBatchResponse> => {
    const response = await apiClient.post<ApiResponse<RFMBatchResponse>>(
      '/cdp/rfm/compute',
      config
    );
    return response.data.data;
  },

  /**
   * Get RFM summary
   */
  getRFMSummary: async (): Promise<RFMSummaryResponse> => {
    const response = await apiClient.get<ApiResponse<RFMSummaryResponse>>('/cdp/rfm/summary');
    return response.data.data;
  },

  // Funnel/Journey Endpoints
  /**
   * Create a new funnel
   */
  createFunnel: async (funnel: FunnelCreate): Promise<CDPFunnel> => {
    const response = await apiClient.post<ApiResponse<CDPFunnel>>('/cdp/funnels', funnel);
    return response.data.data;
  },

  /**
   * List all funnels
   */
  listFunnels: async (params?: {
    status?: FunnelStatus;
    limit?: number;
    offset?: number;
  }): Promise<FunnelListResponse> => {
    const response = await apiClient.get<ApiResponse<FunnelListResponse>>('/cdp/funnels', {
      params,
    });
    return response.data.data;
  },

  /**
   * Get a funnel by ID
   */
  getFunnel: async (funnelId: string): Promise<CDPFunnel> => {
    const response = await apiClient.get<ApiResponse<CDPFunnel>>(`/cdp/funnels/${funnelId}`);
    return response.data.data;
  },

  /**
   * Update a funnel
   */
  updateFunnel: async (funnelId: string, update: FunnelUpdate): Promise<CDPFunnel> => {
    const response = await apiClient.patch<ApiResponse<CDPFunnel>>(
      `/cdp/funnels/${funnelId}`,
      update
    );
    return response.data.data;
  },

  /**
   * Delete a funnel
   */
  deleteFunnel: async (funnelId: string): Promise<void> => {
    await apiClient.delete(`/cdp/funnels/${funnelId}`);
  },

  /**
   * Compute funnel metrics
   */
  computeFunnel: async (funnelId: string): Promise<FunnelComputeResponse> => {
    const response = await apiClient.post<ApiResponse<FunnelComputeResponse>>(
      `/cdp/funnels/${funnelId}/compute`
    );
    return response.data.data;
  },

  /**
   * Analyze funnel with date filtering
   */
  analyzeFunnel: async (
    funnelId: string,
    params?: FunnelAnalysisRequest
  ): Promise<FunnelAnalysisResponse> => {
    const response = await apiClient.post<ApiResponse<FunnelAnalysisResponse>>(
      `/cdp/funnels/${funnelId}/analyze`,
      params
    );
    return response.data.data;
  },

  /**
   * Get profiles that dropped off at a specific step
   */
  getFunnelDropOffs: async (
    funnelId: string,
    step: number,
    params?: { limit?: number; offset?: number }
  ): Promise<FunnelDropOffResponse> => {
    const response = await apiClient.get<ApiResponse<FunnelDropOffResponse>>(
      `/cdp/funnels/${funnelId}/drop-offs/${step}`,
      { params }
    );
    return response.data.data;
  },

  /**
   * Get a profile's funnel journeys
   */
  getProfileFunnelJourneys: async (
    profileId: string,
    funnelId?: string
  ): Promise<ProfileFunnelJourneysResponse> => {
    const response = await apiClient.get<ApiResponse<ProfileFunnelJourneysResponse>>(
      `/cdp/profiles/${profileId}/funnels`,
      { params: funnelId ? { funnel_id: funnelId } : undefined }
    );
    return response.data.data;
  },

  // Analytics Endpoints
  /**
   * Get event statistics
   * @param period_days Analysis period in days
   */
  getEventStatistics: async (period_days?: number): Promise<EventStatisticsResponse> => {
    const response = await apiClient.get<EventStatisticsResponse>('/cdp/events/statistics', {
      params: period_days ? { period_days } : undefined,
    });
    return response.data;
  },

  /**
   * Get event trends
   * @param period_days Period in days for comparison
   */
  getEventTrends: async (period_days?: number): Promise<EventTrendsResponse> => {
    const response = await apiClient.get<EventTrendsResponse>('/cdp/events/trends', {
      params: period_days ? { period_days } : undefined,
    });
    return response.data;
  },

  /**
   * Get profile statistics
   */
  getProfileStatistics: async (): Promise<ProfileStatisticsResponse> => {
    const response = await apiClient.get<ProfileStatisticsResponse>('/cdp/profiles/statistics');
    return response.data;
  },

  // Profile Search Endpoints
  /**
   * Search profiles with advanced filters
   * @param params Search parameters including filters and sorting
   */
  searchProfiles: async (params?: ProfileSearchParams): Promise<ProfileSearchResponse> => {
    const response = await apiClient.post<ProfileSearchResponse>('/cdp/profiles/search', null, {
      params,
    });
    return response.data;
  },

  // Audience Export Endpoints
  /**
   * Export audience with advanced filters
   * @param params Export parameters including filters and format
   */
  exportAudience: async (params?: AudienceExportParams): Promise<AudienceExportResponse | Blob> => {
    const format = params?.format || 'json';

    if (format === 'csv') {
      const response = await apiClient.post('/cdp/audiences/export', null, {
        params: { ...params, format: 'csv' },
        responseType: 'blob',
      });
      return response.data;
    }

    const response = await apiClient.post<AudienceExportResponse>('/cdp/audiences/export', null, {
      params,
    });
    return response.data;
  },
};

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
  identityGraph: (profileId: string) =>
    [...cdpQueryKeys.profiles(), profileId, 'identity-graph'] as const,
  canonicalIdentity: (profileId: string) =>
    [...cdpQueryKeys.profiles(), profileId, 'canonical'] as const,
  profileMergeHistory: (profileId: string) =>
    [...cdpQueryKeys.profiles(), profileId, 'merge-history'] as const,
  mergeHistory: () => [...cdpQueryKeys.all, 'merge-history'] as const,
  identityLinks: () => [...cdpQueryKeys.all, 'identity-links'] as const,
  segments: () => [...cdpQueryKeys.all, 'segments'] as const,
  segment: (id: string) => [...cdpQueryKeys.segments(), id] as const,
  segmentProfiles: (id: string) => [...cdpQueryKeys.segments(), id, 'profiles'] as const,
  profileSegments: (profileId: string) =>
    [...cdpQueryKeys.profiles(), profileId, 'segments'] as const,
  traits: () => [...cdpQueryKeys.all, 'traits'] as const,
  trait: (id: string) => [...cdpQueryKeys.traits(), id] as const,
  profileRFM: (profileId: string) => [...cdpQueryKeys.profiles(), profileId, 'rfm'] as const,
  rfmSummary: () => [...cdpQueryKeys.all, 'rfm-summary'] as const,
  funnels: () => [...cdpQueryKeys.all, 'funnels'] as const,
  funnel: (id: string) => [...cdpQueryKeys.funnels(), id] as const,
  funnelDropOffs: (id: string, step: number) =>
    [...cdpQueryKeys.funnels(), id, 'drop-offs', step] as const,
  profileFunnels: (profileId: string) =>
    [...cdpQueryKeys.profiles(), profileId, 'funnels'] as const,
  profileSearch: () => [...cdpQueryKeys.profiles(), 'search'] as const,
  // Analytics
  eventStatistics: (periodDays?: number) =>
    [...cdpQueryKeys.all, 'event-statistics', periodDays] as const,
  eventTrends: (periodDays?: number) => [...cdpQueryKeys.all, 'event-trends', periodDays] as const,
  profileStatistics: () => [...cdpQueryKeys.all, 'profile-statistics'] as const,
};

/**
 * Hook to get a profile by ID
 */
export function useCDPProfile(profileId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.profile(profileId),
    queryFn: () => cdpApi.getProfile(profileId),
    staleTime: 30 * 1000, // 30 seconds
    enabled: options?.enabled ?? !!profileId,
  });
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
  });
}

/**
 * Hook to list all data sources
 */
export function useCDPSources() {
  return useQuery({
    queryKey: cdpQueryKeys.sources(),
    queryFn: () => cdpApi.listSources(),
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to ingest events
 */
export function useIngestEvents(options?: { sourceKey?: string }) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (events: EventInput[]) => cdpApi.ingestEvents(events, options?.sourceKey),
    onSuccess: () => {
      // Invalidate profiles as they may have been updated
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profiles() });
    },
  });
}

/**
 * Hook to ingest a single event
 */
export function useIngestEvent(options?: { sourceKey?: string }) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (event: EventInput) => cdpApi.ingestEvent(event, options?.sourceKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profiles() });
    },
  });
}

/**
 * Hook to create a new data source
 */
export function useCreateSource() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (source: SourceCreate) => cdpApi.createSource(source),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.sources() });
    },
  });
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
  });
}

/**
 * Hook to list all webhooks
 */
export function useCDPWebhooks() {
  return useQuery({
    queryKey: cdpQueryKeys.webhooks(),
    queryFn: () => cdpApi.listWebhooks(),
    staleTime: 60 * 1000, // 1 minute
  });
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
  });
}

/**
 * Hook to create a new webhook
 */
export function useCreateWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (webhook: WebhookCreate) => cdpApi.createWebhook(webhook),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhooks() });
    },
  });
}

/**
 * Hook to update a webhook
 */
export function useUpdateWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ webhookId, update }: { webhookId: string; update: WebhookUpdate }) =>
      cdpApi.updateWebhook(webhookId, update),
    onSuccess: (_, { webhookId }) => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhooks() });
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhook(webhookId) });
    },
  });
}

/**
 * Hook to delete a webhook
 */
export function useDeleteWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (webhookId: string) => cdpApi.deleteWebhook(webhookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhooks() });
    },
  });
}

/**
 * Hook to test a webhook
 */
export function useTestWebhook() {
  return useMutation({
    mutationFn: (webhookId: string) => cdpApi.testWebhook(webhookId),
  });
}

/**
 * Hook to rotate webhook secret
 */
export function useRotateWebhookSecret() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (webhookId: string) => cdpApi.rotateWebhookSecret(webhookId),
    onSuccess: (_, webhookId) => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.webhook(webhookId) });
    },
  });
}

/**
 * Hook to detect event volume anomalies
 */
export function useEventAnomalies(params?: AnomalyDetectionParams) {
  return useQuery({
    queryKey: [...cdpQueryKeys.anomalies(), params],
    queryFn: () => cdpApi.detectEventAnomalies(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
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
  });
}

/**
 * Hook to get identity graph for a profile
 */
export function useIdentityGraph(profileId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.identityGraph(profileId),
    queryFn: () => cdpApi.getIdentityGraph(profileId),
    staleTime: 30 * 1000, // 30 seconds
    enabled: options?.enabled ?? !!profileId,
  });
}

/**
 * Hook to get canonical identity for a profile
 */
export function useCanonicalIdentity(profileId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.canonicalIdentity(profileId),
    queryFn: () => cdpApi.getCanonicalIdentity(profileId),
    staleTime: 30 * 1000,
    enabled: options?.enabled ?? !!profileId,
  });
}

/**
 * Hook to get merge history for a profile
 */
export function useProfileMergeHistory(profileId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.profileMergeHistory(profileId),
    queryFn: () => cdpApi.getProfileMergeHistory(profileId),
    staleTime: 60 * 1000,
    enabled: options?.enabled ?? !!profileId,
  });
}

/**
 * Hook to list all profile merges
 */
export function useMergeHistory(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: [...cdpQueryKeys.mergeHistory(), params],
    queryFn: () => cdpApi.listMergeHistory(params),
    staleTime: 60 * 1000,
  });
}

/**
 * Hook to list identity links
 */
export function useIdentityLinks(params?: {
  limit?: number;
  offset?: number;
  link_type?: IdentityLinkType;
}) {
  return useQuery({
    queryKey: [...cdpQueryKeys.identityLinks(), params],
    queryFn: () => cdpApi.listIdentityLinks(params),
    staleTime: 60 * 1000,
  });
}

/**
 * Hook to merge profiles
 */
export function useMergeProfiles() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ProfileMergeRequest) => cdpApi.mergeProfiles(request),
    onSuccess: (_, request) => {
      // Invalidate both profiles and merge history
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profile(request.source_profile_id) });
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profile(request.target_profile_id) });
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.mergeHistory() });
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.identityLinks() });
    },
  });
}

// Segment Hooks

/**
 * Hook to list segments
 */
export function useSegments(params?: {
  status?: SegmentStatus;
  segment_type?: SegmentType;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: [...cdpQueryKeys.segments(), params],
    queryFn: () => cdpApi.listSegments(params),
    staleTime: 60 * 1000,
  });
}

/**
 * Hook to get a segment by ID
 */
export function useSegment(segmentId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.segment(segmentId),
    queryFn: () => cdpApi.getSegment(segmentId),
    staleTime: 30 * 1000,
    enabled: options?.enabled ?? !!segmentId,
  });
}

/**
 * Hook to create a segment
 */
export function useCreateSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (segment: SegmentCreate) => cdpApi.createSegment(segment),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.segments() });
    },
  });
}

/**
 * Hook to update a segment
 */
export function useUpdateSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ segmentId, update }: { segmentId: string; update: SegmentUpdate }) =>
      cdpApi.updateSegment(segmentId, update),
    onSuccess: (_, { segmentId }) => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.segments() });
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.segment(segmentId) });
    },
  });
}

/**
 * Hook to delete a segment
 */
export function useDeleteSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (segmentId: string) => cdpApi.deleteSegment(segmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.segments() });
    },
  });
}

/**
 * Hook to compute segment membership
 */
export function useComputeSegment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (segmentId: string) => cdpApi.computeSegment(segmentId),
    onSuccess: (_, segmentId) => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.segment(segmentId) });
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.segmentProfiles(segmentId) });
    },
  });
}

/**
 * Hook to preview segment membership
 */
export function usePreviewSegment() {
  return useMutation({
    mutationFn: (request: SegmentPreviewRequest) => cdpApi.previewSegment(request),
  });
}

/**
 * Hook to get profiles in a segment
 */
export function useSegmentProfiles(
  segmentId: string,
  params?: { limit?: number; offset?: number },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: [...cdpQueryKeys.segmentProfiles(segmentId), params],
    queryFn: () => cdpApi.getSegmentProfiles(segmentId, params),
    staleTime: 60 * 1000,
    enabled: options?.enabled ?? !!segmentId,
  });
}

/**
 * Hook to get segments a profile belongs to
 */
export function useProfileSegments(profileId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.profileSegments(profileId),
    queryFn: () => cdpApi.getProfileSegments(profileId),
    staleTime: 60 * 1000,
    enabled: options?.enabled ?? !!profileId,
  });
}

/**
 * Hook to delete a profile (GDPR)
 */
export function useDeleteProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      profileId,
      params,
    }: {
      profileId: string;
      params?: { delete_events?: boolean; reason?: string };
    }) => cdpApi.deleteProfile(profileId, params),
    onSuccess: (_, { profileId }) => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profile(profileId) });
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profiles() });
    },
  });
}

// Computed Traits Hooks

/**
 * Hook to list computed traits
 */
export function useComputedTraits(params?: {
  active_only?: boolean;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: [...cdpQueryKeys.traits(), params],
    queryFn: () => cdpApi.listTraits(params),
    staleTime: 60 * 1000,
  });
}

/**
 * Hook to get a computed trait by ID
 */
export function useComputedTrait(traitId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.trait(traitId),
    queryFn: () => cdpApi.getTrait(traitId),
    staleTime: 30 * 1000,
    enabled: options?.enabled ?? !!traitId,
  });
}

/**
 * Hook to create a computed trait
 */
export function useCreateComputedTrait() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (trait: ComputedTraitCreate) => cdpApi.createTrait(trait),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.traits() });
    },
  });
}

/**
 * Hook to delete a computed trait
 */
export function useDeleteComputedTrait() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (traitId: string) => cdpApi.deleteTrait(traitId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.traits() });
    },
  });
}

/**
 * Hook to compute all traits
 */
export function useComputeAllTraits() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => cdpApi.computeAllTraits(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profiles() });
    },
  });
}

// RFM Hooks

/**
 * Hook to get RFM scores for a profile
 */
export function useProfileRFM(
  profileId: string,
  params?: RFMConfig,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: [...cdpQueryKeys.profileRFM(profileId), params],
    queryFn: () => cdpApi.getProfileRFM(profileId, params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: options?.enabled ?? !!profileId,
  });
}

/**
 * Hook to compute RFM for all profiles
 */
export function useComputeRFMBatch() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (config?: RFMConfig) => cdpApi.computeRFMBatch(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.profiles() });
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.rfmSummary() });
    },
  });
}

/**
 * Hook to get RFM summary
 */
export function useRFMSummary() {
  return useQuery({
    queryKey: cdpQueryKeys.rfmSummary(),
    queryFn: () => cdpApi.getRFMSummary(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Funnel Hooks

/**
 * Hook to list funnels
 */
export function useFunnels(params?: { status?: FunnelStatus; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: [...cdpQueryKeys.funnels(), params],
    queryFn: () => cdpApi.listFunnels(params),
    staleTime: 60 * 1000,
  });
}

/**
 * Hook to get a funnel by ID
 */
export function useFunnel(funnelId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.funnel(funnelId),
    queryFn: () => cdpApi.getFunnel(funnelId),
    staleTime: 30 * 1000,
    enabled: options?.enabled ?? !!funnelId,
  });
}

/**
 * Hook to create a funnel
 */
export function useCreateFunnel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (funnel: FunnelCreate) => cdpApi.createFunnel(funnel),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.funnels() });
    },
  });
}

/**
 * Hook to update a funnel
 */
export function useUpdateFunnel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ funnelId, update }: { funnelId: string; update: FunnelUpdate }) =>
      cdpApi.updateFunnel(funnelId, update),
    onSuccess: (_, { funnelId }) => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.funnels() });
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.funnel(funnelId) });
    },
  });
}

/**
 * Hook to delete a funnel
 */
export function useDeleteFunnel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (funnelId: string) => cdpApi.deleteFunnel(funnelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.funnels() });
    },
  });
}

/**
 * Hook to compute funnel metrics
 */
export function useComputeFunnel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (funnelId: string) => cdpApi.computeFunnel(funnelId),
    onSuccess: (_, funnelId) => {
      queryClient.invalidateQueries({ queryKey: cdpQueryKeys.funnel(funnelId) });
    },
  });
}

/**
 * Hook to analyze funnel with date filtering
 */
export function useAnalyzeFunnel() {
  return useMutation({
    mutationFn: ({ funnelId, params }: { funnelId: string; params?: FunnelAnalysisRequest }) =>
      cdpApi.analyzeFunnel(funnelId, params),
  });
}

/**
 * Hook to get profiles that dropped off at a specific step
 */
export function useFunnelDropOffs(
  funnelId: string,
  step: number,
  params?: { limit?: number; offset?: number },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: [...cdpQueryKeys.funnelDropOffs(funnelId, step), params],
    queryFn: () => cdpApi.getFunnelDropOffs(funnelId, step, params),
    staleTime: 60 * 1000,
    enabled: options?.enabled ?? (!!funnelId && step > 0),
  });
}

/**
 * Hook to get a profile's funnel journeys
 */
export function useProfileFunnelJourneys(
  profileId: string,
  funnelId?: string,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: [...cdpQueryKeys.profileFunnels(profileId), funnelId],
    queryFn: () => cdpApi.getProfileFunnelJourneys(profileId, funnelId),
    staleTime: 60 * 1000,
    enabled: options?.enabled ?? !!profileId,
  });
}

// Profile Search Hook

/**
 * Hook to search profiles with advanced filters
 */
export function useSearchProfiles(params?: ProfileSearchParams, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...cdpQueryKeys.profileSearch(), params],
    queryFn: () => cdpApi.searchProfiles(params),
    staleTime: 30 * 1000,
    enabled: options?.enabled ?? true,
  });
}

/**
 * Hook to search profiles (mutation for on-demand searches)
 */
export function useSearchProfilesMutation() {
  return useMutation({
    mutationFn: (params?: ProfileSearchParams) => cdpApi.searchProfiles(params),
  });
}

// Audience Export Hook

/**
 * Hook to export audience with advanced filters
 */
export function useExportAudience() {
  return useMutation({
    mutationFn: (params?: AudienceExportParams) => cdpApi.exportAudience(params),
  });
}

// Analytics Hooks

/**
 * Hook to get event statistics
 * @param periodDays Analysis period in days (default 30)
 */
export function useEventStatistics(periodDays?: number, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.eventStatistics(periodDays),
    queryFn: () => cdpApi.getEventStatistics(periodDays),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: options?.enabled ?? true,
  });
}

/**
 * Hook to get event trends (period-over-period comparison)
 * @param periodDays Period in days for comparison (default 7)
 */
export function useEventTrends(periodDays?: number, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.eventTrends(periodDays),
    queryFn: () => cdpApi.getEventTrends(periodDays),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: options?.enabled ?? true,
  });
}

/**
 * Hook to get profile statistics
 */
export function useProfileStatistics(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: cdpQueryKeys.profileStatistics(),
    queryFn: () => cdpApi.getProfileStatistics(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: options?.enabled ?? true,
  });
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
        idempotencyKey?: string;
        context?: EventContext;
        consent?: EventConsent;
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
      };
      return cdpApi.ingestEvent(event, sourceKey);
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
      };
      return cdpApi.ingestEvent(event, sourceKey);
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
      };
      return cdpApi.ingestEvent(event, sourceKey);
    },
  };
}

// =============================================================================
// Audience Sync Types
// =============================================================================

export type SyncPlatform = 'meta' | 'google' | 'tiktok' | 'snapchat';
export type SyncStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'partial';
export type SyncOperation = 'create' | 'update' | 'replace' | 'delete';

export interface PlatformAudience {
  id: string;
  segment_id: string;
  platform: SyncPlatform;
  platform_audience_id: string | null;
  platform_audience_name: string;
  ad_account_id: string;
  description: string | null;
  auto_sync: boolean;
  sync_interval_hours: number;
  is_active: boolean;
  last_sync_at: string | null;
  last_sync_status: SyncStatus | null;
  platform_size: number | null;
  matched_size: number | null;
  match_rate: number | null;
  created_at: string;
  updated_at: string;
}

export interface SyncJob {
  id: string;
  platform_audience_id: string;
  operation: SyncOperation;
  status: SyncStatus;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  profiles_total: number;
  profiles_sent: number;
  profiles_added: number;
  profiles_removed: number;
  profiles_failed: number;
  error_message: string | null;
  triggered_by: string | null;
  created_at: string;
}

export interface ConnectedPlatform {
  platform: SyncPlatform;
  ad_accounts: Array<{
    ad_account_id: string;
    ad_account_name: string | null;
  }>;
}

export interface PlatformAudienceCreate {
  segment_id: string;
  platform: SyncPlatform;
  ad_account_id: string;
  audience_name: string;
  description?: string;
  auto_sync?: boolean;
  sync_interval_hours?: number;
}

export interface PlatformAudienceListResponse {
  audiences: PlatformAudience[];
  total: number;
}

export interface SyncHistoryResponse {
  jobs: SyncJob[];
}

// =============================================================================
// Audience Sync API
// =============================================================================

export const audienceSyncApi = {
  // Get connected platforms
  getConnectedPlatforms: async (): Promise<ConnectedPlatform[]> => {
    const response = await apiClient.get<ApiResponse<ConnectedPlatform[]>>(
      '/cdp/audience-sync/platforms'
    );
    return response.data.data;
  },

  // List platform audiences
  listPlatformAudiences: async (params?: {
    segment_id?: string;
    platform?: SyncPlatform;
    limit?: number;
    offset?: number;
  }): Promise<PlatformAudienceListResponse> => {
    const response = await apiClient.get<ApiResponse<PlatformAudienceListResponse>>(
      '/cdp/audience-sync/audiences',
      { params }
    );
    return response.data.data;
  },

  // Create platform audience
  createPlatformAudience: async (data: PlatformAudienceCreate): Promise<PlatformAudience> => {
    const response = await apiClient.post<ApiResponse<PlatformAudience>>(
      '/cdp/audience-sync/audiences',
      data
    );
    return response.data.data;
  },

  // Get platform audience
  getPlatformAudience: async (audienceId: string): Promise<PlatformAudience> => {
    const response = await apiClient.get<ApiResponse<PlatformAudience>>(
      `/cdp/audience-sync/audiences/${audienceId}`
    );
    return response.data.data;
  },

  // Trigger sync
  triggerSync: async (
    audienceId: string,
    operation: 'update' | 'replace' = 'update'
  ): Promise<SyncJob> => {
    const response = await apiClient.post<ApiResponse<SyncJob>>(
      `/cdp/audience-sync/audiences/${audienceId}/sync`,
      { operation }
    );
    return response.data.data;
  },

  // Get sync history
  getSyncHistory: async (audienceId: string, limit?: number): Promise<SyncHistoryResponse> => {
    const response = await apiClient.get<ApiResponse<SyncHistoryResponse>>(
      `/cdp/audience-sync/audiences/${audienceId}/history`,
      { params: { limit } }
    );
    return response.data.data;
  },

  // Delete platform audience
  deletePlatformAudience: async (audienceId: string, deleteFromPlatform = true): Promise<void> => {
    await apiClient.delete(`/cdp/audience-sync/audiences/${audienceId}`, {
      params: { delete_from_platform: deleteFromPlatform },
    });
  },

  // Get segment audiences
  getSegmentAudiences: async (segmentId: string): Promise<PlatformAudienceListResponse> => {
    const response = await apiClient.get<ApiResponse<PlatformAudienceListResponse>>(
      `/cdp/audience-sync/segments/${segmentId}/audiences`
    );
    return response.data.data;
  },

  // Sync segment to all platforms
  syncSegmentToAllPlatforms: async (
    segmentId: string,
    operation: 'update' | 'replace' = 'update'
  ): Promise<SyncJob[]> => {
    const response = await apiClient.post<ApiResponse<SyncJob[]>>(
      `/cdp/audience-sync/segments/${segmentId}/sync-all`,
      null,
      { params: { operation } }
    );
    return response.data.data;
  },
};

// =============================================================================
// Audience Sync Hooks
// =============================================================================

export function useConnectedPlatforms() {
  return useQuery({
    queryKey: [...cdpQueryKeys.all, 'connected-platforms'],
    queryFn: () => audienceSyncApi.getConnectedPlatforms(),
  });
}

export function usePlatformAudiences(params?: {
  segment_id?: string;
  platform?: SyncPlatform;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: [...cdpQueryKeys.all, 'platform-audiences', params],
    queryFn: () => audienceSyncApi.listPlatformAudiences(params),
  });
}

export function useSegmentAudiences(segmentId: string) {
  return useQuery({
    queryKey: [...cdpQueryKeys.all, 'segment-audiences', segmentId],
    queryFn: () => audienceSyncApi.getSegmentAudiences(segmentId),
    enabled: !!segmentId,
  });
}

export function useSyncHistory(audienceId: string, limit?: number) {
  return useQuery({
    queryKey: [...cdpQueryKeys.all, 'sync-history', audienceId, limit],
    queryFn: () => audienceSyncApi.getSyncHistory(audienceId, limit),
    enabled: !!audienceId,
  });
}

export function useCreatePlatformAudience() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: PlatformAudienceCreate) => audienceSyncApi.createPlatformAudience(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...cdpQueryKeys.all, 'platform-audiences'] });
      queryClient.invalidateQueries({ queryKey: [...cdpQueryKeys.all, 'segment-audiences'] });
    },
  });
}

export function useTriggerSync() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      audienceId,
      operation,
    }: {
      audienceId: string;
      operation?: 'update' | 'replace';
    }) => audienceSyncApi.triggerSync(audienceId, operation),
    onSuccess: (_, { audienceId }) => {
      queryClient.invalidateQueries({
        queryKey: [...cdpQueryKeys.all, 'sync-history', audienceId],
      });
      queryClient.invalidateQueries({
        queryKey: [...cdpQueryKeys.all, 'platform-audiences'],
      });
    },
  });
}

export function useDeletePlatformAudience() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      audienceId,
      deleteFromPlatform,
    }: {
      audienceId: string;
      deleteFromPlatform?: boolean;
    }) => audienceSyncApi.deletePlatformAudience(audienceId, deleteFromPlatform),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...cdpQueryKeys.all, 'platform-audiences'] });
      queryClient.invalidateQueries({ queryKey: [...cdpQueryKeys.all, 'segment-audiences'] });
    },
  });
}

export function useSyncSegmentToAllPlatforms() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      segmentId,
      operation,
    }: {
      segmentId: string;
      operation?: 'update' | 'replace';
    }) => audienceSyncApi.syncSegmentToAllPlatforms(segmentId, operation),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...cdpQueryKeys.all, 'platform-audiences'] });
      queryClient.invalidateQueries({ queryKey: [...cdpQueryKeys.all, 'sync-history'] });
    },
  });
}
