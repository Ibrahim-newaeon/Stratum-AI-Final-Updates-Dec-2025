/**
 * Stratum AI - Team API
 *
 * Tenant-scoped team member management (backed by /users endpoints).
 * Replaces the former adminApi wiring in TeamManagement, which pointed
 * at /admin/users routes that do not exist on the backend.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface TeamMember {
  id: number
  tenant_id: number
  email: string
  full_name: string | null
  role: string
  department: string | null
  is_active: boolean
  is_verified: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
}

export interface InviteTeamMemberRequest {
  email: string
  full_name?: string
  role?: string
  department?: string
}

export interface UpdateTeamMemberRequest {
  full_name?: string
  role?: string
  is_active?: boolean
  department?: string | null
}

// API functions
export const teamApi = {
  list: async (): Promise<TeamMember[]> => {
    const response = await apiClient.get<ApiResponse<TeamMember[]>>('/users')
    return response.data.data
  },

  invite: async (data: InviteTeamMemberRequest): Promise<TeamMember> => {
    const response = await apiClient.post<ApiResponse<TeamMember>>('/users/invite', data)
    return response.data.data
  },

  update: async (userId: number, data: UpdateTeamMemberRequest): Promise<TeamMember> => {
    const response = await apiClient.patch<ApiResponse<TeamMember>>(`/users/${userId}`, data)
    return response.data.data
  },

  remove: async (userId: number): Promise<void> => {
    await apiClient.delete(`/users/${userId}`)
  },
}

// React Query hooks
export function useTeamMembers() {
  return useQuery({
    queryKey: ['team', 'members'],
    queryFn: teamApi.list,
    staleTime: 30 * 1000,
  })
}

export function useInviteTeamMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: teamApi.invite,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team', 'members'] })
    },
  })
}

export function useUpdateTeamMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, data }: { userId: number; data: UpdateTeamMemberRequest }) =>
      teamApi.update(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team', 'members'] })
    },
  })
}

export function useRemoveTeamMember() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: teamApi.remove,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['team', 'members'] })
    },
  })
}
