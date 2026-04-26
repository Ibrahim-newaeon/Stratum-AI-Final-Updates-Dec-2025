import { useState } from 'react';
import {
  Target,
  ChevronDown,
  ChevronUp,
  Zap,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  ArrowRight,
  Flag,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useGoalTracking } from '@/api/dashboard';
import type { GoalProgress, PacingMilestone, GoalInsight } from '@/api/dashboard';

const pacingConfig = {
  ahead: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', bar: 'bg-emerald-500', label: 'Ahead' },
  on_track: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', bar: 'bg-blue-500', label: 'On Track' },
  behind: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', bar: 'bg-amber-500', label: 'Behind' },
  at_risk: { color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200', bar: 'bg-orange-500', label: 'At Risk' },
  critical: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', bar: 'bg-red-500', label: 'Critical' },
};

const trendIcons = {
  improving: TrendingUp,
  stable: Minus,
  declining: TrendingDown,
};

const severityConfig = {
  positive: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', icon: CheckCircle },
  info: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', icon: Target },
  warning: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', icon: AlertTriangle },
  critical: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: XCircle },
};

function ProgressRing({ pct, status }: { pct: number; status: string }) {
  const cfg = pacingConfig[status as keyof typeof pacingConfig] || pacingConfig.on_track;
  const clampedPct = Math.min(100, Math.max(0, pct));
  return (
    <div className="relative w-12 h-12 flex-shrink-0">
      <svg className="w-12 h-12 -rotate-90" viewBox="0 0 36 36">
        <path
          className="text-muted/20"
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <path
          className={cfg.color}
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeDasharray={`${clampedPct}, 100`}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-foreground">
        {Math.round(pct)}%
      </span>
    </div>
  );
}

