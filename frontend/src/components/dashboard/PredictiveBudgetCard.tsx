import { useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronUp,
  X,
  DollarSign,
  Target,
  Shield,
  Zap,
  AlertTriangle,
  CheckCircle,
  PauseCircle,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePredictiveBudget } from '@/api/dashboard';
import type { CampaignBudgetInsight, PredictiveBudgetResponse } from '@/api/dashboard';

const trustGateConfig = {
  pass: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'PASS', icon: CheckCircle },
  hold: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'HOLD', icon: AlertTriangle },
  block: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', label: 'BLOCK', icon: Shield },
};

const actionConfig = {
  scale: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', icon: TrendingUp, label: 'Scale' },
  reduce: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', icon: TrendingDown, label: 'Reduce' },
  maintain: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', icon: Minus, label: 'Maintain' },
  pause: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', icon: PauseCircle, label: 'Pause' },
};

function ConfidenceBar({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 85 ? 'bg-emerald-500' : pct >= 60 ? 'bg-blue-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-muted/30 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] font-bold text-muted-foreground">{pct}%</span>
    </div>
  );
}

function RecommendationRow({ rec }: { rec: CampaignBudgetInsight }) {
  const [expanded, setExpanded] = useState(false);
  const config = actionConfig[rec.action] || actionConfig.maintain;
  const ActionIcon = config.icon;

  return (
    <div className={cn('rounded-lg border transition-all', config.border, expanded ? config.bg : 'bg-background')}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-center gap-3 text-left"
      >
        <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0', config.bg)}>
          <ActionIcon className={cn('w-4 h-4', config.color)} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground truncate">{rec.campaign_name}</span>
            <span className={cn('text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded', config.bg, config.color)}>
              {config.label}
            </span>
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-xs text-muted-foreground">{rec.platform}</span>
            <span className="text-xs text-muted-foreground">ROAS: {rec.metrics.roas?.toFixed(2)}x</span>
            <span className={cn('text-xs font-bold', rec.change_amount >= 0 ? 'text-emerald-600' : 'text-red-500')}>
              {rec.change_amount >= 0 ? '+' : ''}{rec.change_percent.toFixed(1)}%
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <ConfidenceBar confidence={rec.confidence} />
          {expanded ? <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-inherit">
          <div className="pt-2 grid grid-cols-3 gap-2">
            <div className="text-center">
              <div className="text-[10px] text-muted-foreground">Current</div>
              <div className="text-sm font-bold">${rec.current_spend.toLocaleString()}</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] text-muted-foreground">Recommended</div>
              <div className={cn('text-sm font-bold', config.color)}>${rec.recommended_spend.toLocaleString()}</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] text-muted-foreground">Change</div>
              <div className={cn('text-sm font-bold', rec.change_amount >= 0 ? 'text-emerald-600' : 'text-red-500')}>
                {rec.change_amount >= 0 ? '+' : ''}${Math.abs(rec.change_amount).toLocaleString()}
              </div>
            </div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">{rec.reasoning}</p>
          {rec.risk_factors.length > 0 && (
            <div className="space-y-1">
              {rec.risk_factors.map((risk, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[11px] text-amber-600">
                  <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  {risk}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ForecastCard({ data }: { data: PredictiveBudgetResponse }) {
  const forecast = data.forecast;
  if (!forecast) return null;

  const confColor = forecast.confidence_level === 'high' ? 'text-emerald-600' : forecast.confidence_level === 'medium' ? 'text-blue-600' : 'text-amber-600';

  return (
    <div className="rounded-lg border bg-gradient-to-br from-blue-50/50 to-violet-50/50 p-4">
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="w-4 h-4 text-blue-500" />
        <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Projected Impact</span>
        <span className={cn('text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-white/60 border', confColor)}>
          {forecast.confidence_level} confidence
        </span>
      </div>
      <div className="grid grid-cols-4 gap-3">
        <div>
          <div className="text-[10px] text-muted-foreground">Spend</div>
          <div className="text-sm font-bold">${forecast.projected_spend.toLocaleString()}</div>
          <div className={cn('text-[10px] font-semibold flex items-center', forecast.spend_change_pct >= 0 ? 'text-amber-600' : 'text-emerald-600')}>
            {forecast.spend_change_pct >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {Math.abs(forecast.spend_change_pct).toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground">Revenue</div>
          <div className="text-sm font-bold">${forecast.projected_revenue.toLocaleString()}</div>
          <div className={cn('text-[10px] font-semibold flex items-center', forecast.revenue_change_pct >= 0 ? 'text-emerald-600' : 'text-red-500')}>
            {forecast.revenue_change_pct >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {Math.abs(forecast.revenue_change_pct).toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground">ROAS</div>
          <div className="text-sm font-bold">{forecast.projected_roas.toFixed(2)}x</div>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground">Conversions</div>
          <div className="text-sm font-bold">{forecast.projected_conversions.toLocaleString()}</div>
        </div>
      </div>
    </div>
  );
}

export function PredictiveBudgetCard() {
  const { data, isLoading, error } = usePredictiveBudget();
  const [dismissed, setDismissed] = useState(false);
  const [showRecs, setShowRecs] = useState(true);

  if (dismissed || isLoading || error || !data) return null;
  if (data.total_campaigns_analyzed === 0) return null;

  const gate = trustGateConfig[data.trust_gate_status] || trustGateConfig.block;
  const GateIcon = gate.icon;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-violet-50 border border-violet-200 flex items-center justify-center flex-shrink-0 mt-0.5">
            <DollarSign className="w-5 h-5 text-violet-500" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
                Budget Autopilot
              </h2>
              {data.autopilot_eligible && (
                <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center gap-1">
                  <Zap className="w-3 h-3" />AUTO-ELIGIBLE
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {data.summary}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Trust gate badge */}
          <div className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border', gate.bg, gate.color, gate.border)}>
            <GateIcon className="w-3.5 h-3.5" />
            Trust: {gate.label}
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
        <div className="flex items-center gap-6 text-xs">
          {data.scale_candidates > 0 && (
            <div className="flex items-center gap-1.5 text-emerald-600 font-semibold">
              <TrendingUp className="w-3.5 h-3.5" />
              {data.scale_candidates} to scale
            </div>
          )}
          {data.reduce_candidates > 0 && (
            <div className="flex items-center gap-1.5 text-amber-600 font-semibold">
              <TrendingDown className="w-3.5 h-3.5" />
              {data.reduce_candidates} to reduce
            </div>
          )}
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Target className="w-3.5 h-3.5" />
            {data.total_campaigns_analyzed} analyzed
          </div>
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <DollarSign className="w-3.5 h-3.5" />
            ${data.total_budget_shift.toLocaleString()} shift ({data.budget_shift_pct}%)
          </div>
          {data.high_confidence_count > 0 && (
            <div className="flex items-center gap-1.5 text-blue-600 font-semibold">
              <Zap className="w-3.5 h-3.5" />
              {data.high_confidence_count} high confidence
            </div>
          )}
        </div>
      </div>

      {/* Forecast */}
      {data.forecast && (
        <div className="px-6 pb-4">
          <ForecastCard data={data} />
        </div>
      )}

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setShowRecs(!showRecs)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
          >
            <span className="text-sm font-semibold text-foreground">
              Campaign Recommendations ({data.recommendations.length})
            </span>
            {showRecs ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>
          {showRecs && (
            <div className="px-6 pb-4 space-y-2">
              {data.recommendations.map((rec) => (
                <RecommendationRow key={rec.campaign_id} rec={rec} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
