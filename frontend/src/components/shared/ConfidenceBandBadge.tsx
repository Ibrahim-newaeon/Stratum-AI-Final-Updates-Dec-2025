/**
 * Confidence Band Badge
 * Displays confidence level: Reliable (90+), Directional (60-89), Unsafe (<60)
 */

import { cn } from '@/lib/utils'

export type ConfidenceBand = 'reliable' | 'directional' | 'unsafe'

interface ConfidenceBandBadgeProps {
  score: number // EMQ score 0-100
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

export function getConfidenceBand(score: number): ConfidenceBand {
  if (score >= 90) return 'reliable'
  if (score >= 60) return 'directional'
  return 'unsafe'
}

const bandConfig: Record<ConfidenceBand, { label: string; color: string; bgColor: string; description: string }> = {
  reliable: {
    label: 'Reliable',
    color: 'text-success',
    bgColor: 'bg-success/10',
    description: 'Data is trustworthy for decision-making',
  },
  directional: {
    label: 'Directional',
    color: 'text-warning',
    bgColor: 'bg-warning/10',
    description: 'Data shows trends but may have gaps',
  },
  unsafe: {
    label: 'Unsafe',
    color: 'text-danger',
    bgColor: 'bg-danger/10',
    description: 'Data quality too low for reliable decisions',
  },
}

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-3 py-1',
  lg: 'text-base px-4 py-1.5',
}

export function ConfidenceBandBadge({
  score,
  size = 'md',
  showLabel = true,
  className,
}: ConfidenceBandBadgeProps) {
  const band = getConfidenceBand(score)
  const config = bandConfig[band]

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium transition-all',
        config.bgColor,
        config.color,
        sizeClasses[size],
        className
      )}
      title={config.description}
    >
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full',
          band === 'reliable' && 'bg-success',
          band === 'directional' && 'bg-warning',
          band === 'unsafe' && 'bg-danger'
        )}
      />
      {showLabel && config.label}
    </span>
  )
}

export default ConfidenceBandBadge
