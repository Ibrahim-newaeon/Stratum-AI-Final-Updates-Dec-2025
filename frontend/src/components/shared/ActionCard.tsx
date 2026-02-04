/**
 * Action Card
 * Individual action with confidence level, platform info, and apply/dismiss controls
 */

import { cn } from '@/lib/utils';
import { ConfidenceBandBadge } from './ConfidenceBandBadge';
import {
  ArrowTrendingUpIcon,
  CheckIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  SparklesIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

export type ActionType = 'opportunity' | 'risk' | 'recommendation' | 'fix';
export type ActionStatus = 'pending' | 'queued' | 'applied' | 'dismissed';

export interface Action {
  id: string;
  type: ActionType;
  title: string;
  description: string;
  platform?: string;
  campaign?: string;
  confidence: number; // 0-100
  estimatedImpact: {
    metric: string;
    value: number;
    unit: string;
  };
  status: ActionStatus;
  priority: number;
  createdAt: Date;
}

interface ActionCardProps {
  action: Action;
  onApply?: (action: Action) => void;
  onDismiss?: (action: Action) => void;
  onQueue?: (action: Action) => void;
  disabled?: boolean;
  showControls?: boolean;
  compact?: boolean;
  className?: string;
}

const typeConfig: Record<
  ActionType,
  {
    icon: typeof SparklesIcon;
    color: string;
    bgColor: string;
    label: string;
  }
> = {
  opportunity: {
    icon: ArrowTrendingUpIcon,
    color: 'text-success',
    bgColor: 'bg-success/10',
    label: 'Opportunity',
  },
  risk: {
    icon: ExclamationTriangleIcon,
    color: 'text-danger',
    bgColor: 'bg-danger/10',
    label: 'Risk',
  },
  recommendation: {
    icon: SparklesIcon,
    color: 'text-stratum-400',
    bgColor: 'bg-stratum-500/10',
    label: 'AI Recommendation',
  },
  fix: {
    icon: ExclamationTriangleIcon,
    color: 'text-warning',
    bgColor: 'bg-warning/10',
    label: 'Fix Required',
  },
};

const statusConfig: Record<ActionStatus, { label: string; color: string }> = {
  pending: { label: 'Pending', color: 'text-text-muted' },
  queued: { label: 'Queued', color: 'text-warning' },
  applied: { label: 'Applied', color: 'text-success' },
  dismissed: { label: 'Dismissed', color: 'text-text-muted' },
};

export function ActionCard({
  action,
  onApply,
  onDismiss,
  onQueue,
  disabled = false,
  showControls = true,
  compact = false,
  className,
}: ActionCardProps) {
  const config = typeConfig[action.type];
  const Icon = config.icon;
  const status = statusConfig[action.status];
  const isActionable = action.status === 'pending' && !disabled;

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-3 p-3 rounded-xl bg-surface-secondary border border-white/10',
          className
        )}
      >
        <div className={cn('p-2 rounded-lg', config.bgColor)}>
          <Icon className={cn('w-4 h-4', config.color)} />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-white truncate">{action.title}</h4>
          <div className="flex items-center gap-2 mt-0.5">
            {action.platform && <span className="text-xs text-text-muted">{action.platform}</span>}
            <ConfidenceBandBadge score={action.confidence} size="sm" showLabel={false} />
          </div>
        </div>
        {showControls && isActionable && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => onApply?.(action)}
              className="p-1.5 rounded-lg bg-success/10 text-success hover:bg-success/20 transition-colors"
            >
              <CheckIcon className="w-4 h-4" />
            </button>
            <button
              onClick={() => onDismiss?.(action)}
              className="p-1.5 rounded-lg bg-surface-tertiary text-text-muted hover:text-white transition-colors"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'rounded-xl bg-surface-secondary border border-white/10 overflow-hidden transition-all',
        isActionable && 'hover:border-white/20',
        className
      )}
    >
      <div className="p-4">
        <div className="flex items-start gap-4">
          {/* Icon */}
          <div className={cn('p-2.5 rounded-xl', config.bgColor)}>
            <Icon className={cn('w-5 h-5', config.color)} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <span className={cn('text-xs font-medium', config.color)}>{config.label}</span>
                  {action.status !== 'pending' && (
                    <span className={cn('text-xs', status.color)}>({status.label})</span>
                  )}
                </div>
                <h4 className="font-medium text-white mt-1">{action.title}</h4>
                <p className="text-sm text-text-muted mt-1">{action.description}</p>
              </div>
              <ConfidenceBandBadge score={action.confidence} size="sm" />
            </div>

            {/* Meta row */}
            <div className="flex items-center gap-4 mt-3">
              {action.platform && (
                <span className="text-xs bg-surface-tertiary text-text-muted px-2 py-0.5 rounded">
                  {action.platform}
                </span>
              )}
              {action.campaign && (
                <span className="text-xs text-text-muted truncate max-w-[150px]">
                  {action.campaign}
                </span>
              )}
              <div className="flex items-center gap-1 text-xs">
                <span
                  className={cn(action.estimatedImpact.value > 0 ? 'text-success' : 'text-danger')}
                >
                  {action.estimatedImpact.value > 0 ? '+' : ''}
                  {action.estimatedImpact.value}
                  {action.estimatedImpact.unit}
                </span>
                <span className="text-text-muted">{action.estimatedImpact.metric}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      {showControls && isActionable && (
        <div className="flex items-center gap-2 px-4 py-3 border-t border-white/10 bg-white/[0.02]">
          <button
            onClick={() => onApply?.(action)}
            className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-success/10 text-success hover:bg-success/20 transition-colors text-sm font-medium"
          >
            <CheckIcon className="w-4 h-4" />
            Apply
          </button>
          <button
            onClick={() => onQueue?.(action)}
            className="flex items-center justify-center gap-2 py-2 px-4 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white transition-colors text-sm"
          >
            <ClockIcon className="w-4 h-4" />
            Queue
          </button>
          <button
            onClick={() => onDismiss?.(action)}
            className="flex items-center justify-center gap-2 py-2 px-4 rounded-lg text-text-muted hover:text-white transition-colors text-sm"
          >
            <XMarkIcon className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

export default ActionCard;
