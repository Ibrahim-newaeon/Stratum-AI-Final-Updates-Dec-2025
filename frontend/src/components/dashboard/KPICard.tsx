/**
 * KPI Card Component
 * Displays key performance indicators with trend indicators
 */

import React from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface KPICardProps {
  title: string
  value: string | number
  delta?: number
  deltaText?: string
  trend?: 'up' | 'down' | 'neutral'
  trendIsGood?: boolean
  highlight?: boolean
  size?: 'small' | 'normal'
  icon?: React.ReactNode
  className?: string
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  delta,
  deltaText = 'vs last period',
  trend,
  trendIsGood = false,
  highlight = false,
  size = 'normal',
  icon,
  className = '',
}) => {
  // Determine if trend is positive based on context
  const isPositiveTrend = trendIsGood ? trend === 'up' : trend === 'down'

  // Color classes for delta
  const deltaColorClass =
    delta !== undefined
      ? isPositiveTrend
        ? 'text-green-600 dark:text-green-400'
        : 'text-red-600 dark:text-red-400'
      : 'text-muted-foreground'

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border transition-all duration-200 hover:shadow-lg',
        highlight
          ? 'bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-xl'
          : 'bg-card shadow',
        size === 'small' ? 'p-4' : 'p-6',
        className
      )}
    >
      {/* Accent border (left side) */}
      <div
        className={cn(
          'absolute left-0 top-0 h-full w-1',
          highlight ? 'bg-primary-foreground/30' : 'bg-primary'
        )}
      />

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
            <div className={highlight ? 'text-primary-foreground/80' : 'text-muted-foreground'}>
              {icon}
            </div>
          )}
        </div>

        {/* Value */}
        <div
          className={cn(
            'font-bold',
            size === 'small' ? 'text-2xl' : 'text-3xl',
            highlight ? 'text-primary-foreground' : 'text-foreground'
          )}
        >
          {value}
        </div>

        {/* Delta (change indicator) */}
        {delta !== undefined && (
          <div className={cn('mt-2 flex items-center text-sm', deltaColorClass)}>
            {trend === 'up' && <TrendingUp className="h-4 w-4 mr-1" />}
            {trend === 'down' && <TrendingDown className="h-4 w-4 mr-1" />}
            <span className="font-semibold">
              {delta > 0 ? '+' : ''}
              {delta.toFixed(1)}%
            </span>
            <span
              className={cn(
                'ml-1',
                highlight ? 'text-primary-foreground/70' : 'text-muted-foreground'
              )}
            >
              {deltaText}
            </span>
          </div>
        )}
      </div>

      {/* Decorative background pattern for highlighted cards */}
      {highlight && (
        <div className="absolute -right-4 -bottom-4 opacity-10">
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
