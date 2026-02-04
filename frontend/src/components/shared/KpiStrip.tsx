/**
 * KPI Strip
 * Displays a row of KPIs with confidence stamps
 */

import { cn } from '@/lib/utils';
import { ConfidenceBandBadge, getConfidenceBand } from './ConfidenceBandBadge';
import { ArrowDownIcon, ArrowUpIcon, MinusIcon } from '@heroicons/react/24/solid';

export interface Kpi {
  id: string;
  label: string;
  value: number | string;
  format?: 'currency' | 'percentage' | 'number' | 'multiplier' | 'raw';
  previousValue?: number;
  confidence?: number; // 0-100
  trend?: 'up' | 'down' | 'flat';
  trendIsPositive?: boolean; // If false, "up" trend is bad (e.g., CPA going up)
  unit?: string;
  currency?: string;
}

interface KpiStripProps {
  kpis: Kpi[];
  emqScore?: number; // Overall EMQ score for stamp
  showConfidence?: boolean;
  compact?: boolean;
  className?: string;
}

function formatValue(kpi: Kpi): string {
  const value = typeof kpi.value === 'string' ? kpi.value : kpi.value;

  if (typeof value === 'string') return value;

  switch (kpi.format) {
    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: kpi.currency || 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(value);
    case 'percentage':
      return `${value.toFixed(1)}%`;
    case 'multiplier':
      return `${value.toFixed(2)}x`;
    case 'number':
      return new Intl.NumberFormat('en-US', {
        notation: value > 999999 ? 'compact' : 'standard',
        maximumFractionDigits: 1,
      }).format(value);
    default:
      return String(value);
  }
}

function calculateChange(current: number, previous: number): number {
  if (previous === 0) return 0;
  return ((current - previous) / previous) * 100;
}

function KpiItem({
  kpi,
  showConfidence,
  compact,
}: {
  kpi: Kpi;
  showConfidence: boolean;
  compact: boolean;
}) {
  const change =
    kpi.previousValue !== undefined && typeof kpi.value === 'number'
      ? calculateChange(kpi.value, kpi.previousValue)
      : null;

  const trend =
    kpi.trend || (change !== null ? (change > 0 ? 'up' : change < 0 ? 'down' : 'flat') : undefined);

  const isTrendPositive = kpi.trendIsPositive !== false ? trend === 'up' : trend === 'down';

  const TrendIcon = trend === 'up' ? ArrowUpIcon : trend === 'down' ? ArrowDownIcon : MinusIcon;

  return (
    <div className={cn('flex flex-col', compact ? 'gap-0.5' : 'gap-1')}>
      {/* Label with confidence */}
      <div className="flex items-center gap-1.5">
        <span className={cn('text-text-muted', compact ? 'text-xs' : 'text-sm')}>{kpi.label}</span>
        {showConfidence && kpi.confidence !== undefined && (
          <ConfidenceBandBadge score={kpi.confidence} size="sm" showLabel={false} />
        )}
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-2">
        <span className={cn('font-semibold text-white', compact ? 'text-lg' : 'text-2xl')}>
          {formatValue(kpi)}
        </span>
        {kpi.unit && <span className="text-sm text-text-muted">{kpi.unit}</span>}
      </div>

      {/* Trend */}
      {change !== null && trend && (
        <div
          className={cn(
            'flex items-center gap-1',
            compact ? 'text-xs' : 'text-sm',
            isTrendPositive ? 'text-success' : trend === 'flat' ? 'text-text-muted' : 'text-danger'
          )}
        >
          <TrendIcon className="w-3 h-3" />
          <span>{Math.abs(change).toFixed(1)}%</span>
          <span className="text-text-muted">vs prev</span>
        </div>
      )}
    </div>
  );
}

export function KpiStrip({
  kpis,
  emqScore,
  showConfidence = true,
  compact = false,
  className,
}: KpiStripProps) {
  const band = emqScore !== undefined ? getConfidenceBand(emqScore) : null;

  return (
    <div className={cn('rounded-xl bg-surface-secondary border border-white/10', className)}>
      {/* Header with EMQ stamp */}
      {band && (
        <div
          className={cn(
            'flex items-center justify-between px-4 py-2 border-b border-white/10',
            band === 'reliable' && 'bg-success/5',
            band === 'directional' && 'bg-warning/5',
            band === 'unsafe' && 'bg-danger/5'
          )}
        >
          <span
            className={cn(
              'text-xs font-medium',
              band === 'reliable' && 'text-success',
              band === 'directional' && 'text-warning',
              band === 'unsafe' && 'text-danger'
            )}
          >
            {band === 'reliable'
              ? 'Reliable metrics'
              : band === 'directional'
                ? 'Directional metrics'
                : 'Low confidence metrics'}
          </span>
          <ConfidenceBandBadge score={emqScore!} size="sm" />
        </div>
      )}

      {/* KPIs grid */}
      <div
        className={cn(
          'grid gap-4',
          compact ? 'p-3' : 'p-4',
          kpis.length === 2 && 'grid-cols-2',
          kpis.length === 3 && 'grid-cols-3',
          kpis.length === 4 && 'grid-cols-2 md:grid-cols-4',
          kpis.length >= 5 && 'grid-cols-2 md:grid-cols-3 lg:grid-cols-5'
        )}
      >
        {kpis.map((kpi) => (
          <KpiItem
            key={kpi.id}
            kpi={kpi}
            showConfidence={showConfidence && !band}
            compact={compact}
          />
        ))}
      </div>
    </div>
  );
}

export default KpiStrip;
