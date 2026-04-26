/**
 * Stratum AI - Subscription API
 *
 * Subscription status, configuration, and usage.
 */

import { useQuery } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface SubscriptionStatus {
  tenant_id: number
  plan: string
  tier: string
  status: string
  expires_at?: string
  days_until_expiry?: number
  days_in_grace?: number
  is_access_restricted: boolean
  restriction_reason?: string
  warning_message?: string
  pricing?: Record<string, unknown>
}

export interface SubscriptionConfig {
  grace_period_days: number
  expiry_warning_days: number
  available_plans: Record<string, unknown>[]
}

export interface SubscriptionCheck {
  valid: boolean
  status: string
  message: string
  tier: string
}

export interface SubscriptionWarning {
  type: string
  severity: string
  title: string
  message: string
  action?: {
    label: string
    url: string
  }
}

export interface SubscriptionWarningsResponse {
  warnings: SubscriptionWarning[]
  count: number
}

export interface SubscriptionUsageSummary {
  subscription: Record<string, unknown>
  usage: Record<string, unknown>
  warning_message?: string
}

// API Functions
export const subscriptionApi = {
  getStatus: async (): Promise<SubscriptionStatus> => {
    const response = await apiClient.get<ApiResponse<SubscriptionStatus>>('/subscription/status')
    return response.data.data
  },

  getConfig: async (): Promise<SubscriptionConfig> => {
    const response = await apiClient.get<ApiResponse<SubscriptionConfig>>('/subscription/config')
    return response.data.data
  },

  check: async (): Promise<SubscriptionCheck> => {
    const response = await apiClient.get<ApiResponse<SubscriptionCheck>>('/subscription/check')
    return response.data.data
  },

  getWarnings: async (): Promise<SubscriptionWarningsResponse> => {
    const response = await apiClient.get<ApiResponse<SubscriptionWarningsResponse>>('/subscription/warnings')
    return response.data.data
  },

  getUsageSummary: async (): Promise<SubscriptionUsageSummary> => {
    const response = await apiClient.get<ApiResponse<SubscriptionUsageSummary>>('/subscription/usage-summary')
    return response.data.data
  },
}

// React Query Hooks
export function useSubscriptionStatus() {
  return useQuery({
    queryKey: ['subscription', 'status'],
    queryFn: subscriptionApi.getStatus,
    staleTime: 60 * 1000,
  })
}

export function useSubscriptionConfig() {
  return useQuery({
    queryKey: ['subscription', 'config'],
    queryFn: subscriptionApi.getConfig,
    staleTime: 5 * 60 * 1000,
  })
}

export function useSubscriptionCheck() {
  return useQuery({
    queryKey: ['subscription', 'check'],
    queryFn: subscriptionApi.check,
    staleTime: 60 * 1000,
  })
}

export function useSubscriptionWarnings() {
  return useQuery({
    queryKey: ['subscription', 'warnings'],
    queryFn: subscriptionApi.getWarnings,
    staleTime: 60 * 1000,
  })
}

export function useSubscriptionUsageSummary() {
  return useQuery({
    queryKey: ['subscription', 'usage-summary'],
    queryFn: subscriptionApi.getUsageSummary,
    staleTime: 60 * 1000,
  })
}
