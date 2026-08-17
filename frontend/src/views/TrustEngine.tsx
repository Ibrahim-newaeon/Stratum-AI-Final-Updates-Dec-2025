/**
 * Trust Engine — the diagnostic archetype.
 *
 * There was no Trust Engine screen. /dashboard/trust-engine redirected to
 * /dashboard/trust, which rendered TenantAdminOverview — a generic tenant admin
 * page. The sidebar's flagship destination, for the feature this product is
 * named after, pointed at nothing purpose-built.
 *
 * Everything here comes from GET /trust-layer/trust-gate. Nothing is invented:
 *
 * - `score` and `status` — the composite and its band.
 * - `components` — the real decomposition the API returns (emq, freshness,
 *   variance, anomaly, and cdp when present). NOT the five weighted components
 *   CLAUDE.md documents; no code computes those, and no weights are published,
 *   so none are drawn.
 * - `issues` — the calculator's own reason strings, rendered verbatim so the UI
 *   cannot drift from the logic that produced them.
 * - `thresholds` — the tenant's configured pass/hold values, never hardcoded.
 *
 * A score alone is a claim. A score beside the inputs that produced it, the
 * thresholds it was tested against, and the reason it landed where it did, is a
 * method — which is the argument this screen has to make.
 */
import { useMemo } from 'react'
import { PageHeader } from '@/components/primitives/PageHeader'
import { StatRow, type StatRowItem } from '@/components/primitives/StatRow'
import { StatusPill, type StatusPillVariant } from '@/components/primitives/StatusPill'
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable'
import { useTrustGateStatus } from '@/api/trustLayer'
import { useTenantStore, selectTenantId } from '@/stores/tenantStore'

interface ComponentRow {
  name: string
  score: number
}

/** Band a 0-100 figure against the tenant's own thresholds. */
function bandVariant(score: number, pass: number, hold: number): StatusPillVariant {
  if (score >= pass) return 'healthy'
  if (score >= hold) return 'degraded'
  return 'unhealthy'
}

function statusVariantFor(status: string): StatusPillVariant {
  const s = status?.toLowerCase()
  if (s === 'healthy' || s === 'ok') return 'healthy'
  if (s === 'degraded' || s === 'risk') return 'degraded'
  if (s === 'unhealthy' || s === 'blocked') return 'unhealthy'
  return 'neutral'
}

export function TrustEngine() {
  const tenantId = useTenantStore(selectTenantId) ?? 0
  const { data, isLoading, error } = useTrustGateStatus(tenantId)

  const health = data?.signal_health
  const pass = data?.thresholds?.pass_threshold ?? 70
  const hold = data?.thresholds?.hold_threshold ?? 40

  const components = useMemo((): ComponentRow[] => {
    const raw = health?.components ?? {}
    return Object.entries(raw)
      .filter(([, v]) => typeof v === 'number')
      .map(([name, score]) => ({ name, score: score as number }))
      .sort((a, b) => a.score - b.score) // worst first — that is what needs attention
  }, [health])

  const stats = useMemo((): StatRowItem[] => {
    if (!data?.data_available) return []
    return [
      { label: 'Signal health', value: String(Math.round(health?.score ?? 0)) },
      { label: 'Autopilot', value: data.autopilot_mode ?? '—' },
      { label: 'Pass at', value: String(pass) },
      { label: 'Hold below', value: String(hold) },
    ]
  }, [data, health, pass, hold])

  const columns: DataTableColumn<ComponentRow>[] = [
    {
      id: 'name',
      header: 'Component',
      cell: (c) => <span className="font-medium capitalize text-foreground">{c.name}</span>,
    },
    {
      id: 'score',
      header: 'Score',
      headerClassName: 'text-right',
      cellClassName: 'text-right font-mono tabular-nums',
      cell: (c) => String(Math.round(c.score)),
    },
    {
      id: 'band',
      header: 'Band',
      headerClassName: 'text-right',
      cellClassName: 'text-right',
      cell: (c) => (
        <StatusPill size="sm" variant={bandVariant(c.score, pass, hold)}>
          {c.score >= pass ? 'Pass' : c.score >= hold ? 'Hold' : 'Block'}
        </StatusPill>
      ),
    },
  ]

  const context = error
    ? 'Could not load trust status. Retry, or check the connection.'
    : data && !data.data_available
      ? 'No signal data for this tenant yet — the gate has nothing to evaluate.'
      : (data?.mode_reason ?? 'Evaluating signal health…')

  return (
    <div className="px-8 py-6">
      <PageHeader
        title="Trust Engine"
        context={context}
        actions={
          data?.data_available && health ? (
            <StatusPill variant={statusVariantFor(health.status)}>{health.status}</StatusPill>
          ) : null
        }
      />

      <StatRow items={stats} />

      {data?.data_available && health ? (
        <div className="mt-6 flex flex-col gap-6 lg:flex-row">
          <div className="lg:w-64">
            <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              Composite
            </p>
            <p className="mt-2 font-mono text-[72px] leading-none tabular-nums text-foreground">
              {Math.round(health.score)}
            </p>
            <p className="mt-1 font-mono text-xs text-muted-foreground">/ 100</p>
            {data.as_of_date ? (
              <p className="mt-4 font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                as of {data.as_of_date}
              </p>
            ) : null}
          </div>

          <div className="min-w-0 flex-1">
            <DataTable
              data={components}
              columns={columns}
              rowKey={(c) => c.name}
              ariaLabel="Signal health components"
              emptyMessage="The gate reported no component breakdown."
            />
          </div>
        </div>
      ) : null}

      {/* The calculator's own words. Rendering these rather than re-deriving a
          sentence here is what keeps the screen honest when the logic changes. */}
      {health?.issues?.length ? (
        <section className="mt-8">
          <h2 className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            Why
          </h2>
          <ul className="mt-3 space-y-2">
            {health.issues.map((issue) => (
              <li
                key={issue}
                className="rounded-2xl border border-border bg-card px-4 py-3 text-sm text-foreground"
              >
                {issue}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {data?.data_available && data.restricted_actions?.length ? (
        <section className="mt-8">
          <h2 className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            Currently restricted
          </h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {data.restricted_actions.map((action) => (
              <span
                key={action}
                className="rounded-full border border-border px-3 py-1 font-mono text-xs text-muted-foreground"
              >
                {action}
              </span>
            ))}
          </div>
        </section>
      ) : null}

      {isLoading && !data ? (
        <p className="mt-6 text-sm text-muted-foreground">Loading trust status…</p>
      ) : null}
    </div>
  )
}

export default TrustEngine
