/**
 * Audit Services — Platform Owner page at /console/audit-services.
 *
 * Read-only operator pane over the audit_services router's status
 * surface: the 9-service health roll-up, aggregate counts, enabled
 * toggles, and the rate-limit envelope. The ~35 mutation endpoints
 * (EMQ measure, offline conv upload, experiment start/stop, budget
 * plan approve, LTV predict, etc.) stay backend-only until each
 * gets its own per-domain page.
 */

import {
  useAuditServicesHealth,
  useAuditServicesMetrics,
  useAuditServicesStatus,
  useAuditServicesRateLimits,
  useAuditServicesAuditLog,
  type ServiceHealth,
} from '@/api/auditServices';
import { Card } from '@/components/primitives/Card';
import { KPI } from '@/components/primitives/KPI';
import { StatusPill, type StatusPillVariant } from '@/components/primitives/StatusPill';
import { cn } from '@/lib/utils';

const HEALTH_VARIANT: Record<ServiceHealth, StatusPillVariant> = {
  healthy: 'healthy',
  degraded: 'degraded',
  unhealthy: 'unhealthy',
};

const SERVICE_LABELS: Record<string, string> = {
  emq: 'EMQ measurement',
  offline_conversions: 'Offline conversions',
  ab_testing: 'A/B testing',
  latency_tracking: 'Latency tracking',
  creative_performance: 'Creative performance',
  benchmarking: 'Benchmarking',
  budget_reallocation: 'Budget reallocation',
  audience_insights: 'Audience insights',
  ltv_predictor: 'LTV predictor',
};

function prettyServiceName(key: string): string {
  return SERVICE_LABELS[key] ?? key.replace(/_/g, ' ');
}

export default function AuditServices() {
  const healthQuery = useAuditServicesHealth();
  const metricsQuery = useAuditServicesMetrics();
  const statusQuery = useAuditServicesStatus();
  const rateLimitsQuery = useAuditServicesRateLimits();
  const auditLogQuery = useAuditServicesAuditLog();

  const health = healthQuery.data;
  const metrics = metricsQuery.data;
  const status = statusQuery.data;
  const rateLimits = rateLimitsQuery.data;

  const services = health?.services ?? {};
  const enabled = status?.services ?? {};

  const healthCount = Object.values(services).filter((s) => s === 'healthy').length;
  const totalCount = Object.keys(services).length;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight">Audit Services</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Aggregate status for the analytics and ML services that produce trust signals (EMQ
          measurement, offline-conversion ingestion, A/B testing, latency tracking, creative &
          audience scoring, LTV prediction).
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <KPI
          label="Subsystem"
          value={health ? health.status[0].toUpperCase() + health.status.slice(1) : undefined}
          status={
            health
              ? {
                  label: health.status,
                  variant: HEALTH_VARIANT[health.status],
                  pulse: health.status === 'healthy',
                }
              : undefined
          }
          loading={healthQuery.isLoading}
        />
        <KPI
          label="Services healthy"
          value={totalCount > 0 ? `${healthCount} / ${totalCount}` : undefined}
          loading={healthQuery.isLoading}
        />
        <KPI
          label="Active experiments"
          value={metrics ? metrics.experiments.active_count.toString() : undefined}
          loading={metricsQuery.isLoading}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="mb-4 font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Service health
          </h2>
          <ul className="space-y-2">
            {Object.entries(services).map(([key, state]) => {
              const isEnabled = enabled[key];
              return (
                <li
                  key={key}
                  className="flex items-center justify-between gap-3 rounded-xl border border-border bg-muted/40 p-3"
                >
                  <div className="min-w-0 space-y-0.5">
                    <p className="truncate text-sm font-medium">{prettyServiceName(key)}</p>
                    {typeof isEnabled === 'boolean' && (
                      <p className="font-mono text-xs text-muted-foreground">
                        {isEnabled ? 'enabled' : 'disabled'}
                      </p>
                    )}
                  </div>
                  <StatusPill variant={HEALTH_VARIANT[state]} size="sm">
                    {state}
                  </StatusPill>
                </li>
              );
            })}
            {!healthQuery.isLoading && totalCount === 0 && (
              <li className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                Health check returned no services.
              </li>
            )}
          </ul>
        </Card>

        <Card className="p-6">
          <h2 className="mb-4 font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Activity today
          </h2>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {metrics && (
              <>
                <Stat label="EMQ measurements" value={metrics.emq.measurements_today} />
                <Stat
                  label="Offline conv. uploads"
                  value={metrics.offline_conversions.uploads_today}
                />
                <Stat
                  label="Records processed"
                  value={metrics.offline_conversions.records_processed}
                />
                <Stat label="Fatigue alerts" value={metrics.creative_alerts.fatigue_alerts_today} />
                <Stat label="Unacknowledged" value={metrics.creative_alerts.unacknowledged} />
                <Stat label="Budget plans pending" value={metrics.budget_plans.pending_approval} />
                <Stat label="Plans executed" value={metrics.budget_plans.executed_today} />
                <Stat label="Active experiments" value={metrics.experiments.active_count} />
              </>
            )}
          </dl>
          {metrics?.timestamp && (
            <p className="mt-4 font-mono text-[10px] text-muted-foreground">
              Sampled {new Date(metrics.timestamp).toLocaleString()}
            </p>
          )}
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="mb-4 font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Rate limits
          </h2>
          {rateLimitsQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : rateLimits && Object.keys(rateLimits).length > 0 ? (
            <ul className="space-y-2 text-sm">
              {Object.entries(rateLimits).map(([k, v]) => (
                <li
                  key={k}
                  className="flex items-center justify-between border-b border-border/50 pb-2 last:border-b-0"
                >
                  <span className="font-mono text-xs text-muted-foreground">{k}</span>
                  <span className="font-mono tabular-nums">
                    {typeof v === 'number' || typeof v === 'string' ? String(v) : '—'}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No rate-limit data.</p>
          )}
        </Card>

        <Card className="p-6">
          <h2 className="mb-4 font-mono text-sm uppercase tracking-wider text-muted-foreground">
            Audit log
          </h2>
          {auditLogQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : auditLogQuery.data ? (
            <div className="space-y-2 text-sm">
              <p className="text-foreground">{auditLogQuery.data.message}</p>
              {auditLogQuery.data.log_location && (
                <p className="font-mono text-xs text-muted-foreground">
                  Location: {auditLogQuery.data.log_location}
                </p>
              )}
              <p className="text-xs text-muted-foreground italic">{auditLogQuery.data.hint}</p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No audit-log info.</p>
          )}
        </Card>
      </section>

      {health?.timestamp && (
        <p className={cn('pt-2 font-mono text-[10px] text-muted-foreground text-right')}>
          Health checked {new Date(health.timestamp).toLocaleString()}
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-muted/40 p-3">
      <dt className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 text-lg font-semibold tabular-nums">{value.toLocaleString()}</dd>
    </div>
  );
}
