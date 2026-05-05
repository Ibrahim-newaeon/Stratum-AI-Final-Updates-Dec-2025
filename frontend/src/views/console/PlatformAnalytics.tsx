/**
 * Platform Analytics — Platform Owner page at /console/analytics.
 *
 * Cross-tenant rollup of platform health. Composed thinly over
 * existing react-query hooks:
 *
 *   usePlatformOverview(days)        — KPI strip
 *   useSignalHealthTrends(days)      — line chart
 *   useActionsAnalytics(days)        — breakdowns + daily counts
 *   useTenantProfitability(days)     — DataTable
 *
 * Window picker (7d / 14d / 30d) drives all four hooks in sync.
 */

import { useState } from 'react';
import {
  usePlatformOverview,
  useSignalHealthTrends,
  useActionsAnalytics,
  useTenantProfitability,
  formatPlatformName,
  type TenantProfitability,
} from '@/api/superadminAnalytics';
import { Card } from '@/components/primitives/Card';
import { KPI } from '@/components/primitives/KPI';
import { LineChart, AreaChart } from '@/components/primitives/Chart';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';
import { StatusPill } from '@/components/primitives/StatusPill';
import { cn } from '@/lib/utils';

type Window = 7 | 14 | 30;

const WINDOWS: { value: Window; label: string }[] = [
  { value: 7, label: '7d' },
  { value: 14, label: '14d' },
  { value: 30, label: '30d' },
];

