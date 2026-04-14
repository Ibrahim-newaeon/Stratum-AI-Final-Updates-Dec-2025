/**
 * Feature #14 — Campaign Creative Scoring Card
 *
 * Grades creatives A-F, detects fatigue, identifies winners vs underperformers.
 */

import { useState } from 'react';
import {
  Palette,
  Trophy,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Zap,
  BarChart3,
  RefreshCw,
  Pause,
} from 'lucide-react';
import {
  useCreativeScoring,
  type CreativeScore,
  type PlatformCreativeSummary,
  type CreativeInsight,
} from '@/api/dashboard';

const gradeConfig: Record<string, { color: string; bg: string; ring: string }> = {
  A: { color: 'text-emerald-600', bg: 'bg-emerald-50', ring: 'stroke-emerald-500' },
  B: { color: 'text-blue-600', bg: 'bg-blue-50', ring: 'stroke-blue-500' },
  C: { color: 'text-amber-600', bg: 'bg-amber-50', ring: 'stroke-amber-500' },
  D: { color: 'text-orange-600', bg: 'bg-orange-50', ring: 'stroke-orange-500' },
  F: { color: 'text-red-600', bg: 'bg-red-50', ring: 'stroke-red-500' },
};

const statusConfig: Record<string, { color: string; bg: string; label: string; icon: typeof Trophy }> = {
  winner: { color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Winner', icon: Trophy },
  active: { color: 'text-blue-600', bg: 'bg-blue-50', label: 'Active', icon: Zap },
  underperforming: { color: 'text-red-600', bg: 'bg-red-50', label: 'Underperforming', icon: Pause },
  fatigued: { color: 'text-amber-600', bg: 'bg-amber-50', label: 'Fatigued', icon: RefreshCw },
  new: { color: 'text-slate-600', bg: 'bg-slate-50', label: 'New', icon: Zap },
};

const severityConfig: Record<string, { color: string; bg: string; icon: typeof CheckCircle2 }> = {
  positive: { color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 },
  info: { color: 'text-blue-600', bg: 'bg-blue-50', icon: BarChart3 },
  warning: { color: 'text-amber-600', bg: 'bg-amber-50', icon: AlertTriangle },
  critical: { color: 'text-red-600', bg: 'bg-red-50', icon: AlertTriangle },
};

function GradeBadge({ grade, size = 'md' }: { grade: string; size?: 'sm' | 'md' }) {
  const cfg = gradeConfig[grade] || gradeConfig.C;
  const sz = size === 'sm' ? 'w-8 h-8 text-sm' : 'w-12 h-12 text-xl';
  return (
    <div className={`${sz} rounded-xl ${cfg.bg} ${cfg.color} font-black flex items-center justify-center`}>
      {grade}
    </div>
  );
}

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between text-[10px] mb-1">
        <span className="text-slate-400 uppercase font-bold">{label}</span>
        <span className="font-bold text-slate-600">{score.toFixed(0)}</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
    </div>
  );
}

function CreativeRow({ creative }: { creative: CreativeScore }) {
  const [open, setOpen] = useState(false);
  const gcfg = gradeConfig[creative.grade] || gradeConfig.C;
  const scfg = statusConfig[creative.status] || statusConfig.active;
  const StatusIcon = scfg.icon;

  return (
    <div className={`border rounded-xl transition-all ${open ? 'border-slate-200' : 'border-slate-100'}`}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 p-3 text-left hover:bg-slate-50/50 rounded-xl transition-colors">
        <GradeBadge grade={creative.grade} size="sm" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-slate-900 truncate">{creative.campaign_name}</span>
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded flex items-center gap-1 ${scfg.bg} ${scfg.color}`}>
              <StatusIcon className="w-3 h-3" />{scfg.label}
            </span>
          </div>
          <div className="flex gap-3 mt-0.5 text-xs text-slate-500">
            <span>{creative.platform}</span>
            <span>{creative.roas.toFixed(1)}x ROAS</span>
            <span>{creative.ctr.toFixed(2)}% CTR</span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-sm font-bold ${gcfg.color}`}>{creative.overall_score.toFixed(0)}</span>
          {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-slate-50 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <ScoreBar label="CTR" score={creative.ctr_score} color="bg-blue-500" />
            <ScoreBar label="CVR" score={creative.cvr_score} color="bg-indigo-500" />
            <ScoreBar label="ROAS" score={creative.roas_score} color="bg-emerald-500" />
            <ScoreBar label="CPA" score={creative.cpa_score} color="bg-purple-500" />
          </div>
          {creative.fatigue_level !== 'none' && (
            <div className="flex items-center gap-2 text-xs">
              <RefreshCw className="w-3.5 h-3.5 text-amber-500" />
              <span className="text-amber-600 font-semibold">Fatigue: {creative.fatigue_level} ({creative.fatigue_score.toFixed(0)}%)</span>
            </div>
          )}
          <div className="flex gap-4 text-xs text-slate-500">
            <span>${creative.spend.toLocaleString(undefined, { maximumFractionDigits: 0 })} spend</span>
            <span>{creative.conversions.toLocaleString()} conv</span>
            <span>{creative.days_running}d running</span>
          </div>
          <div className="text-xs text-slate-600 bg-slate-50 rounded-lg px-3 py-2 italic">
            {creative.recommendation}
          </div>
        </div>
      )}
    </div>
  );
}

