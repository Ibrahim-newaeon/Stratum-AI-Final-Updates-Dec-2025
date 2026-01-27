/**
 * Autopilot Mode Banner
 * Displays current autopilot mode with explanation of allowed actions
 */

import { cn } from '@/lib/utils';
import {
  ExclamationTriangleIcon,
  PauseCircleIcon,
  PlayCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

export type AutopilotMode = 'normal' | 'limited' | 'cuts_only' | 'frozen';

interface AutopilotModeBannerProps {
  mode: AutopilotMode;
  showDescription?: boolean;
  compact?: boolean;
  className?: string;
}

const modeConfig: Record<
  AutopilotMode,
  {
    label: string;
    icon: typeof PlayCircleIcon;
    color: string;
    bgColor: string;
    borderColor: string;
    description: string;
    allowedActions: string[];
  }
> = {
  normal: {
    label: 'Normal',
    icon: PlayCircleIcon,
    color: 'text-success',
    bgColor: 'bg-success/5',
    borderColor: 'border-success/20',
    description: 'Full automation enabled',
    allowedActions: [
      'Scale budgets up/down',
      'Pause/activate campaigns',
      'Apply all recommendations',
    ],
  },
  limited: {
    label: 'Limited',
    icon: PauseCircleIcon,
    color: 'text-warning',
    bgColor: 'bg-warning/5',
    borderColor: 'border-warning/20',
    description: 'Scaling capped at +10%',
    allowedActions: [
      'Scale budgets up to +10%',
      'Pause underperforming',
      'Review before major changes',
    ],
  },
  cuts_only: {
    label: 'Cuts Only',
    icon: ExclamationTriangleIcon,
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/5',
    borderColor: 'border-orange-500/20',
    description: 'Only pauses and reductions allowed',
    allowedActions: ['Pause campaigns', 'Reduce budgets', 'No increases allowed'],
  },
  frozen: {
    label: 'Frozen',
    icon: XCircleIcon,
    color: 'text-danger',
    bgColor: 'bg-danger/5',
    borderColor: 'border-danger/20',
    description: 'All automation paused',
    allowedActions: ['No actions allowed', 'Focus on fixing data issues', 'Manual control only'],
  },
};

export function AutopilotModeBanner({
  mode,
  showDescription = true,
  compact = false,
  className,
}: AutopilotModeBannerProps) {
  const config = modeConfig[mode];
  const Icon = config.icon;

  if (compact) {
    return (
      <div
        className={cn(
          'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border',
          config.bgColor,
          config.borderColor,
          className
        )}
      >
        <Icon className={cn('w-4 h-4', config.color)} />
        <span className={cn('text-sm font-medium', config.color)}>{config.label}</span>
      </div>
    );
  }

  return (
    <div className={cn('rounded-xl border p-4', config.bgColor, config.borderColor, className)}>
      <div className="flex items-start gap-3">
        <div className={cn('p-2 rounded-lg', config.bgColor)}>
          <Icon className={cn('w-5 h-5', config.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className={cn('font-semibold', config.color)}>Autopilot: {config.label}</h4>
          </div>
          {showDescription && (
            <>
              <p className="text-sm text-text-secondary mt-1">{config.description}</p>
              <div className="mt-3 space-y-1">
                {config.allowedActions.map((action, index) => (
                  <div key={index} className="flex items-center gap-2 text-sm text-text-muted">
                    <span
                      className={cn(
                        'w-1 h-1 rounded-full',
                        mode === 'normal'
                          ? 'bg-success'
                          : mode === 'frozen'
                            ? 'bg-danger'
                            : 'bg-warning'
                      )}
                    />
                    {action}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default AutopilotModeBanner;
