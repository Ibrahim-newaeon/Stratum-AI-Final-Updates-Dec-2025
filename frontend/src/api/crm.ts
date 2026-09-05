/**
 * Stratum AI - CRM Integration API
 *
 * Talks to the tenant-scoped CRM surface at /integrations/crm. The tenant is
 * taken from the caller's token, so nothing here sends a tenant id.
 *
 * Field names are the API's, unchanged. The client sends no case transform
 * (see api/client.ts), so renaming them here would mean maintaining a second
 * spelling of every field for no gain.
 *
 * This module previously declared a much wider surface — contact detail,
 * contact journey, deal detail, pipeline metrics, writeback history, writeback
 * retry, connect, disconnect, connection settings — against endpoints that
 * were never built, and typed it with fields the backend does not store
 * (contact email and name are held only as SHA256 hashes). Nothing rendered
 * any of it. Those declarations are gone rather than left pointing at 404s;
 * add them back alongside the endpoint when a view needs one.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse, PaginatedResponse } from './client'

// =============================================================================
// Types
// =============================================================================

export type CRMProvider = 'hubspot' | 'pipedrive'
export type CRMConnectionStatus = 'pending' | 'connected' | 'disconnected' | 'error' | 'syncing'
export type DealStage = 'lead' | 'qualified' | 'proposal' | 'negotiation' | 'won' | 'lost'

export interface CRMConnection {
  id: string
  provider: CRMProvider
  status: CRMConnectionStatus
  status_message?: string | null
  provider_account_id?: string | null
  provider_account_name?: string | null
  sync_contacts: boolean
  sync_deals: boolean
  sync_companies: boolean
  last_sync_at?: string | null
  last_sync_status?: string | null
  last_sync_contacts_count?: number | null
  last_sync_deals_count?: number | null
  created_at: string
  updated_at: string
}

/**
 * A synced contact. Carries no email, name, phone or company: crm_contacts
 * stores only email_hash and phone_hash, so there is no plaintext to return.
 */
export interface CRMContact {
  id: string
  crm_contact_id: string
  lifecycle_stage?: string | null
  lead_source?: string | null
  first_touch_campaign_id?: string | null
  last_touch_campaign_id?: string | null
  first_touch_ts?: string | null
  last_touch_ts?: string | null
  touch_count?: number | null
  stratum_quality_score?: number | null
}

/** A synced deal. Value is in cents; the float `amount` column is deprecated. */
export interface CRMDeal {
  id: string
  crm_deal_id: string
  deal_name?: string | null
  stage?: string | null
  stage_normalized?: DealStage | null
  amount_cents?: number | null
  currency: string
  close_date?: string | null
  expected_close_date?: string | null
  is_won: boolean
  is_closed: boolean
  won_at?: string | null
  attributed_campaign_id?: string | null
  attributed_platform?: string | null
}

export interface PipelineSummary {
  /** 'not_connected' when the tenant has no CRM connection at all. */
  status: string
  stage_counts: Record<string, number>
  stage_values: Record<string, number>
  total_pipeline_value: number
  total_won_value: number
  won_deal_count: number
  last_sync_at?: string | null
}

export interface WritebackConfig {
  id: string
  connection_id: string
  enabled: boolean
  sync_contacts: boolean
  sync_deals: boolean
  auto_sync_enabled: boolean
  sync_interval_hours: number
  sync_attribution: boolean
  sync_profit_metrics: boolean
  sync_touchpoint_count: boolean
  properties_created: boolean
  last_sync_at?: string | null
  last_sync_status?: string | null
  last_sync_contacts?: number | null
  last_sync_deals?: number | null
  last_sync_errors?: number | null
  next_sync_at?: string | null
}

export interface WritebackConfigUpdate {
  enabled?: boolean
  sync_contacts?: boolean
  sync_deals?: boolean
  auto_sync_enabled?: boolean
  sync_interval_hours?: number
  sync_attribution?: boolean
  sync_profit_metrics?: boolean
  sync_touchpoint_count?: boolean
}

export interface SyncTriggerResult {
  connection_id: string
  provider: CRMProvider
  /** 'queued' on success; 'not_connected' or 'unsupported' otherwise. */
  status: string
  contacts_synced: number
  deals_synced: number
  message?: string | null
}

// =============================================================================
// API Functions
// =============================================================================

export const crmApi = {
  getConnections: async () => {
    const response = await apiClient.get<ApiResponse<CRMConnection[]>>(
      '/integrations/crm/connections'
    )
    return response.data.data
  },

  triggerSync: async (connectionId: string) => {
    const response = await apiClient.post<ApiResponse<SyncTriggerResult>>(
      `/integrations/crm/connections/${connectionId}/sync`
    )
    return response.data.data
  },

  getContacts: async (params?: { limit?: number; offset?: number; lifecycle_stage?: string }) => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<CRMContact>>>(
      '/integrations/crm/contacts',
      { params }
    )
    return response.data.data
  },

  getDeals: async (params?: { limit?: number; offset?: number; stage?: DealStage }) => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<CRMDeal>>>(
      '/integrations/crm/deals',
      { params }
    )
    return response.data.data
  },

  getPipelineSummary: async () => {
    const response = await apiClient.get<ApiResponse<PipelineSummary>>(
      '/integrations/crm/pipeline/summary'
    )
    return response.data.data
  },

  getWritebackConfig: async () => {
    const response = await apiClient.get<ApiResponse<WritebackConfig | null>>(
      '/integrations/crm/writeback/config'
    )
    return response.data.data
  },

  updateWritebackConfig: async (config: WritebackConfigUpdate) => {
    const response = await apiClient.put<ApiResponse<WritebackConfig>>(
      '/integrations/crm/writeback/config',
      config
    )
    return response.data.data
  },
}

// =============================================================================
// React Query Hooks
// =============================================================================

export function useCRMConnections() {
  return useQuery({
    queryKey: ['crm', 'connections'],
    queryFn: crmApi.getConnections,
  })
}

export function useTriggerCRMSync() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: crmApi.triggerSync,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm'] })
    },
  })
}

export function useCRMContacts(params?: {
  limit?: number
  offset?: number
  lifecycle_stage?: string
}) {
  return useQuery({
    queryKey: ['crm', 'contacts', params],
    queryFn: () => crmApi.getContacts(params),
  })
}

export function useCRMDeals(params?: { limit?: number; offset?: number; stage?: DealStage }) {
  return useQuery({
    queryKey: ['crm', 'deals', params],
    queryFn: () => crmApi.getDeals(params),
  })
}

export function usePipelineSummary() {
  return useQuery({
    queryKey: ['crm', 'pipeline', 'summary'],
    queryFn: crmApi.getPipelineSummary,
  })
}

export function useWritebackConfig() {
  return useQuery({
    queryKey: ['crm', 'writeback', 'config'],
    queryFn: crmApi.getWritebackConfig,
  })
}

export function useUpdateWritebackConfig() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: crmApi.updateWritebackConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm', 'writeback'] })
    },
  })
}
