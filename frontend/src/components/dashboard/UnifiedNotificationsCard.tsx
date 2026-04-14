import { useState } from 'react';
import {
  Bell,
  ChevronDown,
  ChevronUp,
  X,
  AlertTriangle,
  CheckCircle,
  Info,
  XCircle,
  Zap,
  ArrowRight,
  Activity,
  BarChart3,
  Globe,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useUnifiedNotifications } from '@/api/dashboard';
import type { PrioritizedNotification, NotificationGroup } from '@/api/dashboard';

const priorityConfig = {
  critical: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', dot: 'bg-red-500' },
  high: { color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200', dot: 'bg-orange-500' },
  medium: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-amber-500' },
  low: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', dot: 'bg-blue-500' },
};

const typeIcons = {
  error: XCircle,
  warning: AlertTriangle,
  success: CheckCircle,
  info: Info,
  alert: AlertTriangle,
};

const sourceIcons = {
  campaign: BarChart3,
  signal_health: Activity,
  system: Shield,
  pacing: Zap,
  anomaly: AlertTriangle,
  trust_gate: Shield,
  churn: AlertTriangle,
};

function PriorityBadge({ score, label }: { score: number; label: string }) {
  const config = priorityConfig[label as keyof typeof priorityConfig] || priorityConfig.low;
  return (
    <div className={cn('flex items-center gap-1.5 px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider', config.bg, config.color)}>
      <span className={cn('w-1.5 h-1.5 rounded-full', config.dot)} />
      {label} ({Math.round(score)})
    </div>
  );
}

function NotificationRow({ notification }: { notification: PrioritizedNotification }) {
  const [expanded, setExpanded] = useState(false);
  const config = priorityConfig[notification.priority_label] || priorityConfig.low;
  const TypeIcon = typeIcons[notification.notification_type] || Info;
  const SourceIcon = sourceIcons[notification.source] || Info;

  return (
    <div className={cn('rounded-lg border transition-all', config.border, expanded ? config.bg + '/30' : 'bg-background')}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-start gap-3 text-left"
      >
        <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5', config.bg)}>
          <TypeIcon className={cn('w-3.5 h-3.5', config.color)} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground truncate">{notification.title}</span>
            <PriorityBadge score={notification.priority_score} label={notification.priority_label} />
          </div>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{notification.message}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 mt-1">
          <SourceIcon className="w-3 h-3 text-muted-foreground" />
          {expanded ? <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-inherit ml-10">
          <p className="text-xs text-muted-foreground leading-relaxed pt-2">{notification.message}</p>
          <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
            <span>Urgency: {Math.round(notification.urgency)}</span>
            <span>Impact: {Math.round(notification.impact)}</span>
            <span>Actionability: {Math.round(notification.actionability)}</span>
            <span className="capitalize">{notification.source.replace('_', ' ')}</span>
          </div>
          {notification.suggested_action && (
            <div className={cn('flex items-center gap-2 p-2 rounded-lg border', config.border, config.bg + '/50')}>
              <ArrowRight className={cn('w-3.5 h-3.5 flex-shrink-0', config.color)} />
              <div className="flex-1">
                <span className={cn('text-xs font-semibold', config.color)}>{notification.suggested_action.label}</span>
                {notification.suggested_action.description && (
                  <span className="text-[10px] text-muted-foreground ml-1">— {notification.suggested_action.description}</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function GroupSection({ group }: { group: NotificationGroup }) {
  const [expanded, setExpanded] = useState(group.top_priority >= 50);

  return (
    <div className="border-t">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{group.label}</span>
          <span className="text-[10px] font-medium text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded">
            {group.count}
          </span>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
      </button>
      {expanded && (
        <div className="px-6 pb-4 space-y-2">
          {group.notifications.map((n) => (
            <NotificationRow key={n.id} notification={n} />
          ))}
        </div>
      )}
    </div>
  );
}

export function UnifiedNotificationsCard() {
  const { data, isLoading, error } = useUnifiedNotifications();
  const [dismissed, setDismissed] = useState(false);
  const [viewMode, setViewMode] = useState<'priority' | 'grouped'>('priority');

  if (dismissed || isLoading || error || !data) return null;
  if (data.total_count === 0) return null;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="relative w-10 h-10 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Bell className="w-5 h-5 text-blue-500" />
            {data.unread_count > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
                {data.unread_count > 9 ? '9+' : data.unread_count}
              </span>
            )}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
                Notifications
              </h2>
              <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-200 flex items-center gap-1">
                <Zap className="w-3 h-3" />AI-PRIORITIZED
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {data.summary}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* View mode toggle */}
          <div className="flex items-center bg-muted/30 rounded-lg p-0.5 border">
            <button
              onClick={() => setViewMode('priority')}
              className={cn('text-[10px] font-semibold px-2.5 py-1 rounded-md transition-colors',
                viewMode === 'priority' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              Priority
            </button>
            <button
              onClick={() => setViewMode('grouped')}
              className={cn('text-[10px] font-semibold px-2.5 py-1 rounded-md transition-colors',
                viewMode === 'grouped' ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              Grouped
            </button>
          </div>
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
        <div className="flex items-center gap-4 text-xs">
          {data.critical_count > 0 && (
            <span className="flex items-center gap-1.5 text-red-600 font-semibold">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              {data.critical_count} critical
            </span>
          )}
          {data.high_count > 0 && (
            <span className="flex items-center gap-1.5 text-orange-600 font-semibold">
              <span className="w-2 h-2 rounded-full bg-orange-500" />
              {data.high_count} high
            </span>
          )}
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Globe className="w-3.5 h-3.5" />
            {data.total_count} total
          </span>
          {data.unread_count > 0 && (
            <span className="flex items-center gap-1.5 text-blue-600 font-semibold">
              <Bell className="w-3.5 h-3.5" />
              {data.unread_count} unread
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      {viewMode === 'priority' ? (
        <div className="border-t">
          <div className="px-6 py-3">
            <span className="text-sm font-semibold text-foreground">All Notifications</span>
          </div>
          <div className="px-6 pb-4 space-y-2">
            {data.notifications.map((n) => (
              <NotificationRow key={n.id} notification={n} />
            ))}
          </div>
        </div>
      ) : (
        data.groups.map((group) => (
          <GroupSection key={group.category} group={group} />
        ))
      )}
    </div>
  );
}
