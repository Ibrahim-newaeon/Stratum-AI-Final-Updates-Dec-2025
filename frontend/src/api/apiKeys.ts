/**
 * Stratum AI - API Keys API
 *
 * API key management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface ApiKey {
  id: number
  name: string
  key_prefix: string
  masked_key: string
  scopes: string[]
  is_active: boolean
  last_used_at?: string
  expires_at?: string
  created_at: string
}

export interface ApiKeyCreate {
  name: string
  scopes?: string[]
  expires_in_days?: number
}

export interface ApiKeyCreated {
  id: number
  name: string
  key: string
  key_prefix: string
  scopes: string[]
  expires_at?: string
  created_at: string
}

// API Functions
export const apiKeysApi = {
  getApiKeys: async (): Promise<ApiKey[]> => {
    const response = await apiClient.get<ApiResponse<ApiKey[]>>('/api-keys')
    return response.data.data
  },

  createApiKey: async (data: ApiKeyCreate): Promise<ApiKeyCreated> => {
    const response = await apiClient.post<ApiResponse<ApiKeyCreated>>('/api-keys', data)
    return response.data.data
  },

  deleteApiKey: async (id: number): Promise<void> => {
    await apiClient.delete(`/api-keys/${id}`)
  },
}

// React Query Hooks
export function useApiKeys() {
  return useQuery({
    queryKey: ['api-keys'],
    queryFn: apiKeysApi.getApiKeys,
    staleTime: 30 * 1000,
  })
}

export function useCreateApiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: apiKeysApi.createApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}

export function useDeleteApiKey() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: apiKeysApi.deleteApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    },
  })
}
