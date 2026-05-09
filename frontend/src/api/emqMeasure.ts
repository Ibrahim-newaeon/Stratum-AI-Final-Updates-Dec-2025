/**
 * EMQ Measure Workflow API — POST /audit-services/emq/measure +
 * GET /audit-services/emq/history. Operator-driven manual EMQ run
 * for a single (platform, pixel_id) pair, plus the rolling history.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export type EMQPlatform = 'meta' | 'google' | 'tiktok' | 'snapchat';

export interface EMQMeasurementRequest {
  platform: EMQPlatform;
  pixel_id: string;
  start_date?: string;
  end_date?: string;
}

export interface EMQMeasurementResult {
  success: boolean;
  platform: string;
  pixel_id: string;
  overall_score: number | null;
  parameter_quality: number | null;
  event_coverage: number | null;
  match_rate: number | null;
  recommendations: string[] | null;
  error: string | null;
}

export interface EMQHistoryEntry {
  measured_at: string;
  overall_score: number | null;
  parameter_quality: number | null;
  event_coverage: number | null;
  match_rate: number | null;
}

export interface EMQHistoryResponse {
  data: EMQHistoryEntry[];
}

export function useMeasureEMQ() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (req: EMQMeasurementRequest) => {
      const res = await apiClient.post<EMQMeasurementResult>('/audit-services/emq/measure', req);
      return res.data;
    },
    onSuccess: (_data, vars) => {
      queryClient.invalidateQueries({
        queryKey: ['audit-services', 'emq-history', vars.platform, vars.pixel_id],
      });
    },
  });
}

export function useEMQHistory(platform: EMQPlatform | '', pixelId: string, days: number = 30) {
  return useQuery({
    queryKey: ['audit-services', 'emq-history', platform, pixelId, days],
    queryFn: async () => {
      const res = await apiClient.get<EMQHistoryResponse>(
        `/audit-services/emq/history?platform=${encodeURIComponent(
          platform
        )}&pixel_id=${encodeURIComponent(pixelId)}&days=${days}`
      );
      return res.data.data;
    },
    enabled: Boolean(platform && pixelId),
    staleTime: 60 * 1000,
  });
}
