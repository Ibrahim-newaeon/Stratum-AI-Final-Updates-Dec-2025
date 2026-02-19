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
    initialData: {
      problems: [
        {
          id: '1',
          severity: 'critical' as const,
          title: 'Creative Fatigue Detected',
          description:
            'Ad creative performance has dropped 34% in the last 7 days across 12 campaigns.',
          impact: '-$3,400/week',
          impactAmount: 3400,
          affectedCampaigns: 12,
          platform: 'Meta',
          detectedAt: '2024-12-08',
          status: 'active' as const,
        },
        {
          id: '2',
          severity: 'warning' as const,
          title: 'Budget Pacing Issue',
          description: 'Google Search campaigns are under-spending by 28% against daily targets.',
          impact: '-$1,800/week',
          impactAmount: 1800,
          affectedCampaigns: 5,
          platform: 'Google',
          detectedAt: '2024-12-09',
          status: 'active' as const,
        },
        {
          id: '3',
          severity: 'warning' as const,
          title: 'Audience Overlap',
          description: '3 Meta ad sets share 45% audience overlap, causing self-competition.',
          impact: '-$1,000/week',
          impactAmount: 1000,
          affectedCampaigns: 3,
          platform: 'Meta',
          detectedAt: '2024-12-10',
          status: 'active' as const,
        },
      ],
      summary: {
        critical: 1,
        warnings: 2,
        resolved30d: 8,
        revenueAtRisk: 6200,
      },
    },
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
    placeholderData: {
      attributedRevenue: 284500,
      touchpointsTracked: 45200,
      avgPathLength: 4.2,
      conversionWindow: '7 days',
      modelComparison: [
        { channel: 'Google Search', firstTouch: 42, lastTouch: 38, linear: 35, dataDriven: 37 },
        { channel: 'Meta Ads', firstTouch: 28, lastTouch: 32, linear: 30, dataDriven: 31 },
        { channel: 'Display', firstTouch: 12, lastTouch: 8, linear: 14, dataDriven: 13 },
        { channel: 'TikTok', firstTouch: 10, lastTouch: 12, linear: 11, dataDriven: 11 },
        { channel: 'Snapchat', firstTouch: 5, lastTouch: 6, linear: 6, dataDriven: 5 },
        { channel: 'Organic', firstTouch: 3, lastTouch: 4, linear: 4, dataDriven: 3 },
      ],
    },
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
    placeholderData: [
      { channel: 'Google Search', revenue: 105000, percentage: 37, color: '#4285F4' },
      { channel: 'Meta Ads', revenue: 88000, percentage: 31, color: '#0866FF' },
      { channel: 'Display', revenue: 37000, percentage: 13, color: '#34A853' },
      { channel: 'TikTok', revenue: 31000, percentage: 11, color: '#000000' },
      { channel: 'Snapchat', revenue: 14000, percentage: 5, color: '#FFFC00' },
      { channel: 'Organic', revenue: 9500, percentage: 3, color: '#6B7280' },
    ],
  });
}
