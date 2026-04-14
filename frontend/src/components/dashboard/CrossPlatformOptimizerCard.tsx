import { useState } from 'react';
import {
  Globe,
  ChevronDown,
  ChevronUp,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
  BarChart3,
  Shuffle,
  Target,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCrossPlatformOptimizer } from '@/api/dashboard';
import type { OptimizationStrategy, PlatformEfficiency, PlatformRecommendation, OptimizationScenario, AllocationShift } from '@/api/dashboard';

const strategyConfig = {
  roas_max: { label: 'ROAS Max', description: 'Maximize return on ad spend' },
  balanced: { label: 'Balanced', description: 'Balance efficiency and volume' },
  volume_max: { label: 'Volume Max', description: 'Maximize conversion volume' },
};

const actionConfig = {
  scale: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', icon: TrendingUp },
  reduce: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: TrendingDown },
  maintain: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', icon: Minus },
};

function EfficiencyBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-muted/30 overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${score}%` }} />
      </div>
      <span className="text-[10px] font-bold text-muted-foreground">{Math.round(score)}</span>
    </div>
  );
}

function PlatformRow({ platform }: { platform: PlatformEfficiency }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg border bg-background">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <span className="w-5 h-5 rounded-md bg-blue-50 border border-blue-200 flex items-center justify-center text-[9px] font-bold text-blue-600">
          #{platform.efficiency_rank}
        </span>
        <span className="text-sm font-semibold text-foreground truncate">{platform.platform}</span>
        <span className="text-[10px] text-muted-foreground">{platform.campaigns} campaigns</span>
      </div>
      <div className="flex items-center gap-4 text-xs">
        <div className="text-right">
          <span className="font-semibold text-foreground">{platform.roas.toFixed(2)}x</span>
          <span className="text-[10px] text-muted-foreground ml-1">ROAS</span>
        </div>
        <div className="text-right">
          <span className="font-medium text-muted-foreground">{platform.spend_share_pct.toFixed(0)}%</span>
          <span className="text-[10px] text-muted-foreground ml-1">share</span>
        </div>
        <EfficiencyBar score={platform.efficiency_score} />
      </div>
    </div>
  );
}

function RecommendationRow({ rec }: { rec: PlatformRecommendation }) {
  const [expanded, setExpanded] = useState(false);
  const config = actionConfig[rec.action];
  const ActionIcon = config.icon;

  return (
    <div className={cn('rounded-lg border transition-all', config.border, expanded ? config.bg + '/30' : 'bg-background')}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-start gap-3 text-left"
      >
        <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5', config.bg)}>
          <ActionIcon className={cn('w-3.5 h-3.5', config.color)} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">{rec.platform}</span>
            <span className={cn('text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded', config.bg, config.color)}>
              {rec.action}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            ${rec.current_spend.toLocaleString()} → ${rec.recommended_spend.toLocaleString()}
            <span className={cn('ml-1.5 font-semibold', rec.change_pct > 0 ? 'text-emerald-600' : rec.change_pct < 0 ? 'text-red-600' : 'text-muted-foreground')}>
              {rec.change_pct > 0 ? '+' : ''}{rec.change_pct.toFixed(1)}%
            </span>
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 mt-1">
          <span className="text-[10px] text-muted-foreground">{Math.round(rec.confidence * 100)}% conf</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-inherit ml-10">
          <p className="text-xs text-muted-foreground leading-relaxed pt-2">{rec.reasoning}</p>
          <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
            <span>Projected ROAS: {rec.projected_roas.toFixed(2)}x</span>
            <span>Projected Revenue: ${rec.projected_revenue.toLocaleString()}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function ShiftRow({ shift }: { shift: AllocationShift }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg border bg-background text-xs">
      <span className="font-semibold text-red-600">{shift.from_platform}</span>
      <ArrowRight className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
      <span className="font-semibold text-emerald-600">{shift.to_platform}</span>
      <span className="ml-auto text-muted-foreground">${shift.shift_amount.toLocaleString()}</span>
      <span className="text-[10px] text-muted-foreground">({shift.shift_pct}%)</span>
    </div>
  );
}

function ScenarioCard({ scenario }: { scenario: OptimizationScenario }) {
  const isPositive = scenario.improvement_pct > 0;
  return (
    <div className="rounded-lg border bg-background p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-foreground">{scenario.name}</span>
        <span className={cn('text-xs font-bold', isPositive ? 'text-emerald-600' : 'text-muted-foreground')}>
          {isPositive ? '+' : ''}{scenario.improvement_pct.toFixed(1)}%
        </span>
      </div>
      <p className="text-[10px] text-muted-foreground">{scenario.description}</p>
      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
        <span>ROAS: {scenario.projected_roas.toFixed(2)}x</span>
        <span>Revenue: ${scenario.projected_revenue.toLocaleString()}</span>
        <span>Conversions: {scenario.projected_conversions.toLocaleString()}</span>
      </div>
    </div>
  );
}

export function CrossPlatformOptimizerCard() {
  const [strategy, setStrategy] = useState<OptimizationStrategy>('balanced');
  const [activeSection, setActiveSection] = useState<'platforms' | 'recommendations' | 'scenarios'>('recommendations');
  const { data, isLoading, error } = useCrossPlatformOptimizer(strategy);

  if (isLoading || error || !data) return null;
  if (data.total_campaigns === 0) return null;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="relative w-10 h-10 rounded-lg bg-purple-50 border border-purple-200 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Shuffle className="w-5 h-5 text-purple-500" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
                Cross-Platform Optimizer
              </h2>
              <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 border border-purple-200 flex items-center gap-1">
                <Zap className="w-3 h-3" />AI-OPTIMIZED
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {data.summary}
            </p>
          </div>
        </div>
        {/* Strategy selector */}
        <div className="flex items-center bg-muted/30 rounded-lg p-0.5 border flex-shrink-0">
          {(Object.keys(strategyConfig) as OptimizationStrategy[]).map((s) => (
            <button
              key={s}
              onClick={() => setStrategy(s)}
              className={cn('text-[10px] font-semibold px-2.5 py-1 rounded-md transition-colors',
                strategy === s ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {strategyConfig[s].label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats bar */}
      <div className="px-6 pb-4">
        <div className="flex items-center gap-5 text-xs">
          <span className="flex items-center gap-1.5 text-foreground font-semibold">
            <Globe className="w-3.5 h-3.5 text-purple-500" />
            {data.platforms_count} platforms
          </span>
          <span className="flex items-center gap-1.5 text-foreground font-semibold">
            <BarChart3 className="w-3.5 h-3.5 text-blue-500" />
            {data.current_roas.toFixed(2)}x → {data.optimized_roas.toFixed(2)}x ROAS
          </span>
          {data.roas_improvement_pct > 0 && (
            <span className="flex items-center gap-1.5 text-emerald-600 font-semibold">
              <TrendingUp className="w-3.5 h-3.5" />
              +{data.roas_improvement_pct.toFixed(1)}% improvement
            </span>
          )}
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Target className="w-3.5 h-3.5" />
            ${data.total_budget.toLocaleString()} total budget
          </span>
          {data.reallocation_amount > 0 && (
            <span className="flex items-center gap-1.5 text-amber-600 font-semibold">
              <Shuffle className="w-3.5 h-3.5" />
              ${data.reallocation_amount.toLocaleString()} reallocation
            </span>
          )}
        </div>
      </div>

      {/* Section tabs */}
      <div className="border-t px-6">
        <div className="flex items-center gap-1 -mb-px">
          {([
            { key: 'recommendations', label: 'Recommendations', icon: Target },
            { key: 'platforms', label: 'Platform Efficiency', icon: Layers },
            { key: 'scenarios', label: 'Scenarios', icon: BarChart3 },
          ] as const).map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveSection(key)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors',
                activeSection === key
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-4 space-y-2">
        {activeSection === 'recommendations' && (
          <>
            {data.recommendations.map((rec) => (
              <RecommendationRow key={rec.platform} rec={rec} />
            ))}
            {data.shifts.length > 0 && (
              <div className="pt-3 space-y-2">
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Budget Shifts</span>
                {data.shifts.map((shift, i) => (
                  <ShiftRow key={i} shift={shift} />
                ))}
              </div>
            )}
          </>
        )}

        {activeSection === 'platforms' && (
          data.platforms.map((p) => (
            <PlatformRow key={p.platform} platform={p} />
          ))
        )}

        {activeSection === 'scenarios' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {data.scenarios.map((s) => (
              <ScenarioCard key={s.name} scenario={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
