/**
 * Stratum AI - Campaign Builder API Hooks
 *
 * React Query hooks for the Campaign Builder feature:
 * - Platform connectors
 * - Ad accounts
 * - Campaign drafts
 * - Publish logs
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './client'

// =============================================================================
// Types
// =============================================================================

export type Platform = 'meta' | 'google' | 'tiktok' | 'snapchat'
export type ConnectionStatus = 'connected' | 'expired' | 'error' | 'disconnected'
export type DraftStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'publishing' | 'published' | 'failed'
export type PublishResult = 'success' | 'failure'

export interface ConnectorStatus {
  platform: string
  status: ConnectionStatus
  connected_at?: string
  last_refreshed_at?: string
  scopes: string[]
  last_error?: string
}

export interface AdAccount {
  id: string
  platform: string
  platform_account_id: string
  name: string
  business_name?: string
  currency: string
  timezone: string
  is_enabled: boolean
  daily_budget_cap?: number
  last_synced_at?: string
}

export interface CampaignDraft {
  id: string
  tenant_id: number
  platform: string
  ad_account_id?: string
  name: string
  description?: string
  status: DraftStatus
  draft_json: Record<string, any>
  created_at: string
  updated_at: string
  submitted_at?: string
  approved_at?: string
  rejected_at?: string
  rejection_reason?: string
  platform_campaign_id?: string
  published_at?: string
}

export interface PublishLog {
  id: string
  draft_id?: string
  platform: string
  platform_account_id: string
  event_time: string
  result_status: PublishResult
  platform_campaign_id?: string
  error_code?: string
  error_message?: string
  retry_count: number
}

export interface CreateDraftPayload {
  platform: string
  ad_account_id: string
  name: string
  description?: string
  draft_json: Record<string, any>
}

export interface UpdateDraftPayload {
  name?: string
  description?: string
  draft_json?: Record<string, any>
}

// =============================================================================
// Connector Hooks
// =============================================================================

export function useConnectorStatus(tenantId: number, platform: Platform) {
  return useQuery({
    queryKey: ['connector-status', tenantId, platform],
    queryFn: async () => {
      const response = await api.get<{ data: ConnectorStatus }>(
        `/tenant/${tenantId}/connect/${platform}/status`
      )
      return response.data.data
    },
    enabled: !!tenantId && !!platform,
  })
}

export function useStartConnection(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (platform: Platform) => {
      const response = await api.post<{ data: { oauth_url: string } }>(
        `/tenant/${tenantId}/connect/${platform}/start`
      )
      return response.data.data
    },
    onSuccess: (_, platform) => {
      queryClient.invalidateQueries({ queryKey: ['connector-status', tenantId, platform] })
    },
  })
}

export function useRefreshToken(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (platform: Platform) => {
      const response = await api.post(`/tenant/${tenantId}/connect/${platform}/refresh`)
      return response.data
    },
    onSuccess: (_, platform) => {
      queryClient.invalidateQueries({ queryKey: ['connector-status', tenantId, platform] })
    },
  })
}

export function useDisconnectPlatform(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (platform: Platform) => {
      const response = await api.delete(`/tenant/${tenantId}/connect/${platform}`)
      return response.data
    },
    onSuccess: (_, platform) => {
      queryClient.invalidateQueries({ queryKey: ['connector-status', tenantId, platform] })
      queryClient.invalidateQueries({ queryKey: ['ad-accounts', tenantId, platform] })
    },
  })
}

// =============================================================================
// Ad Account Hooks
// =============================================================================

export function useAdAccounts(tenantId: number, platform: Platform, enabledOnly = false) {
  return useQuery({
    queryKey: ['ad-accounts', tenantId, platform, enabledOnly],
    queryFn: async () => {
      const response = await api.get<{ data: AdAccount[] }>(
        `/tenant/${tenantId}/ad-accounts/${platform}`,
        { params: { enabled_only: enabledOnly } }
      )
      return response.data.data
    },
    enabled: !!tenantId && !!platform,
  })
}

export function useSyncAdAccounts(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (platform: Platform) => {
      const response = await api.post(`/tenant/${tenantId}/ad-accounts/${platform}/sync`)
      return response.data
    },
    onSuccess: (_, platform) => {
      // Delay refetch to allow sync to complete
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['ad-accounts', tenantId, platform] })
      }, 2000)
    },
  })
}

export function useUpdateAdAccount(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      platform,
      accountId,
      data,
    }: {
      platform: Platform
      accountId: string
      data: { is_enabled?: boolean; daily_budget_cap?: number }
    }) => {
      const response = await api.put<{ data: AdAccount }>(
        `/tenant/${tenantId}/ad-accounts/${platform}/${accountId}`,
        data
      )
      return response.data.data
    },
    onSuccess: (_, { platform }) => {
      queryClient.invalidateQueries({ queryKey: ['ad-accounts', tenantId, platform] })
    },
  })
}

// =============================================================================
// Campaign Draft Hooks
// =============================================================================

export function useCampaignDrafts(
  tenantId: number,
  filters?: {
    platform?: Platform
    status?: DraftStatus
    ad_account_id?: string
  }
) {
  return useQuery({
    queryKey: ['campaign-drafts', tenantId, filters],
    queryFn: async () => {
      const response = await api.get<{ data: CampaignDraft[] }>(
        `/tenant/${tenantId}/campaign-drafts`,
        { params: filters }
      )
      return response.data.data
    },
    enabled: !!tenantId,
  })
}

export function useCampaignDraft(tenantId: number, draftId: string) {
  return useQuery({
    queryKey: ['campaign-draft', tenantId, draftId],
    queryFn: async () => {
      const response = await api.get<{ data: CampaignDraft }>(
        `/tenant/${tenantId}/campaign-drafts/${draftId}`
      )
      return response.data.data
    },
    enabled: !!tenantId && !!draftId,
  })
}

export function useCreateCampaignDraft(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CreateDraftPayload) => {
      const response = await api.post<{ data: CampaignDraft }>(
        `/tenant/${tenantId}/campaign-drafts`,
        data
      )
      return response.data.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign-drafts', tenantId] })
    },
  })
}

export function useUpdateCampaignDraft(tenantId: number, draftId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: UpdateDraftPayload) => {
      const response = await api.put<{ data: CampaignDraft }>(
        `/tenant/${tenantId}/campaign-drafts/${draftId}`,
        data
      )
      return response.data.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaign-drafts', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['campaign-draft', tenantId, draftId] })
    },
  })
}

export function useSubmitDraft(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (draftId: string) => {
      const response = await api.post<{ data: CampaignDraft }>(
        `/tenant/${tenantId}/campaign-drafts/${draftId}/submit`
      )
      return response.data.data
    },
    onSuccess: (_, draftId) => {
      queryClient.invalidateQueries({ queryKey: ['campaign-drafts', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['campaign-draft', tenantId, draftId] })
    },
  })
}

export function useApproveDraft(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (draftId: string) => {
      const response = await api.post<{ data: CampaignDraft }>(
        `/tenant/${tenantId}/campaign-drafts/${draftId}/approve`
      )
      return response.data.data
    },
    onSuccess: (_, draftId) => {
      queryClient.invalidateQueries({ queryKey: ['campaign-drafts', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['campaign-draft', tenantId, draftId] })
    },
  })
}

export function useRejectDraft(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ draftId, reason }: { draftId: string; reason: string }) => {
      const response = await api.post<{ data: CampaignDraft }>(
        `/tenant/${tenantId}/campaign-drafts/${draftId}/reject`,
        null,
        { params: { reason } }
      )
      return response.data.data
    },
    onSuccess: (_, { draftId }) => {
      queryClient.invalidateQueries({ queryKey: ['campaign-drafts', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['campaign-draft', tenantId, draftId] })
    },
  })
}

export function usePublishDraft(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (draftId: string) => {
      const response = await api.post<{ data: CampaignDraft }>(
        `/tenant/${tenantId}/campaign-drafts/${draftId}/publish`
      )
      return response.data.data
    },
    onSuccess: (_, draftId) => {
      queryClient.invalidateQueries({ queryKey: ['campaign-drafts', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['campaign-draft', tenantId, draftId] })
      queryClient.invalidateQueries({ queryKey: ['publish-logs', tenantId] })
    },
  })
}

// =============================================================================
// Publish Log Hooks
// =============================================================================

export function usePublishLogs(
  tenantId: number,
  filters?: {
    draft_id?: string
    platform?: Platform
    result_status?: PublishResult
  }
) {
  return useQuery({
    queryKey: ['publish-logs', tenantId, filters],
    queryFn: async () => {
      const response = await api.get<{ data: PublishLog[] }>(
        `/tenant/${tenantId}/campaign-publish-logs`,
        { params: filters }
      )
      return response.data.data
    },
    enabled: !!tenantId,
  })
}

export function useRetryPublish(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (logId: string) => {
      const response = await api.post(`/tenant/${tenantId}/campaign-publish-logs/${logId}/retry`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['publish-logs', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['campaign-drafts', tenantId] })
    },
  })
}
