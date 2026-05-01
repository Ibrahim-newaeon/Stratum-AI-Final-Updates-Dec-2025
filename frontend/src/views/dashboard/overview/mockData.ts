/**
 * Deterministic mock data for the Overview composition.
 *
 * The real API has hooks for `useDashboardOverview`, `useTrustStatus`,
 * `useDashboardSignalHealth`, etc. — but they require a tenant_id, demo
 * credentials, and live backend wiring that's out of scope for the
 * primitives-rebuild commit. Phase 3 ships the composition + UI contract;
 * a follow-up commit replaces these mocks with the live hooks.
 *
 * Every mock here matches the shape the UI sub-components expect, so
 * swapping to real data is a one-line import change per block.
 */

import type {
  AlertSummary,
  AutopilotDecisionRow,
  PacingBreachRow,
  RevenueSpendPoint,
  SignalDropDetail,
  TrustHoldRow,
} from './types';

export const mockAlertSummaries: AlertSummary[] = [
  { count: 3, severity: 'critical', focus: 'trust-holds', label: 'Trust holds' },
  { count: 2, severity: 'warning', focus: 'signal-drops', label: 'Signal drops' },
  { count: 5, severity: 'info', focus: 'autopilot-pending', label: 'Autopilot pending' },
];

export const mockTrustHolds: TrustHoldRow[] = [
  {
    id: 'th-1',
    campaign: 'Summer Sale — Prospecting',
    account: 'Meta · Acme',
    violation: 'Spend spike +118% vs. 7d avg',
    severity: 'critical',
    detectedAt: '2 min ago',
    recommendedAction: 'pause',
  },
  {
    id: 'th-2',
    campaign: 'Brand EU — Search',
    account: 'Google · Acme',
    violation: 'CTR dropped to 0.4% (−68%)',
    severity: 'warning',
    detectedAt: '14 min ago',
    recommendedAction: 'hold',
  },
  {
    id: 'th-3',
    campaign: 'Retarget — Cart Abandoners',
    account: 'Meta · Acme',
    violation: 'CPA jumped to $124 (target $40)',
    severity: 'critical',
    detectedAt: '38 min ago',
    recommendedAction: 'pause',
  },
];

export const mockSignalDrop: SignalDropDetail = {
  emqScore: 71,
  emqDelta: -12,
  pipelineHealth: 'degraded',
  recentEvents: 8420,
  expectedEvents: 14200,
  affectedPlatforms: ['Meta', 'TikTok'],
};

export const mockPacingBreaches: PacingBreachRow[] = [
  {
    id: 'pb-1',
    target: 'Q2 EU — Performance',
    budget: 120_000,
    spent: 92_400,
    percentOfTarget: 132,
    daysRemaining: 11,
  },
  {
    id: 'pb-2',
    target: 'Q2 US — Brand',
    budget: 80_000,
    spent: 18_300,
    percentOfTarget: 64,
    daysRemaining: 11,
  },
];

export const mockAutopilotDecisions: AutopilotDecisionRow[] = [
  {
    id: 'ap-1',
    time: '12:42',
    campaign: 'Summer Sale — Prospecting',
    action: 'pause',
    result: 'held',
    trust: 62,
  },
  {
    id: 'ap-2',
    time: '12:31',
    campaign: 'Q2 Promo — Retargeting',
    action: 'budget_increase',
    result: 'executed',
    trust: 91,
  },
  {
    id: 'ap-3',
    time: '12:15',
    campaign: 'Spring Lookalikes',
    action: 'bid_adjust',
    result: 'executed',
    trust: 87,
  },
  {
    id: 'ap-4',
    time: '11:58',
    campaign: 'Brand EU — Search',
    action: 'budget_decrease',
    result: 'pending',
    trust: 74,
  },
  {
    id: 'ap-5',
    time: '11:41',
    campaign: 'Cold Audiences — TikTok',
    action: 'pause',
    result: 'blocked',
    trust: 38,
  },
];

export const mockRevenueSpend: RevenueSpendPoint[] = [
  { date: '2026-04-01', revenue: 28_400, spend: 7_200 },
  { date: '2026-04-04', revenue: 31_200, spend: 7_800 },
  { date: '2026-04-07', revenue: 26_900, spend: 8_100 },
  { date: '2026-04-10', revenue: 35_700, spend: 8_400 },
  { date: '2026-04-13', revenue: 41_200, spend: 9_300 },
  { date: '2026-04-16', revenue: 38_800, spend: 9_600 },
  { date: '2026-04-19', revenue: 44_100, spend: 10_100 },
  { date: '2026-04-22', revenue: 47_600, spend: 10_700 },
  { date: '2026-04-25', revenue: 51_300, spend: 11_400 },
  { date: '2026-04-28', revenue: 48_900, spend: 11_900 },
];

export const mockKpis = {
  trustGate: {
    status: 'pass' as const,
    holds: 3,
    delta: -1,
  },
  signalHealth: {
    score: 87,
    delta: 4.1,
    status: 'healthy' as const,
  },
  roas: {
    value: 4.2,
    delta: 0.3,
  },
  pacing: {
    onTrack: 12,
    breaches: 2,
    deltaPercent: 3.2,
  },
};
