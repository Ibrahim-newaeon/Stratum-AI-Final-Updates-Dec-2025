/**
 * AnomalyFeedCard - Dismissable anomaly/alert feed
 */

import { useState } from 'react';
import { AlertTriangle, CheckCircle2, Info, Loader2, X, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePacingAlerts, type PacingAlert, type AlertSeverity } from '@/api/pacing';

interface AnomalyItem {
  id: string;
  severity: AlertSeverity;
  title: string;
  description: string;
  platform?: string;
  metric?: string;
  timestamp: string;
}

const FALLBACK_ANOMALIES: AnomalyItem[] = [
  {
    id: 'a-1',
    severity: 'critical',
    title: 'CPA Spike Detected',
    description: 'Meta prospecting CPA jumped 42% in the last 6 hours',
    platform: 'meta',
    metric: 'CPA: $38.50 (+42%)',
    timestamp: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    id: 'a-2',
    severity: 'warning',
    title: 'Google Spend Underpacing',
    description: 'Google Ads spend is 15% behind daily target',
    platform: 'google',
    metric: 'Daily: $520 / $600 target',
    timestamp: new Date(Date.now() - 5400000).toISOString(),
  },
  {
    id: 'a-3',
    severity: 'info',
    title: 'TikTok ROAS Improving',
    description: 'TikTok brand campaign ROAS up 18% week-over-week',
    platform: 'tiktok',
    metric: 'ROAS: 3.2x (+18%)',
    timestamp: new Date(Date.now() - 10800000).toISOString(),
  },
  {
    id: 'a-4',
    severity: 'warning',
    title: 'Event Match Quality Dropping',
    description: 'EMQ score decreased from 82 to 71 in the past 24 hours',
    platform: 'meta',
    metric: 'EMQ: 71 (-13%)',
    timestamp: new Date(Date.now() - 18000000).toISOString(),
  },
];

function mapAlertsToAnomalies(alerts: PacingAlert[]): AnomalyItem[] {
  return alerts.map((a) => ({
    id: a.id,
    severity: a.severity,
    title: a.alertType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    description: a.message,
    platform: a.target?.platform ?? undefined,
    metric: `Deviation: ${a.deviationPct > 0 ? '+' : ''}${a.deviationPct.toFixed(1)}%`,
    timestamp: a.triggeredAt,
  }));
}

const SEVERITY_CONFIG: Record<AlertSeverity, { icon: React.ElementType; cls: string }> = {
  critical: { icon: XCircle, cls: 'text-red-500 bg-red-500/10' },
  warning: { icon: AlertTriangle, cls: 'text-amber-500 bg-amber-500/10' },
  info: { icon: Info, cls: 'text-blue-500 bg-blue-500/10' },
};

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function AnomalyFeedCard() {
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const { data: alerts, isLoading } = usePacingAlerts({ status: 'active' });

  const anomalies: AnomalyItem[] =
    alerts && alerts.length > 0 ? mapAlertsToAnomalies(alerts) : FALLBACK_ANOMALIES;

  const visible = anomalies.filter((a) => !dismissed.has(a.id));

  const dismiss = (id: string) => {
    setDismissed((prev) => new Set(prev).add(id));
  };

  const dismissAll = () => {
    setDismissed(new Set(anomalies.map((a) => a.id)));
  };

  if (isLoading) {
    return (
      <div className="widget-card flex items-center justify-center min-h-[12.5rem]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="widget-card h-full flex flex-col">
      <div className="widget-header">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-amber-500/10">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          </div>
          <h3 className="widget-title">
            Anomaly Feed
          </h3>
        </div>
        {visible.length > 0 && (
          <button
            onClick={dismissAll}
            aria-label="Dismiss all anomalies"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Dismiss All
          </button>
        )}
      </div>

      {visible.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <CheckCircle2 className="w-10 h-10 text-emerald-500/50 mb-3" />
          <p className="text-sm font-medium text-muted-foreground">No active anomalies</p>
          <p className="text-xs text-muted-foreground mt-1">All signals are operating within normal parameters</p>
        </div>
      ) : (
        <div className="flex-1 space-y-2 overflow-y-auto max-h-[25rem] scrollbar-hide">
          {visible.map((item) => {
            const cfg = SEVERITY_CONFIG[item.severity];
            const Icon = cfg.icon;
            return (
              <div
                key={item.id}
                className="flex items-start gap-3 p-3 rounded-xl bg-foreground/[0.02] hover:bg-foreground/[0.05] transition-colors duration-200"
              >
                <div className={cn('shrink-0 p-1.5 rounded-md', cfg.cls)}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium">{item.title}</p>
                    <button
                      onClick={() => dismiss(item.id)}
                      aria-label="Dismiss anomaly"
                      className="shrink-0 p-1 rounded hover:bg-muted transition-colors"
                    >
                      <X className="w-3.5 h-3.5 text-muted-foreground" />
                    </button>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                  <div className="flex items-center gap-3 mt-1.5">
                    {item.platform && (
                      <span className="text-[11px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground capitalize">
                        {item.platform}
                      </span>
                    )}
                    {item.metric && (
                      <span className="text-[11px] text-muted-foreground font-mono">{item.metric}</span>
                    )}
                    <span className="text-[11px] text-muted-foreground ml-auto">
                      {formatRelativeTime(item.timestamp)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
