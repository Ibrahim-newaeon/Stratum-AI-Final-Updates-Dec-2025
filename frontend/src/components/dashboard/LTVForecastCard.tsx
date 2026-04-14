/**
 * Feature #13 — Customer LTV Forecasting Card
 *
 * Displays customer lifetime value by cohort and segment,
 * LTV distribution, projections, and AI insights.
 */

import { useState } from 'react';
import {
  TrendingUp,
  Users,
  DollarSign,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Target,
} from 'lucide-react';
import {
  useLTVForecast,
  type CohortLTV,
  type SegmentForecast,
  type LTVDistributionBucket,
  type LTVInsight,
} from '@/api/dashboard';

// ── Config ──────────────────────────────────────────────────────────────────

const healthConfig = {
  excellent: { color: 'text-emerald-600', bg: 'bg-emerald-50', bar: 'bg-emerald-500', label: 'Excellent' },
  good: { color: 'text-blue-600', bg: 'bg-blue-50', bar: 'bg-blue-500', label: 'Good' },
  needs_attention: { color: 'text-amber-600', bg: 'bg-amber-50', bar: 'bg-amber-500', label: 'Needs Attention' },
  poor: { color: 'text-red-600', bg: 'bg-red-50', bar: 'bg-red-500', label: 'Poor' },
};

