/**
 * Stratum AI - Launch Readiness API
 *
 * Superadmin-only. Drives the sequential go-live wizard: phase N+1 is
 * locked until phase N is 100% complete. Each check/uncheck appends to
 * an immutable audit trail.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------
export interface LaunchReadinessItem {
  key: string
  title: string
  description?: string | null
  is_checked: boolean
  checked_by_user_id?: number | null
  checked_by_user_name?: string | null
  checked_at?: string | null
  note?: string | null
}

export interface LaunchReadinessPhase {
  number: number
  slug: string
  title: string
  description?: string | null
  items: LaunchReadinessItem[]
  completed_count: number
  total_count: number
  is_complete: boolean
  is_active: boolean
  is_locked: boolean
}

export interface LaunchReadinessState {
  phases: LaunchReadinessPhase[]
  current_phase_number: number
  overall_completed: number
  overall_total: number
  is_launched: boolean
}

export type LaunchReadinessEventAction =
  | 'checked'
  | 'unchecked'
  | 'phase_completed'
  | 'phase_reopened'

export interface LaunchReadinessEvent {
  id: number
  phase_number: number
  item_key?: string | null
  action: LaunchReadinessEventAction | string
  user_id?: number | null
  user_name?: string | null
  note?: string | null
  created_at: string
}

export interface ToggleItemRequest {
  itemKey: string
  checked: boolean
  note?: string
}

// -----------------------------------------------------------------------------
// API functions
// -----------------------------------------------------------------------------
export const launchReadinessApi = {
  getState: async (): Promise<LaunchReadinessState> => {
    const response = await apiClient.get<ApiResponse<LaunchReadinessState>>(
      '/superadmin/launch-readiness'
    )
    return response.data.data
  },

  toggleItem: async ({
    itemKey,
    checked,
    note,
  }: ToggleItemRequest): Promise<LaunchReadinessState> => {
    const response = await apiClient.patch<ApiResponse<LaunchReadinessState>>(
      `/superadmin/launch-readiness/items/${encodeURIComponent(itemKey)}`,
      { checked, note: note ?? null }
    )
    return response.data.data
  },

  getEvents: async (params: { phaseNumber?: number; limit?: number } = {}): Promise<
    LaunchReadinessEvent[]
  > => {
    const response = await apiClient.get<ApiResponse<LaunchReadinessEvent[]>>(
      '/superadmin/launch-readiness/events',
      {
        params: {
          phase_number: params.phaseNumber,
          limit: params.limit ?? 100,
        },
      }
    )
    return response.data.data
  },
}

// -----------------------------------------------------------------------------
// React Query hooks
// -----------------------------------------------------------------------------
const stateKey = ['launch-readiness', 'state'] as const
const eventsKey = (phaseNumber?: number) =>
  ['launch-readiness', 'events', phaseNumber ?? 'all'] as const

export function useLaunchReadinessState() {
  return useQuery({
    queryKey: stateKey,
    queryFn: launchReadinessApi.getState,
    staleTime: 10 * 1000,
  })
}

export function useToggleLaunchReadinessItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: launchReadinessApi.toggleItem,
    onSuccess: (state) => {
      // Server already returned the fresh state; seed the cache
      // then invalidate the events log.
      queryClient.setQueryData(stateKey, state)
      queryClient.invalidateQueries({ queryKey: ['launch-readiness', 'events'] })
    },
  })
}

export function useLaunchReadinessEvents(phaseNumber?: number, limit = 100) {
  return useQuery({
    queryKey: eventsKey(phaseNumber),
    queryFn: () => launchReadinessApi.getEvents({ phaseNumber, limit }),
    staleTime: 30 * 1000,
  })
}
