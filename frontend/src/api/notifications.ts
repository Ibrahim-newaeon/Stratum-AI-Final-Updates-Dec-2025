/**
 * Stratum AI - Notifications API
 *
 * In-app notification management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface AppNotification {
  id: number
  title: string
  message: string
  type: string
  category: string
  is_read: boolean
  read_at?: string
  action_url?: string
  action_label?: string
  metadata?: Record<string, unknown>
  created_at: string
}

export interface NotificationCount {
  unread_count: number
  total_count: number
}

export interface MarkReadRequest {
  notification_ids?: number[]
}

// API Functions
export const notificationsApi = {
  getNotifications: async (filters?: {
    unread_only?: boolean
    category?: string
    limit?: number
    offset?: number
  }): Promise<AppNotification[]> => {
    const response = await apiClient.get<ApiResponse<AppNotification[]>>('/notifications', {
      params: filters,
    })
    return response.data.data
  },

  getNotificationCount: async (): Promise<NotificationCount> => {
    const response = await apiClient.get<ApiResponse<NotificationCount>>('/notifications/count')
    return response.data.data
  },

  markRead: async (data: MarkReadRequest = {}): Promise<{ marked_read: number }> => {
    const response = await apiClient.post<ApiResponse<{ marked_read: number }>>('/notifications/mark-read', data)
    return response.data.data
  },

  deleteNotification: async (id: number): Promise<void> => {
    await apiClient.delete(`/notifications/${id}`)
  },
}

// React Query Hooks
export function useNotifications(filters?: {
  unread_only?: boolean
  category?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['notifications', filters],
    queryFn: () => notificationsApi.getNotifications(filters),
    staleTime: 30 * 1000,
  })
}

export function useNotificationCount() {
  return useQuery({
    queryKey: ['notifications', 'count'],
    queryFn: notificationsApi.getNotificationCount,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  })
}

export function useMarkNotificationsRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}

export function useDeleteNotification() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: notificationsApi.deleteNotification,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })
}
