/**
 * QA Fixes — wraps the /qa-fixes router.
 *
 * Complements emqV2: emqV2 ships the priority-queue playbook (status,
 * owner, estimatedImpact); qa_fixes ships the step-by-step instructions
 * for each fix and an application history. Surfaced inside EMQDiagnostics
 * as the "how to do it" companion to the emq_v2 task list.
 */

import { useQuery } from '@tanstack/react-query';
import api from './client';

export interface QAFixPlaybookItem {
  id: string;
  title: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  estimated_impact: number;
  platform: string | null;
  status: 'pending' | 'in_progress' | 'completed';
  steps: string[];
}

export interface QAFixPlaybookResponse {
  items: QAFixPlaybookItem[];
  total: number;
  estimated_total_impact: number;
}

export interface QAFixHistoryEntry {
  id: string;
  timestamp: string | null;
  action_type: string;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown> | null;
}

export interface QAFixHistoryResponse {
  history: QAFixHistoryEntry[];
  total: number;
  skip: number;
  limit: number;
}

export function useQAFixesPlaybook(tenantId: number) {
  return useQuery({
    queryKey: ['qa-fixes', 'playbook', tenantId],
    queryFn: async () => {
      const res = await api.get<QAFixPlaybookResponse>(`/qa-fixes/${tenantId}/playbook`);
      return res.data;
    },
    enabled: tenantId > 0,
    staleTime: 60 * 1000,
  });
}

export function useQAFixesHistory(tenantId: number, limit = 10) {
  return useQuery({
    queryKey: ['qa-fixes', 'history', tenantId, limit],
    queryFn: async () => {
      const res = await api.get<QAFixHistoryResponse>(
        `/qa-fixes/${tenantId}/history?limit=${limit}`
      );
      return res.data;
    },
    enabled: tenantId > 0,
    staleTime: 60 * 1000,
  });
}
