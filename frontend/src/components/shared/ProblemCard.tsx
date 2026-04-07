/**
 * ProblemCard - Color-coded problem display card
 *
 * Used in KG Problem Detection view to show detected issues
 * with severity indicator, impact badge, and action buttons.
 */

import { cn } from '@/lib/utils';
import {
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

export type ProblemSeverity = 'critical' | 'warning' | 'info';

interface ProblemCardProps {
  severity: ProblemSeverity;
  title: string;
  description: string;
  impact: string;
  affectedCampaigns: number;
  platform: string;
  onResolve?: () => void;
  onReview?: () => void;
  resolved?: boolean;
}

const severityConfig = {
  critical: {
    borderColor: 'border-l-red-500',
    bgColor: 'bg-red-500/5',
    iconColor: 'text-red-500',
    badgeColor: 'bg-red-500/10 text-red-500 border-red-500/20',
    Icon: ExclamationCircleIcon,
    label: 'Critical',
  },
  warning: {
    borderColor: 'border-l-amber-500',
    bgColor: 'bg-amber-500/5',
    iconColor: 'text-amber-500',
    badgeColor: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
    Icon: ExclamationTriangleIcon,
    label: 'Warning',
  },
  info: {
    borderColor: 'border-l-blue-500',
    bgColor: 'bg-blue-500/5',
    iconColor: 'text-blue-500',
    badgeColor: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    Icon: InformationCircleIcon,
    label: 'Info',
  },
};

export function ProblemCard({
  severity,
  title,
  description,
  impact,
  affectedCampaigns,
  platform,
  onResolve,
  onReview,
  resolved,
}: ProblemCardProps) {
  const config = severityConfig[severity];
  const Icon = config.Icon;

  return (
    <div
      className={cn(
        'rounded-xl border border-l-4 p-5 transition-all',
        config.borderColor,
        config.bgColor,
        resolved && 'opacity-60'
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 flex-1">
          <Icon className={cn('h-6 w-6 mt-0.5 flex-shrink-0', config.iconColor)} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold">{title}</h3>
              <span
                className={cn(
                  'px-2 py-0.5 rounded-full text-xs font-medium border',
                  config.badgeColor
                )}
              >
                {config.label}
              </span>
              {resolved && (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-500 border border-green-500/20 flex items-center gap-1">
                  <CheckCircleIcon className="h-3 w-3" />
                  Resolved
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground mb-3">{description}</p>
            <div className="flex items-center gap-4 text-sm">
              <span className="font-medium text-red-400">{impact} impact</span>
              <span className="text-muted-foreground">
                {affectedCampaigns} campaign{affectedCampaigns !== 1 ? 's' : ''} affected
              </span>
              <span className="px-2 py-0.5 rounded bg-white/5 text-xs">{platform}</span>
            </div>
          </div>
        </div>

        {!resolved && (
          <div className="flex items-center gap-2 flex-shrink-0">
            {severity === 'critical' && onResolve && (
              <button
                onClick={onResolve}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors"
              >
                Resolve
              </button>
            )}
            {onReview && (
              <button
                onClick={onReview}
                className="px-4 py-2 text-sm font-medium rounded-lg border border-white/10 hover:bg-white/5 transition-colors"
              >
                Review
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ProblemCard;
