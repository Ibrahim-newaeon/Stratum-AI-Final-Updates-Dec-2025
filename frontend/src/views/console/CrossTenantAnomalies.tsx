/**
 * Cross-Tenant Anomalies — Platform Owner page at /console/anomalies.
 *
 * Backed by /superadmin/anomalies-rollup, which aggregates every
 * tenant's anomalies in one backend call (one async session, N
 * database queries, zero HTTP fan-out). Replaces the prior pattern
 * of N parallel useAnomalies() requests from the browser, which
 * was fine at ~50 tenants but quadratic in network cost as we grow.
 */

import { useMemo, useState } from 'react';
import { useAnomaliesRollup, type CrossTenantAnomaly } from '@/api/superadminAnalytics';
import { Card } from '@/components/primitives/Card';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';
import { StatusPill } from '@/components/primitives/StatusPill';
import { cn } from '@/lib/utils';
import { ArrowDown, ArrowUp, X } from 'lucide-react';

type Severity = 'critical' | 'high' | 'medium' | 'low';

const SEVERITIES: { value: Severity | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const SEVERITY_VARIANT: Record<Severity, 'unhealthy' | 'degraded' | 'neutral'> = {
  critical: 'unhealthy',
  high: 'unhealthy',
  medium: 'degraded',
  low: 'neutral',
};

export default function CrossTenantAnomalies() {
  const [filter, setFilter] = useState<Severity | 'all'>('all');
  const [selected, setSelected] = useState<CrossTenantAnomaly | null>(null);

  const rollupQuery = useAnomaliesRollup();
  const rollup = rollupQuery.data;
  const allAnomalies = rollup?.anomalies ?? [];

  const visible = useMemo(
    () => (filter === 'all' ? allAnomalies : allAnomalies.filter((a) => a.severity === filter)),
    [allAnomalies, filter]
  );

  const tallies = rollup?.by_severity ?? { critical: 0, high: 0, medium: 0, low: 0 };

  const columns: DataTableColumn<CrossTenantAnomaly>[] = [
    {
      id: 'time',
      header: 'Detected',
      cell: (a) => (
        <span className="font-mono tabular-nums text-xs text-muted-foreground">
          {formatTime(a.detected_at)}
        </span>
      ),
      sortable: true,
      sortAccessor: (a) => new Date(a.detected_at).getTime(),
    },
    {
      id: 'tenant',
      header: 'Tenant',
      cell: (a) => <span className="font-medium text-foreground">{a.tenant_name}</span>,
      sortable: true,
      sortAccessor: (a) => a.tenant_name,
    },
    {
      id: 'metric',
      header: 'Metric',
      cell: (a) => (
        <span className="font-mono text-xs text-foreground">
          {a.metric} <span className="text-muted-foreground">· {a.entity_type}</span>
        </span>
      ),
      sortable: true,
      sortAccessor: (a) => a.metric,
    },
    {
      id: 'direction',
      header: 'Δ',
      cell: (a) => (
        <span
          className={cn(
            'inline-flex items-center gap-1 font-mono tabular-nums text-xs',
            a.direction === 'spike' ? 'text-warning' : 'text-info'
          )}
        >
          {a.direction === 'spike' ? (
            <ArrowUp className="w-3 h-3" />
          ) : (
            <ArrowDown className="w-3 h-3" />
          )}
          {a.current_value.toLocaleString()}{' '}
          {a.expected_value != null && (
            <span className="text-muted-foreground">vs {a.expected_value.toLocaleString()}</span>
          )}
        </span>
      ),
    },
    {
      id: 'severity',
      header: 'Severity',
      cell: (a) => <StatusPill variant={SEVERITY_VARIANT[a.severity]}>{a.severity}</StatusPill>,
      sortable: true,
      sortAccessor: (a) => severityWeight(a.severity),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">
          Cross-Tenant Anomalies
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Aggregated across {rollup?.tenants_scanned ?? '—'} tenant
          {rollup?.tenants_scanned === 1 ? '' : 's'}. Click a row for diagnosis + recommended
          actions.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {SEVERITIES.map((s) => {
          const count = s.value === 'all' ? allAnomalies.length : tallies[s.value as Severity];
          const active = filter === s.value;
          return (
            <button
              key={s.value}
              type="button"
              onClick={() => setFilter(s.value)}
              className={cn(
                'inline-flex items-center gap-2 px-3 h-8 rounded-full text-xs font-mono uppercase tracking-wider',
                'border transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                active
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-card text-muted-foreground border-border hover:text-foreground'
              )}
            >
              {s.label}
              <span
                className={cn(
                  'inline-flex items-center justify-center min-w-5 px-1.5 h-5 rounded-full text-[10px] font-bold',
                  active
                    ? 'bg-primary-foreground/20 text-primary-foreground'
                    : 'bg-muted text-muted-foreground'
                )}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      <Card>
        <DataTable<CrossTenantAnomaly>
          data={visible}
          columns={columns}
          rowKey={(r) => `${r.tenant_id}:${r.id}`}
          onRowClick={(r) => setSelected(r)}
          loading={rollupQuery.isLoading}
          emptyMessage={
            filter === 'all' ? 'No anomalies detected in any tenant.' : `No ${filter} anomalies.`
          }
          ariaLabel="Cross-tenant anomalies"
        />
      </Card>

      {selected && <AnomalyDetail anomaly={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

interface AnomalyDetailProps {
  anomaly: CrossTenantAnomaly;
  onClose: () => void;
}

function AnomalyDetail({ anomaly, onClose }: AnomalyDetailProps) {
  return (
    <>
      <div
        aria-hidden="true"
        onClick={onClose}
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm animate-fade-in"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="anomaly-detail-title"
        className={cn(
          'fixed top-0 right-0 bottom-0 z-50',
          'w-full sm:max-w-lg',
          'bg-card border-l border-border',
          'overflow-y-auto'
        )}
      >
        <div className="sticky top-0 bg-card/95 backdrop-blur border-b border-border px-6 py-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <StatusPill variant={SEVERITY_VARIANT[anomaly.severity]}>
                {anomaly.severity}
              </StatusPill>
              {anomaly.zscore != null && (
                <span className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                  z = {anomaly.zscore.toFixed(2)}
                </span>
              )}
            </div>
            <h2 id="anomaly-detail-title" className="text-lg font-semibold text-foreground">
              {anomaly.metric} · {anomaly.tenant_name}
            </h2>
            <p className="text-xs text-muted-foreground font-mono mt-0.5">
              {formatTime(anomaly.detected_at)} · {anomaly.entity_type} ·{' '}
              {anomaly.entity_name || anomaly.entity_id}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close detail"
            className="flex-shrink-0 p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          <section>
            <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">
              Description
            </div>
            <p className="text-sm text-foreground leading-relaxed">{anomaly.description}</p>
          </section>

          <section>
            <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">
              Values
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-border p-3">
                <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  Current
                </div>
                <div className="mt-1 text-xl font-semibold tabular-nums text-foreground">
                  {anomaly.current_value.toLocaleString()}
                </div>
              </div>
              <div className="rounded-lg border border-border p-3">
                <div className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                  Expected
                </div>
                <div className="mt-1 text-xl font-semibold tabular-nums text-foreground">
                  {anomaly.expected_value != null ? anomaly.expected_value.toLocaleString() : '—'}
                </div>
              </div>
            </div>
          </section>

          {anomaly.possible_causes.length > 0 && (
            <section>
              <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">
                Possible causes
              </div>
              <ul className="list-disc list-inside text-sm text-foreground space-y-1">
                {anomaly.possible_causes.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </section>
          )}

          {anomaly.recommended_actions.length > 0 && (
            <section>
              <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">
                Recommended actions
              </div>
              <ul className="list-disc list-inside text-sm text-foreground space-y-1">
                {anomaly.recommended_actions.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </aside>
    </>
  );
}

function formatTime(iso: string): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return iso;
  }
}

function severityWeight(s: Severity): number {
  return { critical: 4, high: 3, medium: 2, low: 1 }[s];
}
