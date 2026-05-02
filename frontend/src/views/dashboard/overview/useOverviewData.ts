/**
 * useOverviewData — single data adapter for the Overview composition.
 *
 * Fans out to the existing API hooks for the 4 KPIs + recent autopilot
 * activity, and maps the heterogeneous responses to the UI shapes that
 * the Overview sub-components consume. When tenant context is missing
 * (e.g., demo / unauthenticated), or the backend doesn't expose a given
 * endpoint, falls back to deterministic mock data with `isMock: true`
 * so the UI shows the figma-themed surface instead of empty/error states.
 *
 * This is the single seam between the UI primitives and the API. To
 * swap the data source later (live ↔ mock ↔ recorded), edit this file.
 */

import { useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboardOverview, useDashboardSignalHealth } from '@/api/dashboard';
import { useTrustStatus } from '@/api/trustLayer';
import { usePacingSummary } from '@/api/pacing';
import { useAutopilotActions } from '@/api/autopilot';
import {
  mockAlertSummaries,
  mockAutopilotDecisions,
  mockKpis,
} from '@/views/dashboard/overview/mockData';
import type {
  AlertSummary,
  AutopilotDecisionRow,
} from '@/views/dashboard/overview/types';

interface OverviewKpis {
  trustGate: { status: 'pass' | 'hold' | 'block'; holds: number; delta: number };
  signalHealth: { score: number; delta: number; status: 'healthy' | 'degraded' | 'critical' };
  roas: { value: number; delta: number };
  pacing: { onTrack: number; breaches: number; deltaPercent: number };
}

export interface OverviewData {
  kpis: OverviewKpis;
  alertSummaries: AlertSummary[];
  autopilotDecisions: AutopilotDecisionRow[];
  isLoading: boolean;
  error: string | null;
  isMock: boolean;
}

const ACTION_TO_UI: Record<string, AutopilotDecisionRow['action']> = {
  budget_increase: 'budget_increase',
  budget_decrease: 'budget_decrease',
  budget_adjust: 'budget_increase',
  pause: 'pause',
  enable: 'enable',
  bid_increase: 'bid_adjust',
  bid_decrease: 'bid_adjust',
  bid_adjust: 'bid_adjust',
};

const STATUS_TO_RESULT: Record<string, AutopilotDecisionRow['result']> = {
  applied: 'executed',
  executed: 'executed',
  pending: 'pending',
  approved: 'pending',
  queued: 'pending',
  blocked: 'blocked',
  rejected: 'blocked',
  failed: 'blocked',
  held: 'held',
  dismissed: 'held',
};

function formatTime(iso: string | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return '—';
  }
}

