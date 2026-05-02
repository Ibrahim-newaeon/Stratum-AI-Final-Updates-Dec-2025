/**
 * Launch Readiness (Super Admin Go-Live Wizard)
 *
 * Sequential 12-phase launch gate for multi-tenant production. Phase N+1
 * stays locked until phase N is 100% complete. Every check and uncheck
 * appends to an audit trail. No skip.
 */

import { useMemo, useState } from 'react'
import { cn } from '@/lib/utils'
import {
  CheckCircleIcon,
  LockClosedIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ClockIcon,
  RocketLaunchIcon,
  ExclamationTriangleIcon,
  BoltIcon,
} from '@heroicons/react/24/outline'
import { CheckCircleIcon as CheckCircleSolid } from '@heroicons/react/24/solid'
import {
  useLaunchReadinessState,
  useToggleLaunchReadinessItem,
  useLaunchReadinessEvents,
  type LaunchReadinessItem,
  type LaunchReadinessPhase,
} from '@/api/launchReadiness'

type PhaseStatus = 'complete' | 'active' | 'locked'

function phaseStatus(phase: LaunchReadinessPhase): PhaseStatus {
  if (phase.is_complete) return 'complete'
  if (phase.is_active) return 'active'
  return 'locked'
}

function formatRelative(isoDate: string | null | undefined): string {
  if (!isoDate) return ''
  const then = new Date(isoDate).getTime()
  const now = Date.now()
  const diff = Math.max(0, now - then)
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return new Date(isoDate).toLocaleDateString()
}

