import { useState } from 'react';
import {
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  X,
  AlertTriangle,
  CheckCircle,
  Phone,
  Paintbrush,
  DollarSign,
  Target,
  Wrench,
  TrendingDown,
  TrendingUp,
  Minus,
  HeartPulse,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChurnPrevention } from '@/api/dashboard';
import type { AtRiskCampaign, ChurnIntervention, RetentionMetric } from '@/api/dashboard';

const riskConfig = {
  healthy: { color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200', label: 'Healthy' },
  watch: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', label: 'Watch' },
  warning: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Warning' },
  critical: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', label: 'Critical' },
};

const campaignRiskColors = {
  low: 'bg-emerald-500',
  medium: 'bg-amber-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500',
};

const categoryIcons = {
  outreach: Phone,
  optimize: Target,
  budget: DollarSign,
  creative: Paintbrush,
  technical: Wrench,
};

const priorityConfig = {
  immediate: { color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200', label: 'Immediate' },
  soon: { color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200', label: 'Soon' },
  monitor: { color: 'text-blue-600', bg: 'bg-blue-50', border: 'border-blue-200', label: 'Monitor' },
};

function RiskBar({ score }: { score: number }) {
  const color = score >= 70 ? 'bg-red-500' : score >= 45 ? 'bg-orange-500' : score >= 25 ? 'bg-amber-500' : 'bg-emerald-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-muted/30 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
      <span className="text-[10px] font-bold text-muted-foreground">{score}%</span>
    </div>
  );
}

function MetricPill({ metric }: { metric: RetentionMetric }) {
  const trendIcon = metric.trend === 'improving'
    ? <TrendingUp className="w-3 h-3" />
    : metric.trend === 'declining'
      ? <TrendingDown className="w-3 h-3" />
      : <Minus className="w-3 h-3" />;

  return (
    <div className={cn(
      'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium',
      metric.is_healthy ? 'bg-emerald-50/50 border-emerald-200 text-emerald-700' : 'bg-amber-50/50 border-amber-200 text-amber-700',
    )}>
      <span className="text-muted-foreground">{metric.label}:</span>
      <span className="font-bold">{metric.value}</span>
      <span className={cn(
        'flex items-center gap-0.5',
        metric.trend === 'improving' ? 'text-emerald-600' : metric.trend === 'declining' ? 'text-red-500' : 'text-muted-foreground',
      )}>
        {trendIcon}
      </span>
    </div>
  );
}

function InterventionRow({ intervention }: { intervention: ChurnIntervention }) {
  const pConfig = priorityConfig[intervention.priority];
  const CatIcon = categoryIcons[intervention.category] || Target;

  return (
    <div className={cn('flex items-start gap-3 p-3 rounded-lg border', pConfig.border, pConfig.bg + '/30')}>
      <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0', pConfig.bg)}>
        <CatIcon className={cn('w-3.5 h-3.5', pConfig.color)} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{intervention.title}</span>
          <span className={cn('text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded', pConfig.bg, pConfig.color)}>
            {pConfig.label}
          </span>
          {intervention.auto_eligible && (
            <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-violet-50 text-violet-600 border border-violet-200 flex items-center gap-0.5">
              <Zap className="w-2.5 h-2.5" />Auto
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{intervention.description}</p>
      </div>
    </div>
  );
}

function CampaignRiskRow({ campaign }: { campaign: AtRiskCampaign }) {
  const [expanded, setExpanded] = useState(false);
  const riskColor = campaignRiskColors[campaign.risk_level];

  return (
    <div className={cn('rounded-lg border transition-colors', expanded ? 'bg-muted/20' : 'bg-background')}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-center gap-3 text-left"
      >
        <div className={cn('w-2 h-8 rounded-full flex-shrink-0', riskColor)} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground truncate">{campaign.campaign_name}</span>
            <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-wider">{campaign.platform}</span>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
            <span>ROAS: {campaign.current_roas.toFixed(2)}x</span>
            <span>${campaign.spend.toLocaleString()} spend</span>
            <span>{campaign.signals.length} risk signal{campaign.signals.length !== 1 ? 's' : ''}</span>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <RiskBar score={campaign.risk_score} />
          {expanded ? <ChevronUp className="w-3.5 h-3.5 text-muted-foreground" /> : <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />}
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-inherit">
          {/* Risk signals */}
          {campaign.signals.length > 0 && (
            <div className="pt-2 space-y-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Risk Signals</div>
              {campaign.signals.map((sig, i) => (
                <div key={i} className={cn(
                  'flex items-start gap-1.5 text-[11px]',
                  sig.severity === 'critical' ? 'text-red-600' : sig.severity === 'high' ? 'text-orange-600' : 'text-amber-600',
                )}>
                  <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  {sig.description}
                </div>
              ))}
            </div>
          )}
          {/* Interventions */}
          {campaign.interventions.length > 0 && (
            <div className="space-y-1.5">
              <div className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Recommended Actions</div>
              {campaign.interventions.map((interv, i) => (
                <InterventionRow key={i} intervention={interv} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ChurnPreventionCard() {
  const { data, isLoading, error } = useChurnPrevention();
  const [dismissed, setDismissed] = useState(false);
  const [showCampaigns, setShowCampaigns] = useState(true);
  const [showInterventions, setShowInterventions] = useState(true);

  if (dismissed || isLoading || error || !data) return null;
  if (data.total_campaigns_analyzed === 0) return null;

  const portfolioConfig = riskConfig[data.portfolio_risk_level] || riskConfig.healthy;

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 flex items-start justify-between">
        <div className="flex items-start gap-4">
          <div className={cn(
            'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 border',
            data.portfolio_risk_level === 'critical' || data.portfolio_risk_level === 'warning'
              ? 'bg-red-50 border-red-200' : 'bg-emerald-50 border-emerald-200',
          )}>
            {data.at_risk_count > 0
              ? <ShieldAlert className="w-5 h-5 text-red-500" />
              : <HeartPulse className="w-5 h-5 text-emerald-500" />
            }
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-display font-bold text-foreground tracking-tight">
                Churn Prevention
              </h2>
            </div>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl leading-relaxed">
              {data.summary}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className={cn('flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border', portfolioConfig.bg, portfolioConfig.color, portfolioConfig.border)}>
            {data.portfolio_risk_level === 'healthy' ? <CheckCircle className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
            {portfolioConfig.label}
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

      {/* Retention metrics */}
      <div className="px-6 pb-4">
        <div className="flex items-center gap-2 flex-wrap">
          {data.metrics.map((m) => (
            <MetricPill key={m.label} metric={m} />
          ))}
        </div>
      </div>

      {/* Risk distribution bar */}
      {data.total_campaigns_analyzed > 0 && (
        <div className="px-6 pb-4">
          <div className="flex items-center gap-1 h-2 rounded-full overflow-hidden bg-muted/30">
            {data.risk_distribution.critical > 0 && (
              <div className="bg-red-500 h-full rounded-full" style={{ width: `${(data.risk_distribution.critical / data.total_campaigns_analyzed) * 100}%` }} />
            )}
            {data.risk_distribution.high > 0 && (
              <div className="bg-orange-500 h-full rounded-full" style={{ width: `${(data.risk_distribution.high / data.total_campaigns_analyzed) * 100}%` }} />
            )}
            {data.risk_distribution.medium > 0 && (
              <div className="bg-amber-500 h-full rounded-full" style={{ width: `${(data.risk_distribution.medium / data.total_campaigns_analyzed) * 100}%` }} />
            )}
            {data.risk_distribution.low > 0 && (
              <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${(data.risk_distribution.low / data.total_campaigns_analyzed) * 100}%` }} />
            )}
          </div>
          <div className="flex items-center gap-4 mt-1.5 text-[10px] text-muted-foreground">
            {data.risk_distribution.critical > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" />{data.risk_distribution.critical} critical</span>}
            {data.risk_distribution.high > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-orange-500" />{data.risk_distribution.high} high</span>}
            {data.risk_distribution.medium > 0 && <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" />{data.risk_distribution.medium} medium</span>}
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" />{data.risk_distribution.low} healthy</span>
          </div>
        </div>
      )}

      {/* Top interventions */}
      {data.top_interventions.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setShowInterventions(!showInterventions)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
          >
            <span className="text-sm font-semibold text-foreground">
              Priority Interventions ({data.top_interventions.length})
            </span>
            {showInterventions ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>
          {showInterventions && (
            <div className="px-6 pb-4 space-y-2">
              {data.top_interventions.map((interv, i) => (
                <InterventionRow key={i} intervention={interv} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* At-risk campaigns */}
      {data.at_risk_campaigns.length > 0 && (
        <div className="border-t">
          <button
            onClick={() => setShowCampaigns(!showCampaigns)}
            className="w-full px-6 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors"
          >
            <span className="text-sm font-semibold text-foreground">
              At-Risk Campaigns ({data.at_risk_campaigns.length})
            </span>
            {showCampaigns ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>
          {showCampaigns && (
            <div className="px-6 pb-4 space-y-2">
              {data.at_risk_campaigns.map((c) => (
                <CampaignRiskRow key={c.campaign_id} campaign={c} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
