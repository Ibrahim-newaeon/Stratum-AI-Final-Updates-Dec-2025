/**
 * FocusPane — URL-driven adaptive surface.
 *
 * The selected focus key (?focus= query param) drives which sub-view is
 * rendered. Each sub-view is a different *kind* of detail — Trust holds
 * need a table; Signal drops need an EMQ pipeline view; Pacing breaches
 * need a budget chart. Forcing them into the same widget would muddy
 * each.
 *
 * Sub-views are intentionally simple compositions of primitives (Card,
 * DataTable, Chart) — no bespoke layout logic, so each is reviewable
 * and replaceable in isolation.
 */

import { useMemo } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Pause,
  PlayCircle,
  ShieldAlert,
  TrendingUp,
} from 'lucide-react';
import { Card } from '@/components/primitives/Card';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';
import { LineChart } from '@/components/primitives/Chart';
import { StatusPill } from '@/components/primitives/StatusPill';
import { cn } from '@/lib/utils';
import { mockTrustHolds, mockSignalDrop, mockPacingBreaches, mockRevenueSpend } from './mockData';
import type { AutopilotDecisionRow, FocusKey, PacingBreachRow, TrustHoldRow } from './types';

interface FocusPaneProps {
  focus: FocusKey;
  /** Optional autopilot pending list (for the autopilot-pending sub-view). */
  autopilotPending?: AutopilotDecisionRow[];
  loading?: boolean;
}

function FocusHeader({
  icon: Icon,
  title,
  description,
  tone = 'neutral',
}: {
  icon: typeof AlertCircle;
  title: string;
  description?: string;
  tone?: 'critical' | 'warning' | 'info' | 'success' | 'neutral';
}) {
  const toneClass = {
    critical: 'text-danger',
    warning: 'text-warning',
    info: 'text-info',
    success: 'text-success',
    neutral: 'text-muted-foreground',
  }[tone];
  return (
    <div className="flex items-start gap-3 mb-5">
      <Icon className={cn('w-5 h-5 mt-0.5 flex-shrink-0', toneClass)} aria-hidden="true" />
      <div>
        <h2 className="text-h2 font-medium tracking-tight text-foreground">{title}</h2>
        {description && <p className="text-body text-muted-foreground mt-1">{description}</p>}
      </div>
    </div>
  );
}

// ───────────────────────── Trust holds ─────────────────────────

const TRUST_ACTION_LABEL: Record<TrustHoldRow['recommendedAction'], string> = {
  scale: 'Scale',
  pause: 'Pause',
  hold: 'Hold',
};

const TRUST_ACTION_ICON: Record<TrustHoldRow['recommendedAction'], typeof Pause> = {
  scale: TrendingUp,
  pause: Pause,
  hold: ShieldAlert,
};

