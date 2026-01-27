/**
 * Stratum AI - GDPR Compliance API
 *
 * GDPR data management, export, anonymization, and audit logs
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse, PaginatedResponse } from './client';

// Types
export type AuditAction =
  | 'login'
  | 'logout'
  | 'data_export'
  | 'data_delete'
  | 'consent_update'
  | 'user_create'
  | 'user_update'
  | 'user_delete'
  | 'campaign_create'
  | 'campaign_update'
  | 'campaign_delete'
  | 'settings_update';

export interface AuditLog {
  id: string;
  userId: number;
  userName: string;
  tenantId: number | null;
  action: AuditAction;
  resourceType: string;
  resourceId: string | null;
  details: Record<string, unknown>;
  ipAddress: string;
  userAgent: string;
  createdAt: string;
}

export interface DataExportRequest {
  id: string;
  userId: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  format: 'json' | 'csv';
  downloadUrl: string | null;
  expiresAt: string | null;
  createdAt: string;
  completedAt: string | null;
}

export interface ConsentRecord {
  id: string;
  userId: number;
  consentType: string;
  granted: boolean;
  grantedAt: string;
  revokedAt: string | null;
  ipAddress: string;
  source: string;
}

export interface AnonymizationRequest {
  id: string;
  userId: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  scope: 'full' | 'partial';
  dataCategories: string[];
  createdAt: string;
  completedAt: string | null;
  error: string | null;
}

export interface AuditLogFilters {
  userId?: number;
  tenantId?: number;
  action?: AuditAction;
  resourceType?: string;
  startDate?: string;
  endDate?: string;
  skip?: number;
  limit?: number;
}

// API Functions
export const gdprApi = {
  /**
   * Request data export
   */
  requestExport: async (format: 'json' | 'csv' = 'json'): Promise<DataExportRequest> => {
    const response = await apiClient.post<ApiResponse<DataExportRequest>>('/gdpr/export', {
      format,
    });
    return response.data.data;
  },

  /**
   * Get export status
   */
  getExportStatus: async (id: string): Promise<DataExportRequest> => {
    const response = await apiClient.get<ApiResponse<DataExportRequest>>(`/gdpr/export/${id}`);
    return response.data.data;
  },

  /**
   * Get all export requests for user
   */
  getExportHistory: async (): Promise<DataExportRequest[]> => {
    const response = await apiClient.get<ApiResponse<DataExportRequest[]>>('/gdpr/export');
    return response.data.data;
  },

  /**
   * Request data anonymization
   */
  requestAnonymization: async (
    scope: 'full' | 'partial',
    dataCategories?: string[]
  ): Promise<AnonymizationRequest> => {
    const response = await apiClient.post<ApiResponse<AnonymizationRequest>>('/gdpr/anonymize', {
      scope,
      data_categories: dataCategories,
    });
    return response.data.data;
  },

  /**
   * Get anonymization status
   */
  getAnonymizationStatus: async (id: string): Promise<AnonymizationRequest> => {
    const response = await apiClient.get<ApiResponse<AnonymizationRequest>>(
      `/gdpr/anonymize/${id}`
    );
    return response.data.data;
  },

  /**
   * Get audit logs (admin only)
   */
  getAuditLogs: async (filters: AuditLogFilters = {}): Promise<PaginatedResponse<AuditLog>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<AuditLog>>>(
      '/gdpr/audit-logs',
      { params: filters }
    );
    return response.data.data;
  },

  /**
   * Get user's consent records
   */
  getConsentRecords: async (userId?: number): Promise<ConsentRecord[]> => {
    const params = userId ? { user_id: userId } : {};
    const response = await apiClient.get<ApiResponse<ConsentRecord[]>>('/gdpr/consent', { params });
    return response.data.data;
  },

  /**
   * Update consent
   */
  updateConsent: async (consentType: string, granted: boolean): Promise<ConsentRecord> => {
    const response = await apiClient.post<ApiResponse<ConsentRecord>>('/gdpr/consent', {
      consent_type: consentType,
      granted,
    });
    return response.data.data;
  },

  /**
   * Get data categories available for export/anonymization
   */
  getDataCategories: async (): Promise<{ id: string; name: string; description: string }[]> => {
    const response =
      await apiClient.get<ApiResponse<{ id: string; name: string; description: string }[]>>(
        '/gdpr/data-categories'
      );
    return response.data.data;
  },

  /**
   * Request right to be forgotten (full account deletion)
   */
  requestDeletion: async (reason?: string): Promise<{ requestId: string; scheduledAt: string }> => {
    const response = await apiClient.post<ApiResponse<{ requestId: string; scheduledAt: string }>>(
      '/gdpr/delete',
      { reason }
    );
    return response.data.data;
  },

  /**
   * Cancel deletion request
   */
  cancelDeletion: async (requestId: string): Promise<{ success: boolean }> => {
    const response = await apiClient.delete<ApiResponse<{ success: boolean }>>(
      `/gdpr/delete/${requestId}`
    );
    return response.data.data;
  },
};

// React Query Hooks

export function useExportData() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: gdprApi.requestExport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gdpr', 'exports'] });
    },
  });
}

export function useExportStatus(id: string) {
  return useQuery({
    queryKey: ['gdpr', 'exports', id],
    queryFn: () => gdprApi.getExportStatus(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 5000; // Poll every 5 seconds while processing
    },
  });
}

export function useExportHistory() {
  return useQuery({
    queryKey: ['gdpr', 'exports'],
    queryFn: gdprApi.getExportHistory,
  });
}

export function useAnonymizeData() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      scope,
      dataCategories,
    }: {
      scope: 'full' | 'partial';
      dataCategories?: string[];
    }) => gdprApi.requestAnonymization(scope, dataCategories),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gdpr', 'anonymization'] });
    },
  });
}

export function useAnonymizationStatus(id: string) {
  return useQuery({
    queryKey: ['gdpr', 'anonymization', id],
    queryFn: () => gdprApi.getAnonymizationStatus(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false;
      }
      return 5000;
    },
  });
}

export function useAuditLogs(filters: AuditLogFilters = {}) {
  return useQuery({
    queryKey: ['gdpr', 'audit-logs', filters],
    queryFn: () => gdprApi.getAuditLogs(filters),
    staleTime: 30 * 1000,
  });
}

export function useConsentRecords(userId?: number) {
  return useQuery({
    queryKey: ['gdpr', 'consent', userId],
    queryFn: () => gdprApi.getConsentRecords(userId),
  });
}

export function useUpdateConsent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ consentType, granted }: { consentType: string; granted: boolean }) =>
      gdprApi.updateConsent(consentType, granted),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gdpr', 'consent'] });
    },
  });
}

export function useDataCategories() {
  return useQuery({
    queryKey: ['gdpr', 'data-categories'],
    queryFn: gdprApi.getDataCategories,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useRequestDeletion() {
  return useMutation({
    mutationFn: gdprApi.requestDeletion,
  });
}

export function useCancelDeletion() {
  return useMutation({
    mutationFn: gdprApi.cancelDeletion,
  });
}
