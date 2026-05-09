/**
 * Audit Services per-domain API hooks.
 *
 * Surfaces four operator workflows over the audit_services router:
 *   - Offline conversions (POST /upload, GET /batches)
 *   - Experiments lifecycle (POST /create, GET /list, POST /start, POST /stop)
 *   - Budget reallocation (POST /plan, /approve, /execute, /rollback)
 *   - LTV batch predict + segment definitions
 *
 * Each surface is rendered by its own page in views/console/. The
 * `useAuditServicesHealth` hook on the existing AuditServices page
 * gives the bird's-eye overview; these are the per-domain drilldowns.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

// =============================================================================
// Offline conversions
// =============================================================================

export interface OfflineConversionRecord {
  event_name: string;
  event_time: string;
  value?: number;
  currency?: string;
  email?: string;
  phone?: string;
  external_id?: string;
  click_id?: string;
}

export interface OfflineConversionUploadRequest {
  platform: string;
  conversions: OfflineConversionRecord[];
  batch_name?: string;
}

export interface OfflineConversionUploadResponse {
  success: boolean;
  batch_id: string | null;
  total_records: number;
  successful: number;
  failed: number;
  errors: string[] | null;
}

export interface OfflineConversionBatch {
  batch_id: string;
  platform: string;
  status: string;
  total_records: number;
  successful: number;
  failed: number;
  created_at: string;
  batch_name: string | null;
}

export function useUploadOfflineConversions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (req: OfflineConversionUploadRequest) => {
      const res = await apiClient.post<OfflineConversionUploadResponse>(
        '/audit-services/offline-conversions/upload',
        req
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['audit-services', 'offline-batches'] });
    },
  });
}

export function useOfflineConversionBatches(platform?: string, status?: string) {
  return useQuery({
    queryKey: ['audit-services', 'offline-batches', platform ?? 'all', status ?? 'all'],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (platform) params.set('platform', platform);
      if (status) params.set('status', status);
      const qs = params.toString();
      const res = await apiClient.get<{ data: OfflineConversionBatch[] }>(
        `/audit-services/offline-conversions/batches${qs ? `?${qs}` : ''}`
      );
      return res.data.data;
    },
    staleTime: 30 * 1000,
  });
}

// =============================================================================
// Experiments lifecycle
// =============================================================================

export type ExperimentStatus = 'draft' | 'running' | 'stopped' | 'completed';

export interface CreateExperimentRequest {
  name: string;
  model_name: string;
  champion_version: string;
  challenger_version: string;
  traffic_split?: number;
  min_samples?: number;
  significance_threshold?: number;
}

export interface Experiment {
  id: string;
  name: string;
  model_name: string;
  status: string;
  champion_version: string;
  challenger_version: string;
  traffic_split: number;
  champion_predictions: number;
  challenger_predictions: number;
  created_at: string | null;
}

export function useExperiments(modelName?: string, status?: string) {
  return useQuery({
    queryKey: ['audit-services', 'experiments', modelName ?? 'all', status ?? 'all'],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (modelName) params.set('model_name', modelName);
      if (status) params.set('status', status);
      const qs = params.toString();
      const res = await apiClient.get<{ data: Experiment[] }>(
        `/audit-services/experiments${qs ? `?${qs}` : ''}`
      );
      return res.data.data;
    },
    staleTime: 30 * 1000,
  });
}

export function useCreateExperiment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (req: CreateExperimentRequest) => {
      const res = await apiClient.post('/audit-services/experiments', req);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['audit-services', 'experiments'] });
    },
  });
}

export function useStartExperiment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (experimentId: string) => {
      const res = await apiClient.post(
        `/audit-services/experiments/${encodeURIComponent(experimentId)}/start`
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['audit-services', 'experiments'] });
    },
  });
}

export function useStopExperiment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (experimentId: string) => {
      const res = await apiClient.post(
        `/audit-services/experiments/${encodeURIComponent(experimentId)}/stop`
      );
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['audit-services', 'experiments'] });
    },
  });
}

// =============================================================================
// Budget reallocation
// =============================================================================

export interface CampaignBudgetInput {
  campaign_id: string;
  campaign_name: string;
  platform: string;
  current_daily_budget: number;
  current_spend: number;
  performance_metrics: Record<string, number>;
}

export interface ReallocationPlanRequest {
  campaigns: CampaignBudgetInput[];
  strategy?: string;
  min_campaign_budget?: number;
  max_change_percent?: number;
}

export interface ReallocationChange {
  campaign_id: string;
  campaign_name: string;
  current_budget: number;
  new_budget: number;
  change_percent: number;
  reason: string;
}

export interface ReallocationPlanResponse {
  plan_id: string;
  status: string;
  total_budget: number;
  campaigns_affected: number;
  changes: ReallocationChange[];
  projected_impact: { roas_change: number; revenue_change: number };
}

export function useCreateReallocationPlan() {
  return useMutation({
    mutationFn: async (req: ReallocationPlanRequest) => {
      const res = await apiClient.post<ReallocationPlanResponse>(
        '/audit-services/budget/reallocation-plan',
        req
      );
      return res.data;
    },
  });
}

export function useApproveReallocationPlan() {
  return useMutation({
    mutationFn: async (planId: string) => {
      const res = await apiClient.post(
        `/audit-services/budget/reallocation-plan/${encodeURIComponent(planId)}/approve`
      );
      return res.data;
    },
  });
}

export function useExecuteReallocationPlan() {
  return useMutation({
    mutationFn: async (planId: string) => {
      const res = await apiClient.post(
        `/audit-services/budget/reallocation-plan/${encodeURIComponent(planId)}/execute`
      );
      return res.data;
    },
  });
}

export function useRollbackReallocationPlan() {
  return useMutation({
    mutationFn: async (planId: string) => {
      const res = await apiClient.post(
        `/audit-services/budget/reallocation-plan/${encodeURIComponent(planId)}/rollback`
      );
      return res.data;
    },
  });
}

// =============================================================================
// LTV batch predict
// =============================================================================

export interface CustomerBehaviorInput {
  customer_id: string;
  acquisition_date: string;
  acquisition_channel: string;
  first_order_value: number;
  total_orders?: number;
  total_revenue?: number;
  avg_order_value?: number;
  days_since_last_order?: number;
  sessions_first_week?: number;
  email_opens_first_week?: number;
}

export interface BatchLTVPrediction {
  customer_id: string;
  segment: string;
  predicted_ltv_365d: number;
  churn_probability: number;
  max_cac: number;
}

export interface LTVSegment {
  name: string;
  value: string;
  ltv_threshold: number | null;
  description: string;
}

export function useBatchPredictLTV() {
  return useMutation({
    mutationFn: async (customers: CustomerBehaviorInput[]) => {
      const res = await apiClient.post<{ predictions: BatchLTVPrediction[] }>(
        '/audit-services/ltv/batch-predict',
        customers
      );
      return res.data;
    },
  });
}

export function useLTVSegments() {
  return useQuery({
    queryKey: ['audit-services', 'ltv-segments'],
    queryFn: async () => {
      const res = await apiClient.get<{ segments: LTVSegment[] }>('/audit-services/ltv/segments');
      return res.data.segments;
    },
    staleTime: 60 * 60 * 1000,
  });
}