function TrustHoldsView({ rows, loading }: { rows: TrustHoldRow[]; loading?: boolean }) {
  const columns: DataTableColumn<TrustHoldRow>[] = useMemo(
    () => [
      {
        id: 'campaign',
        header: 'Campaign',
        cell: (r) => (
          <div className="min-w-0">
            <p className="text-foreground font-medium truncate">{r.campaign}</p>
            <p className="text-meta text-muted-foreground mt-0.5">{r.account}</p>
          </div>
        ),
        className: 'w-2/5',
      },
      {
        id: 'violation',
        header: 'Violation',
        cell: (r) => (
          <div className="flex items-center gap-2">
            <StatusPill variant={r.severity === 'critical' ? 'unhealthy' : 'degraded'} size="sm">
              {r.severity}
            </StatusPill>
            <span className="text-body text-foreground">{r.violation}</span>
          </div>
        ),
        hideOnMobile: false,
      },
      {
        id: 'detected',
        header: 'Detected',
        cell: (r) => (
          <span className="text-meta text-muted-foreground font-mono tabular-nums">
            {r.detectedAt}
          </span>
        ),
        hideOnMobile: true,
        className: 'w-32',
      },
      {
        id: 'action',
        header: '',
        cell: (r) => {
          const Icon = TRUST_ACTION_ICON[r.recommendedAction];
          return (
            <button
              type="button"
              className={cn(
                'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full',
                'text-meta font-medium',
                'bg-card border border-border text-foreground',
                'hover:border-primary/50 hover:bg-muted transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              <Icon className="w-3.5 h-3.5" aria-hidden="true" />
              {TRUST_ACTION_LABEL[r.recommendedAction]}
            </button>
          );
        },
        className: 'w-32 text-right',
      },
    ],
    []
  );

  return (
    <>
      <FocusHeader
        icon={AlertCircle}
        title="Trust holds"
        description="Automations the trust gate is holding for manual review."
        tone="critical"
      />
      <DataTable
        data={rows}
        columns={columns}
        rowKey={(r) => r.id}
        loading={loading}
        emptyMessage="No trust holds in the last 24 hours."
        ariaLabel="Trust holds"
      />
    </>
  );
}

// ───────────────────────── Signal drops ─────────────────────────

function SignalDropsView({ loading }: { loading?: boolean }) {
  if (loading) {
    return (
      <>
        <FocusHeader icon={AlertTriangle} title="Signal drops" tone="warning" />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl bg-muted/40 animate-pulse" />
          ))}
        </div>
      </>
    );
  }

  const d = mockSignalDrop;
  const lossPct = Math.round((1 - d.recentEvents / d.expectedEvents) * 100);
  const pipelineTone =
    d.pipelineHealth === 'healthy'
      ? 'healthy'
      : d.pipelineHealth === 'degraded'
        ? 'degraded'
        : 'unhealthy';

  return (
    <>
      <FocusHeader
        icon={AlertTriangle}
        title="Signal drops"
        description="Event-quality fell below the trust gate threshold. Investigate before resuming."
        tone="warning"
      />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        <Card className="p-5">
          <p className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono mb-2">
            EMQ score
          </p>
          <p className="text-display-xs font-medium tabular-nums text-foreground">
            {d.emqScore}
            <span className="text-meta text-danger font-mono ml-2">
              {d.emqDelta > 0 ? '+' : ''}
              {d.emqDelta}
            </span>
          </p>
        </Card>
        <Card className="p-5">
          <p className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono mb-2">
            Event loss
          </p>
          <p className="text-display-xs font-medium tabular-nums text-foreground">{lossPct}%</p>
          <p className="text-meta text-muted-foreground mt-1 font-mono tabular-nums">
            {d.recentEvents.toLocaleString()} / {d.expectedEvents.toLocaleString()} expected
          </p>
        </Card>
        <Card className="p-5">
          <p className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono mb-2">
            Pipeline
          </p>
          <StatusPill variant={pipelineTone} size="md" pulse={pipelineTone !== 'healthy'}>
            {d.pipelineHealth}
          </StatusPill>
          <p className="text-meta text-muted-foreground mt-3">{d.affectedPlatforms.join(' · ')}</p>
        </Card>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary text-primary-foreground text-meta font-medium hover:brightness-110 transition-all"
        >
          View pipeline
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border bg-card text-foreground text-meta font-medium hover:bg-muted transition-colors"
        >
          Rerun diagnostics
        </button>
      </div>
    </>
  );
}

// ───────────────────────── Pacing breaches ─────────────────────

function PacingBreachesView({ rows, loading }: { rows: PacingBreachRow[]; loading?: boolean }) {
  const columns: DataTableColumn<PacingBreachRow>[] = useMemo(
    () => [
      {
        id: 'target',
        header: 'Target',
        cell: (r) => <span className="text-foreground font-medium truncate">{r.target}</span>,
      },
      {
        id: 'spent',
        header: 'Spent',
        cell: (r) => (
          <span className="text-foreground tabular-nums font-mono">
            ${r.spent.toLocaleString()}
            <span className="text-muted-foreground ml-1.5">/ ${r.budget.toLocaleString()}</span>
          </span>
        ),
        sortable: true,
        sortAccessor: (r) => r.spent,
      },
      {
        id: 'pct',
        header: '% of target',
        cell: (r) => (
          <span
            className={cn(
              'tabular-nums font-mono',
              r.percentOfTarget > 110 || r.percentOfTarget < 80 ? 'text-warning' : 'text-foreground'
            )}
          >
            {r.percentOfTarget}%
          </span>
        ),
        sortable: true,
        sortAccessor: (r) => r.percentOfTarget,
        className: 'w-32',
      },
      {
        id: 'days',
        header: 'Days left',
        cell: (r) => (
          <span className="text-muted-foreground tabular-nums font-mono">{r.daysRemaining}d</span>
        ),
        hideOnMobile: true,
        className: 'w-24',
      },
    ],
    []
  );

  return (
    <>
      <FocusHeader
        icon={AlertTriangle}
        title="Pacing breaches"
        description="Targets either over- or under-pacing relative to the period plan."
        tone="warning"
      />
      <DataTable
        data={rows}
        columns={columns}
        rowKey={(r) => r.id}
        loading={loading}
        emptyMessage="All targets pacing within tolerance."
        ariaLabel="Pacing breaches"
      />
    </>
  );
}

