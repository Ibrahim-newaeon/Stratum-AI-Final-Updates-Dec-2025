/**
 * EMQ Score Card
 * Displays the Event Measurement Quality score with gauge and drivers breakdown
 */

import { cn } from '@/lib/utils';
import { ConfidenceBandBadge, getConfidenceBand } from './ConfidenceBandBadge';
import {
  BugAntIcon,
  ChartBarIcon,
  ClockIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';

interface EmqDriver {
  name: string;
  value: number; // 0-100
  weight: number;
  status: 'good' | 'warning' | 'critical';
}

interface EmqScoreCardProps {
  score: number; // 0-100
  previousScore?: number;
  drivers?: EmqDriver[];
  showDrivers?: boolean;
  compact?: boolean;
  className?: string;
}

const defaultDrivers: EmqDriver[] = [
  { name: 'Freshness', value: 95, weight: 0.3, status: 'good' },
  { name: 'Data Loss', value: 88, weight: 0.25, status: 'good' },
  { name: 'Variance', value: 72, weight: 0.25, status: 'warning' },
  { name: 'Errors', value: 98, weight: 0.2, status: 'good' },
];

const driverIcons: Record<string, typeof ClockIcon> = {
  Freshness: ClockIcon,
  'Data Loss': ExclamationCircleIcon,
  Variance: ChartBarIcon,
  Errors: BugAntIcon,
};

function ScoreGauge({ score, size = 120 }: { score: number; size?: number }) {
  const band = getConfidenceBand(score);
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const color = band === 'reliable'
    ? 'var(--teal, #00c7be)'
    : band === 'directional'
      ? 'var(--status-warning, #f59e0b)'
      : 'var(--coral, #ff6b6b)';

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-white/10"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-white">{score}</span>
        <span className="text-xs text-text-muted">EMQ</span>
      </div>
    </div>
  );
}

export function EmqScoreCard({
  score,
  previousScore,
  drivers = defaultDrivers,
  showDrivers = true,
  compact = false,
  className,
}: EmqScoreCardProps) {
  const delta = previousScore ? score - previousScore : null;

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-3 p-3 rounded-xl bg-surface-secondary border border-white/10',
          className
        )}
      >
        <ScoreGauge score={score} size={60} />
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-semibold text-white">EMQ Score</span>
            <ConfidenceBandBadge score={score} size="sm" />
          </div>
          {delta !== null && (
            <span
              className={cn(
                'text-sm',
                delta > 0 ? 'text-success' : delta < 0 ? 'text-danger' : 'text-text-muted'
              )}
            >
              {delta > 0 ? '+' : ''}
              {delta} from yesterday
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('p-6 rounded-2xl bg-surface-secondary border border-white/10', className)}>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-white">Event Measurement Quality</h3>
          <p className="text-sm text-text-muted mt-1">How reliable is your data today?</p>
        </div>
        <ConfidenceBandBadge score={score} />
      </div>

      <div className="flex items-center gap-8">
        <ScoreGauge score={score} />

        {showDrivers && (
          <div className="flex-1 space-y-3">
            {drivers.map((driver) => {
              const Icon = driverIcons[driver.name] || ChartBarIcon;
              return (
                <div key={driver.name} className="flex items-center gap-3">
                  <Icon
                    className={cn(
                      'w-4 h-4',
                      driver.status === 'good'
                        ? 'text-success'
                        : driver.status === 'warning'
                          ? 'text-warning'
                          : 'text-danger'
                    )}
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-text-secondary">{driver.name}</span>
                      <span
                        className={cn(
                          'text-sm font-medium',
                          driver.status === 'good'
                            ? 'text-success'
                            : driver.status === 'warning'
                              ? 'text-warning'
                              : 'text-danger'
                        )}
                      >
                        {driver.value}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all duration-500',
                          driver.status === 'good'
                            ? 'bg-success'
                            : driver.status === 'warning'
                              ? 'bg-warning'
                              : 'bg-danger'
                        )}
                        style={{ width: `${driver.value}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {delta !== null && (
        <div className="mt-4 pt-4 border-t border-white/10">
          <span
            className={cn(
              'text-sm',
              delta > 0 ? 'text-success' : delta < 0 ? 'text-danger' : 'text-text-muted'
            )}
          >
            {delta > 0 ? '+' : ''}
            {delta} points from yesterday
          </span>
        </div>
      )}
    </div>
  );
}

export default EmqScoreCard;
