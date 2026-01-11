/**
 * TrustGateStatus - Visual trust gate indicator
 *
 * Shows the current trust gate status based on signal health:
 * - PASS (green): Signal health >= 70, autopilot enabled
 * - HOLD (yellow): Signal health 40-69, alerts only
 * - BLOCK (red): Signal health < 40, manual required
 */

import { Loader2, ShieldCheck, ShieldAlert, ShieldOff, Zap, AlertTriangle, Hand } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SignalHealthSummary } from '@/api/dashboard'

// Trust engine thresholds from CLAUDE.md
const HEALTHY_THRESHOLD = 70
const DEGRADED_THRESHOLD = 40

type GateStatus = 'PASS' | 'HOLD' | 'BLOCK'

interface TrustGateStatusProps {
  signalHealth?: SignalHealthSummary
  loading?: boolean
}

export function TrustGateStatus({ signalHealth, loading = false }: TrustGateStatusProps) {
  if (loading) {
    return (
      <div className="bg-card border rounded-lg p-6 h-full flex items-center justify-center min-h-[200px]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Determine gate status from signal health score
  const getGateStatus = (): GateStatus => {
    if (!signalHealth) return 'BLOCK'
    if (signalHealth.overall_score >= HEALTHY_THRESHOLD) return 'PASS'
    if (signalHealth.overall_score >= DEGRADED_THRESHOLD) return 'HOLD'
    return 'BLOCK'
  }

  const gateStatus = getGateStatus()

  const gateConfigs = {
    PASS: {
      icon: ShieldCheck,
      color: 'text-green-500',
      bgColor: 'bg-green-500',
      bgLight: 'bg-green-500/10',
      borderColor: 'border-green-500/30',
      ringColor: 'ring-green-500/20',
      label: 'PASS',
      description: 'Autopilot Enabled',
      detail: 'Signal health is strong. Automations will execute automatically.',
      actionIcon: Zap,
      actionLabel: 'Auto-Execute',
    },
    HOLD: {
      icon: ShieldAlert,
      color: 'text-yellow-500',
      bgColor: 'bg-yellow-500',
      bgLight: 'bg-yellow-500/10',
      borderColor: 'border-yellow-500/30',
      ringColor: 'ring-yellow-500/20',
      label: 'HOLD',
      description: 'Alert Mode',
      detail: 'Signal health is degraded. Automation on hold, alerts only.',
      actionIcon: AlertTriangle,
      actionLabel: 'Alert Only',
    },
    BLOCK: {
      icon: ShieldOff,
      color: 'text-red-500',
      bgColor: 'bg-red-500',
      bgLight: 'bg-red-500/10',
      borderColor: 'border-red-500/30',
      ringColor: 'ring-red-500/20',
      label: 'BLOCK',
      description: 'Manual Required',
      detail: 'Signal health is critical. All automations blocked, manual action required.',
      actionIcon: Hand,
      actionLabel: 'Manual Only',
    },
  }

  const config = gateConfigs[gateStatus]
  const GateIcon = config.icon
  const ActionIcon = config.actionIcon

  return (
    <div className={cn('bg-card border rounded-lg p-6 h-full', config.borderColor)}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Trust Gate</h3>
        <div
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-bold',
            config.bgLight,
            config.color
          )}
        >
          <GateIcon className="w-4 h-4" />
          {config.label}
        </div>
      </div>

      {/* Visual Gate Indicator */}
      <div className="flex items-center justify-center py-6">
        <div className="relative">
          {/* Outer ring */}
          <div
            className={cn(
              'w-32 h-32 rounded-full ring-4 flex items-center justify-center',
              config.ringColor,
              config.bgLight
            )}
          >
            {/* Inner circle with icon */}
            <div
              className={cn(
                'w-20 h-20 rounded-full flex items-center justify-center',
                config.bgLight
              )}
            >
              <GateIcon className={cn('w-10 h-10', config.color)} />
            </div>
          </div>

          {/* Pulsing effect for PASS status */}
          {gateStatus === 'PASS' && (
            <div
              className={cn(
                'absolute inset-0 w-32 h-32 rounded-full animate-ping opacity-20',
                config.bgColor
              )}
            />
          )}
        </div>
      </div>

      {/* Status Description */}
      <div className="text-center mb-6">
        <div className={cn('text-lg font-semibold mb-1', config.color)}>
          {config.description}
        </div>
        <p className="text-sm text-muted-foreground">{config.detail}</p>
      </div>

      {/* Threshold Indicator */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Signal Score</span>
          <span className={cn('font-bold', config.color)}>
            {signalHealth?.overall_score ?? 0}/100
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div className="h-full flex">
            <div
              className="bg-red-500 transition-all duration-500"
              style={{ width: `${Math.min(DEGRADED_THRESHOLD, signalHealth?.overall_score ?? 0)}%` }}
            />
            <div
              className="bg-yellow-500 transition-all duration-500"
              style={{
                width: `${Math.max(0, Math.min(HEALTHY_THRESHOLD - DEGRADED_THRESHOLD, (signalHealth?.overall_score ?? 0) - DEGRADED_THRESHOLD))}%`,
              }}
            />
            <div
              className="bg-green-500 transition-all duration-500"
              style={{
                width: `${Math.max(0, (signalHealth?.overall_score ?? 0) - HEALTHY_THRESHOLD)}%`,
              }}
            />
          </div>
        </div>

        {/* Threshold markers */}
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>0</span>
          <span className="text-red-500">Block (&lt;{DEGRADED_THRESHOLD})</span>
          <span className="text-yellow-500">Hold ({DEGRADED_THRESHOLD}-{HEALTHY_THRESHOLD - 1})</span>
          <span className="text-green-500">Pass (&gt;={HEALTHY_THRESHOLD})</span>
        </div>
      </div>

      {/* Action Mode */}
      <div
        className={cn(
          'mt-6 pt-4 border-t flex items-center justify-between',
          config.borderColor
        )}
      >
        <div className="flex items-center gap-2">
          <ActionIcon className={cn('w-4 h-4', config.color)} />
          <span className="text-sm font-medium">{config.actionLabel}</span>
        </div>
        {signalHealth?.autopilot_enabled && gateStatus === 'PASS' && (
          <span className="text-xs px-2 py-1 bg-green-500/10 text-green-500 rounded-full font-medium">
            Active
          </span>
        )}
      </div>
    </div>
  )
}
