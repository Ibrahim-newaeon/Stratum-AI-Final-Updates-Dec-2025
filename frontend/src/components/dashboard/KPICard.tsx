/**
 * KPI Card Component
 * Displays key performance indicators with trend indicators and animations
 */

import React, { useState } from 'react'
import CountUp from 'react-countup'
import { TrendingUp, TrendingDown, MoreHorizontal, Eye, Bell, Download } from 'lucide-react'
import { cn } from '@/lib/utils'

interface KPICardProps {
  title: string
  value: string | number
  numericValue?: number
  prefix?: string
  suffix?: string
  decimals?: number
  delta?: number
  deltaText?: string
  trend?: 'up' | 'down' | 'neutral'
  trendIsGood?: boolean
  highlight?: boolean
  size?: 'small' | 'normal'
  icon?: React.ReactNode
  className?: string
  loading?: boolean
  enableAnimation?: boolean
  onViewDetails?: () => void
  onSetAlert?: () => void
  onExport?: () => void
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  numericValue,
  prefix = '',
  suffix = '',
  decimals = 0,
  delta,
  deltaText = 'vs last period',
  trend,
  trendIsGood = false,
  highlight = false,
  size = 'normal',
  icon,
  className = '',
  loading = false,
  enableAnimation = true,
  onViewDetails,
  onSetAlert,
  onExport,
}) => {
  const [showActions, setShowActions] = useState(false)
  const hasActions = onViewDetails || onSetAlert || onExport

  // Determine if trend is positive based on context
  const isPositiveTrend = trendIsGood ? trend === 'up' : trend === 'down'

  // Color classes for delta - using design system colors
  const deltaColorClass =
    delta !== undefined
      ? isPositiveTrend
        ? 'text-success'
        : 'text-danger'
      : 'text-muted-foreground'

  // Parse numeric value from string if needed
  const getNumericValue = (): number => {
    if (numericValue !== undefined) return numericValue
    if (typeof value === 'number') return value
    // Try to parse from formatted string
    const parsed = parseFloat(value.toString().replace(/[^0-9.-]/g, ''))
    return isNaN(parsed) ? 0 : parsed
  }

  // Loading skeleton
  if (loading) {
    return (
      <div
        className={cn(
          'relative overflow-hidden rounded-xl border bg-card animate-pulse',
          size === 'small' ? 'p-4' : 'p-6',
          className
        )}
      >
        <div className="absolute left-0 top-0 h-full w-1 bg-muted" />
        <div className="relative space-y-3">
          <div className="flex items-center justify-between">
            <div className="h-4 w-24 bg-muted rounded" />
            <div className="h-5 w-5 bg-muted rounded" />
          </div>
          <div className={cn('h-8 bg-muted rounded', size === 'small' ? 'w-20' : 'w-28')} />
          {size === 'normal' && (
            <div className="flex items-center gap-2">
              <div className="h-4 w-4 bg-muted rounded" />
              <div className="h-4 w-16 bg-muted rounded" />
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-lg border motion-card motion-enter group',
        highlight
          ? 'bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-glow'
          : 'bg-card shadow-card hover:shadow-card-hover hover:border-[rgba(168,85,247,0.30)]',
        size === 'small' ? 'p-4' : 'p-6',
        className
      )}
      onMouseEnter={() => hasActions && setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      role="article"
      aria-label={`${title}: ${value}${delta !== undefined ? `, ${delta > 0 ? 'up' : 'down'} ${Math.abs(delta).toFixed(1)}% ${deltaText}` : ''}`}
    >
      {/* Accent border (left side) */}
      <div
        className={cn(
          'absolute left-0 top-0 h-full w-1 transition-all duration-200',
          highlight ? 'bg-primary-foreground/30' : 'bg-primary',
          'group-hover:w-1.5'
        )}
      />

      {/* Quick Actions Menu */}
      {hasActions && showActions && (
        <div className="absolute top-2 right-2 flex items-center gap-1 animate-in fade-in duration-200 z-10">
          {onViewDetails && (
            <button
              onClick={onViewDetails}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                highlight
                  ? 'hover:bg-primary-foreground/20 text-primary-foreground'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              )}
              title="View details"
              aria-label="View details"
            >
              <Eye className="w-3.5 h-3.5" />
            </button>
          )}
          {onSetAlert && (
            <button
              onClick={onSetAlert}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                highlight
                  ? 'hover:bg-primary-foreground/20 text-primary-foreground'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              )}
              title="Set alert"
              aria-label="Set alert"
            >
              <Bell className="w-3.5 h-3.5" />
            </button>
          )}
          {onExport && (
            <button
              onClick={onExport}
              className={cn(
                'p-1.5 rounded-md transition-colors',
                highlight
                  ? 'hover:bg-primary-foreground/20 text-primary-foreground'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
              )}
              title="Export data"
              aria-label="Export data"
            >
              <Download className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {/* Content */}
      <div className="relative">
        {/* Title */}
        <div className="flex items-center justify-between mb-2">
          <p
            className={cn(
              'text-sm font-medium',
              highlight ? 'text-primary-foreground/80' : 'text-muted-foreground'
            )}
          >
            {title}
          </p>
          {icon && (
            <div className={cn(
              highlight ? 'text-primary-foreground/80' : 'text-muted-foreground',
              'transition-transform group-hover:scale-110'
            )}>
              {icon}
            </div>
          )}
        </div>

        {/* Value with animation */}
        <div
          className={cn(
            'font-bold tabular-nums',
            size === 'small' ? 'text-2xl' : 'text-3xl',
            highlight ? 'text-primary-foreground' : 'text-foreground'
          )}
        >
          {enableAnimation && numericValue !== undefined ? (
            <CountUp
              start={0}
              end={getNumericValue()}
              duration={0.8}
              decimals={decimals}
              prefix={prefix}
              suffix={suffix}
              separator=","
              preserveValue
            />
          ) : (
            value
          )}
        </div>

        {/* Delta (change indicator) - with motion-delta animation */}
        {delta !== undefined && (
          <div className={cn('mt-2 flex items-center text-sm motion-delta', deltaColorClass)}>
            {trend === 'up' && <TrendingUp className="h-4 w-4 mr-1" aria-hidden="true" />}
            {trend === 'down' && <TrendingDown className="h-4 w-4 mr-1" aria-hidden="true" />}
            <span className="font-semibold">
              {delta > 0 ? '+' : ''}
              {delta.toFixed(1)}%
            </span>
            <span
              className={cn(
                'ml-1 text-meta',
                highlight ? 'text-primary-foreground/70' : 'text-text-muted'
              )}
            >
              {deltaText}
            </span>
          </div>
        )}
      </div>

      {/* Decorative background pattern for highlighted cards */}
      {highlight && (
        <div className="absolute -right-4 -bottom-4 opacity-10" aria-hidden="true">
          <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
            <circle cx="60" cy="60" r="50" stroke="currentColor" strokeWidth="2" />
            <circle cx="60" cy="60" r="35" stroke="currentColor" strokeWidth="2" />
            <circle cx="60" cy="60" r="20" stroke="currentColor" strokeWidth="2" />
          </svg>
        </div>
      )}
    </div>
  )
}

export default KPICard
