/**
 * Stratum AI - Knowledge Graph API Hooks
 *
 * React Query hooks for Knowledge Graph features:
 * - Problem Detection (severity filter, resolve action)
 * - Revenue Attribution (period-based, channel breakdown)
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

// =============================================================================
// Types
// =============================================================================

export type ProblemSeverity = 'critical' | 'warning' | 'info';

export interface KGProblem {
  id: string;
  severity: ProblemSeverity;
  title: string;
  description: string;
  impact: string;
  impactAmount: number;
  affectedCampaigns: number;
  platform: string;
  detectedAt: string;
  status: 'active' | 'resolved' | 'dismissed';
}

export interface KGProblemsData {
  problems: KGProblem[];
  summary: {
    critical: number;
    warnings: number;
    resolved30d: number;
    revenueAtRisk: number;
  };
}

export interface KGRevenueData {
  attributedRevenue: number;
  touchpointsTracked: number;
  avgPathLength: number;
  conversionWindow: string;
  modelComparison: {
    channel: string;
    firstTouch: number;
    lastTouch: number;
    linear: number;
    dataDriven: number;
  }[];
}

export interface KGChannelBreakdown {
  channel: string;
  revenue: number;
  percentage: number;
  color: string;
}

// =============================================================================
// Hooks
// =============================================================================

export function useKGProblems(filters?: { severity?: ProblemSeverity; status?: string }) {
  return useQuery({
    queryKey: ['kg', 'problems', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.severity) params.append('severity', filters.severity);
      if (filters?.status) params.append('status', filters.status);

      const response = await apiClient.get<{ data: KGProblemsData }>(
        `/knowledge-graph/insights/problems?${params}`
      );
      return response.data.data;
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
    // No initialData — avoid flashing fake/demo data before real data loads
  });
}

export function useResolveKGProblem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (problemId: string) => {
      const response = await apiClient.post(`/knowledge-graph/problems/${problemId}/resolve`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['kg', 'problems'] });
    },
  });
}

export function useKGRevenueAttribution(period: string = '30d') {
  return useQuery({
    queryKey: ['kg', 'revenue', period],
    queryFn: async () => {
      const response = await apiClient.get<{ data: KGRevenueData }>(
        `/knowledge-graph/revenue?period=${period}`
      );
      return response.data.data;
    },
    staleTime: 5 * 60 * 1000,
    // No placeholderData — avoid flashing fake/demo data before real data loads
  });
}

export function useKGChannelBreakdown(period: string = '30d') {
  return useQuery({
    queryKey: ['kg', 'channels', period],
    queryFn: async () => {
      const response = await apiClient.get<{ data: KGChannelBreakdown[] }>(
        `/knowledge-graph/channels?period=${period}`
      );
      return response.data.data;
    },
    staleTime: 5 * 60 * 1000,
    // No placeholderData — avoid flashing fake/demo data before real data loads
  });
}
