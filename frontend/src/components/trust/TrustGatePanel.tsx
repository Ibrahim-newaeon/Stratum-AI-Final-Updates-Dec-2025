/**
 * Trust Gate Panel — the real engine's posture, live on the dashboard.
 *
 * Surfaces GET /trust/tenant/{id}/trust-gate (autopilot mode, engine-weighted
 * signal health, allowed vs restricted action types) and drives
 * POST .../trust-gate/evaluate for a "would this run right now?" preview.
 * The evaluate call is read-only on the backend — nothing executes.
 */

import { useMemo, useState, type FormEvent } from 'react'
import { Card } from '@/components/primitives/Card'
import { StatusPill, type StatusPillVariant } from '@/components/primitives/StatusPill'
import {
  useEvaluateTrustGate,
  useTrustGateStatus,
  type AutopilotGateMode,
  type GateDecision,
} from '@/api/trustLayer'
import { cn } from '@/lib/utils'

interface TrustGatePanelProps {
  tenantId: number
  className?: string
}

const MODE_LABEL: Record<AutopilotGateMode, string> = {
  normal: 'Normal',
  limited: 'Limited',
  cuts_only: 'Cuts only',
  frozen: 'Frozen',
}

const MODE_VARIANT: Record<AutopilotGateMode, StatusPillVariant> = {
  normal: 'healthy',
  limited: 'degraded',
  cuts_only: 'degraded',
  frozen: 'unhealthy',
}

const DECISION_LABEL: Record<GateDecision, string> = {
  pass: 'PASS',
  hold: 'HOLD',
  block: 'BLOCK',
}

const DECISION_VARIANT: Record<GateDecision, StatusPillVariant> = {
  pass: 'healthy',
  hold: 'degraded',
  block: 'unhealthy',
}

const PLATFORMS = ['meta', 'google', 'tiktok', 'snapchat'] as const

const fieldClass =
  'w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground ' +
  'focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/50'

function ActionChips({ actions, restricted }: { actions: string[]; restricted?: boolean }) {
  if (actions.length === 0) {
    return <p className="text-sm text-muted-foreground">None</p>
  }
  return (
    <ul className="flex flex-wrap gap-1.5">
      {actions.map((action) => (
        <li
          key={action}
          className={cn(
            'rounded-full border px-2.5 py-0.5 font-mono text-[10.5px]',
            restricted
              ? 'border-danger/30 text-danger/90 line-through decoration-danger/50'
              : 'border-border text-muted-foreground'
          )}
        >
          {action}
        </li>
      ))}
    </ul>
  )
}

