import { useState } from 'react';
import {
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  ChevronDown,
  ChevronUp,
  X,
  Zap,
  DollarSign,
  Target,
  Activity,
  Shield,
  ArrowRight,
  Lightbulb,
  Link2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAnomalyNarratives } from '@/api/dashboard';
import type { AnomalyNarrative, CorrelationInsight } from '@/api/dashboard';

const severityConfig = {
  critical: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', dot: 'bg-red-500', label: 'Critical' },
  high: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-amber-500', label: 'High' },
  medium: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', dot: 'bg-blue-500', label: 'Medium' },
  low: { color: 'text-muted-foreground', bg: 'bg-muted/30', border: 'border-border', dot: 'bg-slate-400', label: 'Low' },
};

const riskConfig = {
  low: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Low Risk' },
  moderate: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', label: 'Moderate' },
  elevated: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Elevated' },
  high: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', label: 'High Risk' },
};

const categoryIcons = {
  spend: DollarSign,
  revenue: Zap,
  efficiency: Target,
  quality: Shield,
  other: Activity,
};

function NarrativeCard({ narrative }: { narrative: AnomalyNarrative }) {
  const [expanded, setExpanded] = useState(false);
  const sev = severityConfig[narrative.severity] || severityConfig.medium;
  const Icon = categoryIcons[narrative.category] || Activity;
  const isUp = narrative.direction === 'up';

  return (
    <div className={cn('rounded-lg border transition-colors', sev.border, expanded ? sev.bg : 'bg-background')}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-start gap-3 text-left"
      >
        <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0', isUp ? 'bg-emerald-50' : 'bg-red-50')}>
          {isUp ? <TrendingUp className="w-4.5 h-4.5 text-emerald-600" /> : <TrendingDown className="w-4.5 h-4.5 text-red-500" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Icon className="w-3.5 h-3.5 text-muted-foreground/60" />
            <span className="text-sm font-semibold text-foreground">{narrative.title}</span>
            <span className={cn('text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded', sev.bg, sev.color)}>
              {sev.label}
            </span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">{narrative.summary}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className={cn('text-xs font-bold', isUp ? 'text-emerald-600' : 'text-red-500')}>
              {isUp ? '+' : '-'}{narrative.change_percent}%
            </span>
            <span className="text-[10px] text-muted-foreground">
              z-score: {Math.abs(narrative.zscore).toFixed(1)}
            </span>
          </div>
        </div>
        <div className="flex-shrink-0 mt-1">
          {expanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-inherit">
          {/* Likely Causes */}
          <div className="pt-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Likely Causes</span>
            </div>
            <ul className="space-y-1.5">
              {narrative.likely_causes.map((cause, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <div className="w-1 h-1 rounded-full bg-muted-foreground/40 mt-1.5 flex-shrink-0" />
                  {cause}
                </li>
              ))}
            </ul>
          </div>

          {/* Recommended Actions */}
          <div>
            <div className="flex items-center gap-1.5 mb-2">
              <ArrowRight className="w-3.5 h-3.5 text-blue-500" />
              <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Recommended Actions</span>
            </div>
            <ul className="space-y-1.5">
              {narrative.recommended_actions.map((action, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-foreground/80">
                  <div className={cn('w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0', sev.dot)} />
                  {action}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function CorrelationCard({ insight }: { insight: CorrelationInsight }) {
  const sev = severityConfig[insight.severity as keyof typeof severityConfig] || severityConfig.medium;

  return (
    <div className={cn('rounded-lg border p-4', sev.border, sev.bg)}>
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-foreground/80 border flex items-center justify-center flex-shrink-0">
          <Link2 className={cn('w-4.5 h-4.5', sev.color)} />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn('text-sm font-semibold', sev.color)}>{insight.title}</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">{insight.description}</p>
          <div className="flex items-center gap-2 mt-2">
            {insight.related_metrics.map((metric) => (
              <span key={metric} className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground bg-foreground/60 px-2 py-0.5 rounded border">
                {metric.replace('_', ' ')}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function AnomalyNarrativesCard() {
  const { data, isLoading, error } = useAnomalyNarratives();
  const [dismissed, setDismissed] = useState(false);
  const [showNarratives, setShowNarratives] = useState(true);

  if (dismissed || isLoading || error || !data) return null;
  if (data.total_anomalies === 0 && data.correlations.length === 0) return null;

  const risk = riskConfig[data.portfolio_risk] || riskConfig.low;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center flex-shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5 text-red-500" />
          </div>
          <div>
            <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
              Anomaly Intelligence
            </h2>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {data.executive_summary}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Portfolio risk badge */}
          <div className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border', risk.bg, risk.color, risk.border)}>
            <Shield className="w-3.5 h-3.5" />
            {risk.label}
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
          {data.critical_count > 0 && (
            <div className="flex items-center gap-1.5 text-red-600 font-semibold">
              <div className="w-2 h-2 rounded-full bg-red-500" />
              {data.critical_count} critical
            </div>
          )}
          {data.high_count > 0 && (
            <div className="flex items-center gap-1.5 text-amber-600 font-semibold">
              <div className="w-2 h-2 rounded-full bg-amber-500" />
              {data.high_count} high
            </div>
          )}
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <Activity className="w-3.5 h-3.5" />
            {data.total_anomalies} anomal{data.total_anomalies === 1 ? 'y' : 'ies'} detected
          </div>
          {data.correlations.length > 0 && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Link2 className="w-3.5 h-3.5" />
              {data.correlations.length} correlation{data.correlations.length > 1 ? 's' : ''}
            </div>
          )}
        </div>
      </div>

      {/* Correlations (shown first — most important) */}
      {data.correlations.length > 0 && (
        <div className="px-6 pb-4 space-y-2">
          {data.correlations.map((c, i) => (
            <CorrelationCard key={i} insight={c} />
          ))}
        </div>
      )}

      {/* Narrative cards */}
      {data.narratives.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setShowNarratives(!showNarratives)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
          >
            <span className="text-sm font-semibold text-foreground">
              Anomaly Details ({data.narratives.length})
            </span>
            {showNarratives ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>
          {showNarratives && (
            <div className="px-6 pb-4 space-y-2">
              {data.narratives.map((n, i) => (
                <NarrativeCard key={i} narrative={n} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