export default function PlatformAnalytics() {
  const [days, setDays] = useState<Window>(7);

  const overview = usePlatformOverview(days);
  const trends = useSignalHealthTrends(days);
  const actions = useActionsAnalytics(days);
  const profitability = useTenantProfitability(days);

  const successRate = overview.data
    ? Math.round(overview.data.success_rate * 100) / 100
    : undefined;

  return (
    <div className="space-y-6">
      {/* Header + window picker */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">
            Platform Analytics
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Cross-tenant rollup of platform health, automation outcomes, and tenant efficiency.
          </p>
        </div>
        <div
          role="tablist"
          aria-label="Time window"
          className="inline-flex p-1 rounded-full border border-border bg-card"
        >
          {WINDOWS.map((w) => (
            <button
              key={w.value}
              role="tab"
              aria-selected={days === w.value}
              onClick={() => setDays(w.value)}
              className={cn(
                'px-4 h-8 text-xs font-mono uppercase tracking-wider rounded-full',
                'transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                days === w.value
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <KPI
          label="Active tenants"
          value={overview.data?.active_tenants}
          loading={overview.isPending}
          error={overview.error?.message}
          footnote={`${days}-day window`}
        />
        <KPI
          label="Total actions"
          value={overview.data?.total_actions?.toLocaleString()}
          loading={overview.isPending}
          error={overview.error?.message}
          footnote={
            overview.data
              ? `${overview.data.applied_actions.toLocaleString()} applied · ${overview.data.failed_actions.toLocaleString()} failed`
              : undefined
          }
        />
        <KPI
          label="Success rate"
          value={successRate !== undefined ? `${successRate}%` : undefined}
          loading={overview.isPending}
          error={overview.error?.message}
          status={
            successRate === undefined
              ? undefined
              : {
                  label:
                    successRate >= 90 ? 'Healthy' : successRate >= 70 ? 'Degraded' : 'Unhealthy',
                  variant:
                    successRate >= 90 ? 'healthy' : successRate >= 70 ? 'degraded' : 'unhealthy',
                }
          }
        />
        <KPI
          label="Trend direction"
          value={trends.data ? capitalize(trends.data.trend_direction) : undefined}
          loading={trends.isPending}
          error={trends.error?.message}
          footnote="Composite signal health"
        />
      </div>

      {/* Signal health trends */}
      <Card>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-foreground">Signal health trends</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Per-day average across all tenants. EMQ + freshness up = healthier; event loss + API
            error rate down = healthier.
          </p>
        </div>
        <LineChart
          data={trends.data?.trends ?? []}
          xKey="date"
          xFormat={(v) => formatShortDate(String(v))}
          yFormat={(v) => v.toFixed(1)}
          series={[
            { dataKey: 'avg_emq', name: 'Avg EMQ', color: 'hsl(var(--primary))' },
            { dataKey: 'avg_event_loss', name: 'Event loss %', color: 'hsl(var(--danger))' },
            {
              dataKey: 'avg_freshness_minutes',
              name: 'Freshness (min)',
              color: 'hsl(var(--info))',
            },
            {
              dataKey: 'avg_api_error_rate',
              name: 'API error %',
              color: 'hsl(var(--warning))',
            },
          ]}
          loading={trends.isPending}
          error={trends.error?.message}
          emptyMessage="No trend data for this window."
          height={280}
        />
      </Card>

      {/* Actions: daily counts + breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Card className="lg:col-span-2">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-foreground">Daily actions</h2>
            <p className="text-sm text-muted-foreground mt-0.5">
              Total automation actions per day across the platform.
            </p>
          </div>
          <AreaChart
            data={actions.data?.daily_counts ?? []}
            xKey="date"
            xFormat={(v) => formatShortDate(String(v))}
            series={[{ dataKey: 'count', name: 'Actions', color: 'hsl(var(--primary))' }]}
            loading={actions.isPending}
            error={actions.error?.message}
            emptyMessage="No actions in this window."
            height={240}
          />
        </Card>
        <Card>
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-foreground">Breakdowns</h2>
            <p className="text-sm text-muted-foreground mt-0.5">By type · status · platform</p>
          </div>
          <Breakdown
            title="Action type"
            data={actions.data?.type_breakdown}
            loading={actions.isPending}
          />
          <Breakdown
            title="Status"
            data={actions.data?.status_breakdown}
            loading={actions.isPending}
          />
          <Breakdown
            title="Platform"
            data={actions.data?.platform_breakdown}
            loading={actions.isPending}
            keyFormatter={formatPlatformName}
          />
        </Card>
      </div>

      {/* Tenant profitability table */}
      <Card>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-foreground">Tenant profitability</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Per-tenant action efficiency, EMQ, and composite health score over the last {days} days.
          </p>
        </div>
        <DataTable<TenantProfitability>
          data={profitability.data?.tenants ?? []}
          loading={profitability.isPending}
          error={profitability.error?.message}
          emptyMessage="No tenants active in this window."
          rowKey={(row) => row.tenant_id}
          ariaLabel="Tenant profitability"
          columns={tenantColumns}
        />
      </Card>
    </div>
  );
}

const tenantColumns: DataTableColumn<TenantProfitability>[] = [
  {
    id: 'tenant',
    header: 'Tenant',
    cell: (r) => <span className="font-medium text-foreground">#{r.tenant_id}</span>,
    sortable: true,
    sortAccessor: (r) => r.tenant_id,
  },
  {
    id: 'actions',
    header: 'Actions',
    cell: (r) => (
      <span className="font-mono tabular-nums">
        {r.applied_actions}/{r.total_actions}
      </span>
    ),
    sortable: true,
    sortAccessor: (r) => r.total_actions,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'efficiency',
    header: 'Efficiency',
    cell: (r) => (
      <span className="font-mono tabular-nums">{(r.action_efficiency * 100).toFixed(1)}%</span>
    ),
    sortable: true,
    sortAccessor: (r) => r.action_efficiency,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'emq',
    header: 'EMQ',
    cell: (r) => <span className="font-mono tabular-nums">{r.avg_emq_score.toFixed(1)}</span>,
    sortable: true,
    sortAccessor: (r) => r.avg_emq_score,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'event-loss',
    header: 'Event loss',
    cell: (r) => (
      <span className="font-mono tabular-nums">{(r.avg_event_loss * 100).toFixed(1)}%</span>
    ),
    sortable: true,
    sortAccessor: (r) => r.avg_event_loss,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
  },
  {
    id: 'days',
    header: 'Active days',
    cell: (r) => <span className="font-mono tabular-nums">{r.active_days}</span>,
    sortable: true,
    sortAccessor: (r) => r.active_days,
    cellClassName: 'text-right',
    headerClassName: 'text-right',
    hideOnMobile: true,
  },
  {
    id: 'health',
    header: 'Health',
    cell: (r) => {
      const v: 'healthy' | 'degraded' | 'unhealthy' =
        r.health_score >= 70 ? 'healthy' : r.health_score >= 40 ? 'degraded' : 'unhealthy';
      return <StatusPill variant={v}>{Math.round(r.health_score)}</StatusPill>;
    },
    sortable: true,
    sortAccessor: (r) => r.health_score,
  },
];

interface BreakdownProps {
  title: string;
  data?: Record<string, number>;
  loading?: boolean;
  keyFormatter?: (key: string) => string;
}

function Breakdown({ title, data, loading, keyFormatter }: BreakdownProps) {
  const entries = data
    ? Object.entries(data)
        .filter(([, v]) => v > 0)
        .sort((a, b) => b[1] - a[1])
    : [];
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  return (
    <div className="mb-5 last:mb-0">
      <div className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-2">
        {title}
      </div>
      {loading && (
        <div className="space-y-1.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-4 bg-muted/40 rounded animate-pulse" />
          ))}
        </div>
      )}
      {!loading && entries.length === 0 && (
        <div className="text-sm text-muted-foreground">No data.</div>
      )}
      {!loading &&
        entries.map(([key, count]) => {
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          return (
            <div key={key} className="mb-2 last:mb-0">
              <div className="flex items-center justify-between text-xs">
                <span className="text-foreground capitalize">
                  {keyFormatter ? keyFormatter(key) : key.replace(/_/g, ' ')}
                </span>
                <span className="font-mono tabular-nums text-muted-foreground">
                  {count.toLocaleString()} · {pct}%
                </span>
              </div>
              <div className="mt-1 h-1.5 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
    </div>
  );
}

function capitalize(s: string): string {
  if (!s) return '';
  return s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, ' ');
}

function formatShortDate(iso: string): string {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return iso;
  }
}
