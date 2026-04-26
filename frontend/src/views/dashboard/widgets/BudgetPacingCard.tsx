/**
 * BudgetPacingCard - Per-platform budget pacing with progress bars
 */

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAllPacingStatus, type PacingStatus } from '@/api/pacing';

type PeriodFilter = '7d' | '14d' | '30d';

const FALLBACK_DATA: PacingStatus[] = [
  {
    targetId: 'fb-1',
    targetName: 'Meta Ads',
    metricType: 'spend',
    targetValue: 25000,
    currentValue: 17500,
    pacingPct: 70,
    projectedValue: 24200,
    projectedPct: 96.8,
    daysRemaining: 9,
    daysElapsed: 21,
    dailyTarget: 833,
    dailyActual: 780,
    status: 'on_track',
    trend: 'stable',
  },
  {
    targetId: 'g-1',
    targetName: 'Google Ads',
    metricType: 'spend',
    targetValue: 18000,
    currentValue: 10800,
    pacingPct: 60,
    projectedValue: 15200,
    projectedPct: 84.4,
    daysRemaining: 9,
    daysElapsed: 21,
    dailyTarget: 600,
    dailyActual: 520,
    status: 'behind',
    trend: 'declining',
  },
  {
    targetId: 'tt-1',
    targetName: 'TikTok Ads',
    metricType: 'spend',
    targetValue: 8000,
    currentValue: 6800,
    pacingPct: 85,
    projectedValue: 9100,
    projectedPct: 113.8,
    daysRemaining: 9,
    daysElapsed: 21,
    dailyTarget: 267,
    dailyActual: 310,
    status: 'ahead',
    trend: 'improving',
  },
  {
    targetId: 'sc-1',
    targetName: 'Snapchat Ads',
    metricType: 'spend',
    targetValue: 5000,
    currentValue: 2100,
    pacingPct: 42,
    projectedValue: 3200,
    projectedPct: 64,
    daysRemaining: 9,
    daysElapsed: 21,
    dailyTarget: 167,
    dailyActual: 100,
    status: 'at_risk',
    trend: 'declining',
  },
];

const PLATFORM_COLORS: Record<string, string> = {
  'Meta Ads': 'bg-blue-500',
  'Google Ads': 'bg-red-500',
  'TikTok Ads': 'bg-cyan-500',
  'Snapchat Ads': 'bg-yellow-400',
};

function getStatusBadge(status: PacingStatus['status']) {
  switch (status) {
    case 'on_track':
    case 'ahead':
      return { label: status === 'ahead' ? 'Ahead' : 'On Track', cls: 'bg-emerald-500/10 text-emerald-500' };
    case 'behind':
      return { label: 'Behind', cls: 'bg-amber-500/10 text-amber-500' };
    case 'at_risk':
    case 'missed':
      return { label: status === 'missed' ? 'Missed' : 'At Risk', cls: 'bg-red-500/10 text-red-500' };
    default:
      return { label: status, cls: 'bg-muted text-muted-foreground' };
  }
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

export function BudgetPacingCard() {
  const [period, setPeriod] = useState<PeriodFilter>('30d');
  const { data, isLoading } = useAllPacingStatus();

  const items = data && data.length > 0 ? data : FALLBACK_DATA;

  if (isLoading) {
    return (
      <div className="widget-card flex items-center justify-center min-h-[17.5rem]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="widget-card h-full">
      <div className="widget-header">
        <h3 className="widget-title">
          Budget Pacing
        </h3>
        <div className="flex bg-white/[0.04] border border-white/[0.06] rounded-lg p-0.5">
          {(['7d', '14d', '30d'] as PeriodFilter[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              aria-label={`Filter by: ${p}`}
              aria-current={period === p ? "true" : undefined}
              className={cn(
                'px-3 py-1.5 text-xs font-medium rounded-md transition-colors duration-200',
                period === p ? 'bg-primary/20 text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4">
        {items.map((item) => {
          const badge = getStatusBadge(item.status);
          const barColor = PLATFORM_COLORS[item.targetName] || 'bg-primary';
          const pct = Math.min(item.pacingPct, 100);
          const projPct = Math.min(item.projectedPct, 100);

          return (
            <div key={item.targetId}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <div className={cn('w-2.5 h-2.5 rounded-full', barColor)} />
                  <span className="text-sm font-medium">{item.targetName}</span>
                </div>
                <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', badge.cls)}>
                  {badge.label}
                </span>
              </div>

              {/* Progress bar — rounded with glow */}
              <div className="relative h-2 bg-white/[0.06] rounded-full overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-[width] duration-700 ease-out', barColor)}
                  style={{ width: `${pct}%`, boxShadow: `0 0 8px ${barColor === 'bg-blue-500' ? 'hsl(var(--primary) / 0.4)' : barColor === 'bg-red-500' ? 'hsl(var(--status-critical) / 0.4)' : barColor === 'bg-cyan-500' ? 'hsl(var(--status-healthy) / 0.4)' : 'rgba(250,204,21,0.4)'}` }}
                />
                {/* Projected marker */}
                {projPct > 0 && projPct <= 100 && (
                  <div
                    className="absolute top-0 h-full w-0.5 bg-foreground/40"
                    style={{ left: `${projPct}%` }}
                  />
                )}
              </div>

              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-muted-foreground">
                  {formatCurrency(item.currentValue)} / {formatCurrency(item.targetValue)}
                </span>
                <span className="text-xs text-muted-foreground">{item.daysRemaining}d left</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
