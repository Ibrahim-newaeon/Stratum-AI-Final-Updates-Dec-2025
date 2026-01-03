/**
 * Trust Status Header
 * Universal header component showing EMQ + band + mode + budget-at-risk
 * Used on ALL dashboard pages
 */

import { cn } from '@/lib/utils'
import { ConfidenceBandBadge, getConfidenceBand } from './ConfidenceBandBadge'
import { AutopilotModeBanner, type AutopilotMode } from './AutopilotModeBanner'
import { BudgetAtRiskChip } from './BudgetAtRiskChip'
import { VolatilityBadge } from './VolatilityBadge'
import {
  ShieldCheckIcon,
  ShieldExclamationIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'

interface TrustStatusHeaderProps {
  emqScore: number
  autopilotMode: AutopilotMode
  budgetAtRisk: number
  svi?: number // Signal Volatility Index
  currency?: string
  onViewDetails?: () => void
  compact?: boolean
  className?: string
}

function getEmqStatus(score: number) {
  const band = getConfidenceBand(score)
  if (band === 'reliable') {
    return {
      icon: ShieldCheckIcon,
      color: 'text-success',
      bgColor: 'bg-success/10',
      message: 'Data is trustworthy for decision-making',
    }
  }
  if (band === 'directional') {
    return {
      icon: ShieldExclamationIcon,
      color: 'text-warning',
      bgColor: 'bg-warning/10',
      message: 'Data shows trends but may have gaps',
    }
  }
  return {
    icon: ShieldExclamationIcon,
    color: 'text-danger',
    bgColor: 'bg-danger/10',
    message: 'Data quality too low for reliable decisions',
  }
}

export function TrustStatusHeader({
  emqScore,
  autopilotMode,
  budgetAtRisk,
  svi,
  currency = 'USD',
  onViewDetails,
  compact = false,
  className,
}: TrustStatusHeaderProps) {
  const status = getEmqStatus(emqScore)
  const StatusIcon = status.icon

  if (compact) {
    return (
      <div className={cn(
        'flex items-center gap-4 p-3 rounded-xl bg-surface-secondary border border-white/10',
        className
      )}>
        <div className="flex items-center gap-2">
          <StatusIcon className={cn('w-5 h-5', status.color)} />
          <span className="text-lg font-bold text-white">{emqScore}</span>
          <ConfidenceBandBadge score={emqScore} size="sm" />
        </div>
        <div className="h-4 w-px bg-white/10" />
        <AutopilotModeBanner mode={autopilotMode} compact />
        {budgetAtRisk > 0 && (
          <>
            <div className="h-4 w-px bg-white/10" />
            <BudgetAtRiskChip amount={budgetAtRisk} currency={currency} size="sm" />
          </>
        )}
        {svi !== undefined && (
          <>
            <div className="h-4 w-px bg-white/10" />
            <VolatilityBadge svi={svi} size="sm" />
          </>
        )}
      </div>
    )
  }

  return (
    <div className={cn(
      'rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden',
      className
    )}>
      {/* Main header */}
      <div className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div className={cn('p-3 rounded-xl', status.bgColor)}>
              <StatusIcon className={cn('w-6 h-6', status.color)} />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold text-white">EMQ {emqScore}</h2>
                <ConfidenceBandBadge score={emqScore} />
              </div>
              <p className="text-sm text-text-secondary mt-1">{status.message}</p>
            </div>
          </div>

          {onViewDetails && (
            <button
              onClick={onViewDetails}
              className="flex items-center gap-1 text-sm text-stratum-400 hover:text-stratum-300 transition-colors"
            >
              View details
              <ChevronRightIcon className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-6 mt-6 pt-6 border-t border-white/10">
          <div className="flex-1">
            <AutopilotModeBanner mode={autopilotMode} showDescription={false} compact />
          </div>
          {budgetAtRisk > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-text-muted">Budget at Risk:</span>
              <BudgetAtRiskChip amount={budgetAtRisk} currency={currency} />
            </div>
          )}
          {svi !== undefined && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-text-muted">Volatility:</span>
              <VolatilityBadge svi={svi} />
            </div>
          )}
        </div>
      </div>

      {/* "Can I trust today?" quick answer */}
      <div className={cn(
        'px-6 py-4 border-t',
        status.bgColor,
        'border-white/10'
      )}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-medium text-white">Can I trust today?</span>
            <span className={cn('font-semibold', status.color)}>
              {emqScore >= 90 ? 'Yes, data is reliable' :
               emqScore >= 60 ? 'Partially, use with caution' :
               'No, fix data issues first'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default TrustStatusHeader
