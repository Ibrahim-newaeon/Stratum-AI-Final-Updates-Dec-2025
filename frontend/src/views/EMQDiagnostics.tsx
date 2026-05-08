/**
 * EMQ Diagnostics — operator-facing event measurement quality page.
 *
 * Surfaces the EMQ v2 endpoints (score, drivers, confidence band,
 * playbook, recent incidents) that previously had no UI even though
 * the API client was already wired in `frontend/src/api/emqV2.ts`.
 *
 * Mounted at /dashboard/trust/emq under the Trust Engine sub-nav.
 */

import { useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Minus,
} from 'lucide-react';

import { useTenantStore, selectTenantId } from '@/stores/tenantStore';
import { useQAFixesPlaybook, useQAFixesHistory, type QAFixPlaybookItem } from '@/api/qaFixes';
import {
  useEmqScore,
  useConfidence,
  useEmqPlaybook,
  useEmqIncidents,
  useUpdatePlaybookItem,
  type PlaybookItem,
} from '@/api/emqV2';
import { Card } from '@/components/primitives/Card';
import { KPI } from '@/components/primitives/KPI';
import { StatusPill, type StatusPillVariant } from '@/components/primitives/StatusPill';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';
import { cn } from '@/lib/utils';

const PRIORITY_VARIANT: Record<PlaybookItem['priority'], StatusPillVariant> = {
  critical: 'unhealthy',
  high: 'degraded',
  medium: 'neutral',
  low: 'healthy',
};

const STATUS_VARIANT: Record<PlaybookItem['status'], StatusPillVariant> = {
  pending: 'neutral',
  in_progress: 'degraded',
  completed: 'healthy',
};