// ───────────────────────── Autopilot pending ───────────────────

function AutopilotPendingView({
  rows,
  loading,
}: {
  rows: AutopilotDecisionRow[];
  loading?: boolean;
}) {
  const columns: DataTableColumn<AutopilotDecisionRow>[] = useMemo(
    () => [
      {
        id: 'time',
        header: 'Time',
        cell: (r) => (
          <span className="text-meta text-muted-foreground font-mono tabular-nums">{r.time}</span>
        ),
        className: 'w-20',
      },
      {
        id: 'campaign',
        header: 'Campaign',
        cell: (r) => <span className="text-foreground">{r.campaign}</span>,
      },
      {
        id: 'action',
        header: 'Action',
        cell: (r) => (
          <span className="text-meta text-muted-foreground font-mono uppercase tracking-[0.06em]">
            {r.action.replace('_', ' ')}
          </span>
        ),
        hideOnMobile: true,
      },
      {
        id: 'trust',
        header: 'Trust',
        cell: (r) => (
          <span
            className={cn(
              'tabular-nums font-mono',
              r.trust >= 70 ? 'text-success' : r.trust >= 40 ? 'text-warning' : 'text-danger'
            )}
          >
            {r.trust}
          </span>
        ),
        className: 'w-20',
      },
    ],
    []
  );

  return (
    <>
      <FocusHeader
        icon={PlayCircle}
        title="Autopilot pending"
        description="Decisions queued for soft-block approval."
        tone="info"
      />
      <DataTable
        data={rows}
        columns={columns}
        rowKey={(r) => r.id}
        loading={loading}
        emptyMessage="No pending decisions."
        ariaLabel="Autopilot pending"
      />
    </>
  );
}

// ───────────────────────── All clear ───────────────────────────

function AllClearView({ loading }: { loading?: boolean }) {
  return (
    <>
      <FocusHeader
        icon={CheckCircle2}
        title="System nominal"
        description="All signals operational. Recent revenue vs. spend."
        tone="success"
      />
      <LineChart
        data={mockRevenueSpend}
        series={[
          { dataKey: 'revenue', name: 'Revenue' },
          { dataKey: 'spend', name: 'Spend' },
        ]}
        xKey="date"
        loading={loading}
        height={260}
        xFormat={(v) => {
          if (typeof v !== 'string') return String(v);
          const d = new Date(v);
          return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }}
        yFormat={(v) => `$${(v / 1000).toFixed(0)}k`}
        tooltipFormat={(v) => `$${v.toLocaleString()}`}
      />
    </>
  );
}

// ───────────────────────── Router ──────────────────────────────

export function FocusPane({ focus, autopilotPending = [], loading }: FocusPaneProps) {
  return (
    <Card className="p-6">
      {focus === 'trust-holds' && <TrustHoldsView rows={mockTrustHolds} loading={loading} />}
      {focus === 'signal-drops' && <SignalDropsView loading={loading} />}
      {focus === 'pacing-breaches' && (
        <PacingBreachesView rows={mockPacingBreaches} loading={loading} />
      )}
      {focus === 'autopilot-pending' && (
        <AutopilotPendingView rows={autopilotPending} loading={loading} />
      )}
      {focus === 'all-clear' && <AllClearView loading={loading} />}
    </Card>
  );
}

export default FocusPane;
