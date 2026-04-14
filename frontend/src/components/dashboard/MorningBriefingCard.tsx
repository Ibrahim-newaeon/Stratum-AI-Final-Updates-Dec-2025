import { useState } from 'react';
import {
  Sun,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Shield,
  ChevronDown,
  ChevronUp,
  X,
  Zap,
  DollarSign,
  Target,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useMorningBriefing } from '@/api/dashboard';

function formatCurrency(value: number): string {
  if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`;
  return `$${value.toFixed(0)}`;
}

function formatNumber(value: number): string {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value.toFixed(0);
}

const healthConfig = {
  strong: { label: 'Strong', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', icon: CheckCircle },
  steady: { label: 'Steady', color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', icon: Activity },
  needs_attention: { label: 'Needs Attention', color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', icon: AlertTriangle },
  critical: { label: 'Critical', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: AlertTriangle },
};

const signalConfig = {
  healthy: { label: 'Healthy', color: 'text-emerald-600', bg: 'bg-emerald-50' },
  risk: { label: 'At Risk', color: 'text-amber-600', bg: 'bg-amber-50' },
  degraded: { label: 'Degraded', color: 'text-orange-600', bg: 'bg-orange-50' },
  critical: { label: 'Critical', color: 'text-red-600', bg: 'bg-red-50' },
};

const priorityConfig = {
  critical: { color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200', dot: 'bg-red-500' },
  high: { color: 'text-amber-700', bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-amber-500' },
  medium: { color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200', dot: 'bg-blue-500' },
};

const actionTypeIcons = {
  budget: DollarSign,
  creative: Zap,
  signal: Shield,
  campaign: Target,
};

export function MorningBriefingCard() {
  const { data: briefing, isLoading, error } = useMorningBriefing();
  const [dismissed, setDismissed] = useState(false);
  const [showChanges, setShowChanges] = useState(true);
  const [showActions, setShowActions] = useState(true);

  if (dismissed || isLoading || error || !briefing) return null;

  const health = healthConfig[briefing.portfolio_health] || healthConfig.steady;
  const signal = signalConfig[briefing.signal_status] || signalConfig.healthy;
  const HealthIcon = health.icon;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Sun className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
              {briefing.greeting}
            </h2>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {briefing.summary_narrative}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Portfolio health badge */}
          <div className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border', health.bg, health.color, health.border)}>
            <HealthIcon className="w-3.5 h-3.5" />
            {health.label}
          </div>
          <button
            onClick={() => setDismissed(true)}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
            aria-label="Dismiss briefing"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* KPI Mini Cards */}
      <div className="px-6 pb-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Revenue', value: formatCurrency(briefing.total_revenue), change: briefing.revenue_change_pct, icon: DollarSign },
            { label: 'Spend', value: formatCurrency(briefing.total_spend), change: briefing.spend_change_pct, icon: Target },
            { label: 'ROAS', value: `${briefing.roas.toFixed(2)}x`, change: briefing.roas_change_pct, icon: TrendingUp },
            { label: 'Conversions', value: formatNumber(briefing.total_conversions), change: null, icon: Zap },
          ].map((kpi) => (
            <div key={kpi.label} className="rounded-lg border bg-background p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{kpi.label}</span>
                <kpi.icon className="w-3.5 h-3.5 text-muted-foreground/50" />
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-lg font-bold text-foreground font-display">{kpi.value}</span>
                {kpi.change !== null && (
                  <span className={cn('flex items-center text-xs font-semibold', kpi.change >= 0 ? 'text-emerald-600' : 'text-red-500')}>
                    {kpi.change >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                    {Math.abs(kpi.change).toFixed(1)}%
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Signal Health + Stats Bar */}
      <div className="px-6 pb-4">
        <div className="flex items-center gap-6 text-xs">
          <div className="flex items-center gap-2">
            <Shield className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Signal:</span>
            <span className={cn('font-semibold px-2 py-0.5 rounded', signal.bg, signal.color)}>
              {signal.label} ({briefing.signal_score})
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Activity className="w-3.5 h-3.5" />
            {briefing.active_campaigns} active campaigns
          </div>
          {briefing.scale_candidates > 0 && (
            <div className="flex items-center gap-1.5 text-emerald-600 font-medium">
              <TrendingUp className="w-3.5 h-3.5" />
              {briefing.scale_candidates} ready to scale
            </div>
          )}
          {briefing.autopilot_enabled && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              Autopilot active
            </div>
          )}
        </div>
      </div>

      {/* Top Changes Section */}
      {briefing.top_changes.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setShowChanges(!showChanges)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
          >
            <span className="text-sm font-semibold text-foreground">
              Overnight Changes ({briefing.top_changes.length})
            </span>
            {showChanges ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>
          {showChanges && (
            <div className="px-6 pb-4 space-y-2">
              {briefing.top_changes.map((change, i) => {
                const isUp = change.direction === 'up';
                return (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30">
                    <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0', isUp ? 'bg-emerald-50' : 'bg-red-50')}>
                      {isUp ? <TrendingUp className="w-4 h-4 text-emerald-600" /> : <TrendingDown className="w-4 h-4 text-red-500" />}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-semibold text-foreground capitalize">{change.metric}</span>
                        <span className={cn('text-xs font-bold', isUp ? 'text-emerald-600' : 'text-red-500')}>
                          {isUp ? '+' : '-'}{change.change_percent.toFixed(1)}%
                        </span>
                        {change.severity === 'critical' && (
                          <span className="text-[10px] font-bold uppercase tracking-wider text-red-600 bg-red-50 px-1.5 py-0.5 rounded">Critical</span>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{change.narrative}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Actions Today Section */}
      {briefing.actions_today.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setShowActions(!showActions)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
          >
            <span className="text-sm font-semibold text-foreground">
              Actions Today ({briefing.actions_today.length})
            </span>
            {showActions ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>
          {showActions && (
            <div className="px-6 pb-4 space-y-2">
              {briefing.actions_today.map((action, i) => {
                const pConfig = priorityConfig[action.priority] || priorityConfig.medium;
                const ActionIcon = actionTypeIcons[action.action_type] || Target;
                return (
                  <div key={i} className={cn('flex items-start gap-3 p-3 rounded-lg border', pConfig.bg, pConfig.border)}>
                    <div className="w-8 h-8 rounded-lg bg-white/80 border flex items-center justify-center flex-shrink-0">
                      <ActionIcon className={cn('w-4 h-4', pConfig.color)} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-0.5">
                        <div className={cn('w-1.5 h-1.5 rounded-full', pConfig.dot)} />
                        <span className={cn('text-sm font-semibold', pConfig.color)}>{action.title}</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{action.description}</p>
                      {action.impact_estimate && (
                        <span className="inline-block mt-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground bg-white/60 px-2 py-0.5 rounded border">
                          {action.impact_estimate}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
