/**
 * InfoIcon Component - Starburst Design
 * Per Design System: SVG-only, 12-14px, click-triggered tooltip
 * Trigger definition/help via tooltip or popover
 */

import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface InfoIconProps {
  size?: 12 | 14 | 16
  className?: string
  onClick?: () => void
  'aria-label'?: string
}

export const InfoIcon = forwardRef<HTMLButtonElement, InfoIconProps>(
  ({ size = 12, className, onClick, 'aria-label': ariaLabel = 'More information' }, ref) => {
    return (
      <button
        ref={ref}
        type="button"
        onClick={onClick}
        className={cn(
          'rounded-md p-0.5 text-muted-foreground hover:text-primary',
          'focus:outline-none focus:ring-2 focus:ring-primary/50',
          'transition-colors duration-200',
          className
        )}
        aria-label={ariaLabel}
      >
        <svg
          width={size}
          height={size}
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
          className="info-mark"
        >
          {/* Back shards */}
          <path
            d="M4.2 12.2 9.2 10.3 8.1 14.2 4.8 15.7Z"
            opacity="0.3"
          />
          <path
            d="M19.8 12.2 14.8 10.3 15.9 14.2 19.2 15.7Z"
            opacity="0.3"
          />

          {/* Core 4-point starburst */}
          <path d="M12 3.2 L13.35 10.65 L20.8 12 L13.35 13.35 L12 20.8 L10.65 13.35 L3.2 12 L10.65 10.65 Z" />

          {/* Thin spikes */}
          <path d="M12 1.3 12.55 8.2 12 9.1 11.45 8.2Z" />
          <path d="M12 22.7 12.55 15.8 12 14.9 11.45 15.8Z" />
          <path d="M1.3 12 8.2 11.45 9.1 12 8.2 12.55Z" />
          <path d="M22.7 12 15.8 11.45 14.9 12 15.8 12.55Z" />

          {/* Micro-sparkles */}
          <path
            d="M16.9 5.1 17.35 6.35 18.6 6.8 17.35 7.25 16.9 8.5 16.45 7.25 15.2 6.8 16.45 6.35Z"
            opacity="0.6"
          />
          <path
            d="M6.2 6.6 6.55 7.55 7.5 7.9 6.55 8.25 6.2 9.2 5.85 8.25 4.9 7.9 5.85 7.55Z"
            opacity="0.6"
          />
          <path
            d="M15.9 17.1 16.2 17.9 17 18.2 16.2 18.5 15.9 19.3 15.6 18.5 14.8 18.2 15.6 17.9Z"
            opacity="0.6"
          />
        </svg>
      </button>
    )
  }
)

InfoIcon.displayName = 'InfoIcon'

export default InfoIcon
