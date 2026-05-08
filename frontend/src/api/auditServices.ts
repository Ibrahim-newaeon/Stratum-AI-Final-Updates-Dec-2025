/**
 * Audit Services API — read-only hooks for the platform-owner
 * "Audit Services" console page.
 *
 * The audit_services router exposes ~40 endpoints across EMQ
 * measurement, offline conversions, experiments, latency, creatives,
 * benchmarks, budget reallocation, audiences, LTV, models, and
 * service admin. This module surfaces only the cross-cutting health/
 * status/rate-limit reads that an operator needs to know "are the
 * audit services up?" — the per-domain mutations stay backend-only
 * until each gets its own UI.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export type ServiceHealth = 'healthy' | 'unhealthy' | 'degraded';

export interface AuditServicesHealth {
  status: ServiceHealth;
  services: Record<string, ServiceHealth>;
  timestamp: string;
}

export interface AuditServicesMetrics {
  emq: { measurements_today: number; avg_score: number | null };
  offline_conversions: { uploads_today: number; records_processed: number };
  experiments: { active_count: number; completed_count: number };
  creative_alerts: { fatigue_alerts_today: number; unacknowledged: number };
  budget_plans: { pending_approval: number; executed_today: number };
  timestamp: string;
}

export interface ServicesStatusResponse {
  services: Record<string, boolean>;
  timestamp: string;
}

export interface RateLimitsResponse {
  read_limit_per_minute?: number;
  write_limit_per_minute?: number;
  batch_limit_per_minute?: number;
  [k: string]: unknown;
}

export interface AuditLogResponse {
  message: string;
  log_location: string | null;
  filters: { operation: string | null; resource_type: string | null };
  hint: string;
}

export function useAuditServicesHealth() {
  return useQuery({
    queryKey: ['audit-services', 'health'],
    queryFn: async () => {
      const res = await apiClient.get<AuditServicesHealth>('/audit-services/health');
      return res.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useAuditServicesMetrics() {
  return useQuery({
    queryKey: ['audit-services', 'metrics'],
    queryFn: async () => {
      const res = await apiClient.get<AuditServicesMetrics>('/audit-services/metrics');
      return res.data;
    },
    staleTime: 60 * 1000,
  });
}

export function useAuditServicesStatus() {
  return useQuery({
    queryKey: ['audit-services', 'admin-status'],
    queryFn: async () => {
      const res = await apiClient.get<ServicesStatusResponse>(
        '/audit-services/admin/services/status'
      );
      return res.data;
    },
    staleTime: 60 * 1000,
  });
}

export function useAuditServicesRateLimits() {
  return useQuery({
    queryKey: ['audit-services', 'rate-limits'],
    queryFn: async () => {
      const res = await apiClient.get<RateLimitsResponse>('/audit-services/admin/rate-limits');
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useAuditServicesAuditLog() {
  return useQuery({
    queryKey: ['audit-services', 'admin-audit-log'],
    queryFn: async () => {
      const res = await apiClient.get<AuditLogResponse>('/audit-services/admin/audit-log');
      return res.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}
