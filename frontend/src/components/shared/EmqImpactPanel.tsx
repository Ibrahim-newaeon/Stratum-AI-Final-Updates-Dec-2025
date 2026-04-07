/**
 * EMQ Impact Panel
 * Displays estimated ROAS impact from data quality issues
 */

import { cn } from '@/lib/utils'
import { ConfidenceBandBadge, getConfidenceBand } from './ConfidenceBandBadge'
import {
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'

interface ImpactBreakdown {
  platform: string
  actualRoas: number
  estimatedRoas: number
  confidence: number
  revenueImpact: number
}

interface EmqImpactPanelProps {
  totalImpact: number
  currency?: string
  emqScore: number
  breakdown?: ImpactBreakdown[]
  showBreakdown?: boolean
  className?: string
}

function formatCurrency(amount: number, currency: string): string {
  const isNegative = amount < 0
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.abs(amount))
  return isNegative ? `-${formatted}` : formatted
}

export function EmqImpactPanel({
  totalImpact,
  currency = 'USD',
  emqScore,
  breakdown = [],
  showBreakdown = true,
  className,
}: EmqImpactPanelProps) {
  const band = getConfidenceBand(emqScore)
  const isPositive = totalImpact >= 0

  const confidenceLabel = band === 'reliable' ? 'high' :
                          band === 'directional' ? 'medium' : 'low'

  return (
    <div className={cn(
      'rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden',
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className={cn(
            'p-2 rounded-lg',
            isPositive ? 'bg-success/10' : 'bg-danger/10'
          )}>
            <CurrencyDollarIcon className={cn(
              'w-5 h-5',
              isPositive ? 'text-success' : 'text-danger'
            )} />
          </div>
          <div>
            <h3 className="font-semibold text-white">Estimated ROAS Impact</h3>
            <p className="text-sm text-text-muted">
              Based on current data quality
            </p>
          </div>
        </div>
      </div>

      {/* Main impact */}
      <div className="p-6">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-baseline gap-2">
              <span className={cn(
                'text-4xl font-bold',
                isPositive ? 'text-success' : 'text-danger'
              )}>
                {formatCurrency(totalImpact, currency)}
              </span>
              {isPositive ? (
                <ArrowTrendingUpIcon className="w-6 h-6 text-success" />
              ) : (
                <ArrowTrendingDownIcon className="w-6 h-6 text-danger" />
              )}
            </div>
            <p className="text-sm text-text-muted mt-1">
              {isPositive ? 'Potential revenue gain' : 'Revenue at risk'}
            </p>
          </div>

          <div className="text-right">
            <div className="flex items-center gap-2 justify-end">
              <span className="text-sm text-text-muted">Confidence:</span>
              <ConfidenceBandBadge score={emqScore} size="sm" />
            </div>
            <p className="text-xs text-text-muted mt-1">
              Estimate has {confidenceLabel} accuracy
            </p>
          </div>
        </div>

        {/* Info callout */}
        <div className={cn(
          'flex items-start gap-3 mt-4 p-3 rounded-xl',
          band === 'reliable' ? 'bg-success/5' :
          band === 'directional' ? 'bg-warning/5' : 'bg-danger/5'
        )}>
          <InformationCircleIcon className={cn(
            'w-5 h-5 flex-shrink-0',
            band === 'reliable' ? 'text-success' :
            band === 'directional' ? 'text-warning' : 'text-danger'
          )} />
          <p className="text-sm text-text-secondary">
            {band === 'reliable'
              ? 'This estimate is based on reliable data and can be used for decision-making.'
              : band === 'directional'
              ? 'This estimate shows the general trend but may have a margin of error.'
              : 'This estimate has low confidence. Fix data issues for more accurate projections.'}
          </p>
        </div>
      </div>

      {/* Breakdown by platform */}
      {showBreakdown && breakdown.length > 0 && (
        <div className="border-t border-white/10">
          <div className="p-4">
            <h4 className="text-sm font-medium text-white mb-3">Impact by Platform</h4>
            <div className="space-y-3">
              {breakdown.map((item) => (
                <div key={item.platform} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-text-secondary">{item.platform}</span>
                    <span className="text-xs text-text-muted">
                      ROAS: {item.actualRoas.toFixed(2)}x → {item.estimatedRoas.toFixed(2)}x
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      'text-sm font-medium',
                      item.revenueImpact >= 0 ? 'text-success' : 'text-danger'
                    )}>
                      {formatCurrency(item.revenueImpact, currency)}
                    </span>
                    <ConfidenceBandBadge score={item.confidence} size="sm" showLabel={false} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EmqImpactPanel
