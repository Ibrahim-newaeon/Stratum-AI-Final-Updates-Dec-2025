/**
 * Overview — Stratum dashboard home.
 *
 * Composition (top → bottom):
 *   1. KpiStrip       — 4 compact cards (Trust / Signal / ROAS / Pacing)
 *   2. SignalStrip    — alert chips + bulk-acknowledge
 *   3. FocusPane      — URL-driven adaptive surface (?focus=…)
 *   4. RecentAutopilot — last 24h decisions, always present
 *
 * Selected focus is URL-driven so the page is shareable, refreshable,
 * and honors the browser back button. Default focus = highest-severity
 * alert if any, otherwise 'all-clear'.
 */

import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';

import { KpiStrip } from './overview/KpiStrip';
import { SignalStrip } from './overview/SignalStrip';
import { FocusPane } from './overview/FocusPane';
import { RecentAutopilot } from './overview/RecentAutopilot';
import { mockAlertSummaries, mockAutopilotDecisions } from './overview/mockData';
import type { AlertSummary, FocusKey } from './overview/types';

const SEVERITY_RANK: Record<AlertSummary['severity'], number> = {
  critical: 0,
  warning: 1,
  info: 2,
};

const VALID_FOCUS: FocusKey[] = [
  'trust-holds',
  'signal-drops',
  'pacing-breaches',
  'autopilot-pending',
  'all-clear',
];

function isValidFocus(value: string | null): value is FocusKey {
  return value !== null && (VALID_FOCUS as string[]).includes(value);
}

function pickDefaultFocus(summaries: AlertSummary[]): FocusKey {
  const withCount = summaries.filter((s) => s.count > 0);
  if (withCount.length === 0) return 'all-clear';
  const sorted = [...withCount].sort(
    (a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]
  );
  return sorted[0].focus;
}

export default function Overview() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Real API hooks would replace these — see overview/mockData.ts.
  const summaries = mockAlertSummaries;
  const autopilotDecisions = mockAutopilotDecisions;
  const autopilotPending = useMemo(
    () => autopilotDecisions.filter((r) => r.result === 'pending'),
    [autopilotDecisions]
  );

  const requestedFocus = searchParams.get('focus');
  const selectedFocus: FocusKey = isValidFocus(requestedFocus)
    ? requestedFocus
    : pickDefaultFocus(summaries);

  const setFocus = useCallback(
    (focus: FocusKey) => {
      const next = new URLSearchParams(searchParams);
      next.set('focus', focus);
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const handleAcknowledgeAll = useCallback(() => {
    // TODO: wire to bulk-acknowledge mutation with confirmation drawer.
    // Intentional no-op until the action API + drawer ship in a follow-up.
  }, []);

  const handleAutopilotRowClick = useCallback((_row: (typeof mockAutopilotDecisions)[number]) => {
    // TODO: navigate to /dashboard/autopilot/:id detail. Deferred to
    // route-wiring follow-up.
  }, []);

  return (
    <>
      <Helmet>
        <title>Overview · Stratum AI</title>
      </Helmet>

      <div className="space-y-6">
        <header>
          <h1 className="text-h1 font-medium tracking-tight text-foreground">Overview</h1>
          <p className="text-body text-muted-foreground mt-1">
            What needs your attention right now.
          </p>
        </header>

        <KpiStrip />

        <SignalStrip
          summaries={summaries}
          selectedFocus={selectedFocus}
          onSelectFocus={setFocus}
          onAcknowledgeAll={handleAcknowledgeAll}
        />

        <FocusPane focus={selectedFocus} autopilotPending={autopilotPending} />

        <RecentAutopilot rows={autopilotDecisions} onRowClick={handleAutopilotRowClick} />
      </div>
    </>
  );
}