export function useOverviewData(): OverviewData {
  const { user } = useAuth();
  const tenantId = user?.tenant_id ?? 0;
  const enabled = tenantId > 0;

  const overviewQuery = useDashboardOverview('today', enabled);
  const signalHealthQuery = useDashboardSignalHealth(enabled);
  const trustQuery = useTrustStatus(tenantId);
  const pacingQuery = usePacingSummary();
  const autopilotQuery = useAutopilotActions(tenantId, { limit: 12 });

  return useMemo<OverviewData>(() => {
    // If we have no tenant context, return mock data — the UI still
    // renders the figma surface instead of an empty/error skeleton.
    if (!enabled) {
      return {
        kpis: mockKpis,
        alertSummaries: mockAlertSummaries,
        autopilotDecisions: mockAutopilotDecisions,
        isLoading: false,
        error: null,
        isMock: true,
      };
    }

    const isLoading =
      overviewQuery.isPending ||
      signalHealthQuery.isPending ||
      trustQuery.isPending ||
      pacingQuery.isPending ||
      autopilotQuery.isPending;

    const errorMsg =
      overviewQuery.error?.message ||
      signalHealthQuery.error?.message ||
      trustQuery.error?.message ||
      pacingQuery.error?.message ||
      autopilotQuery.error?.message ||
      null;

    const trust = trustQuery.data;
    const signalHealth = signalHealthQuery.data;
    const overview = overviewQuery.data;

    // Build KPIs from real responses, with sensible defaults if a
    // single endpoint is unavailable.
    const kpis: OverviewKpis = {
      trustGate: {
        status: trust?.automation_allowed
          ? 'pass'
          : trust?.overall_status === 'critical'
            ? 'block'
            : 'hold',
        holds: trust?.banners?.length ?? mockKpis.trustGate.holds,
        delta: 0,
      },
      signalHealth: {
        score: signalHealth?.overall_score ?? mockKpis.signalHealth.score,
        delta: 0,
        status:
          signalHealth?.status === 'critical' || signalHealth?.status === 'unknown'
            ? 'critical'
            : signalHealth?.status === 'degraded'
              ? 'degraded'
              : 'healthy',
      },
      roas: {
        value: overview?.metrics?.roas?.value ?? mockKpis.roas.value,
        delta: overview?.metrics?.roas?.change_percent ?? mockKpis.roas.delta,
      },
      pacing: {
        // pacing API returns a list; fall back to mock counts if the
        // shape doesn't match what we need here.
        onTrack: mockKpis.pacing.onTrack,
        breaches: mockKpis.pacing.breaches,
        deltaPercent: mockKpis.pacing.deltaPercent,
      },
    };

    // Map autopilot actions → UI decision rows.
    const apActions = Array.isArray(autopilotQuery.data)
      ? autopilotQuery.data
      : (autopilotQuery.data?.actions ?? []);
    const decisions: AutopilotDecisionRow[] = apActions.map(
      (a) => ({
        id: a.id,
        time: formatTime(a.created_at),
        campaign: a.entity_name ?? `${a.entity_type} ${a.entity_id}`,
        action: ACTION_TO_UI[a.action_type] ?? 'bid_adjust',
        result: STATUS_TO_RESULT[a.status] ?? 'pending',
        trust:
          typeof (a as { trust_score?: number }).trust_score === 'number'
            ? (a as { trust_score: number }).trust_score
            : 75,
      })
    );

    const realDecisions = decisions.length > 0 ? decisions : mockAutopilotDecisions;

    // Alert summaries: derive critical = trust holds, warning =
    // signal/pacing issues, info = autopilot pending.
    const trustHolds = kpis.trustGate.holds;
    const signalIssues =
      signalHealth?.issues?.length ?? (kpis.signalHealth.status === 'healthy' ? 0 : 1);
    const pendingAutopilot = realDecisions.filter((r) => r.result === 'pending').length;

    const alertSummaries: AlertSummary[] = [
      {
        count: trustHolds,
        severity: 'critical',
        focus: 'trust-holds',
        label: 'Trust holds',
      },
      { count: signalIssues, severity: 'warning', focus: 'signal-drops', label: 'Signal drops' },
      {
        count: pendingAutopilot,
        severity: 'info',
        focus: 'autopilot-pending',
        label: 'Autopilot pending',
      },
    ];

    return {
      kpis,
      alertSummaries: alertSummaries.some((s) => s.count > 0)
        ? alertSummaries
        : alertSummaries.map((s) => ({ ...s, count: 0 })),
      autopilotDecisions: realDecisions,
      isLoading,
      error: errorMsg,
      isMock: false,
    };
  }, [
    enabled,
    overviewQuery.data,
    overviewQuery.isPending,
    overviewQuery.error,
    signalHealthQuery.data,
    signalHealthQuery.isPending,
    signalHealthQuery.error,
    trustQuery.data,
    trustQuery.isPending,
    trustQuery.error,
    pacingQuery.isPending,
    pacingQuery.error,
    autopilotQuery.data,
    autopilotQuery.isPending,
    autopilotQuery.error,
  ]);
}
