/**
 * Stratum AI - Audit Log API Hooks
 *
 * React Query hooks for tenant audit log features:
 * - Paginated audit log entries
 * - Daily volume + action type distribution
 * - CSV export
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

// =============================================================================
// Types
// =============================================================================

export type AuditAction =
  | 'create'
  | 'update'
  | 'delete'
  | 'login'
  | 'logout'
  | 'export'
  | 'sync'
  | 'invite';

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  userId: number;
  userName: string;
  userAvatar?: string;
  action: AuditAction;
  resource: string;
  details: string;
  status: 'success' | 'failure';
  ipAddress: string;
}

export interface AuditLogParams {
  page?: number;
  limit?: number;
  action?: AuditAction;
  userId?: number;
  search?: string;
  startDate?: string;
  endDate?: string;
}

export interface AuditLogResponse {
  entries: AuditLogEntry[];
  total: number;
  page: number;
  limit: number;
}

export interface AuditStats {
  totalEvents: number;
  successful: number;
  failed: number;
  activeUsers: number;
  dailyVolume: { date: string; count: number }[];
  byAction: { action: AuditAction; count: number }[];
}

// =============================================================================
// Hooks
// =============================================================================

export function useTenantAuditLogs(tenantId: number, params: AuditLogParams = {}) {
  return useQuery({
    queryKey: ['audit', 'logs', tenantId, params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params.page) searchParams.append('page', params.page.toString());
      if (params.limit) searchParams.append('limit', params.limit.toString());
      if (params.action) searchParams.append('action', params.action);
      if (params.userId) searchParams.append('user_id', params.userId.toString());
      if (params.search) searchParams.append('search', params.search);

      const response = await apiClient.get<{ data: AuditLogResponse }>(
        `/tenants/${tenantId}/audit?${searchParams}`
      );
      return response.data.data;
    },
    enabled: !!tenantId,
    staleTime: 30 * 1000,
    // No placeholderData — avoid flashing fake/demo data before real data loads
  });
}

export function useTenantAuditStats(tenantId: number, period: string = '14d') {
  return useQuery({
    queryKey: ['audit', 'stats', tenantId, period],
    queryFn: async () => {
      const response = await apiClient.get<{ data: AuditStats }>(
        `/tenants/${tenantId}/audit/stats?period=${period}`
      );
      return response.data.data;
    },
    enabled: !!tenantId,
    staleTime: 60 * 1000,
    // No placeholderData — avoid flashing fake/demo data before real data loads
  });
}

export function useExportAuditLogs(tenantId: number) {
  return useMutation({
    mutationFn: async (params?: { startDate?: string; endDate?: string }) => {
      const response = await apiClient.post(
        `/tenants/${tenantId}/audit/export`,
        params,
        { responseType: 'blob' }
      );
      // Trigger download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `audit-log-${tenantId}-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
  });
}
