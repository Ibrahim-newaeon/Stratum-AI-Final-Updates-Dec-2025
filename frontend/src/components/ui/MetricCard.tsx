/**
 * Metric Card Component
 * Colored shiny cards with status-based styling
 * Part of Stratum AI Dashboard Enhancement
 */

import { memo, ReactNode } from 'react';
import { cn } from '@/lib/utils';

export type MetricCardVariant = 'success' | 'warning' | 'error' | 'info' | 'premium' | 'active' | 'default';

interface MetricCardProps {
  variant?: MetricCardVariant;
  className?: string;
  children: ReactNode;
  /** Show progress bar at bottom */
  progress?: number;
  /** Click handler */
  onClick?: () => void;
}

export const MetricCard = memo(function MetricCard({
  variant = 'default',
  className,
  children,
  progress,
  onClick,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        'metric-card',
        variant !== 'default' && variant,
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
    >
      <div className="card-content relative">
        {children}
        {progress !== undefined && (
          <div className="progress-bar">
            <div
              className="fill"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
});

interface MetricValueProps {
  children: ReactNode;
  className?: string;
}

export const MetricValue = memo(function MetricValue({
  children,
  className,
}: MetricValueProps) {
  return (
    <div className={cn('metric-value', className)}>
      {children}
    </div>
  );
});

interface MetricLabelProps {
  children: ReactNode;
  className?: string;
}

export const MetricLabel = memo(function MetricLabel({
  children,
  className,
}: MetricLabelProps) {
  return (
    <span className={cn('metric-label', className)}>
      {children}
    </span>
  );
});

interface MetricBadgeProps {
  children: ReactNode;
  variant?: 'success' | 'warning' | 'error' | 'info' | 'premium' | 'active';
  className?: string;
}

export const MetricBadge = memo(function MetricBadge({
  children,
  variant = 'info',
  className,
}: MetricBadgeProps) {
  const variantClasses = {
    success: 'bg-green-500/10 text-green-400 border-green-500/20',
    warning: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    error: 'bg-red-500/10 text-red-400 border-red-500/20',
    info: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    premium: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    active: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
});

interface MetricTrendProps {
  value: number;
  suffix?: string;
  inverted?: boolean;
  className?: string;
}

export const MetricTrend = memo(function MetricTrend({
  value,
  suffix = '%',
  inverted = false,
  className,
}: MetricTrendProps) {
  const isPositive = inverted ? value < 0 : value > 0;
  const displayValue = Math.abs(value);

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 text-sm font-medium',
        isPositive ? 'text-green-400' : 'text-red-400',
        className
      )}
    >
      <span className="text-xs">{isPositive ? '↗' : '↘'}</span>
      {displayValue.toFixed(0)}{suffix}
    </span>
  );
});

export default MetricCard;