function GoalRow({ goal }: { goal: GoalProgress }) {
  const [expanded, setExpanded] = useState(false);
  const cfg = pacingConfig[goal.pacing_status];
  const TrendIcon = trendIcons[goal.trend];

  return (
    <div className={cn('rounded-lg border transition-colors', cfg.border, expanded ? cfg.bg + '/30' : 'bg-background')}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-center gap-3 text-left"
      >
        <ProgressRing pct={goal.progress_pct} status={goal.pacing_status} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">{goal.label}</span>
            <span className={cn('text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded', cfg.bg, cfg.color)}>
              {cfg.label}
            </span>
            <TrendIcon className={cn('w-3 h-3', goal.trend === 'improving' ? 'text-emerald-500' : goal.trend === 'declining' ? 'text-red-500' : 'text-muted-foreground')} />
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs">
            <span className="font-semibold text-foreground">{goal.formatted_current}</span>
            <span className="text-muted-foreground">of {goal.formatted_target}</span>
            <span className="text-muted-foreground">•</span>
            <span className="text-muted-foreground">Proj: {goal.formatted_projected}</span>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Progress bar */}
          <div className="w-24 h-2 rounded-full bg-muted/20 overflow-hidden hidden sm:block">
            <div
              className={cn('h-full rounded-full transition-[width]', cfg.bar)}
              style={{ width: `${Math.min(100, goal.progress_pct)}%` }}
            />
          </div>
          {expanded ? <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-inherit ml-[60px]">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="text-center">
              <span className="text-[10px] text-muted-foreground block">Pacing</span>
              <span className={cn('text-sm font-bold', cfg.color)}>{goal.pacing_pct.toFixed(0)}%</span>
            </div>
            <div className="text-center">
              <span className="text-[10px] text-muted-foreground block">Gap</span>
              <span className="text-sm font-bold text-foreground">{goal.gap >= 0 ? '+' : ''}{goal.is_inverted ? '' : ''}{goal.formatted_target.charAt(0) === '$' ? '$' : ''}{Math.abs(goal.gap).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
            </div>
            <div className="text-center">
              <span className="text-[10px] text-muted-foreground block">Daily Needed</span>
              <span className="text-sm font-bold text-foreground">{goal.formatted_target.charAt(0) === '$' ? '$' : ''}{Math.abs(goal.daily_needed).toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
            </div>
            <div className="text-center">
              <span className="text-[10px] text-muted-foreground block">Days Left</span>
              <span className="text-sm font-bold text-foreground">{goal.days_remaining}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MilestoneTrack({ milestones }: { milestones: PacingMilestone[] }) {
  if (milestones.length === 0) return null;

  return (
    <div className="flex items-center gap-1">
      {milestones.map((m, i) => {
        const isLast = i === milestones.length - 1;
        const statusColor = m.status === 'hit' ? 'bg-emerald-500' : m.status === 'missed' ? 'bg-red-500' : 'bg-muted/30';
        const textColor = m.status === 'hit' ? 'text-emerald-600' : m.status === 'missed' ? 'text-red-600' : 'text-muted-foreground';
        return (
          <div key={i} className="flex items-center gap-1 flex-1">
            <div className="flex flex-col items-center gap-0.5 flex-shrink-0">
              <div className={cn('w-3 h-3 rounded-full border-2 border-background', statusColor)} />
              <span className={cn('text-[9px] font-semibold', textColor)}>{m.label}</span>
            </div>
            {!isLast && <div className="h-0.5 flex-1 bg-muted/20 rounded-full" />}
          </div>
        );
      })}
    </div>
  );
}

function InsightRow({ insight }: { insight: GoalInsight }) {
  const cfg = severityConfig[insight.severity];
  const Icon = cfg.icon;

  return (
    <div className={cn('flex items-start gap-3 p-3 rounded-lg border', cfg.border, cfg.bg + '/50')}>
      <Icon className={cn('w-4 h-4 flex-shrink-0 mt-0.5', cfg.color)} />
      <div className="flex-1 min-w-0">
        <span className={cn('text-xs font-semibold', cfg.color)}>{insight.title}</span>
        <p className="text-[10px] text-muted-foreground mt-0.5">{insight.description}</p>
        {insight.action_label && (
          <div className="flex items-center gap-1 mt-1">
            <ArrowRight className={cn('w-3 h-3', cfg.color)} />
            <span className={cn('text-[10px] font-semibold', cfg.color)}>{insight.action_label}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function GoalTrackingCard() {
  const [activeTab, setActiveTab] = useState<'goals' | 'insights'>('goals');
  const { data, isLoading, error } = useGoalTracking();

  if (isLoading || error || !data) return null;
  if (data.goals.length === 0) return null;

  const overallCfg = pacingConfig[data.overall_pacing];

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="relative w-10 h-10 rounded-lg bg-teal-50 border border-teal-200 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Target className="w-5 h-5 text-teal-500" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
                Goal Tracking
              </h2>
              <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-teal-50 text-teal-600 border border-teal-200 flex items-center gap-1">
                <Zap className="w-3 h-3" />LIVE PACING
              </span>
              <span className={cn('text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border flex items-center gap-1', overallCfg.bg, overallCfg.color, overallCfg.border)}>
                <Flag className="w-3 h-3" />{overallCfg.label}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {data.summary}
            </p>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <span className="text-[10px] text-muted-foreground block">{data.period_label}</span>
          <span className="text-xs font-semibold text-foreground">Day {data.days_elapsed}/{data.days_total}</span>
        </div>
      </div>

      {/* Period progress bar */}
      <div className="px-6 pb-3">
        <div className="flex items-center gap-3">
          <Clock className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
          <div className="flex-1 h-1.5 rounded-full bg-muted/20 overflow-hidden">
            <div
              className="h-full rounded-full bg-teal-500 transition-[width]"
              style={{ width: `${Math.min(100, data.progress_pct)}%` }}
            />
          </div>
          <span className="text-[10px] font-semibold text-muted-foreground">{data.progress_pct}%</span>
        </div>
      </div>

      {/* Milestones */}
      {data.milestones.length > 0 && (
        <div className="px-6 pb-4">
          <MilestoneTrack milestones={data.milestones} />
        </div>
      )}

      {/* Stats bar */}
      <div className="px-6 pb-4">
        <div className="flex items-center gap-5 text-xs">
          <span className="flex items-center gap-1.5 text-emerald-600 font-semibold">
            <CheckCircle className="w-3.5 h-3.5" />
            {data.goals_on_track} on track
          </span>
          {data.goals_at_risk > 0 && (
            <span className="flex items-center gap-1.5 text-orange-600 font-semibold">
              <AlertTriangle className="w-3.5 h-3.5" />
              {data.goals_at_risk} at risk
            </span>
          )}
          {data.goals_behind > 0 && (
            <span className="flex items-center gap-1.5 text-red-600 font-semibold">
              <XCircle className="w-3.5 h-3.5" />
              {data.goals_behind} behind
            </span>
          )}
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Clock className="w-3.5 h-3.5" />
            {data.days_remaining} days remaining
          </span>
        </div>
      </div>

      {/* Section tabs */}
      <div className="border-t px-6">
        <div className="flex items-center gap-1 -mb-px">
          {([
            { key: 'goals', label: 'Goals', count: data.goals.length },
            { key: 'insights', label: 'Insights', count: data.insights.length },
          ] as const).map(({ key, label, count }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors',
                activeTab === key
                  ? 'border-teal-500 text-teal-600'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {label}
              <span className="text-[10px] font-medium text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded">
                {count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-4 space-y-2">
        {activeTab === 'goals' && (
          data.goals.map((goal) => (
            <GoalRow key={goal.goal_id} goal={goal} />
          ))
        )}

        {activeTab === 'insights' && (
          data.insights.map((insight, i) => (
            <InsightRow key={i} insight={insight} />
          ))
        )}
      </div>
    </div>
  );
}
