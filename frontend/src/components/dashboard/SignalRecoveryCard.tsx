import { useState } from 'react';
import {
  Wifi,
  WifiOff,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  Shield,
  Activity,
  ArrowRight,
  Radio,
  Loader2,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSignalRecovery, useSyncPlatform } from '@/api/dashboard';
import type { SignalIssue, RecoveryAction, RecoveryTimeline } from '@/api/dashboard';

const statusConfig = {
  healthy: {
    color: 'text-emerald-600',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    icon: CheckCircle,
    label: 'All Signals Healthy',
    pulse: false,
  },
  recovering: {
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: RefreshCw,
    label: 'Recovering',
    pulse: true,
  },
  degraded: {
    color: 'text-amber-600',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: AlertTriangle,
    label: 'Degraded',
    pulse: true,
  },
  critical: {
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: WifiOff,
    label: 'Critical',
    pulse: true,
  },
};

const severityColors = {
  critical: { text: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', dot: 'bg-red-500' },
  high: { text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-amber-500' },
  medium: { text: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', dot: 'bg-blue-500' },
  low: { text: 'text-muted-foreground', bg: 'bg-muted/30', border: 'border-border', dot: 'bg-slate-400' },
};

const priorityConfig = {
  urgent: { label: 'URGENT', color: 'text-red-600 bg-red-50' },
  high: { label: 'HIGH', color: 'text-amber-600 bg-amber-50' },
  normal: { label: 'NORMAL', color: 'text-muted-foreground bg-muted/30' },
};

const actionTypeIcons = {
  resync: RefreshCw,
  diagnostics: Activity,
  check_capi: Radio,
  check_pixel: Zap,
  alert_team: AlertTriangle,
  expand_params: Shield,
};

function IssueCard({ issue }: { issue: SignalIssue }) {
  const sev = severityColors[issue.severity] || severityColors.medium;

  return (
    <div className={cn('rounded-lg border p-3', sev.border, sev.bg)}>
      <div className="flex items-start gap-2.5">
        <div className={cn('w-2 h-2 rounded-full mt-1.5 flex-shrink-0', sev.dot)} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={cn('text-sm font-semibold', sev.text)}>{issue.title}</span>
            <span className={cn('text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded', sev.bg, sev.text)}>
              {issue.severity}
            </span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">{issue.description}</p>
          {issue.metric_value !== null && issue.threshold !== null && (
            <div className="flex items-center gap-3 mt-1.5">
              <span className={cn('text-xs font-bold', sev.text)}>
                Current: {issue.metric_value.toFixed(1)}
              </span>
              <span className="text-[10px] text-muted-foreground">
                Threshold: {issue.threshold.toFixed(1)}
              </span>
            </div>
          )}
          {issue.affected_platforms.length > 0 && (
            <div className="flex items-center gap-1.5 mt-1.5">
              {issue.affected_platforms.map((p) => (
                <span key={p} className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground bg-white/60 px-2 py-0.5 rounded border">
                  {p}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ActionCard({ action, onTrigger }: { action: RecoveryAction; onTrigger?: () => void }) {
  const Icon = actionTypeIcons[action.type] || Activity;
  const priority = priorityConfig[action.priority] || priorityConfig.normal;

  const statusBadge = {
    pending: { label: 'Pending', color: 'text-muted-foreground bg-muted/30 border-border' },
    in_progress: { label: 'In Progress', color: 'text-blue-600 bg-blue-50 border-blue-200' },
    completed: { label: 'Done', color: 'text-emerald-600 bg-emerald-50 border-emerald-200' },
    failed: { label: 'Failed', color: 'text-red-600 bg-red-50 border-red-200' },
  }[action.status];

  return (
    <div className="rounded-lg border bg-background p-3">
      <div className="flex items-start gap-2.5">
        <div className={cn(
          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
          action.auto_triggered ? 'bg-blue-50' : 'bg-muted/30'
        )}>
          {action.status === 'in_progress' ? (
            <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
          ) : (
            <Icon className={cn('w-4 h-4', action.auto_triggered ? 'text-blue-500' : 'text-muted-foreground')} />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-semibold text-foreground">{action.title}</span>
            <span className={cn('text-[9px] font-bold uppercase tracking-wider px-1 py-0.5 rounded', priority.color)}>
              {priority.label}
            </span>
            <span className={cn('text-[9px] font-bold uppercase tracking-wider px-1 py-0.5 rounded border', statusBadge.color)}>
              {statusBadge.label}
            </span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">{action.description}</p>
          <div className="flex items-center gap-3 mt-1.5">
            {action.auto_triggered && (
              <span className="text-[10px] font-semibold text-blue-600">
                <Zap className="w-3 h-3 inline mr-0.5" />Auto-triggered
              </span>
            )}
            {action.estimated_minutes && (
              <span className="text-[10px] text-muted-foreground">
                <Clock className="w-3 h-3 inline mr-0.5" />~{action.estimated_minutes}min
              </span>
            )}
            {action.status === 'pending' && action.type === 'resync' && onTrigger && (
              <button
                onClick={onTrigger}
                className="text-[10px] font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-0.5"
              >
                <ArrowRight className="w-3 h-3" />Execute now
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function TimelineEntry({ entry }: { entry: RecoveryTimeline }) {
  const typeConfig = {
    detection: { icon: AlertTriangle, color: 'text-red-500' },
    action: { icon: Zap, color: 'text-blue-500' },
    progress: { icon: ArrowRight, color: 'text-amber-500' },
    resolution: { icon: CheckCircle, color: 'text-emerald-500' },
  }[entry.type] || { icon: Activity, color: 'text-muted-foreground' };

  const Icon = typeConfig.icon;

  return (
    <div className="flex items-start gap-2.5 py-1.5">
      <Icon className={cn('w-3.5 h-3.5 mt-0.5 flex-shrink-0', typeConfig.color)} />
      <div className="min-w-0">
        <span className="text-xs text-foreground font-medium">{entry.event}</span>
        {entry.details && (
          <span className="text-[10px] text-muted-foreground ml-2">{entry.details}</span>
        )}
      </div>
    </div>
  );
}

function HealthScoreRing({ score, status }: { score: number; status: string }) {
  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.healthy;
  const circumference = 2 * Math.PI * 20;
  const progress = (score / 100) * circumference;

  return (
    <div className="relative w-14 h-14 flex-shrink-0">
      <svg className="w-14 h-14 -rotate-90" viewBox="0 0 48 48">
        <circle cx="24" cy="24" r="20" fill="none" stroke="currentColor" strokeWidth="3"
          className="text-muted/20" />
        <circle cx="24" cy="24" r="20" fill="none" strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - progress}
          strokeLinecap="round"
          className={config.color}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={cn('text-sm font-bold', config.color)}>{score}</span>
      </div>
    </div>
  );
}

export function SignalRecoveryCard() {
  const { data, isLoading, error } = useSignalRecovery();
  const syncPlatform = useSyncPlatform();
  const [dismissed, setDismissed] = useState(false);
  const [showDetails, setShowDetails] = useState(true);
  const [showTimeline, setShowTimeline] = useState(false);

  if (dismissed || isLoading || error || !data) return null;
  if (data.status === 'healthy' && !data.has_active_recovery) return null;

  const config = statusConfig[data.status] || statusConfig.healthy;
  const StatusIcon = config.icon;

  const handleResync = () => {
    if (data.platforms_affected.length > 0) {
      syncPlatform.mutate({ platform: data.platforms_affected[0], daysBack: 7 });
    }
  };

  return (
    <div className={cn('rounded-xl border bg-card shadow-sm overflow-hidden', config.border)}>
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className={cn(
            'w-10 h-10 rounded-lg border flex items-center justify-center flex-shrink-0 mt-0.5',
            config.bg, config.border
          )}>
            <StatusIcon className={cn('w-5 h-5', config.color, config.pulse && 'animate-pulse')} />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
                Signal Recovery
              </h2>
              <div className={cn(
                'flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border',
                config.bg, config.color, config.border
              )}>
                {config.pulse && <span className="relative flex h-2 w-2">
                  <span className={cn('animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', config.color.replace('text-', 'bg-'))} />
                  <span className={cn('relative inline-flex rounded-full h-2 w-2', config.color.replace('text-', 'bg-'))} />
                </span>}
                {config.label}
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {data.summary}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <HealthScoreRing score={data.overall_health_score} status={data.status} />
          <button
            onClick={() => setDismissed(true)}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="px-6 pb-4">
        <div className="flex items-center gap-6 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <AlertTriangle className="w-3.5 h-3.5" />
            {data.issues.length} issue{data.issues.length !== 1 ? 's' : ''} detected
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Activity className="w-3.5 h-3.5" />
            {data.recovery_actions.length} recovery action{data.recovery_actions.length !== 1 ? 's' : ''}
          </div>
          {data.recovery_actions.filter(a => a.auto_triggered).length > 0 && (
            <div className="flex items-center gap-1.5 text-blue-600 font-semibold">
              <Zap className="w-3.5 h-3.5" />
              {data.recovery_actions.filter(a => a.auto_triggered).length} auto-triggered
            </div>
          )}
          {data.estimated_recovery_minutes && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Clock className="w-3.5 h-3.5" />
              ~{data.estimated_recovery_minutes}min estimated
            </div>
          )}
          {data.platforms_affected.length > 0 && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Wifi className="w-3.5 h-3.5" />
              {data.platforms_affected.join(', ')}
            </div>
          )}
        </div>

        {/* Recovery progress bar */}
        {data.has_active_recovery && data.recovery_progress_pct < 100 && (
          <div className="mt-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Recovery Progress
              </span>
              <span className={cn('text-xs font-bold', config.color)}>
                {data.recovery_progress_pct}%
              </span>
            </div>
            <div className="w-full h-1.5 bg-muted/30 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-[width] duration-500', config.color.replace('text-', 'bg-'))}
                style={{ width: `${data.recovery_progress_pct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Issues & Actions */}
      {(data.issues.length > 0 || data.recovery_actions.length > 0) && (
        <div className="border-t">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
          >
            <span className="text-sm font-semibold text-foreground">
              Issues & Recovery Actions ({data.issues.length + data.recovery_actions.length})
            </span>
            {showDetails ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>
          {showDetails && (
            <div className="px-6 pb-4 space-y-4">
              {/* Issues */}
              {data.issues.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    Detected Issues
                  </span>
                  {data.issues.map((issue) => (
                    <IssueCard key={issue.id} issue={issue} />
                  ))}
                </div>
              )}

              {/* Recovery Actions */}
              {data.recovery_actions.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    Recovery Actions
                  </span>
                  {data.recovery_actions.map((action) => (
                    <ActionCard
                      key={action.id}
                      action={action}
                      onTrigger={action.type === 'resync' ? handleResync : undefined}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Timeline */}
      {data.timeline.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setShowTimeline(!showTimeline)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
          >
            <span className="text-sm font-semibold text-foreground">
              Recovery Timeline ({data.timeline.length})
            </span>
            {showTimeline ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>
          {showTimeline && (
            <div className="px-6 pb-4">
              <div className="pl-3 ml-1 space-y-0.5">
                {data.timeline.map((entry, i) => (
                  <TimelineEntry key={i} entry={entry} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
