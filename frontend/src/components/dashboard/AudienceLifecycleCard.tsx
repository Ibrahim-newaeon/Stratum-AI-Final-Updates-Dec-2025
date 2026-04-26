import { useState } from 'react';
import {
  Users,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  Zap,
  Activity,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Shield,
  Globe,
  TrendingUp,
  TrendingDown,
  Minus,
  Play,
  Target,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAudienceLifecycle } from '@/api/dashboard';
import type { LifecycleStageMetric, LifecycleTransition, AudienceRule, LifecycleRecommendation } from '@/api/dashboard';

const stageConfig: Record<string, { color: string; bg: string; border: string; icon: typeof Users }> = {
  anonymous: { color: 'text-muted-foreground', bg: 'bg-muted/30', border: 'border-border', icon: Users },
  known: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', icon: Target },
  customer: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', icon: CheckCircle },
  churned: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: XCircle },
};

const healthConfig = {
  excellent: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Excellent' },
  good: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', label: 'Good' },
  needs_attention: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Needs Attention' },
  poor: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', label: 'Poor' },
};

const categoryConfig: Record<string, { color: string; bg: string }> = {
  acquisition: { color: 'text-purple-600', bg: 'bg-purple-50' },
  activation: { color: 'text-blue-600', bg: 'bg-blue-50' },
  retention: { color: 'text-emerald-600', bg: 'bg-emerald-50' },
  reactivation: { color: 'text-amber-600', bg: 'bg-amber-50' },
};

