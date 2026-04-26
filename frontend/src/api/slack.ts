/**
 * Stratum AI - Slack Integration API
 *
 * Slack webhook configuration and notifications.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface SlackConfig {
  id: number
  webhook_url_masked: string
  channel_name?: string
  notify_trust_gate: boolean
  notify_anomalies: boolean
  notify_signal_health: boolean
  notify_daily_summary: boolean
  is_active: boolean
  last_test_at?: string
  last_test_success?: boolean
  created_at: string
  updated_at: string
}

export interface SlackConnectRequest {
  webhook_url: string
  channel_name?: string
  notify_trust_gate?: boolean
  notify_anomalies?: boolean
  notify_signal_health?: boolean
  notify_daily_summary?: boolean
}

export interface SlackNotifyRequest {
  message: string
  type?: string
}

export interface SlackTestResponse {
  success: boolean
  message: string
}

// API Functions
export const slackApi = {
  getStatus: async (): Promise<SlackConfig | null> => {
    const response = await apiClient.get<ApiResponse<SlackConfig | null>>('/slack')
    return response.data.data
  },

  connect: async (data: SlackConnectRequest): Promise<SlackConfig> => {
    const response = await apiClient.post<ApiResponse<SlackConfig>>('/slack', data)
    return response.data.data
  },

  disconnect: async (): Promise<void> => {
    await apiClient.delete('/slack')
  },

  notify: async (data: SlackNotifyRequest): Promise<SlackTestResponse> => {
    const response = await apiClient.post<ApiResponse<SlackTestResponse>>('/slack/notify', data)
    return response.data.data
  },

  testConnection: async (): Promise<SlackTestResponse> => {
    const response = await apiClient.post<ApiResponse<SlackTestResponse>>('/slack/test')
    return response.data.data
  },
}

// React Query Hooks
export function useSlackStatus() {
  return useQuery({
    queryKey: ['slack', 'status'],
    queryFn: slackApi.getStatus,
    staleTime: 60 * 1000,
  })
}

export function useSlackConnect() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: slackApi.connect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slack', 'status'] })
    },
  })
}

export function useSlackDisconnect() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: slackApi.disconnect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slack', 'status'] })
    },
  })
}

export function useSlackNotify() {
  return useMutation({
    mutationFn: slackApi.notify,
  })
}

export function useSlackTestConnection() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: slackApi.testConnection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['slack', 'status'] })
    },
  })
}
