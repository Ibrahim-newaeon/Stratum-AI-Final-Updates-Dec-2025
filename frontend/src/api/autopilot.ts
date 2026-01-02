/**
 * Stratum AI - Autopilot API Hooks
 *
 * React Query hooks for autopilot action management:
 * - Action queue
 * - Approval workflow
 * - Status monitoring
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './client'

// =============================================================================
// Types
// =============================================================================

export type ActionStatus = 'queued' | 'approved' | 'applied' | 'failed' | 'dismissed'

export type ActionType =
  | 'budget_increase'
  | 'budget_decrease'
  | 'pause_campaign'
  | 'pause_adset'
  | 'pause_creative'
  | 'enable_campaign'
  | 'enable_adset'
  | 'enable_creative'
  | 'bid_increase'
  | 'bid_decrease'

export interface AutopilotAction {
  id: string
  date: string
  action_type: ActionType
  entity_type: 'campaign' | 'adset' | 'creative'
  entity_id: string
  entity_name: string | null
  platform: string
  action_json: Record<string, unknown>
  before_value: Record<string, unknown> | null
  after_value: Record<string, unknown> | null
  status: ActionStatus
  created_at: string
  approved_at: string | null
  applied_at: string | null
  error: string | null
}

export interface AutopilotStatus {
  autopilot_level: number
  autopilot_level_name: string
  pending_actions: number
  caps: {
    max_daily_budget_change: number
    max_budget_pct_change: number
    max_actions_per_day: number
  }
  enabled: boolean
}

export interface ActionsSummary {
  days: number
  start_date: string
  status_counts: Record<ActionStatus, number>
  type_counts: Record<ActionType, number>
  platform_counts: Record<string, number>
  total: number
  pending_approval: number
  success_rate: number
}

export interface QueueActionRequest {
  action_type: ActionType
  entity_type: 'campaign' | 'adset' | 'creative'
  entity_id: string
  entity_name: string
  platform: string
  action_json: Record<string, unknown>
  before_value?: Record<string, unknown>
}

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * Get current autopilot status for a tenant.
 */
export function useAutopilotStatus(tenantId: number) {
  return useQuery({
    queryKey: ['autopilot-status', tenantId],
    queryFn: async () => {
      const response = await api.get<{ data: AutopilotStatus }>(
        `/autopilot/tenant/${tenantId}/autopilot/status`
      )
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  })
}

/**
 * Get actions for a tenant.
 */
export function useAutopilotActions(
  tenantId: number,
  filters?: {
    date?: string
    status?: ActionStatus
    platform?: string
    limit?: number
  }
) {
  return useQuery({
    queryKey: ['autopilot-actions', tenantId, filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters?.date) params.append('date', filters.date)
      if (filters?.status) params.append('status', filters.status)
      if (filters?.platform) params.append('platform', filters.platform)
      if (filters?.limit) params.append('limit', filters.limit.toString())

      const response = await api.get<{
        data: { actions: AutopilotAction[]; count: number }
      }>(`/autopilot/tenant/${tenantId}/autopilot/actions?${params}`)
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  })
}

/**
 * Get actions summary for a tenant.
 */
export function useActionsSummary(tenantId: number, days: number = 7) {
  return useQuery({
    queryKey: ['autopilot-summary', tenantId, days],
    queryFn: async () => {
      const response = await api.get<{ data: ActionsSummary }>(
        `/autopilot/tenant/${tenantId}/autopilot/actions/summary?days=${days}`
      )
      return response.data.data
    },
    enabled: !!tenantId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

/**
 * Get a specific action by ID.
 */
export function useAutopilotAction(tenantId: number, actionId: string) {
  return useQuery({
    queryKey: ['autopilot-action', tenantId, actionId],
    queryFn: async () => {
      const response = await api.get<{ data: { action: AutopilotAction } }>(
        `/autopilot/tenant/${tenantId}/autopilot/actions/${actionId}`
      )
      return response.data.data.action
    },
    enabled: !!tenantId && !!actionId,
  })
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Queue a new action.
 */
export function useQueueAction(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: QueueActionRequest) => {
      const response = await api.post<{
        data: {
          action: AutopilotAction
          auto_approved: boolean
          requires_approval: boolean
          reason: string | null
        }
      }>(`/autopilot/tenant/${tenantId}/autopilot/actions`, request)
      return response.data.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autopilot-actions', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['autopilot-status', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['autopilot-summary', tenantId] })
    },
  })
}

/**
 * Approve an action.
 */
export function useApproveAction(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (actionId: string) => {
      const response = await api.post<{ data: { action: AutopilotAction } }>(
        `/autopilot/tenant/${tenantId}/autopilot/actions/${actionId}/approve`
      )
      return response.data.data.action
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autopilot-actions', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['autopilot-status', tenantId] })
    },
  })
}

/**
 * Approve multiple actions at once.
 */
export function useApproveAllActions(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (actionIds?: string[]) => {
      const response = await api.post<{ data: { approved_count: number } }>(
        `/autopilot/tenant/${tenantId}/autopilot/actions/approve-all`,
        actionIds ? { action_ids: actionIds } : undefined
      )
      return response.data.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autopilot-actions', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['autopilot-status', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['autopilot-summary', tenantId] })
    },
  })
}

/**
 * Dismiss an action.
 */
export function useDismissAction(tenantId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (actionId: string) => {
      const response = await api.post<{ data: { action: AutopilotAction } }>(
        `/autopilot/tenant/${tenantId}/autopilot/actions/${actionId}/dismiss`
      )
      return response.data.data.action
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['autopilot-actions', tenantId] })
      queryClient.invalidateQueries({ queryKey: ['autopilot-status', tenantId] })
    },
  })
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get human-readable action type label.
 */
export function getActionTypeLabel(type: ActionType): string {
  const labels: Record<ActionType, string> = {
    budget_increase: 'Budget Increase',
    budget_decrease: 'Budget Decrease',
    pause_campaign: 'Pause Campaign',
    pause_adset: 'Pause Ad Set',
    pause_creative: 'Pause Creative',
    enable_campaign: 'Enable Campaign',
    enable_adset: 'Enable Ad Set',
    enable_creative: 'Enable Creative',
    bid_increase: 'Bid Increase',
    bid_decrease: 'Bid Decrease',
  }
  return labels[type] || type
}

/**
 * Get status color for UI.
 */
export function getActionStatusColor(status: ActionStatus): string {
  const colors: Record<ActionStatus, string> = {
    queued: 'yellow',
    approved: 'blue',
    applied: 'green',
    failed: 'red',
    dismissed: 'gray',
  }
  return colors[status] || 'gray'
}

/**
 * Get status label.
 */
export function getActionStatusLabel(status: ActionStatus): string {
  const labels: Record<ActionStatus, string> = {
    queued: 'Pending Approval',
    approved: 'Approved',
    applied: 'Applied',
    failed: 'Failed',
    dismissed: 'Dismissed',
  }
  return labels[status] || status
}

/**
 * Get platform icon.
 */
export function getPlatformIcon(platform: string): string {
  const icons: Record<string, string> = {
    meta: '📘',
    google: '🔴',
    tiktok: '🎵',
    snapchat: '👻',
  }
  return icons[platform] || '📊'
}
