/**
 * MetricCard - Dashboard metric display card
 */

import { ArrowDown, ArrowUp, Minus, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TrendDirection } from '@/api/dashboard'

interface MetricCardProps {
  title: string
  value: string
  change?: number | null
  trend?: TrendDirection
  icon?: React.ReactNode
  loading?: boolean
  size?: 'default' | 'small'
  highlight?: boolean
  positive?: boolean
}

export function MetricCard({
  title,
  value,
  change,
  trend,
  icon,
  loading = false,
  size = 'default',
  highlight = false,
  positive = false,
}: MetricCardProps) {
  const isSmall = size === 'small'

  const getTrendIcon = () => {
    if (!trend) return null
    switch (trend) {
      case 'up':
        return <ArrowUp className={cn('w-3 h-3', positive ? 'text-green-500' : 'text-red-500')} />
      case 'down':
        return <ArrowDown className={cn('w-3 h-3', positive ? 'text-red-500' : 'text-green-500')} />
      case 'stable':
        return <Minus className="w-3 h-3 text-muted-foreground" />
      default:
        return null
    }
  }

  const getChangeColor = () => {
    if (change === null || change === undefined) return 'text-muted-foreground'
    if (change === 0) return 'text-muted-foreground'
    if (positive) {
      return change > 0 ? 'text-green-500' : 'text-red-500'
    }
    return change > 0 ? 'text-red-500' : 'text-green-500'
  }

  if (loading) {
    return (
      <div
        className={cn(
          'bg-card border rounded-lg flex items-center justify-center',
          isSmall ? 'p-3' : 'p-5'
        )}
      >
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div
      className={cn(
        'bg-card border rounded-lg transition-all',
        isSmall ? 'p-3' : 'p-5',
        highlight && 'ring-2 ring-primary/20 border-primary/50'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p
            className={cn(
              'text-muted-foreground font-medium truncate',
              isSmall ? 'text-xs' : 'text-sm'
            )}
          >
            {title}
          </p>
          <p
            className={cn(
              'font-bold mt-1 truncate',
              isSmall ? 'text-lg' : 'text-2xl'
            )}
          >
            {value}
          </p>
          {change !== null && change !== undefined && (
            <div className={cn('flex items-center gap-1 mt-1', getChangeColor())}>
              {getTrendIcon()}
              <span className={cn('font-medium', isSmall ? 'text-xs' : 'text-sm')}>
                {change > 0 ? '+' : ''}
                {change.toFixed(1)}%
              </span>
            </div>
          )}
        </div>
        {icon && (
          <div
            className={cn(
              'flex-shrink-0 rounded-lg bg-muted flex items-center justify-center',
              isSmall ? 'w-8 h-8' : 'w-10 h-10',
              highlight && 'bg-primary/10 text-primary'
            )}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}
