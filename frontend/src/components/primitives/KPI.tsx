/**
 * KPI — composed KPI card.
 *
 * Layout:
 *   ┌────────────────────────────────────┐
 *   │ LABEL (mono micro)            […] │
 *   │                                    │
 *   │ VALUE (display)        ↑ +12.4%   │  ← delta on the right
 *   │                                    │
 *   │ FOOTNOTE (muted small)             │
 *   └────────────────────────────────────┘
 *
 * Props:
 * - label      : top-left mono caption
 * - value      : main number / text (already formatted by caller)
 * - delta      : { value: number, format?: 'percent' | 'absolute' | 'raw',
 *                  direction?: 'up' | 'down' | 'auto', invert?: boolean }
 *                'invert' lets callers say "down is good" (e.g. CAC ↓).
 * - footnote   : small contextual text under value
 * - status     : optional StatusPill props for the top-right slot
 * - icon       : optional decorative icon (top-right when no status)
 * - emphasis   : 'default' | 'glow' — primary KPI gets the radial bleed
 * - loading    : skeleton bars instead of value/delta
 * - empty      : text shown when value is null/undefined
 * - error      : error string shown in a danger pill
 *
 * Reuses Card under the hood — KPI = composed primitive, not a sibling.
 */

import { type ReactNode } from 'react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';
import { Card, type CardVariant } from './Card';
import { StatusPill, type StatusPillVariant } from './StatusPill';
import { cn } from '@/lib/utils';

interface KPIDelta {
  /** Raw numeric delta. For percent format, pass the percent value (e.g. 12.4 = 12.4%). */
  value: number;
  format?: 'percent' | 'absolute' | 'raw';
  /** Force a direction; otherwise auto from sign. */
  direction?: 'up' | 'down' | 'auto';
  /** When true, downward movement is treated as positive (e.g. CAC, latency). */
  invert?: boolean;
}

interface KPIProps {
  label: string;
  value?: ReactNode;
  delta?: KPIDelta;
  footnote?: ReactNode;
  status?: { label: string; variant?: StatusPillVariant; pulse?: boolean };
  icon?: ReactNode;
  emphasis?: 'default' | 'glow';
  loading?: boolean;
  /** Text to show when value is missing — defaults to "—". */
  empty?: string;
  error?: string;
  className?: string;
}

function formatDelta(delta: KPIDelta): string {
  const v = delta.value;
  const abs = Math.abs(v);
  switch (delta.format ?? 'percent') {
    case 'percent':
      return `${v >= 0 ? '+' : '−'}${abs.toFixed(1)}%`;
    case 'absolute':
      return `${v >= 0 ? '+' : '−'}${abs.toLocaleString()}`;
    case 'raw':
      return v.toString();
  }
}

function deltaTone(delta: KPIDelta): 'positive' | 'negative' | 'flat' {
  if (delta.value === 0) return 'flat';
  const direction = delta.direction ?? 'auto';
  const isUp = direction === 'auto' ? delta.value > 0 : direction === 'up';
  const positive = delta.invert ? !isUp : isUp;
  return positive ? 'positive' : 'negative';
}

export function KPI({
  label,
  value,
  delta,
  footnote,
  status,
  icon,
  emphasis = 'default',
  loading = false,
  empty = '—',
  error,
  className,
}: KPIProps) {
  const cardVariant: CardVariant = emphasis === 'glow' ? 'glow' : 'default';

  const renderValue = () => {
    if (loading) {
      return <div className="h-9 w-32 bg-muted rounded animate-pulse" aria-hidden="true" />;
    }
    if (error) {
      return (
        <span className="text-display-xs font-medium tabular-nums text-muted-foreground">—</span>
      );
    }
    if (value === null || value === undefined) {
      return (
        <span className="text-display-xs font-medium tabular-nums text-muted-foreground">
          {empty}
        </span>
      );
    }
    return (
      <span className="text-display-xs font-medium tabular-nums tracking-tight text-foreground">
        {value}
      </span>
    );
  };

  const renderDelta = () => {
    if (loading || error || delta === undefined) return null;
    const tone = deltaTone(delta);
    const Arrow = tone === 'flat' ? Minus : tone === 'positive' ? ArrowUpRight : ArrowDownRight;
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 text-meta tabular-nums',
          tone === 'positive' && 'text-success',
          tone === 'negative' && 'text-danger',
          tone === 'flat' && 'text-muted-foreground'
        )}
      >
        <Arrow className="w-3.5 h-3.5" aria-hidden="true" />
        {formatDelta(delta)}
      </span>
    );
  };

  return (
    <Card variant={cardVariant} className={cn('p-6', className)}>
      <div className="flex items-start justify-between mb-6">
        <span className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono">
          {label}
        </span>
        <div className="flex items-center gap-2">
          {status ? (
            <StatusPill variant={status.variant ?? 'healthy'} size="sm" pulse={status.pulse}>
              {status.label}
            </StatusPill>
          ) : icon ? (
            <span aria-hidden="true" className="text-muted-foreground">
              {icon}
            </span>
          ) : null}
        </div>
      </div>

      <div className="flex items-end justify-between gap-3">
        {renderValue()}
        {renderDelta()}
      </div>

      {(footnote || error) && (
        <div className={cn('mt-3 text-meta', error ? 'text-danger' : 'text-muted-foreground')}>
          {error ?? footnote}
        </div>
      )}
    </Card>
  );
}

export default KPI;
export type { KPIProps, KPIDelta };