function PlatformSummaryRow({ ps }: { ps: PlatformCreativeSummary }) {
  const grade = ps.avg_score >= 80 ? 'A' : ps.avg_score >= 65 ? 'B' : ps.avg_score >= 50 ? 'C' : ps.avg_score >= 35 ? 'D' : 'F';
  const cfg = gradeConfig[grade];
  return (
    <div className="flex items-center gap-3 p-3 rounded-xl border border-slate-100">
      <GradeBadge grade={grade} size="sm" />
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm text-slate-900">{ps.platform}</div>
        <div className="flex gap-3 text-xs text-slate-500 mt-0.5">
          <span>{ps.total_creatives} creatives</span>
          <span className="text-emerald-600">{ps.winners} winner{ps.winners !== 1 ? 's' : ''}</span>
          {ps.fatigued > 0 && <span className="text-amber-600">{ps.fatigued} fatigued</span>}
        </div>
      </div>
      <div className="text-right">
        <div className={`text-sm font-bold ${cfg.color}`}>{ps.avg_score.toFixed(0)}</div>
        <div className="text-[10px] text-slate-400">avg score</div>
      </div>
    </div>
  );
}

function InsightRow({ insight }: { insight: CreativeInsight }) {
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

type TabKey = 'creatives' | 'platforms' | 'insights';

export function CreativeScoringCard() {
  const { data, isLoading, error } = useCreativeScoring();
  const [tab, setTab] = useState<TabKey>('creatives');

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse">
        <div className="h-6 bg-slate-100 rounded w-48 mb-4" />
        <div className="h-20 bg-slate-50 rounded-xl" />
      </div>
    );
  }

  if (error || !data) return null;

  const gcfg = gradeConfig[data.overall_grade] || gradeConfig.C;

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'creatives', label: 'Creatives', count: data.total_creatives },
    { key: 'platforms', label: 'By Platform', count: data.platform_summaries.length },
    { key: 'insights', label: 'Insights', count: data.insights.length },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4 border-b border-slate-100">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-50 flex items-center justify-center">
              <Palette className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-slate-900">Creative Scoring</h3>
                <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${gcfg.bg} ${gcfg.color}`}>
                  Grade {data.overall_grade}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">{data.summary}</p>
            </div>
          </div>
          <GradeBadge grade={data.overall_grade} />
        </div>

        <div className="flex gap-3 mt-4 text-xs">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-emerald-50 rounded-lg text-emerald-600">
            <Trophy className="w-3.5 h-3.5" />
            <span>{data.winners_count} winner{data.winners_count !== 1 ? 's' : ''}</span>
          </div>
          {data.fatigued_count > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-amber-50 rounded-lg text-amber-600">
              <RefreshCw className="w-3.5 h-3.5" />
              <span>{data.fatigued_count} fatigued</span>
            </div>
          )}
          {data.underperforming_count > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-red-50 rounded-lg text-red-600">
              <Pause className="w-3.5 h-3.5" />
              <span>{data.underperforming_count} underperforming</span>
            </div>
          )}
          {data.refresh_needed_pct > 0 && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-50 rounded-lg text-slate-500">
              <span>{data.refresh_needed_pct.toFixed(0)}% need refresh</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex border-b border-slate-100 px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key ? 'border-purple-600 text-purple-600' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-[10px] text-slate-400">({t.count})</span>}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-2 max-h-[480px] overflow-y-auto">
        {tab === 'creatives' && data.creatives.map((cr, i) => <CreativeRow key={i} creative={cr} />)}
        {tab === 'platforms' && data.platform_summaries.map((ps, i) => <PlatformSummaryRow key={i} ps={ps} />)}
        {tab === 'insights' && data.insights.map((ins, i) => <InsightRow key={i} insight={ins} />)}
      </div>
    </div>
  );
}
