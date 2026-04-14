/**
 * Feature #16 — Scheduled A/B Test Analysis Card
 *
 * Shows detected A/B tests, statistical significance, winners, and recommendations.
 */

import { useState } from 'react';
import {
  FlaskConical,
  Trophy,
  Clock,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  BarChart3,
  HelpCircle,
  Zap,
} from 'lucide-react';
import {
  useABTestAnalysis,
  type ABTestResult,
  type ABTestInsight,
} from '@/api/dashboard';

const statusConfig: Record<string, { color: string; bg: string; label: string; icon: typeof Trophy }> = {
  winner_found: { color: 'text-emerald-600', bg: 'bg-emerald-50', label: 'Winner Found', icon: Trophy },
  running: { color: 'text-blue-600', bg: 'bg-blue-50', label: 'Running', icon: Clock },
  needs_more_data: { color: 'text-amber-600', bg: 'bg-amber-50', label: 'Needs Data', icon: HelpCircle },
  inconclusive: { color: 'text-slate-600', bg: 'bg-slate-50', label: 'Inconclusive', icon: BarChart3 },
};

const severityConfig: Record<string, { color: string; bg: string; icon: typeof CheckCircle2 }> = {
  positive: { color: 'text-emerald-600', bg: 'bg-emerald-50', icon: CheckCircle2 },
  info: { color: 'text-blue-600', bg: 'bg-blue-50', icon: Zap },
  warning: { color: 'text-amber-600', bg: 'bg-amber-50', icon: AlertTriangle },
  critical: { color: 'text-red-600', bg: 'bg-red-50', icon: AlertTriangle },
};

function ConfidenceBar({ confidence }: { confidence: number }) {
  const color = confidence >= 95 ? 'bg-emerald-500' : confidence >= 80 ? 'bg-blue-500' : confidence >= 60 ? 'bg-amber-500' : 'bg-slate-300';
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${Math.min(confidence, 100)}%` }} />
      </div>
      <span className="text-xs font-bold text-slate-600">{confidence.toFixed(0)}%</span>
    </div>
  );
}

function TestRow({ test }: { test: ABTestResult }) {
  const [open, setOpen] = useState(false);
  const scfg = statusConfig[test.status] || statusConfig.running;
  const StatusIcon = scfg.icon;

  return (
    <div className={`border rounded-xl transition-all ${open ? 'border-slate-200' : 'border-slate-100'}`}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 p-3 text-left hover:bg-slate-50/50 rounded-xl transition-colors">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${scfg.bg}`}>
          <StatusIcon className={`w-4.5 h-4.5 ${scfg.color}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-slate-900 truncate">{test.test_name}</span>
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${scfg.bg} ${scfg.color}`}>
              {scfg.label}
            </span>
          </div>
          <div className="flex gap-3 mt-0.5 text-xs text-slate-500">
            <span>{test.platform}</span>
            <span>{test.days_running}d running</span>
            {test.winning_variant && <span className="text-emerald-600">Winner: {test.winning_variant}</span>}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <ConfidenceBar confidence={test.confidence} />
          {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-slate-50 space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {test.variants.map((v) => (
              <div key={v.variant_id} className={`p-3 rounded-lg border ${test.winning_variant === v.variant_label ? 'border-emerald-200 bg-emerald-50/50' : 'border-slate-100 bg-slate-50/50'}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-sm font-bold ${test.winning_variant === v.variant_label ? 'text-emerald-600' : 'text-slate-700'}`}>
                    Variant {v.variant_label}
                  </span>
                  {test.winning_variant === v.variant_label && <Trophy className="w-3.5 h-3.5 text-emerald-500" />}
                </div>
                <div className="grid grid-cols-2 gap-1.5 text-xs">
                  <div>
                    <span className="text-slate-400">CTR</span>
                    <div className="font-bold text-slate-700">{v.ctr.toFixed(2)}%</div>
                  </div>
                  <div>
                    <span className="text-slate-400">CVR</span>
                    <div className="font-bold text-slate-700">{v.cvr.toFixed(2)}%</div>
                  </div>
                  <div>
                    <span className="text-slate-400">ROAS</span>
                    <div className="font-bold text-slate-700">{v.roas.toFixed(1)}x</div>
                  </div>
                  <div>
                    <span className="text-slate-400">CPA</span>
                    <div className="font-bold text-slate-700">${v.cpa.toFixed(0)}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
          {test.lift_pct > 0 && (
            <div className="flex items-center gap-2 text-xs bg-emerald-50 rounded-lg px-3 py-2">
              <Trophy className="w-3.5 h-3.5 text-emerald-600" />
              <span className="text-emerald-700 font-semibold">+{test.lift_pct.toFixed(1)}% lift</span>
              <span className="text-emerald-600">at {test.confidence.toFixed(0)}% confidence</span>
            </div>
          )}
          <div className="text-xs text-slate-600 bg-slate-50 rounded-lg px-3 py-2 italic">
            {test.recommended_action}
          </div>
        </div>
      )}
    </div>
  );
}

function InsightRow({ insight }: { insight: ABTestInsight }) {
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

type TabKey = 'tests' | 'insights';

export function ABTestAnalysisCard() {
  const { data, isLoading, error } = useABTestAnalysis();
  const [tab, setTab] = useState<TabKey>('tests');

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
    { key: 'tests', label: 'Tests', count: data.total_tests },
    { key: 'insights', label: 'Insights', count: data.insights.length },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 pt-5 pb-4 border-b border-slate-100">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center">
              <FlaskConical className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900">A/B Test Analysis</h3>
              <p className="text-xs text-slate-500 mt-0.5">{data.summary}</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Tests</div>
            <div className="text-lg font-bold text-slate-900">{data.total_tests}</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Winners</div>
            <div className="text-lg font-bold text-emerald-600">{data.winners_found}</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Avg Confidence</div>
            <div className="text-lg font-bold text-slate-900">{data.avg_confidence.toFixed(0)}%</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3">
            <div className="text-[10px] font-bold uppercase text-slate-400">Savings</div>
            <div className="text-lg font-bold text-emerald-600">${data.potential_savings.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
          </div>
        </div>
      </div>

      <div className="flex border-b border-slate-100 px-6">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
              tab === t.key ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-400 hover:text-slate-600'
            }`}
          >
            {t.label}
            {t.count !== undefined && <span className="ml-1 text-[10px] text-slate-400">({t.count})</span>}
          </button>
        ))}
      </div>

      <div className="p-4 space-y-2 max-h-[480px] overflow-y-auto">
        {tab === 'tests' && data.tests.map((t, i) => <TestRow key={i} test={t} />)}
        {tab === 'insights' && data.insights.map((ins, i) => <InsightRow key={i} insight={ins} />)}
      </div>
    </div>
  );
}
