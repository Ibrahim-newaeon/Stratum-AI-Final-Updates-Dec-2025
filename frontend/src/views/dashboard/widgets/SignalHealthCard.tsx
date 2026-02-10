/**
 * SignalHealthCard - Signal health summary display
 */

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  Server,
  XCircle,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SignalHealthSummary } from '@/api/dashboard';

interface SignalHealthCardProps {
  signalHealth?: SignalHealthSummary;
  loading?: boolean;
}

export function SignalHealthCard({ signalHealth, loading = false }: SignalHealthCardProps) {
  if (loading) {
    return (
      <div className="glass border border-white/10 rounded-xl p-5 h-full flex items-center justify-center min-h-[200px]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!signalHealth) {
    return (
      <div className="glass border border-white/10 rounded-xl p-5 h-full">
        <div className="text-center text-muted-foreground py-8">
          <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No signal health data available</p>
        </div>
      </div>
    );
  }

  const getStatusConfig = (status: SignalHealthSummary['status']) => {
    switch (status) {
      case 'healthy':
        return {
          color: 'text-[#00c7be]',
          bgColor: 'bg-[#00c7be]/10',
          icon: CheckCircle2,
          label: 'Healthy',
        };
      case 'degraded':
        return {
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-500/10',
          icon: AlertTriangle,
          label: 'Degraded',
        };
      case 'critical':
        return {
          color: 'text-[#ff6b6b]',
          bgColor: 'bg-[#ff6b6b]/10',
          icon: XCircle,
          label: 'Critical',
        };
      default:
        return {
          color: 'text-muted-foreground',
          bgColor: 'bg-muted',
          icon: Activity,
          label: 'Unknown',
        };
    }
  };

  const statusConfig = getStatusConfig(signalHealth.status);
  const StatusIcon = statusConfig.icon;

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-[#00c7be]';
    if (score >= 40) return 'text-yellow-500';
    return 'text-[#ff6b6b]';
  };

  const formatFreshness = (minutes: number | null) => {
    if (minutes === null) return 'Unknown';
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  return (
    <div className="glass border border-white/10 rounded-xl p-5 h-full card-3d">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Signal Health</h3>
        <div
          className={cn(
            'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ai-chip',
            statusConfig.bgColor,
            statusConfig.color
          )}
        >
          <div
            className={cn(
              'w-1.5 h-1.5 rounded-full',
              signalHealth.status === 'healthy' && 'dot-healthy',
              signalHealth.status === 'degraded' && 'dot-degraded',
              signalHealth.status === 'critical' && 'dot-critical'
            )}
          />
          <StatusIcon className="w-3.5 h-3.5" />
          {statusConfig.label}
        </div>
      </div>

      {/* Score Display */}
      <div className="text-center mb-4">
        <div className={cn('text-4xl font-bold', getScoreColor(signalHealth.overall_score))}>
          {signalHealth.overall_score}
        </div>
        <div className="text-xs text-muted-foreground mt-1">Overall Score</div>
        {/* Progress bar */}
        <div className="h-1.5 rounded-full bg-white/10 overflow-hidden mt-2">
          <div
            className={cn(
              'h-full rounded-full transition-all duration-500',
              signalHealth.overall_score >= 70
                ? 'bg-gradient-to-r from-[#00c7be] to-[#34c759]'
                : signalHealth.overall_score >= 40
                  ? 'bg-gradient-to-r from-yellow-500 to-amber-400'
                  : 'bg-gradient-to-r from-[#ff6b6b] to-[#ff8a8a]'
            )}
            style={{ width: `${signalHealth.overall_score}%` }}
          />
        </div>
      </div>

      {/* Metrics */}
      <div className="space-y-3">
        {signalHealth.emq_score !== null && (
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Activity className="w-4 h-4" />
              <span>EMQ Score</span>
            </div>
            <span className={cn('font-medium', getScoreColor(signalHealth.emq_score))}>
              {signalHealth.emq_score}
            </span>
          </div>
        )}

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span>Data Freshness</span>
          </div>
          <span className="font-medium">
            {formatFreshness(signalHealth.data_freshness_minutes)}
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Server className="w-4 h-4" />
            <span>API Health</span>
          </div>
          <span
            className={cn(
              'font-medium',
              signalHealth.api_health ? 'text-[#00c7be]' : 'text-[#ff6b6b]'
            )}
          >
            {signalHealth.api_health ? 'Online' : 'Offline'}
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Zap className="w-4 h-4" />
            <span>Autopilot</span>
          </div>
          <span
            className={cn(
              'font-medium',
              signalHealth.autopilot_enabled ? 'text-[#00c7be]' : 'text-muted-foreground'
            )}
          >
            {signalHealth.autopilot_enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
      </div>

      {/* Issues */}
      {signalHealth.issues.length > 0 && (
        <div className="mt-4 pt-4 border-t">
          <div className="text-xs font-medium text-muted-foreground mb-2">Issues</div>
          <ul className="space-y-1">
            {signalHealth.issues.slice(0, 3).map((issue, index) => (
              <li key={index} className="text-xs text-yellow-600 flex items-start gap-2">
                <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                <span>{issue}</span>
              </li>
            ))}
            {signalHealth.issues.length > 3 && (
              <li className="text-xs text-muted-foreground">
                +{signalHealth.issues.length - 3} more issues
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
