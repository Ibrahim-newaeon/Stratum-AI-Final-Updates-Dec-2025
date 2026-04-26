/**
 * Stratum AI - MFA API
 *
 * Two-factor authentication management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface MFAStatus {
  enabled: boolean
  verified_at?: string
  backup_codes_remaining: number
  is_locked: boolean
  lockout_until?: string
}

export interface MFASetupResponse {
  secret: string
  provisioning_uri: string
  qr_code_base64: string
}

export interface MFAVerifyRequest {
  code: string
}

export interface MFAVerifyResponse {
  success: boolean
  message: string
  backup_codes: string[]
}

export interface MFADisableRequest {
  code: string
}

export interface MFAValidateRequest {
  user_id: number
  code: string
}

export interface MFAValidateResponse {
  valid: boolean
  message: string
}

export interface BackupCodesRequest {
  code: string
}

export interface BackupCodesResponse {
  success: boolean
  message: string
  backup_codes: string[]
}

// API Functions
export const mfaApi = {
  getStatus: async (): Promise<MFAStatus> => {
    const response = await apiClient.get<ApiResponse<MFAStatus>>('/mfa/status')
    return response.data.data
  },

  setup: async (): Promise<MFASetupResponse> => {
    const response = await apiClient.post<ApiResponse<MFASetupResponse>>('/mfa/setup')
    return response.data.data
  },

  verify: async (data: MFAVerifyRequest): Promise<MFAVerifyResponse> => {
    const response = await apiClient.post<ApiResponse<MFAVerifyResponse>>('/mfa/verify', data)
    return response.data.data
  },

  disable: async (data: MFADisableRequest): Promise<MFAVerifyResponse> => {
    const response = await apiClient.post<ApiResponse<MFAVerifyResponse>>('/mfa/disable', data)
    return response.data.data
  },

  regenerateBackupCodes: async (data: BackupCodesRequest): Promise<BackupCodesResponse> => {
    const response = await apiClient.post<ApiResponse<BackupCodesResponse>>('/mfa/backup-codes', data)
    return response.data.data
  },

  validate: async (data: MFAValidateRequest): Promise<MFAValidateResponse> => {
    const response = await apiClient.post<ApiResponse<MFAValidateResponse>>('/mfa/validate', data)
    return response.data.data
  },
}

// React Query Hooks
export function useMFAStatus() {
  return useQuery({
    queryKey: ['mfa', 'status'],
    queryFn: mfaApi.getStatus,
    staleTime: 60 * 1000,
  })
}

export function useMFASetup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: mfaApi.setup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mfa', 'status'] })
    },
  })
}

export function useMFAVerify() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: mfaApi.verify,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mfa', 'status'] })
    },
  })
}

export function useMFADisable() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: mfaApi.disable,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mfa', 'status'] })
    },
  })
}

export function useMFABackupCodes() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: mfaApi.regenerateBackupCodes,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mfa', 'status'] })
    },
  })
}

export function useMFAValidate() {
  return useMutation({
    mutationFn: mfaApi.validate,
  })
}