export default function LaunchReadiness() {
  const { data: state, isLoading, error } = useLaunchReadinessState()
  const [expandedPhases, setExpandedPhases] = useState<Set<number>>(new Set())

  // Once the state is known, auto-expand the active phase on first render.
  const activePhaseNumber = state?.phases.find((p) => p.is_active)?.number
  const effectiveExpanded = useMemo(() => {
    if (expandedPhases.size > 0) return expandedPhases
    if (activePhaseNumber) return new Set([activePhaseNumber])
    return new Set<number>()
  }, [expandedPhases, activePhaseNumber])

  const togglePhase = (n: number) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev.size === 0 && activePhaseNumber ? [activePhaseNumber] : prev)
      if (next.has(n)) next.delete(n)
      else next.add(n)
      return next
    })
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-24 rounded-2xl bg-surface-secondary border border-foreground/10 animate-pulse" />
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-20 rounded-2xl bg-surface-secondary border border-foreground/10 animate-pulse"
            />
          ))}
        </div>
      </div>
    )
  }

  if (error || !state) {
    return (
      <div className="rounded-2xl bg-danger/10 border border-danger/20 p-6">
        <div className="flex items-center gap-3 text-danger">
          <ExclamationTriangleIcon className="w-5 h-5" />
          <span className="font-medium">Failed to load Launch Readiness state.</span>
        </div>
      </div>
    )
  }

  const overallPct =
    state.overall_total === 0
      ? 0
      : Math.round((state.overall_completed / state.overall_total) * 100)

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <RocketLaunchIcon className="w-6 h-6 text-stratum-400" />
          <h1 className="text-2xl font-bold text-white tracking-tight">Launch Readiness</h1>
        </div>
        <p className="text-muted-foreground max-w-2xl">
          Sequential go-live gate. Each phase must be 100% complete before the next
          unlocks. No skipping. Every check is recorded in the audit trail.
        </p>
      </header>

      {/* Overall progress card */}
      <section className="rounded-2xl bg-surface-secondary border border-foreground/10 p-6">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div className="space-y-1">
            <p className="text-xs uppercase tracking-widest text-muted-foreground">
              Overall progress
            </p>
            <p className="text-3xl font-bold text-white">
              {state.overall_completed}
              <span className="text-muted-foreground font-normal text-xl">
                {' / '}
                {state.overall_total}
              </span>
              <span className="ml-3 text-base text-muted-foreground font-normal">
                ({overallPct}%)
              </span>
            </p>
            <p className="text-sm text-muted-foreground">
              {state.is_launched ? (
                <span className="inline-flex items-center gap-2 text-success font-medium">
                  <CheckCircleSolid className="w-4 h-4" />
                  All phases complete — cleared to launch.
                </span>
              ) : (
                <>
                  Currently in{' '}
                  <span className="text-white font-medium">
                    Phase {state.current_phase_number} of {state.phases.length}
                  </span>
                </>
              )}
            </p>
          </div>
          <div className="flex-1 min-w-[240px] max-w-xl">
            <div className="h-2 rounded-full bg-foreground/5 overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all duration-500',
                  state.is_launched
                    ? 'bg-gradient-to-r from-success to-success/70'
                    : 'bg-gradient-to-r from-stratum-500 to-stratum-400'
                )}
                style={{ width: `${overallPct}%` }}
              />
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {state.phases.map((phase) => {
                const st = phaseStatus(phase)
                return (
                  <button
                    key={phase.number}
                    onClick={() => togglePhase(phase.number)}
                    className={cn(
                      'w-8 h-8 rounded-lg text-xs font-semibold flex items-center justify-center transition-colors',
                      st === 'complete' &&
                        'bg-success/20 text-success border border-success/30',
                      st === 'active' &&
                        'bg-stratum-500/20 text-stratum-300 border border-stratum-400/40 ring-2 ring-stratum-400/30',
                      st === 'locked' &&
                        'bg-foreground/5 text-muted-foreground border border-foreground/10'
                    )}
                    title={`Phase ${phase.number} — ${phase.title} (${st})`}
                  >
                    {phase.number}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Phase list */}
      <section className="space-y-4">
        {state.phases.map((phase) => (
          <PhaseCard
            key={phase.number}
            phase={phase}
            expanded={effectiveExpanded.has(phase.number)}
            onToggleExpand={() => togglePhase(phase.number)}
          />
        ))}
      </section>

      {/* Audit trail */}
      <AuditTrail />
    </div>
  )
}

// -----------------------------------------------------------------------------
// Phase card
// -----------------------------------------------------------------------------
interface PhaseCardProps {
  phase: LaunchReadinessPhase
  expanded: boolean
  onToggleExpand: () => void
}

function PhaseCard({ phase, expanded, onToggleExpand }: PhaseCardProps) {
  const status = phaseStatus(phase)
  const pct =
    phase.total_count === 0
      ? 0
      : Math.round((phase.completed_count / phase.total_count) * 100)

  return (
    <article
      className={cn(
        'rounded-2xl border transition-colors overflow-hidden',
        status === 'complete' && 'bg-surface-secondary border-success/20',
        status === 'active' &&
          'bg-surface-secondary border-stratum-400/40 shadow-[0_0_0_1px_rgba(168,85,247,0.15)]',
        status === 'locked' && 'bg-surface-secondary/60 border-foreground/5'
      )}
    >
      <button
        type="button"
        onClick={onToggleExpand}
        className="w-full p-5 flex items-center gap-4 text-left"
        aria-expanded={expanded}
      >
        {/* Status badge */}
        <div
          className={cn(
            'w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg shrink-0',
            status === 'complete' && 'bg-success/15 text-success border border-success/30',
            status === 'active' && 'bg-stratum-500/20 text-stratum-300 border border-stratum-400/40',
            status === 'locked' && 'bg-foreground/5 text-muted-foreground border border-foreground/10'
          )}
        >
          {status === 'complete' ? (
            <CheckCircleSolid className="w-6 h-6" />
          ) : status === 'locked' ? (
            <LockClosedIcon className="w-5 h-5" />
          ) : (
            phase.number
          )}
        </div>

        {/* Title + description */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h2
              className={cn(
                'text-lg font-semibold tracking-tight',
                status === 'locked' ? 'text-muted-foreground' : 'text-white'
              )}
            >
              Phase {phase.number} — {phase.title}
            </h2>
            <StatusPill status={status} />
          </div>
          {phase.description && (
            <p className="text-sm text-muted-foreground mt-1 line-clamp-1">
              {phase.description}
            </p>
          )}
        </div>

        {/* Progress */}
        <div className="hidden md:flex flex-col items-end gap-2 min-w-[160px]">
          <div className="text-sm font-medium">
            <span className={status === 'locked' ? 'text-muted-foreground' : 'text-white'}>
              {phase.completed_count}
            </span>
            <span className="text-muted-foreground">{' / '}{phase.total_count}</span>
          </div>
          <div className="w-40 h-1.5 rounded-full bg-foreground/5 overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                status === 'complete' && 'bg-success',
                status === 'active' && 'bg-stratum-400',
                status === 'locked' && 'bg-foreground/20'
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Chevron */}
        <div className="shrink-0 text-muted-foreground">
          {expanded ? (
            <ChevronDownIcon className="w-5 h-5" />
          ) : (
            <ChevronRightIcon className="w-5 h-5" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-foreground/5 bg-surface-primary/30 px-5 py-4 space-y-2">
          {status === 'locked' && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-foreground/5 border border-foreground/10 mb-2">
              <LockClosedIcon className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
              <p className="text-sm text-muted-foreground">
                This phase is locked. Complete the preceding phase first — no skipping.
              </p>
            </div>
          )}
          {phase.items.map((item) => (
            <ItemRow
              key={item.key}
              item={item}
              disabled={status === 'locked'}
              phaseIsComplete={status === 'complete'}
            />
          ))}
        </div>
      )}
    </article>
  )
}

