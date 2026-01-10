/**
 * Stratum AI - CRM Integration API
 *
 * Handles HubSpot integration, contacts, deals, and sync operations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse, PaginatedResponse } from './client'

// =============================================================================
// Types
// =============================================================================

export type CRMProvider = 'hubspot' | 'salesforce' | 'zoho'
export type CRMConnectionStatus = 'connected' | 'disconnected' | 'error' | 'syncing'
export type DealStage = 'lead' | 'qualified' | 'proposal' | 'negotiation' | 'won' | 'lost'
export type WritebackStatus = 'pending' | 'synced' | 'failed' | 'skipped'

export interface CRMConnection {
  id: string
  tenantId: number
  provider: CRMProvider
  status: CRMConnectionStatus
  portalId?: string
  portalName?: string
  lastSyncAt?: string
  syncEnabled: boolean
  syncFrequencyMinutes: number
  objectsToSync: string[]
  totalContacts: number
  totalDeals: number
  createdAt: string
  updatedAt: string
}

export interface CRMContact {
  id: string
  tenantId: number
  crmProvider: CRMProvider
  externalId: string
  email?: string
  firstName?: string
  lastName?: string
  company?: string
  phone?: string
  lifecycleStage?: string
  leadSource?: string
  firstTouchChannel?: string
  lastTouchChannel?: string
  touchpointCount: number
  totalDealValue: number
  properties: Record<string, any>
  createdAt: string
  updatedAt: string
}

export interface CRMDeal {
  id: string
  tenantId: number
  contactId: string
  crmProvider: CRMProvider
  externalId: string
  dealName: string
  amount: number
  currency: string
  stage: DealStage
  pipeline?: string
  closeDate?: string
  closedWonDate?: string
  probability: number
  touchpointCount: number
  attributedRevenue: Record<string, number>
  properties: Record<string, any>
  createdAt: string
  updatedAt: string
}

export interface Touchpoint {
  id: string
  tenantId: number
  contactId: string
  dealId?: string
  channel: string
  source: string
  medium?: string
  campaign?: string
  content?: string
  platform?: string
  adId?: string
  timestamp: string
  isConverting: boolean
  properties: Record<string, any>
}

export interface PipelineMetrics {
  date: string
  dealsCreated: number
  dealsWon: number
  dealsLost: number
  revenueCreated: number
  revenueWon: number
  avgDealSize: number
  avgCycleTime: number
  conversionRate: number
  pipelineValue: number
}

export interface WritebackConfig {
  id: string
  tenantId: number
  enabled: boolean
  propertyMappings: Record<string, string>
  syncTriggers: string[]
  lastSyncAt?: string
  errorCount: number
}

export interface WritebackSync {
  id: string
  entityType: string
  entityId: string
  status: WritebackStatus
  syncedAt?: string
  errorMessage?: string
  dataSnapshot: Record<string, any>
}

// =============================================================================
// API Functions
// =============================================================================

export const crmApi = {
  // Connections
  getConnections: async () => {
    const response = await apiClient.get<ApiResponse<CRMConnection[]>>('/integrations/crm/connections')
    return response.data.data
  },

  getConnection: async (connectionId: string) => {
    const response = await apiClient.get<ApiResponse<CRMConnection>>(`/integrations/crm/connections/${connectionId}`)
    return response.data.data
  },

  connectHubSpot: async (authCode: string) => {
    const response = await apiClient.post<ApiResponse<CRMConnection>>('/integrations/crm/hubspot/connect', {
      auth_code: authCode,
    })
    return response.data.data
  },

  disconnectCRM: async (connectionId: string) => {
    const response = await apiClient.delete<ApiResponse<void>>(`/integrations/crm/connections/${connectionId}`)
    return response.data
  },

  updateConnectionSettings: async (connectionId: string, settings: Partial<CRMConnection>) => {
    const response = await apiClient.patch<ApiResponse<CRMConnection>>(
      `/integrations/crm/connections/${connectionId}`,
      settings
    )
    return response.data.data
  },

  // Sync
  triggerSync: async (connectionId: string) => {
    const response = await apiClient.post<ApiResponse<{ syncId: string }>>(`/integrations/crm/connections/${connectionId}/sync`)
    return response.data.data
  },

  getSyncStatus: async (connectionId: string) => {
    const response = await apiClient.get<ApiResponse<{ status: string; progress: number; lastSync: string }>>(
      `/integrations/crm/connections/${connectionId}/sync-status`
    )
    return response.data.data
  },

  // Contacts
  getContacts: async (params?: { page?: number; limit?: number; search?: string }) => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<CRMContact>>>('/integrations/crm/contacts', { params })
    return response.data.data
  },

  getContact: async (contactId: string) => {
    const response = await apiClient.get<ApiResponse<CRMContact>>(`/integrations/crm/contacts/${contactId}`)
    return response.data.data
  },

  getContactJourney: async (contactId: string) => {
    const response = await apiClient.get<ApiResponse<{ contact: CRMContact; touchpoints: Touchpoint[]; deals: CRMDeal[] }>>(
      `/integrations/crm/contacts/${contactId}/journey`
    )
    return response.data.data
  },

  // Deals
  getDeals: async (params?: { page?: number; limit?: number; stage?: DealStage; search?: string }) => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<CRMDeal>>>('/integrations/crm/deals', { params })
    return response.data.data
  },

  getDeal: async (dealId: string) => {
    const response = await apiClient.get<ApiResponse<CRMDeal>>(`/integrations/crm/deals/${dealId}`)
    return response.data.data
  },

  // Pipeline Metrics
  getPipelineMetrics: async (params: { startDate: string; endDate: string }) => {
    const response = await apiClient.get<ApiResponse<PipelineMetrics[]>>('/integrations/crm/pipeline/metrics', { params })
    return response.data.data
  },

  getPipelineSummary: async () => {
    const response = await apiClient.get<ApiResponse<{
      totalDeals: number
      totalValue: number
      avgDealSize: number
      conversionRate: number
      byStage: Record<DealStage, { count: number; value: number }>
    }>>('/integrations/crm/pipeline/summary')
    return response.data.data
  },

  // Writeback
  getWritebackConfig: async () => {
    const response = await apiClient.get<ApiResponse<WritebackConfig>>('/integrations/crm/writeback/config')
    return response.data.data
  },

  updateWritebackConfig: async (config: Partial<WritebackConfig>) => {
    const response = await apiClient.put<ApiResponse<WritebackConfig>>('/integrations/crm/writeback/config', config)
    return response.data.data
  },

  getWritebackHistory: async (params?: { page?: number; limit?: number; status?: WritebackStatus }) => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<WritebackSync>>>('/integrations/crm/writeback/history', { params })
    return response.data.data
  },

  retryWriteback: async (syncId: string) => {
    const response = await apiClient.post<ApiResponse<WritebackSync>>(`/integrations/crm/writeback/${syncId}/retry`)
    return response.data.data
  },
}

// =============================================================================
// React Query Hooks
// =============================================================================

// Connections
export function useCRMConnections() {
  return useQuery({
    queryKey: ['crm', 'connections'],
    queryFn: crmApi.getConnections,
  })
}

export function useCRMConnection(connectionId: string) {
  return useQuery({
    queryKey: ['crm', 'connections', connectionId],
    queryFn: () => crmApi.getConnection(connectionId),
    enabled: !!connectionId,
  })
}

export function useConnectHubSpot() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: crmApi.connectHubSpot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm', 'connections'] })
    },
  })
}

export function useDisconnectCRM() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: crmApi.disconnectCRM,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm', 'connections'] })
    },
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

// Contacts
export function useCRMContacts(params?: { page?: number; limit?: number; search?: string }) {
  return useQuery({
    queryKey: ['crm', 'contacts', params],
    queryFn: () => crmApi.getContacts(params),
  })
}

export function useCRMContact(contactId: string) {
  return useQuery({
    queryKey: ['crm', 'contacts', contactId],
    queryFn: () => crmApi.getContact(contactId),
    enabled: !!contactId,
  })
}

export function useContactJourney(contactId: string) {
  return useQuery({
    queryKey: ['crm', 'contacts', contactId, 'journey'],
    queryFn: () => crmApi.getContactJourney(contactId),
    enabled: !!contactId,
  })
}

// Deals
export function useCRMDeals(params?: { page?: number; limit?: number; stage?: DealStage; search?: string }) {
  return useQuery({
    queryKey: ['crm', 'deals', params],
    queryFn: () => crmApi.getDeals(params),
  })
}

export function useCRMDeal(dealId: string) {
  return useQuery({
    queryKey: ['crm', 'deals', dealId],
    queryFn: () => crmApi.getDeal(dealId),
    enabled: !!dealId,
  })
}

// Pipeline
export function usePipelineMetrics(startDate: string, endDate: string) {
  return useQuery({
    queryKey: ['crm', 'pipeline', 'metrics', startDate, endDate],
    queryFn: () => crmApi.getPipelineMetrics({ startDate, endDate }),
    enabled: !!startDate && !!endDate,
  })
}

export function usePipelineSummary() {
  return useQuery({
    queryKey: ['crm', 'pipeline', 'summary'],
    queryFn: crmApi.getPipelineSummary,
  })
}

// Writeback
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

export function useWritebackHistory(params?: { page?: number; limit?: number; status?: WritebackStatus }) {
  return useQuery({
    queryKey: ['crm', 'writeback', 'history', params],
    queryFn: () => crmApi.getWritebackHistory(params),
  })
}

export function useRetryWriteback() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: crmApi.retryWriteback,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm', 'writeback'] })
    },
  })
}