function isoDateNDaysAgo(n: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function trendIcon(trend: 'up' | 'down' | 'flat') {
  if (trend === 'up') return <ArrowUpRight className="h-3.5 w-3.5 text-success" aria-label="up" />;
  if (trend === 'down')
    return <ArrowDownRight className="h-3.5 w-3.5 text-danger" aria-label="down" />;
  return <Minus className="h-3.5 w-3.5 text-muted-foreground" aria-label="flat" />;
}

interface IncidentRow {
  id: string;
  timestamp: string;
  severity: PlaybookItem['priority'];
  title: string;
  platform: string | null;
  emqImpact: number | null;
}

export default function EMQDiagnostics() {
  const tenantId = useTenantStore(selectTenantId) ?? 0;
  const [windowDays] = useState(14);

  const scoreQuery = useEmqScore(tenantId);
  const confidenceQuery = useConfidence(tenantId);
  const playbookQuery = useEmqPlaybook(tenantId);
  const incidentsQuery = useEmqIncidents(tenantId, isoDateNDaysAgo(windowDays), todayIso());
  const updateItem = useUpdatePlaybookItem(tenantId);

  const score = scoreQuery.data;
  const confidence = confidenceQuery.data;
  const playbook = playbookQuery.data ?? [];
  const incidents = (incidentsQuery.data ?? []) as IncidentRow[];

  const delta = useMemo(() => {
    if (!score?.score || score.previousScore == null) return undefined;
    return { value: score.score - score.previousScore, format: 'absolute' as const };
  }, [score]);

  if (!tenantId) {
    return (
      <div className="p-6">
        <Card className="p-8 text-center text-muted-foreground">
          Select a tenant to view EMQ diagnostics.
        </Card>
      </div>
    );
  }

  const incidentColumns: DataTableColumn<IncidentRow>[] = [
    {
      id: 'timestamp',
      header: 'When',
      cell: (r) => (
        <span className="font-mono text-xs text-muted-foreground">
          {new Date(r.timestamp).toLocaleString()}
        </span>
      ),
    },
    {
      id: 'severity',
      header: 'Severity',
      cell: (r) => (
        <StatusPill variant={PRIORITY_VARIANT[r.severity]} size="sm">
          {r.severity}
        </StatusPill>
      ),
    },
    { id: 'title', header: 'Title', cell: (r) => r.title },
    {
      id: 'platform',
      header: 'Platform',
      cell: (r) => r.platform ?? '—',
    },
    {
      id: 'emqImpact',
      header: 'EMQ impact',
      cellClassName: 'text-right',
      headerClassName: 'text-right',
      cell: (r) =>
        r.emqImpact == null ? (
          '—'
        ) : (
          <span className="font-mono tabular-nums">{r.emqImpact.toFixed(1)}</span>
        ),
    },
  ];

  return (
    <div className="space-y-6 p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">EMQ Diagnostics</h1>
        <p className="text-sm text-muted-foreground">
          Event measurement quality, confidence band, fix playbook, and the last {windowDays} days
          of incidents.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <KPI
          label="EMQ score"
          value={score ? score.score.toFixed(1) : undefined}
          delta={delta}
          emphasis={score?.confidenceBand === 'reliable' ? 'glow' : 'default'}
          loading={scoreQuery.isLoading}
        />
        <KPI
          label="Confidence band"
          value={
            confidence?.band
              ? confidence.band[0].toUpperCase() + confidence.band.slice(1)
              : undefined
          }
          loading={confidenceQuery.isLoading}
        />
        <KPI
          label="Open playbook items"
          value={playbook.filter((p) => p.status !== 'completed').length.toString()}
          loading={playbookQuery.isLoading}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="mb-4 font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Drivers
          </h2>
          <ul className="space-y-3">
            {(score?.drivers ?? []).map((d) => (
              <li
                key={d.name}
                className="flex items-center justify-between gap-3 rounded-xl border border-border bg-muted/40 p-3"
              >
                <div className="min-w-0 space-y-0.5">
                  <div className="flex items-center gap-2">
                    <p className="truncate text-sm font-medium">{d.name}</p>
                    {trendIcon(d.trend)}
                  </div>
                  <p className="font-mono text-xs text-muted-foreground">
                    weight {Math.round(d.weight * 100)}%
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm tabular-nums">{d.value.toFixed(1)}</span>
                  <StatusPill
                    variant={
                      d.status === 'good'
                        ? 'healthy'
                        : d.status === 'warning'
                          ? 'degraded'
                          : 'unhealthy'
                    }
                    size="sm"
                  >
                    {d.status}
                  </StatusPill>
                </div>
              </li>
            ))}
            {!scoreQuery.isLoading && (score?.drivers ?? []).length === 0 && (
              <li className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                No driver data yet.
              </li>
            )}
          </ul>
        </Card>

        <Card className="p-6">
          <h2 className="mb-4 font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Confidence factors
          </h2>
          <ul className="space-y-2">
            {(confidence?.factors ?? []).map((f) => (
              <li
                key={f.name}
                className="flex items-center justify-between rounded-xl border border-border bg-muted/40 p-3 text-sm"
              >
                <span className="truncate">{f.name}</span>
                <span
                  className={cn(
                    'font-mono tabular-nums',
                    f.status === 'positive' && 'text-success',
                    f.status === 'negative' && 'text-danger',
                    f.status === 'neutral' && 'text-muted-foreground'
                  )}
                >
                  {f.contribution > 0 ? '+' : ''}
                  {f.contribution.toFixed(1)}
                </span>
              </li>
            ))}
            {!confidenceQuery.isLoading && (confidence?.factors ?? []).length === 0 && (
              <li className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                No factor data yet.
              </li>
            )}
          </ul>
        </Card>
      </section>

      <Card className="p-6">
        <header className="mb-4 flex items-center justify-between">
          <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Fix playbook
          </h2>
          <span className="text-xs text-muted-foreground">{playbook.length} items</span>
        </header>
        <ul className="space-y-3">
          {playbook.map((p) => (
            <li
              key={p.id}
              className="flex items-start justify-between gap-3 rounded-xl border border-border bg-muted/40 p-4"
            >
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <StatusPill variant={PRIORITY_VARIANT[p.priority]} size="sm">
                    {p.priority}
                  </StatusPill>
                  <StatusPill variant={STATUS_VARIANT[p.status]} size="sm">
                    {p.status.replace('_', ' ')}
                  </StatusPill>
                  {p.platform && (
                    <span className="font-mono text-xs text-muted-foreground">{p.platform}</span>
                  )}
                </div>
                <p className="truncate text-sm font-medium">{p.title}</p>
                <p className="line-clamp-2 text-sm text-muted-foreground">{p.description}</p>
                <p className="font-mono text-xs text-muted-foreground">
                  +{p.estimatedImpact.toFixed(1)} EMQ
                  {p.estimatedTime ? ` · ${p.estimatedTime}` : ''}
                </p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-2">
                {p.status !== 'completed' && (
                  <button
                    type="button"
                    disabled={updateItem.isPending}
                    onClick={() =>
                      updateItem.mutate({
                        itemId: p.id,
                        updates: {
                          status: p.status === 'pending' ? 'in_progress' : 'completed',
                        },
                      })
                    }
                    className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 font-mono text-xs uppercase tracking-wider hover:bg-muted disabled:opacity-50"
                  >
                    {p.status === 'pending' ? 'Start' : 'Complete'}
                    {p.status === 'pending' ? (
                      <ArrowRight className="h-3 w-3" />
                    ) : (
                      <CheckCircle2 className="h-3 w-3" />
                    )}
                  </button>
                )}
                {p.actionUrl && (
                  <a
                    href={p.actionUrl}
                    className="text-xs text-primary underline-offset-4 hover:underline"
                  >
                    Open
                  </a>
                )}
              </div>
            </li>
          ))}
          {!playbookQuery.isLoading && playbook.length === 0 && (
            <li className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              <CheckCircle2 className="mx-auto mb-2 h-5 w-5 text-success" />
              No fixes pending — nice.
            </li>
          )}
        </ul>
      </Card>

      <FixGuideSection tenantId={tenantId} />

      <Card className="p-6">
        <header className="mb-4 flex items-center justify-between">
          <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Recent incidents
          </h2>
          <span className="text-xs text-muted-foreground">last {windowDays}d</span>
        </header>
        {!incidentsQuery.isLoading && incidents.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-6 text-sm text-muted-foreground">
            <AlertTriangle className="h-5 w-5" />
            No incidents in the window.
          </div>
        ) : (
          <DataTable<IncidentRow>
            data={incidents}
            columns={incidentColumns}
            loading={incidentsQuery.isLoading}
            rowKey={(r) => r.id}
            ariaLabel="Recent EMQ incidents"
          />
        )}
      </Card>
    </div>
  );
}

