/**
 * Shared types for the Overview composition.
 *
 * Real API hooks shape the source data; these intermediate types are what
 * the UI sub-components consume. Keeping them centralized here means the
 * sub-components stay agnostic of which hook fed them, which makes mocking
 * + future API swaps trivial.
 */

import type { InsightItem } from '@/components/primitives/InsightsPanel';

export type FocusKey =
  | 'trust-holds'
  | 'signal-drops'
  | 'pacing-breaches'
  | 'autopilot-pending'
  | 'all-clear';

export type AlertSeverity = 'critical' | 'warning' | 'info';

export interface AlertSummary {
  /** Total alerts that match this focus key. */
  count: number;
  severity: AlertSeverity;
  /** Stable focus key — clicking the chip drives the FocusPane. */
  focus: FocusKey;
  /** Human label for the chip. */
  label: string;
}

export interface TrustHoldRow {
  id: string;
  campaign: string;
  account: string;
  violation: string;
  severity: AlertSeverity;
  detectedAt: string;
  recommendedAction: 'scale' | 'pause' | 'hold';
}

export interface PacingBreachRow {
  id: string;
  target: string;
  budget: number;
  spent: number;
  percentOfTarget: number;
  daysRemaining: number;
}

export interface AutopilotDecisionRow {
  id: string;
  time: string;
  campaign: string;
  action: 'budget_increase' | 'budget_decrease' | 'pause' | 'enable' | 'bid_adjust';
  result: 'executed' | 'held' | 'blocked' | 'pending';
  trust: number;
}

export interface SignalDropDetail {
  emqScore: number;
  emqDelta: number;
  pipelineHealth: 'healthy' | 'degraded' | 'unhealthy';
  recentEvents: number;
  expectedEvents: number;
  affectedPlatforms: string[];
}

export interface RevenueSpendPoint {
  date: string;
  revenue: number;
  spend: number;
}

export type Insight = InsightItem;
