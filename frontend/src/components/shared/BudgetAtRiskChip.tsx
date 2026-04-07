/**
 * Budget At Risk Chip
 * Displays the dollar amount at risk due to data quality issues
 */

import { cn } from '@/lib/utils'
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline'

interface BudgetAtRiskChipProps {
  amount: number
  currency?: string
  threshold?: number // Amount above which to show warning
  showIcon?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-3 py-1',
  lg: 'text-base px-4 py-1.5',
}

const iconSizes = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
}

function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

export function BudgetAtRiskChip({
  amount,
  currency = 'USD',
  threshold = 1000,
  showIcon = true,
  size = 'md',
  className,
}: BudgetAtRiskChipProps) {
  const isHighRisk = amount >= threshold
  const isCritical = amount >= threshold * 5

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        isCritical ? 'bg-danger/10 text-danger' :
        isHighRisk ? 'bg-warning/10 text-warning' :
        'bg-surface-tertiary text-text-secondary',
        sizeClasses[size],
        className
      )}
      title={`Budget at risk: ${formatCurrency(amount, currency)}`}
    >
      {showIcon && (isHighRisk || isCritical) && (
        <ExclamationTriangleIcon className={cn(
          iconSizes[size],
          isCritical ? 'text-danger' : 'text-warning'
        )} />
      )}
      <span>{formatCurrency(amount, currency)}</span>
      <span className="opacity-70">at risk</span>
    </div>
  )
}

export default BudgetAtRiskChip
