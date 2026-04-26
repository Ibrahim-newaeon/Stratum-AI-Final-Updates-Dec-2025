/**
 * Stratum AI - Webhooks API
 *
 * Webhook management and delivery logs.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface Webhook {
  id: number
  name: string
  url: string
  events: string[]
  status: string
  headers?: Record<string, string>
  failure_count: number
  last_triggered_at?: string
  last_success_at?: string
  last_failure_at?: string
  last_failure_reason?: string
  created_at: string
  updated_at: string
}

export interface WebhookCreate {
  name: string
  url: string
  events: string[]
  headers?: Record<string, string>
}

export interface WebhookUpdate {
  name?: string
  url?: string
  events?: string[]
  headers?: Record<string, string>
  status?: string
}

export interface WebhookTestResult {
  success: boolean
  status_code?: number
  response_body?: string
  error_message?: string
  duration_ms: number
}

export interface WebhookDelivery {
  id: number
  event_type: string
  payload: Record<string, unknown>
  success: boolean
  status_code?: number
  response_body?: string
  error_message?: string
  duration_ms?: number
  created_at: string
}

// API Functions
export const webhooksApi = {
  getWebhooks: async (): Promise<Webhook[]> => {
    const response = await apiClient.get<ApiResponse<Webhook[]>>('/webhooks')
    return response.data.data
  },

  getWebhook: async (id: number): Promise<Webhook> => {
    const response = await apiClient.get<ApiResponse<Webhook>>(`/webhooks/${id}`)
    return response.data.data
  },

  createWebhook: async (data: WebhookCreate): Promise<Webhook> => {
    const response = await apiClient.post<ApiResponse<Webhook>>('/webhooks', data)
    return response.data.data
  },

  updateWebhook: async (id: number, data: WebhookUpdate): Promise<Webhook> => {
    const response = await apiClient.patch<ApiResponse<Webhook>>(`/webhooks/${id}`, data)
    return response.data.data
  },

  deleteWebhook: async (id: number): Promise<void> => {
    await apiClient.delete(`/webhooks/${id}`)
  },

  testWebhook: async (id: number): Promise<WebhookTestResult> => {
    const response = await apiClient.post<ApiResponse<WebhookTestResult>>(`/webhooks/${id}/test`)
    return response.data.data
  },

  getDeliveries: async (id: number, limit = 50, offset = 0): Promise<WebhookDelivery[]> => {
    const response = await apiClient.get<ApiResponse<WebhookDelivery[]>>(
      `/webhooks/${id}/deliveries`,
      { params: { limit, offset } }
    )
    return response.data.data
  },
}

// React Query Hooks
export function useWebhooks() {
  return useQuery({
    queryKey: ['webhooks'],
    queryFn: webhooksApi.getWebhooks,
    staleTime: 30 * 1000,
  })
}

export function useWebhook(id: number) {
  return useQuery({
    queryKey: ['webhooks', id],
    queryFn: () => webhooksApi.getWebhook(id),
    enabled: !!id,
  })
}

export function useCreateWebhook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: webhooksApi.createWebhook,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })
}

export function useUpdateWebhook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: WebhookUpdate }) => webhooksApi.updateWebhook(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
      queryClient.invalidateQueries({ queryKey: ['webhooks', variables.id] })
    },
  })
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: webhooksApi.deleteWebhook,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] })
    },
  })
}

export function useTestWebhook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: webhooksApi.testWebhook,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['webhooks', id] })
    },
  })
}

export function useWebhookDeliveries(id: number, limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['webhooks', id, 'deliveries', limit, offset],
    queryFn: () => webhooksApi.getDeliveries(id, limit, offset),
    enabled: !!id,
  })
}
