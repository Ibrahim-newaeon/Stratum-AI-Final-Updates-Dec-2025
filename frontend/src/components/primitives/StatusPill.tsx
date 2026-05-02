/**
 * StatusPill — figma's signature pill component.
 *
 * Variants map directly to trust-engine semantic states:
 * - healthy   : success (green)
 * - degraded  : warning (amber)
 * - unhealthy : danger  (red)
 * - neutral   : muted   (no semantic, default ember dot)
 *
 * Sizes:
 * - sm  : compact for nav / inline contexts
 * - md  : default for headers / KPI cards
 *
 * Accessibility:
 * - role="status" + aria-live="polite" so AT users hear changes.
 * - Decorative dot is aria-hidden; the label provides the readable state.
 */

import { forwardRef, type HTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

export type StatusPillVariant = 'healthy' | 'degraded' | 'unhealthy' | 'neutral';
export type StatusPillSize = 'sm' | 'md';

interface StatusPillProps extends Omit<HTMLAttributes<HTMLSpanElement>, 'role'> {
  variant?: StatusPillVariant;
  size?: StatusPillSize;
  /** Pulse the dot (active/operational signal). */
  pulse?: boolean;
  children: ReactNode;
}

const DOT_COLOR: Record<StatusPillVariant, string> = {
  healthy: 'bg-success',
  degraded: 'bg-warning',
  unhealthy: 'bg-danger',
  neutral: 'bg-primary',
};

const DOT_GLOW: Record<StatusPillVariant, string> = {
  healthy: '0 0 8px hsl(var(--success))',
  degraded: '0 0 8px hsl(var(--warning))',
  unhealthy: '0 0 8px hsl(var(--danger))',
  neutral: '0 0 8px hsl(var(--primary))',
};

const SIZE_CLASS: Record<StatusPillSize, string> = {
  sm: 'px-2.5 py-1 text-[10.5px] gap-1.5',
  md: 'px-3 py-1.5 text-[11.5px] gap-2',
};

const DOT_SIZE: Record<StatusPillSize, string> = {
  sm: 'w-1 h-1',
  md: 'w-1.5 h-1.5',
};

export const StatusPill = forwardRef<HTMLSpanElement, StatusPillProps>(function StatusPill(
  { variant = 'neutral', size = 'md', pulse = false, className, children, ...rest },
  ref
) {
  return (
    <span
      ref={ref}
      role="status"
      aria-live="polite"
      className={cn(
        'inline-flex items-center rounded-full',
        'border border-border bg-card',
        'font-medium uppercase tracking-[0.06em] text-foreground',
        SIZE_CLASS[size],
        className
      )}
      {...rest}
    >
      <span
        aria-hidden="true"
        className={cn('rounded-full', DOT_SIZE[size], DOT_COLOR[variant], pulse && 'animate-pulse')}
        style={{ boxShadow: DOT_GLOW[variant] }}
      />
      <span className="leading-none">{children}</span>
    </span>
  );
});

export default StatusPill;
