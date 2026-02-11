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
    placeholderData: {
      entries: [
        {
          id: '1',
          timestamp: '2024-12-10T14:32:00Z',
          userId: 1,
          userName: 'Sarah Miller',
          action: 'update' as const,
          resource: 'Campaign "Holiday Sale"',
          details: 'Updated budget from $500 to $750',
          status: 'success' as const,
          ipAddress: '192.168.1.42',
        },
        {
          id: '2',
          timestamp: '2024-12-10T13:15:00Z',
          userId: 2,
          userName: 'Ahmed Hassan',
          action: 'create' as const,
          resource: 'Ad Set "Lookalike US"',
          details: 'Created new ad set targeting US lookalike audience',
          status: 'success' as const,
          ipAddress: '10.0.0.15',
        },
        {
          id: '3',
          timestamp: '2024-12-10T12:45:00Z',
          userId: 1,
          userName: 'Sarah Miller',
          action: 'sync' as const,
          resource: 'Meta Ads',
          details: 'Manual sync triggered for all campaigns',
          status: 'success' as const,
          ipAddress: '192.168.1.42',
        },
        {
          id: '4',
          timestamp: '2024-12-10T11:20:00Z',
          userId: 3,
          userName: 'Carlos Rivera',
          action: 'export' as const,
          resource: 'Performance Report',
          details: 'Exported 30-day performance report as CSV',
          status: 'success' as const,
          ipAddress: '172.16.0.8',
        },
        {
          id: '5',
          timestamp: '2024-12-10T10:05:00Z',
          userId: 2,
          userName: 'Ahmed Hassan',
          action: 'delete' as const,
          resource: 'Draft "Test Campaign Q1"',
          details: 'Deleted campaign draft',
          status: 'success' as const,
          ipAddress: '10.0.0.15',
        },
        {
          id: '6',
          timestamp: '2024-12-10T09:30:00Z',
          userId: 4,
          userName: 'Emily Chen',
          action: 'login' as const,
          resource: 'Dashboard',
          details: 'Logged in via SSO',
          status: 'success' as const,
          ipAddress: '203.0.113.50',
        },
        {
          id: '7',
          timestamp: '2024-12-09T16:45:00Z',
          userId: 1,
          userName: 'Sarah Miller',
          action: 'invite' as const,
          resource: 'Team',
          details: 'Invited newuser@company.com as Analyst',
          status: 'success' as const,
          ipAddress: '192.168.1.42',
        },
        {
          id: '8',
          timestamp: '2024-12-09T15:10:00Z',
          userId: 3,
          userName: 'Carlos Rivera',
          action: 'update' as const,
          resource: 'Campaign "Brand Awareness"',
          details: 'Paused campaign due to high CPA',
          status: 'failure' as const,
          ipAddress: '172.16.0.8',
        },
      ],
      total: 156,
      page: 1,
      limit: 20,
    },
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
    placeholderData: {
      totalEvents: 1284,
      successful: 1247,
      failed: 37,
      activeUsers: 8,
      dailyVolume: Array.from({ length: 14 }, (_, i) => ({
        date: new Date(Date.now() - (13 - i) * 86400000).toISOString().split('T')[0],
        count: Math.floor(60 + Math.random() * 80),
      })),
      byAction: [
        { action: 'update' as const, count: 456 },
        { action: 'create' as const, count: 312 },
        { action: 'login' as const, count: 248 },
        { action: 'sync' as const, count: 128 },
        { action: 'export' as const, count: 76 },
        { action: 'delete' as const, count: 42 },
        { action: 'invite' as const, count: 14 },
        { action: 'logout' as const, count: 8 },
      ],
    },
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
