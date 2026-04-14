/**
 * Feature #15 — Competitor Intelligence Automation Card
 *
 * Shows estimated SOV, competitor profiles, platform competition, and opportunities.
 */

import { useState } from 'react';
import {
  Swords,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Target,
  Eye,
  Zap,
  Shield,
  BarChart3,
} from 'lucide-react';
import {
  useCompetitorIntel,
  type CompetitorProfile,
  type PlatformCompetition,
  type MarketOpportunity,
  type CompetitorInsight,
} from '@/api/dashboard';

const threatConfig: Record<string, { color: string; bg: string; label: string }> = {
  low: { color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Low' },
  medium: { color: 'text-amber-600', bg: 'bg-amber-50', label: 'Medium' },
  high: { color: 'text-orange-600', bg: 'bg-orange-50', label: 'High' },
  critical: { color: 'text-red-600', bg: 'bg-red-50', label: 'Critical' },
};

const compLevelConfig: Record<string, { color: string; bg: string }> = {
  low: { color: 'text-emerald-600', bg: 'bg-emerald-50' },
  medium: { color: 'text-amber-600', bg: 'bg-amber-50' },
  high: { color: 'text-orange-600', bg: 'bg-orange-50' },
  saturated: { color: 'text-red-600', bg: 'bg-red-50' },
};

const impactConfig: Record<string, { color: string; bg: string }> = {
  low: { color: 'text-slate-600', bg: 'bg-slate-50' },
  medium: { color: 'text-amber-600', bg: 'bg-amber-50' },
  high: { color: 'text-emerald-600', bg: 'bg-emerald-50' },
};

const severityConfig: Record<string, { color: string; bg: string; icon: typeof CheckCircle2 }> = {
  positive: { color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 },
  info: { color: 'text-blue-600', bg: 'bg-blue-50', icon: Eye },
  warning: { color: 'text-amber-600', bg: 'bg-amber-50', icon: AlertTriangle },
  critical: { color: 'text-red-600', bg: 'bg-red-50', icon: AlertTriangle },
};

function fmt(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

function TrendIcon({ trend }: { trend: string }) {
  if (trend === 'growing' || trend === 'rising' || trend === 'increasing')
    return <TrendingUp className="w-3.5 h-3.5 text-red-500" />;
  if (trend === 'declining' || trend === 'falling' || trend === 'decreasing')
    return <TrendingDown className="w-3.5 h-3.5 text-emerald-500" />;
  return <Minus className="w-3.5 h-3.5 text-slate-400" />;
}

function PressureGauge({ pressure }: { pressure: number }) {
  const color = pressure >= 70 ? 'bg-red-500' : pressure >= 45 ? 'bg-amber-500' : pressure >= 25 ? 'bg-blue-500' : 'bg-emerald-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${Math.min(pressure, 100)}%` }} />
      </div>
      <span className="text-xs font-bold text-slate-600">{pressure.toFixed(0)}/100</span>
    </div>
  );
}

function CompetitorRow({ comp }: { comp: CompetitorProfile }) {
  const tcfg = threatConfig[comp.threat_level] || threatConfig.medium;
  const strengthColor = comp.relative_strength === 'stronger' ? 'text-red-600' : comp.relative_strength === 'weaker' ? 'text-emerald-600' : 'text-amber-600';

  return (
    <div className="flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:bg-slate-50/50 transition-colors">
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${tcfg.bg}`}>
        <Shield className={`w-4 h-4 ${tcfg.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-slate-900">{comp.name}</span>
          <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${tcfg.bg} ${tcfg.color}`}>
            {tcfg.label} threat
          </span>
        </div>
        <div className="flex gap-3 text-xs text-slate-500 mt-0.5">
          <span className={strengthColor}>{comp.relative_strength}</span>
          <span>~{fmt(comp.estimated_spend)}</span>
          <span>{comp.estimated_sov.toFixed(1)}% SOV</span>
        </div>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <TrendIcon trend={comp.trend} />
        <span className="text-xs text-slate-500 capitalize">{comp.trend}</span>
      </div>
    </div>
  );
}

function PlatformRow({ pc }: { pc: PlatformCompetition }) {
  const [open, setOpen] = useState(false);
  const clcfg = compLevelConfig[pc.competition_level] || compLevelConfig.medium;

  return (
    <div className={`border rounded-xl transition-all ${open ? 'border-slate-200' : 'border-slate-100'}`}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 p-3 text-left hover:bg-slate-50/50 rounded-xl transition-colors">
        <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center shrink-0">
          <BarChart3 className="w-5 h-5 text-slate-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-slate-900">{pc.platform}</span>
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${clcfg.bg} ${clcfg.color}`}>
              {pc.competition_level}
            </span>
          </div>
          <div className="flex gap-3 text-xs text-slate-500 mt-0.5">
            <span>{fmt(pc.your_spend)} spend</span>
            <span>{pc.your_roas.toFixed(1)}x ROAS</span>
            <span>Position: {pc.your_position}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <TrendIcon trend={pc.avg_cpc_trend} />
          {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-slate-50">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="text-center p-2 bg-slate-50 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-slate-400">Competition</div>
              <div className="text-sm font-bold text-slate-700">{pc.competition_score.toFixed(0)}/100</div>
            </div>
            <div className="text-center p-2 bg-slate-50 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-slate-400">Opportunity</div>
              <div className="text-sm font-bold text-emerald-600">{pc.opportunity_score.toFixed(0)}/100</div>
            </div>
            <div className="text-center p-2 bg-slate-50 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-slate-400">CTR</div>
              <div className="text-sm font-bold text-slate-700">{pc.your_ctr.toFixed(2)}%</div>
            </div>
            <div className="text-center p-2 bg-slate-50 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-slate-400">Est. CPM</div>
              <div className="text-sm font-bold text-slate-700">${pc.estimated_market_cpm.toFixed(2)}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function OpportunityRow({ opp }: { opp: MarketOpportunity }) {
  const icfg = impactConfig[opp.potential_impact] || impactConfig.medium;
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl border border-slate-100">
      <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
        <Target className="w-4 h-4 text-emerald-600" />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-900">{opp.title}</span>
          <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${icfg.bg} ${icfg.color}`}>{opp.potential_impact}</span>
        </div>
        <div className="text-xs text-slate-500 mt-0.5">{opp.description}</div>
        <div className="text-xs text-emerald-600 font-semibold mt-1">{opp.action}</div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-xs text-slate-400">Confidence</div>
        <div className="text-sm font-bold text-slate-700">{opp.confidence.toFixed(0)}%</div>
      </div>
    </div>
  );
}

function InsightRow({ insight }: { insight: CompetitorInsight }) {
  const cfg = severityConfig[insight.severity] || severityConfig.info;
  const Icon = cfg.icon;
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl border border-slate-100">
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${cfg.bg}`}>
        <Icon className={`w-4 h-4 ${cfg.color}`} />
      </div>
      <div className="flex-1">
        <div className="text-sm font-semibold text-slate-900">{insight.title}</div>
        <div className="text-xs text-slate-500 mt-0.5">{insight.description}</div>
      </div>
      {insight.action_label && (
        <span className={`text-[10px] font-bold uppercase px-2 py-1 rounded-lg shrink-0 ${cfg.bg} ${cfg.color}`}>
          {insight.action_label}
        </span>
      )}
    </div>
  );
}

type TabKey = 'competitors' | 'platforms' | 'opportunities' | 'insights';

export function CompetitorIntelCard() {
  const { data, isLoading, error } = useCompetitorIntel();
  const [tab, setTab] = useState<TabKey>('competitors');

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse">
        <div className="h-6 bg-slate-100 rounded w-48 mb-4" />
        <div className="h-20 bg-slate-50 rounded-xl" />
      </div>
    );
  }

  if (error || !data) return null;

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'competitors', label: 'Competitors', count: data.competitors.length },
    { key: 'platforms', label: 'Platforms', count: data.platform_competition.length },
    { key: 'opportunities', label: 'Opportunities', count: data.opportunities_count },
    { key: 'insights', label: 'Insights', count: data.insights.length },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4 border-b border-slate-100">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center">
              <Swords className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-slate-900">Competitor Intelligence</h3>
                <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 capitalize">
                  {data.market_position.replace('-', ' ')}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{data.summary}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Your SOV</div>
            <div className="text-lg font-bold text-slate-900">{data.your_estimated_sov.toFixed(1)}%</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Pressure</div>
            <PressureGauge pressure={data.competitive_pressure} />
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Your Spend</div>
            <div className="text-lg font-bold text-slate-900">{fmt(data.total_your_spend)}</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Est. Market</div>
            <div className="text-lg font-bold text-slate-500">{fmt(data.estimated_market_spend)}</div>
          </div>
        </div>
      </div>

      <div className="flex border-b border-slate-100 px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key ? 'border-rose-600 text-rose-600' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-[10px] text-slate-400">({t.count})</span>}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-2 max-h-[480px] overflow-y-auto">
        {tab === 'competitors' && data.competitors.map((c, i) => <CompetitorRow key={i} comp={c} />)}
        {tab === 'platforms' && data.platform_competition.map((p, i) => <PlatformRow key={i} pc={p} />)}
        {tab === 'opportunities' && data.opportunities.map((o, i) => <OpportunityRow key={i} opp={o} />)}
        {tab === 'insights' && data.insights.map((ins, i) => <InsightRow key={i} insight={ins} />)}
      </div>
    </div>
  );
}
