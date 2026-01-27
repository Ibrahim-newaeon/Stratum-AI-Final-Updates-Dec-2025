/**
 * Volatility Badge (SVI - Signal Volatility Index)
 * Displays whether signal quality is stable or unstable
 */

import { cn } from '@/lib/utils';
import { ArrowTrendingDownIcon, ArrowTrendingUpIcon } from '@heroicons/react/24/outline';

interface VolatilityBadgeProps {
  svi: number; // Signal Volatility Index 0-100
  threshold?: number; // Above this = unstable
  showValue?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-3 py-1',
  lg: 'text-base px-4 py-1.5',
};

const iconSizes = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
};

export function VolatilityBadge({
  svi,
  threshold = 30,
  showValue = false,
  size = 'md',
  className,
}: VolatilityBadgeProps) {
  const isUnstable = svi >= threshold;
  const isCritical = svi >= threshold * 2;

  const Icon = isUnstable ? ArrowTrendingUpIcon : ArrowTrendingDownIcon;
  const label = isCritical ? 'High Volatility' : isUnstable ? 'Unstable' : 'Stable';

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium transition-all',
        isCritical
          ? 'bg-danger/10 text-danger'
          : isUnstable
            ? 'bg-warning/10 text-warning'
            : 'bg-success/10 text-success',
        sizeClasses[size],
        className
      )}
      title={`Signal Volatility Index: ${svi}%`}
    >
      <Icon className={iconSizes[size]} />
      <span>{label}</span>
      {showValue && <span className="opacity-70">({svi}%)</span>}
    </span>
  );
}

export default VolatilityBadge;