function FixGuideSection({ tenantId }: { tenantId: number }) {
  const playbookQuery = useQAFixesPlaybook(tenantId);
  const historyQuery = useQAFixesHistory(tenantId, 5);
  const items: QAFixPlaybookItem[] = playbookQuery.data?.items ?? [];
  const history = historyQuery.data?.history ?? [];

  return (
    <Card className="p-6 space-y-4">
      <header className="flex items-center justify-between">
        <h2 className="font-mono text-sm uppercase tracking-wider text-muted-foreground">
          Step-by-step fix guide
        </h2>
        {playbookQuery.data?.estimated_total_impact != null && (
          <span className="font-mono text-xs text-muted-foreground">
            +{playbookQuery.data.estimated_total_impact.toFixed(1)} EMQ available
          </span>
        )}
      </header>

      <ul className="space-y-3">
        {items.map((it) => (
          <li
            key={it.id}
            className="rounded-xl border border-border bg-muted/40 p-4"
          >
            <details>
              <summary className="cursor-pointer list-none flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <StatusPill variant={PRIORITY_VARIANT[it.priority]} size="sm">
                      {it.priority}
                    </StatusPill>
                    {it.platform && (
                      <span className="font-mono text-xs text-muted-foreground">
                        {it.platform}
                      </span>
                    )}
                  </div>
                  <p className="text-sm font-medium">{it.title}</p>
                  <p className="text-sm text-muted-foreground">{it.description}</p>
                </div>
                <span className="font-mono text-xs text-muted-foreground shrink-0">
                  +{it.estimated_impact.toFixed(1)} EMQ
                </span>
              </summary>
              {it.steps.length > 0 && (
                <ol className="mt-3 space-y-1.5 border-t border-border/50 pt-3 text-sm text-foreground">
                  {it.steps.map((step, idx) => (
                    <li key={idx} className="flex gap-2">
                      <span className="font-mono text-xs text-muted-foreground tabular-nums">
                        {idx + 1}.
                      </span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ol>
              )}
            </details>
          </li>
        ))}
        {!playbookQuery.isLoading && items.length === 0 && (
          <li className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            No step-by-step fixes available — connect a platform to detect issues.
          </li>
        )}
      </ul>

      {history.length > 0 && (
        <details className="rounded-xl border border-border bg-muted/40 p-4">
          <summary className="cursor-pointer text-sm font-medium">
            Recent fix activity
            <span className="ml-2 font-mono text-xs text-muted-foreground">
              {historyQuery.data?.total ?? history.length}
            </span>
          </summary>
          <ul className="mt-3 space-y-1.5 text-sm">
            {history.map((h) => (
              <li
                key={h.id}
                className="flex items-baseline justify-between gap-2 text-muted-foreground"
              >
                <span>
                  <span className="font-mono text-xs">{h.action_type}</span>
                  {h.entity_id && ` · ${h.entity_id}`}
                </span>
                {h.timestamp && (
                  <span className="font-mono text-xs tabular-nums">
                    {new Date(h.timestamp).toLocaleString()}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </Card>
  );
}
