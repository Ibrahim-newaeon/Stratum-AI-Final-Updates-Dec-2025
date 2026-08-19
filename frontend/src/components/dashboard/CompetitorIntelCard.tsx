/**
 * Feature #15 — Competitor Intelligence Automation Card
 *
 * Shows SOV, competitor profiles, platform competition, and opportunities.
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
  BarChart3,
} from 'lucide-react';
import {
  useCompetitorIntel,
  type PlatformCompetition,
  type MarketOpportunity,
  type CompetitorInsight,
} from '@/api/dashboard';

const compLevelConfig: Record<string, { color: string; bg: string }> = {
  low: { color: 'text-emerald-600', bg: 'bg-emerald-50' },
  medium: { color: 'text-amber-600', bg: 'bg-amber-50' },
  high: { color: 'text-orange-600', bg: 'bg-orange-50' },
  saturated: { color: 'text-red-600', bg: 'bg-red-50' },
};

const impactConfig: Record<string, { color: string; bg: string }> = {
  low: { color: 'text-muted-foreground', bg: 'bg-muted/30' },
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
  if (trend === 'growing' || trend === 'rising' || trend === 'increasing') {
    return <TrendingUp className="w-3.5 h-3.5 text-red-500" />;
  }
  if (trend === 'declining' || trend === 'falling' || trend === 'decreasing') {
    return <TrendingDown className="w-3.5 h-3.5 text-emerald-500" />;
  }
  return <Minus className="w-3.5 h-3.5 text-muted-foreground/50" />;
}

function PressureGauge({ pressure }: { pressure: number }) {
  const color = pressure >= 70 ? 'bg-red-500' : pressure >= 45 ? 'bg-amber-500' : pressure >= 25 ? 'bg-blue-500' : 'bg-emerald-500';
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-[width]`} style={{ width: `${Math.min(pressure, 100)}%` }} />
      </div>
      <span className="text-xs font-bold text-muted-foreground">{pressure.toFixed(0)}/100</span>
    </div>
  );
}

function PlatformRow({ pc }: { pc: PlatformCompetition }) {
  const [open, setOpen] = useState(false);
  const clcfg = compLevelConfig[pc.competition_level] || compLevelConfig.medium;

  return (
    <div className={`border rounded-xl transition-colors ${open ? 'border-foreground/15' : ''}`}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 p-3 text-left hover:bg-muted/30 rounded-xl transition-colors">
        <div className="w-10 h-10 rounded-lg bg-muted/30 flex items-center justify-center shrink-0">
          <BarChart3 className="w-5 h-5 text-muted-foreground/50" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-foreground">{pc.platform}</span>
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${clcfg.bg} ${clcfg.color}`}>
              {pc.competition_level}
            </span>
          </div>
          <div className="flex gap-3 text-xs text-muted-foreground mt-0.5">
            <span>{fmt(pc.your_spend)} spend</span>
            <span>{pc.your_roas.toFixed(1)}x ROAS</span>
            <span>CTR: {pc.your_ctr.toFixed(2)}%</span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <TrendIcon trend={pc.avg_cpc_trend} />
          {open ? <ChevronDown className="w-4 h-4 text-muted-foreground/50" /> : <ChevronRight className="w-4 h-4 text-muted-foreground/50" />}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Competition</div>
              <div className="text-sm font-bold text-foreground">{pc.competition_score.toFixed(0)}/100</div>
            </div>
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Opportunity</div>
              <div className="text-sm font-bold text-emerald-600">{pc.opportunity_score.toFixed(0)}/100</div>
            </div>
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">CTR</div>
              <div className="text-sm font-bold text-foreground">{pc.your_ctr.toFixed(2)}%</div>
            </div>
            <div className="text-center p-2 bg-muted/30 rounded-lg">
              <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Avg CPM</div>
              <div className="text-sm font-bold text-foreground">${pc.your_cpm.toFixed(2)}</div>
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
    <div className="flex items-start gap-3 p-3 rounded-xl border">
      <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
        <Target className="w-4 h-4 text-emerald-600" />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{opp.title}</span>
          <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${icfg.bg} ${icfg.color}`}>{opp.potential_impact}</span>
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">{opp.description}</div>
        <div className="text-xs text-emerald-600 font-semibold mt-1">{opp.action}</div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-xs text-muted-foreground/50">Confidence</div>
        <div className="text-sm font-bold text-foreground">{opp.confidence.toFixed(0)}%</div>
      </div>
    </div>
  );
}

function InsightRow({ insight }: { insight: CompetitorInsight }) {
  const cfg = severityConfig[insight.severity] || severityConfig.info;
  const Icon = cfg.icon;
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl border">
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

type TabKey = 'platforms' | 'opportunities' | 'insights';

export function CompetitorIntelCard() {
  const { data, isLoading, error } = useCompetitorIntel();
  const [tab, setTab] = useState<TabKey>('platforms');

  if (isLoading) {
    return (
      <div className="rounded-xl border bg-card p-6 animate-pulse">
        <div className="h-6 bg-muted rounded w-48 mb-4" />
        <div className="h-20 bg-muted/30 rounded-xl" />
      </div>
    );
  }

  if (error || !data) return null;

  // No "Competitors" tab: this endpoint sees only our own campaigns. It used
  // to open on five invented companies — same five for every tenant, each with
  // a spend that was a multiple of the viewer's own.
  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'platforms', label: 'Platforms', count: data.platform_competition.length },
    { key: 'opportunities', label: 'Opportunities', count: data.opportunities_count },
    { key: 'insights', label: 'Insights', count: data.insights.length },
  ];

  return (
    <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4 border-b border">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center">
              <Swords className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-foreground">Competitive Pressure</h3>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{data.summary}</p>
            </div>
          </div>
        </div>

        {/* "Your SOV" and "Market Spend" tiles used to sit here. Both were our
            own spend restated through a hard-coded multiplier — SOV never moved
            off 12.5% for a meta-only tenant, at any spend. */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Pressure</div>
            <PressureGauge pressure={data.competitive_pressure} />
          </div>
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Your Spend</div>
            <div className="text-lg font-bold text-foreground">{fmt(data.total_your_spend)}</div>
          </div>
          <div className="bg-muted/30 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-muted-foreground/50">Platforms</div>
            <div className="text-lg font-bold text-foreground">{data.platforms_tracked}</div>
          </div>
        </div>
      </div>

      <div className="flex border-b border px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key ? 'border-rose-600 text-rose-600' : 'border-transparent text-muted-foreground/50 hover:text-muted-foreground'
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-[10px] text-muted-foreground/50">({t.count})</span>}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-2 max-h-[30rem] overflow-y-auto">
        {tab === 'platforms' && data.platform_competition.map((p, i) => <PlatformRow key={p.platform || i} pc={p} />)}
        {tab === 'opportunities' && data.opportunities.map((o, i) => <OpportunityRow key={`${o.title}-${i}`} opp={o} />)}
        {tab === 'insights' && data.insights.map((ins, i) => <InsightRow key={`${ins.title}-${i}`} insight={ins} />)}
      </div>
    </div>
  );
}