export function TrustGatePanel({ tenantId, className }: TrustGatePanelProps) {
  const { data, isLoading, isError, refetch } = useTrustGateStatus(tenantId)
  const evaluate = useEvaluateTrustGate(tenantId)

  const [actionType, setActionType] = useState('')
  const [platform, setPlatform] = useState<string>('meta')
  const [entityId, setEntityId] = useState('preview-entity')

  // The engine's full action vocabulary — restricted ones stay selectable
  // so users can see WHY something would be held or blocked.
  const actionOptions = useMemo(() => {
    if (!data) return []
    return [...new Set([...data.allowed_actions, ...data.restricted_actions])].sort()
  }, [data])

  const selectedAction = actionType || actionOptions[0] || ''

  // Signal-health components, worst-first. Numeric values only: the map is
  // typed Record<string, number> but comes straight off the wire, so a
  // non-numeric entry should be skipped rather than rendered as NaN.
  const componentRows = useMemo(() => {
    const raw = data?.signal_health?.components ?? {}
    return Object.entries(raw)
      .filter(([, value]) => typeof value === 'number' && Number.isFinite(value))
      .map(([name, score]) => ({ name, score: score as number }))
      .sort((a, b) => a.score - b.score)
  }, [data])

  const handleEvaluate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!selectedAction || !entityId.trim()) return
    evaluate.mutate({
      action_type: selectedAction,
      entity_type: 'campaign',
      entity_id: entityId.trim(),
      platform,
    })
  }

  if (isLoading) {
    return (
      <Card className={className}>
        <Card.Header>
          <Card.Title>Trust Gate</Card.Title>
        </Card.Header>
        <Card.Body>
          <div className="animate-pulse space-y-3" aria-label="Loading trust gate status">
            <div className="h-8 w-32 rounded-lg bg-muted" />
            <div className="h-4 w-3/4 rounded bg-muted" />
            <div className="h-4 w-1/2 rounded bg-muted" />
          </div>
        </Card.Body>
      </Card>
    )
  }

  if (isError || !data) {
    return (
      <Card className={className}>
        <Card.Header>
          <Card.Title>Trust Gate</Card.Title>
        </Card.Header>
        <Card.Body>
          <p className="text-sm text-muted-foreground">Could not load the trust gate status.</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-3 rounded-full border border-border px-4 py-1.5 text-sm text-foreground hover:border-primary/40"
          >
            Retry
          </button>
        </Card.Body>
      </Card>
    )
  }

  const result = evaluate.data

  return (
    <Card className={className}>
      <Card.Header className="flex-row items-center justify-between">
        <div>
          <Card.Title>Trust Gate</Card.Title>
          <Card.Description>
            {data.data_available && data.as_of_date
              ? `Signal health as of ${data.as_of_date}`
              : 'No signal health rollup yet — automation is blocked by default'}
          </Card.Description>
        </div>
        <StatusPill variant={MODE_VARIANT[data.autopilot_mode]} pulse={data.autopilot_mode === 'normal'}>
          Autopilot: {MODE_LABEL[data.autopilot_mode]}
        </StatusPill>
      </Card.Header>

      <Card.Body className="space-y-5">
        {/* Engine-weighted health + why the mode is what it is */}
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-3xl font-semibold text-foreground">
            {Math.round(data.signal_health.score)}
          </span>
          <span className="text-sm text-muted-foreground">
            signal health · pass ≥ {data.thresholds.pass_threshold} · hold ≥{' '}
            {data.thresholds.hold_threshold}
          </span>
        </div>
        <p className="text-sm text-muted-foreground">{data.mode_reason}</p>
        {data.signal_health.issues.length > 0 && (
          <ul className="space-y-1">
            {data.signal_health.issues.map((issue) => (
              <li key={issue} className="text-sm text-warning">
                {issue}
              </li>
            ))}
          </ul>
        )}

        {/* The score decomposed into the inputs that produced it.
         *
         * signal_health.components has been in the API response all along and
         * nothing rendered it, so the composite read as a number with no
         * derivation. These are the real component names — emq, freshness,
         * variance, anomaly, and cdp when present — NOT the five weighted
         * components CLAUDE.md documents, which no code computes and which
         * carry no published weights.
         *
         * Sorted worst-first: the failing input is the one that needs
         * attention and should not have to be hunted for. */}
        {componentRows.length > 0 && (
          <div>
            <h4 className="mb-2 font-mono text-[10.5px] uppercase tracking-wider text-muted-foreground">
              Contributing signals
            </h4>
            <ul className="space-y-1">
              {componentRows.map(({ name, score }) => (
                <li key={name} className="flex items-baseline justify-between gap-3 text-sm">
                  <span data-slot="component-name" className="capitalize text-foreground">
                    {name}
                  </span>
                  <span className="flex items-baseline gap-2">
                    <span className="font-mono tabular-nums text-foreground">
                      {Math.round(score)}
                    </span>
                    <StatusPill
                      size="sm"
                      variant={
                        score >= data.thresholds.pass_threshold
                          ? 'healthy'
                          : score >= data.thresholds.hold_threshold
                            ? 'degraded'
                            : 'unhealthy'
                      }
                    >
                      {score >= data.thresholds.pass_threshold
                        ? 'Pass'
                        : score >= data.thresholds.hold_threshold
                          ? 'Hold'
                          : 'Block'}
                    </StatusPill>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <h4 className="mb-2 font-mono text-[10.5px] uppercase tracking-wider text-muted-foreground">
              Allowed now
            </h4>
            <ActionChips actions={data.allowed_actions} />
          </div>
          <div>
            <h4 className="mb-2 font-mono text-[10.5px] uppercase tracking-wider text-muted-foreground">
              Restricted
            </h4>
            <ActionChips actions={data.restricted_actions} restricted />
          </div>
        </div>

        {/* "Would this run right now?" preview */}
        <form onSubmit={handleEvaluate} className="space-y-3 border-t border-border pt-4">
          <h4 className="font-mono text-[10.5px] uppercase tracking-wider text-muted-foreground">
            Would this run right now?
          </h4>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <label className="block text-sm">
              <span className="mb-1 block text-muted-foreground">Action</span>
              <select
                value={selectedAction}
                onChange={(e) => setActionType(e.target.value)}
                className={fieldClass}
                disabled={actionOptions.length === 0}
              >
                {actionOptions.map((action) => (
                  <option key={action} value={action}>
                    {action}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-muted-foreground">Platform</span>
              <select
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
                className={fieldClass}
              >
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-muted-foreground">Entity ID</span>
              <input
                type="text"
                value={entityId}
                onChange={(e) => setEntityId(e.target.value)}
                className={fieldClass}
                placeholder="campaign id"
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={evaluate.isPending || !selectedAction || !entityId.trim()}
            className={cn(
              'rounded-full bg-primary px-5 py-2 text-sm font-medium text-primary-foreground',
              'hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50'
            )}
          >
            {evaluate.isPending ? 'Evaluating…' : 'Evaluate'}
          </button>

          <div aria-live="polite">
            {evaluate.isError && (
              <p className="text-sm text-danger">
                Evaluation failed —{' '}
                {evaluate.error instanceof Error ? evaluate.error.message : 'try again'}
              </p>
            )}
            {result && !evaluate.isPending && (
              <div className="space-y-2 rounded-xl border border-border bg-muted/40 p-4">
                <div className="flex items-center gap-3">
                  <StatusPill variant={DECISION_VARIANT[result.decision]}>
                    {DECISION_LABEL[result.decision]}
                  </StatusPill>
                  <span className="font-mono text-[10.5px] text-muted-foreground">
                    {result.action.type} · {result.action.entity} · {result.action.platform}
                  </span>
                </div>
                <p className="text-sm text-foreground">{result.reason}</p>
                {result.recommendations.length > 0 && (
                  <ul className="list-disc space-y-1 pl-5">
                    {result.recommendations.map((rec) => (
                      <li key={rec} className="text-sm text-muted-foreground">
                        {rec}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </form>
      </Card.Body>
    </Card>
  )
}

export default TrustGatePanel