function StatusPill({ status }: { status: PhaseStatus }) {
  if (status === 'complete') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-success/15 text-success border border-success/30">
        <CheckCircleIcon className="w-3 h-3" />
        Complete
      </span>
    )
  }
  if (status === 'active') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-stratum-500/20 text-stratum-300 border border-stratum-400/40">
        <BoltIcon className="w-3 h-3" />
        In progress
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-foreground/5 text-muted-foreground border border-foreground/10">
      <LockClosedIcon className="w-3 h-3" />
      Locked
    </span>
  )
}

// -----------------------------------------------------------------------------
// Item row
// -----------------------------------------------------------------------------
interface ItemRowProps {
  item: LaunchReadinessItem
  disabled: boolean
  phaseIsComplete: boolean
}

function ItemRow({ item, disabled, phaseIsComplete }: ItemRowProps) {
  const toggle = useToggleLaunchReadinessItem()

  const handleClick = () => {
    if (disabled) return
    // If the phase is complete and the user is unchecking, warn first —
    // the backend will reopen the phase and relock all downstream phases.
    if (phaseIsComplete && item.is_checked) {
      const ok = window.confirm(
        'Unchecking this item will reopen this phase and relock every phase after it. Continue?'
      )
      if (!ok) return
    }
    toggle.mutate({ itemKey: item.key, checked: !item.is_checked })
  }

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-3 rounded-lg border',
        item.is_checked
          ? 'bg-success/5 border-success/15'
          : 'bg-foreground/[0.02] border-foreground/5',
        disabled && 'opacity-60'
      )}
    >
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || toggle.isPending}
        aria-checked={item.is_checked}
        role="checkbox"
        className={cn(
          'mt-0.5 w-5 h-5 rounded-md flex items-center justify-center shrink-0 transition-all',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-stratum-400',
          item.is_checked
            ? 'bg-success border border-success text-white'
            : 'bg-transparent border border-foreground/20 hover:border-foreground/40',
          (disabled || toggle.isPending) && 'cursor-not-allowed'
        )}
      >
        {item.is_checked && (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M5 13l4 4L19 7"
            />
          </svg>
        )}
      </button>

      <div className="flex-1 min-w-0">
        <p
          className={cn(
            'text-sm',
            item.is_checked ? 'text-white' : 'text-foreground/90',
            disabled && 'text-muted-foreground'
          )}
        >
          {item.title}
        </p>
        {item.description && (
          <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
        )}
        {item.is_checked && (item.checked_by_user_name || item.checked_at) && (
          <p className="text-xs text-muted-foreground mt-1.5 flex items-center gap-1.5">
            <CheckCircleIcon className="w-3 h-3 text-success" />
            {item.checked_by_user_name && <span>{item.checked_by_user_name}</span>}
            {item.checked_by_user_name && item.checked_at && <span>·</span>}
            {item.checked_at && <span>{formatRelative(item.checked_at)}</span>}
          </p>
        )}
      </div>
    </div>
  )
}

// -----------------------------------------------------------------------------
// Audit trail
// -----------------------------------------------------------------------------
function AuditTrail() {
  const { data: events, isLoading } = useLaunchReadinessEvents(undefined, 50)

  return (
    <section className="rounded-2xl bg-surface-secondary border border-foreground/10 p-6">
      <div className="flex items-center gap-2 mb-4">
        <ClockIcon className="w-5 h-5 text-muted-foreground" />
        <h2 className="text-lg font-semibold text-white">Activity</h2>
      </div>
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-8 rounded bg-foreground/5 animate-pulse" />
          ))}
        </div>
      ) : !events || events.length === 0 ? (
        <p className="text-sm text-muted-foreground">No activity yet.</p>
      ) : (
        <ol className="space-y-2">
          {events.map((event) => (
            <li
              key={event.id}
              className="flex items-start gap-3 text-sm border-l-2 border-foreground/10 pl-3 py-1"
            >
              <ActionBadge action={event.action} />
              <div className="flex-1 min-w-0">
                <p className="text-foreground/90">
                  <span className="text-muted-foreground">Phase {event.phase_number}</span>
                  {event.item_key && (
                    <>
                      <span className="text-muted-foreground">{' · '}</span>
                      <span className="font-mono text-xs">{event.item_key}</span>
                    </>
                  )}
                </p>
                <p className="text-xs text-muted-foreground">
                  {event.user_name ?? 'system'} · {formatRelative(event.created_at)}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function ActionBadge({ action }: { action: string }) {
  const label = action.replace(/_/g, ' ')
  const styles =
    action === 'checked'
      ? 'bg-success/15 text-success border-success/30'
      : action === 'unchecked'
        ? 'bg-warning/15 text-warning border-warning/30'
        : action === 'phase_completed'
          ? 'bg-stratum-500/20 text-stratum-300 border-stratum-400/40'
          : action === 'phase_reopened'
            ? 'bg-danger/15 text-danger border-danger/30'
            : 'bg-foreground/5 text-muted-foreground border-foreground/10'
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border shrink-0',
        styles
      )}
    >
      {label}
    </span>
  )
}