function StageBar({ stages }: { stages: LifecycleStageMetric[] }) {
  const total = stages.reduce((sum, s) => sum + s.count, 0);
  if (total === 0) return null;

  return (
    <div className="space-y-2">
      {/* Stacked bar */}
      <div className="flex h-3 rounded-full overflow-hidden bg-muted/20">
        {stages.map((s) => {
          const cfg = stageConfig[s.stage] || stageConfig.anonymous;
          const width = (s.count / total) * 100;
          if (width < 1) return null;
          return (
            <div
              key={s.stage}
              className={cn('h-full transition-[width]', cfg.bg.replace('bg-', 'bg-').replace('-50', '-400'))}
              style={{ width: `${width}%` }}
              title={`${s.stage}: ${s.count} (${s.pct_of_total}%)`}
            />
          );
        })}
      </div>
      {/* Labels */}
      <div className="flex items-center gap-4 flex-wrap">
        {stages.map((s) => {
          const cfg = stageConfig[s.stage] || stageConfig.anonymous;
          const StageIcon = cfg.icon;
          return (
            <div key={s.stage} className="flex items-center gap-1.5 text-xs">
              <StageIcon className={cn('w-3 h-3', cfg.color)} />
              <span className="font-semibold text-foreground capitalize">{s.stage}</span>
              <span className="text-muted-foreground">{s.count.toLocaleString()}</span>
              <span className="text-[10px] text-muted-foreground">({s.pct_of_total}%)</span>
              {s.change_7d > 0 && (
                <span className="text-[10px] text-emerald-600 font-semibold">+{s.change_7d}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TransitionRow({ transition }: { transition: LifecycleTransition }) {
  const fromCfg = stageConfig[transition.from_stage] || stageConfig.anonymous;
  const toCfg = stageConfig[transition.to_stage] || stageConfig.anonymous;
  const TrendIcon = transition.trend === 'increasing' ? TrendingUp : transition.trend === 'decreasing' ? TrendingDown : Minus;
  const trendColor = transition.is_positive
    ? (transition.trend === 'increasing' ? 'text-emerald-600' : 'text-muted-foreground')
    : (transition.trend === 'increasing' ? 'text-red-600' : 'text-muted-foreground');

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg border bg-background text-xs">
      <span className={cn('font-semibold capitalize', fromCfg.color)}>{transition.from_stage}</span>
      <ArrowRight className="w-3 h-3 text-muted-foreground flex-shrink-0" />
      <span className={cn('font-semibold capitalize', toCfg.color)}>{transition.to_stage}</span>
      <span className="ml-auto text-muted-foreground">{transition.count_7d}/wk</span>
      <TrendIcon className={cn('w-3 h-3', trendColor)} />
      {transition.is_positive ? (
        <CheckCircle className="w-3 h-3 text-emerald-500" />
      ) : (
        <AlertTriangle className="w-3 h-3 text-red-500" />
      )}
    </div>
  );
}

function RuleRow({ rule }: { rule: AudienceRule }) {
  const [expanded, setExpanded] = useState(false);
  const catCfg = categoryConfig[rule.category] || categoryConfig.activation;
  const priorityColors = { high: 'text-red-600 bg-red-50', medium: 'text-amber-600 bg-amber-50', low: 'text-blue-600 bg-blue-50' };

  return (
    <div className={cn('rounded-lg border transition-colors', expanded ? 'bg-muted/10' : 'bg-background')}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-start gap-3 text-left"
      >
        <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5', catCfg.bg)}>
          <Play className={cn('w-3.5 h-3.5', catCfg.color)} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground truncate">{rule.name}</span>
            <span className={cn('text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded', priorityColors[rule.priority])}>
              {rule.priority}
            </span>
            <span className={cn('text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded', catCfg.bg, catCfg.color)}>
              {rule.category}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{rule.description}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 mt-1">
          <span className="text-[10px] text-muted-foreground">{rule.profiles_matched} profiles</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t ml-10">
          <p className="text-xs text-muted-foreground leading-relaxed pt-2">{rule.description}</p>
          <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
            <span>Trigger: {rule.trigger_condition.replace(/_/g, ' ')}</span>
            <span>Stage: {rule.trigger_stage}</span>
            <span>Action: {rule.action.replace(/_/g, ' ')}</span>
            {rule.target_platform && <span>Platform: {rule.target_platform}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

function RecommendationRow({ rec }: { rec: LifecycleRecommendation }) {
  const impactColors = { high: 'text-red-600 bg-red-50 border-red-200', medium: 'text-amber-600 bg-amber-50 border-amber-200', low: 'text-blue-600 bg-blue-50 border-blue-200' };

  return (
    <div className={cn('flex items-start gap-3 p-3 rounded-lg border', impactColors[rec.impact])}>
      <ArrowRight className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <span className="text-xs font-semibold">{rec.title}</span>
        <p className="text-[10px] text-muted-foreground mt-0.5">{rec.description}</p>
        <div className="flex items-center gap-3 mt-1 text-[10px]">
          <span className="font-semibold">{rec.action_label}</span>
          <span className="text-muted-foreground">{rec.profiles_affected.toLocaleString()} profiles affected</span>
        </div>
      </div>
    </div>
  );
}

export function AudienceLifecycleCard() {
  const [activeTab, setActiveTab] = useState<'rules' | 'transitions' | 'recommendations'>('rules');
  const { data, isLoading, error } = useAudienceLifecycle();

  if (isLoading || error || !data) return null;
  if (data.total_profiles === 0) return null;

  const hCfg = healthConfig[data.lifecycle_health];

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="relative w-10 h-10 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Users className="w-5 h-5 text-indigo-500" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
                Audience Lifecycle
              </h2>
              <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600 border border-indigo-200 flex items-center gap-1">
                <Zap className="w-3 h-3" />AUTOMATED
              </span>
              <span className={cn('text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border flex items-center gap-1', hCfg.bg, hCfg.color, hCfg.border)}>
                <Activity className="w-3 h-3" />{hCfg.label}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {data.summary}
            </p>
          </div>
        </div>
      </div>

      {/* Stage distribution bar */}
      <div className="px-6 pb-4">
        <StageBar stages={data.stages} />
      </div>

      {/* Stats bar */}
      <div className="px-6 pb-4">
        <div className="flex items-center gap-5 text-xs">
          <span className="flex items-center gap-1.5 text-foreground font-semibold">
            <Users className="w-3.5 h-3.5 text-indigo-500" />
            {data.total_profiles.toLocaleString()} profiles
          </span>
          <span className="flex items-center gap-1.5 text-foreground font-semibold">
            <Play className="w-3.5 h-3.5 text-emerald-500" />
            {data.active_rules}/{data.total_rules} rules active
          </span>
          <span className="flex items-center gap-1.5 text-foreground font-semibold">
            <Shield className="w-3.5 h-3.5 text-blue-500" />
            {data.automation_coverage_pct}% coverage
          </span>
          {data.profiles_in_automation > 0 && (
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Globe className="w-3.5 h-3.5" />
              {data.profiles_in_automation.toLocaleString()} in automation
            </span>
          )}
        </div>
      </div>

      {/* Section tabs */}
      <div className="border-t px-6">
        <div className="flex items-center gap-1 -mb-px">
          {([
            { key: 'rules', label: 'Automation Rules', count: data.rules.length },
            { key: 'transitions', label: 'Stage Transitions', count: data.transitions.length },
            { key: 'recommendations', label: 'Recommendations', count: data.recommendations.length },
          ] as const).map(({ key, label, count }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors',
                activeTab === key
                  ? 'border-indigo-500 text-indigo-600'
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
        {activeTab === 'rules' && (
          data.rules.map((rule) => (
            <RuleRow key={rule.rule_id} rule={rule} />
          ))
        )}

        {activeTab === 'transitions' && (
          data.transitions.map((t, i) => (
            <TransitionRow key={i} transition={t} />
          ))
        )}

        {activeTab === 'recommendations' && (
          data.recommendations.map((rec, i) => (
            <RecommendationRow key={i} rec={rec} />
          ))
        )}
      </div>
    </div>
  );
}