const riskConfig = {
  low: { color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Low Risk' },
  medium: { color: 'text-amber-600', bg: 'bg-amber-50', label: 'Medium' },
  high: { color: 'text-orange-600', bg: 'bg-orange-50', label: 'High Risk' },
  critical: { color: 'text-red-600', bg: 'bg-red-50', label: 'Critical' },
};

const severityConfig = {
  positive: { color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 },
  info: { color: 'text-blue-600', bg: 'bg-blue-50', icon: TrendingUp },
  warning: { color: 'text-amber-600', bg: 'bg-amber-50', icon: AlertTriangle },
  critical: { color: 'text-red-600', bg: 'bg-red-50', icon: AlertTriangle },
};

function fmt(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

// ── Sub-components ──────────────────────────────────────────────────────────

function HealthBadge({ health }: { health: string }) {
  const cfg = healthConfig[health as keyof typeof healthConfig] || healthConfig.poor;
  return (
    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${cfg.bg} ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function SegmentRow({ segment }: { segment: SegmentForecast }) {
  const [open, setOpen] = useState(false);
  const risk = riskConfig[segment.risk_level] || riskConfig.medium;

  return (
    <div className={`border rounded-xl transition-all ${open ? 'border-foreground/15' : ''}`}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 p-3 text-left hover:bg-muted/30 rounded-xl transition-colors">
        <div className="w-10 h-10 rounded-lg bg-muted/30 flex items-center justify-center shrink-0">
          <DollarSign className="w-5 h-5 text-muted-foreground/50" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-foreground truncate">{segment.segment_label}</span>
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${risk.bg} ${risk.color}`}>{risk.label}</span>
          </div>
          <div className="flex gap-3 mt-0.5 text-xs text-muted-foreground">
            <span>LTV: <strong className="text-foreground">{fmt(segment.current_avg_ltv)}</strong></span>
            <span>CAC: <strong className="text-foreground">{fmt(segment.cac)}</strong></span>
            <span>LTV:CAC: <strong className="text-foreground">{segment.ltv_to_cac_ratio.toFixed(1)}x</strong></span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {segment.growth_rate > 0 ? (
            <span className="text-xs font-bold text-emerald-600 flex items-center gap-0.5">
              <ArrowUpRight className="w-3 h-3" />{segment.growth_rate.toFixed(0)}%
            </span>
          ) : segment.growth_rate < 0 ? (
            <span className="text-xs font-bold text-red-600 flex items-center gap-0.5">
              <ArrowDownRight className="w-3 h-3" />{Math.abs(segment.growth_rate).toFixed(0)}%
            </span>
          ) : (
            <span className="text-xs font-bold text-muted-foreground/50 flex items-center gap-0.5">
              <Minus className="w-3 h-3" />0%
            </span>
          )}
          {open ? <ChevronDown className="w-4 h-4 text-muted-foreground/50" /> : <ChevronRight className="w-4 h-4 text-muted-foreground/50" />}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Customers</div>
              <div className="text-sm font-bold text-foreground">{segment.customer_count.toLocaleString()}</div>
            </div>
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">12m Projected</div>
              <div className="text-sm font-bold text-foreground">{fmt(segment.projected_12m_ltv)}</div>
            </div>
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Revenue</div>
              <div className="text-sm font-bold text-foreground">{fmt(segment.total_revenue)}</div>
            </div>
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Rev Share</div>
              <div className="text-sm font-bold text-foreground">{segment.revenue_contribution_pct.toFixed(1)}%</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CohortRow({ cohort }: { cohort: CohortLTV }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl border hover:bg-muted/30 transition-colors">
      <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center shrink-0">
        <Users className="w-4 h-4 text-indigo-500" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{cohort.cohort_label}</span>
          <span className="text-[10px] text-muted-foreground/50">{cohort.size.toLocaleString()} customers</span>
        </div>
        <div className="flex gap-3 text-xs text-muted-foreground mt-0.5">
          <span>LTV: <strong className="text-foreground">{fmt(cohort.avg_ltv)}</strong></span>
          <span>Ret: <strong className="text-foreground">{cohort.retention_rate.toFixed(0)}%</strong></span>
          <span>AOV: <strong className="text-foreground">{fmt(cohort.avg_order_value)}</strong></span>
        </div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-xs text-muted-foreground/50">12m Projected</div>
        <div className="text-sm font-bold text-indigo-600">{fmt(cohort.projected_ltv_12m)}</div>
      </div>
    </div>
  );
}

function DistributionBar({ buckets }: { buckets: LTVDistributionBucket[] }) {
  const colors = ['bg-blue-200', 'bg-blue-300', 'bg-blue-400', 'bg-indigo-400', 'bg-indigo-500', 'bg-purple-500', 'bg-purple-600'];
  const total = buckets.reduce((s, b) => s + b.count, 0);

  if (total === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex h-6 rounded-lg overflow-hidden">
        {buckets.map((b, i) => {
          const pct = (b.count / total) * 100;
          if (pct < 1) return null;
          return (
            <div
              key={i}
              className={`${colors[i % colors.length]} relative group`}
              style={{ width: `${pct}%` }}
              title={`${b.bucket_label}: ${b.count} customers (${pct.toFixed(0)}%)`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-2">
        {buckets.map((b, i) => (
          <div key={i} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <div className={`w-2 h-2 rounded-sm ${colors[i % colors.length]}`} />
            <span>{b.bucket_label}: {b.count} ({b.pct.toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function InsightRow({ insight }: { insight: LTVInsight }) {
  const cfg = severityConfig[insight.severity] || severityConfig.info;
  const Icon = cfg.icon;

  return (
    <div className={`flex items-start gap-3 p-3 rounded-xl border border`}>
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${cfg.bg}`}>
        <Icon className={`w-4 h-4 ${cfg.color}`} />
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold text-foreground">{insight.title}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{insight.description}</div>
      </div>
      {insight.action_label && (
        <span className={`text-[10px] font-bold uppercase px-2 py-1 rounded-lg shrink-0 ${cfg.bg} ${cfg.color}`}>
          {insight.action_label}
        </span>
      )}
    </div>
  );
}

// ── Main Card ───────────────────────────────────────────────────────────────

type TabKey = 'segments' | 'cohorts' | 'distribution' | 'insights';

export function LTVForecastCard() {
  const { data, isLoading, error } = useLTVForecast();
  const [tab, setTab] = useState<TabKey>('segments');

  if (isLoading) {
    return (
      <div className="rounded-xl border bg-card p-6 animate-pulse">
        <div className="h-6 bg-muted rounded w-48 mb-4" />
        <div className="h-20 bg-muted/30 rounded-xl" />
      </div>
    );
  }

  if (error || !data) return null;

  const hcfg = healthConfig[data.ltv_health] || healthConfig.poor;

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'segments', label: 'Segments', count: data.segments.length },
    { key: 'cohorts', label: 'Cohorts', count: data.cohorts.length },
    { key: 'distribution', label: 'Distribution' },
    { key: 'insights', label: 'Insights', count: data.insights.length },
  ];

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 pt-5 pb-4 border-b border">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-foreground">Customer LTV Forecast</h3>
                <HealthBadge health={data.ltv_health} />
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{data.summary}</p>
            </div>
          </div>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Avg LTV</div>
            <div className="text-lg font-bold text-foreground">{fmt(data.overall_avg_ltv)}</div>
          </div>
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">12m Projected</div>
            <div className="text-lg font-bold text-indigo-600">{fmt(data.projected_avg_ltv_12m)}</div>
          </div>
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">LTV:CAC</div>
            <div className={`text-lg font-bold ${hcfg.color}`}>{data.avg_ltv_to_cac.toFixed(1)}x</div>
          </div>
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Customers</div>
            <div className="text-lg font-bold text-foreground">{data.total_customers.toLocaleString()}</div>
          </div>
        </div>

        {/* Secondary stats */}
        <div className="flex gap-3 mt-3 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-emerald-50 rounded-lg text-emerald-600">
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Top 20% = {data.high_value_pct.toFixed(0)}% revenue</span>
          </div>
          {data.at_risk_revenue_pct > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-amber-50 rounded-lg text-amber-600">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{data.at_risk_revenue_pct.toFixed(0)}% at-risk revenue</span>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-muted-foreground/50 hover:text-muted-foreground'
            }`}
          >
            {t.label}
            {t.count !== undefined && (
              <span className="ml-1 text-[10px] text-muted-foreground/50">({t.count})</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-4 space-y-2 max-h-[480px] overflow-y-auto">
        {tab === 'segments' && data.segments.map((s, i) => <SegmentRow key={i} segment={s} />)}
        {tab === 'cohorts' && data.cohorts.map((c, i) => <CohortRow key={i} cohort={c} />)}
        {tab === 'distribution' && <DistributionBar buckets={data.distribution} />}
        {tab === 'insights' && data.insights.map((ins, i) => <InsightRow key={i} insight={ins} />)}
        {tab === 'segments' && data.segments.length === 0 && (
          <div className="text-center py-8 text-sm text-muted-foreground/50">
            <Target className="w-8 h-8 mx-auto mb-2 text-muted-foreground/30" />
            No segment data available yet.
          </div>
        )}
      </div>
    </div>
  );
}
