/**
 * Stratum AI - Clients API
 *
 * Client management, assignments, and portal invitations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse, PaginatedResponse } from './client'

// Types
export interface Client {
  id: number
  tenant_id: number
  name: string
  slug: string
  logo_url?: string
  industry?: string
  website?: string
  currency: string
  timezone: string
  monthly_budget_cents?: number
  target_roas?: number
  target_cpa_cents?: number
  target_ctr?: number
  budget_alert_threshold: number
  roas_alert_threshold?: number
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  notes?: string
  settings?: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ClientListItem {
  id: number
  tenant_id: number
  name: string
  slug: string
  industry?: string
  currency: string
  is_active: boolean
  monthly_budget_cents?: number
  target_roas?: number
  created_at: string
  total_campaigns?: number
  total_spend_cents?: number
}

export interface ClientCreate {
  name: string
  slug: string
  logo_url?: string
  industry?: string
  website?: string
  currency?: string
  timezone?: string
  monthly_budget_cents?: number
  target_roas?: number
  target_cpa_cents?: number
  target_ctr?: number
  budget_alert_threshold?: number
  roas_alert_threshold?: number
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  notes?: string
  settings?: Record<string, unknown>
}

export interface ClientUpdate {
  name?: string
  slug?: string
  logo_url?: string
  industry?: string
  website?: string
  currency?: string
  timezone?: string
  monthly_budget_cents?: number
  target_roas?: number
  target_cpa_cents?: number
  target_ctr?: number
  budget_alert_threshold?: number
  roas_alert_threshold?: number
  contact_name?: string
  contact_email?: string
  contact_phone?: string
  notes?: string
  settings?: Record<string, unknown>
}

export interface ClientAssignment {
  id: number
  user_id: number
  client_id: number
  assigned_by?: number
  is_primary: boolean
  created_at: string
  user_email?: string
  user_name?: string
  user_role?: string
}

export interface ClientPortalInviteRequest {
  email: string
  full_name: string
}

export interface ClientFilters {
  page?: number
  page_size?: number
  search?: string
  is_active?: boolean
  industry?: string
}

// API Functions
export const clientsApi = {
  getClients: async (filters: ClientFilters = {}): Promise<PaginatedResponse<ClientListItem>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<ClientListItem>>>('/clients', {
      params: filters,
    })
    return response.data.data
  },

  createClient: async (data: ClientCreate): Promise<Client> => {
    const response = await apiClient.post<ApiResponse<Client>>('/clients', data)
    return response.data.data
  },

  getClient: async (id: number): Promise<Client> => {
    const response = await apiClient.get<ApiResponse<Client>>(`/clients/${id}`)
    return response.data.data
  },

  updateClient: async (id: number, data: ClientUpdate): Promise<Client> => {
    const response = await apiClient.patch<ApiResponse<Client>>(`/clients/${id}`, data)
    return response.data.data
  },

  deleteClient: async (id: number): Promise<void> => {
    await apiClient.delete(`/clients/${id}`)
  },

  getClientUsers: async (id: number): Promise<ClientAssignment[]> => {
    const response = await apiClient.get<ApiResponse<ClientAssignment[]>>(`/clients/${id}/assignments`)
    return response.data.data
  },

  invitePortalUser: async (id: number, data: ClientPortalInviteRequest): Promise<{ message: string }> => {
    const response = await apiClient.post<ApiResponse<{ message: string }>>(`/clients/${id}/invite-portal`, data)
    return response.data.data
  },
}

// React Query Hooks
export function useClients(filters: ClientFilters = {}) {
  return useQuery({
    queryKey: ['clients', filters],
    queryFn: () => clientsApi.getClients(filters),
    staleTime: 30 * 1000,
  })
}

export function useCreateClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: clientsApi.createClient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}

export function useClient(id: number) {
  return useQuery({
    queryKey: ['clients', id],
    queryFn: () => clientsApi.getClient(id),
    enabled: !!id,
  })
}

export function useUpdateClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ClientUpdate }) => clientsApi.updateClient(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
      queryClient.invalidateQueries({ queryKey: ['clients', variables.id] })
    },
  })
}

export function useDeleteClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: clientsApi.deleteClient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] })
    },
  })
}

export function useClientUsers(id: number) {
  return useQuery({
    queryKey: ['clients', id, 'users'],
    queryFn: () => clientsApi.getClientUsers(id),
    enabled: !!id,
  })
}

export function useInvitePortalUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ClientPortalInviteRequest }) =>
      clientsApi.invitePortalUser(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['clients', variables.id, 'users'] })
    },
  })
}
