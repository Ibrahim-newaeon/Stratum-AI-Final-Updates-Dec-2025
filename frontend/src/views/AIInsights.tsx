// =============================================================================
// Stratum AI — AI Insights Dashboard (Gap #3)
// =============================================================================

import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  LightBulbIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  PaperAirplaneIcon,
  SparklesIcon,
  ArrowPathIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';

interface NLQResult {
  question: string;
  generated_sql: string;
  explanation: string;
  results: Record<string, unknown>[];
  result_count: number;
  execution_time_ms: number;
  suggestions: string[];
}

interface AnomalyResult {
  metric: string;
  detected_change_pct: number;
  root_causes: { cause: string; detail: string; impact: string }[];
  contributing_factors: string[];
  recommended_actions: string[];
  historical_context: string;
  confidence: number;
}

interface PredictionResult {
  campaign_id: number;
  campaign_name: string;
  predicted_spend: number;
  predicted_revenue: number;
  predicted_roas: number;
  predicted_conversions: number;
  confidence_interval: { lower: number; upper: number };
  trend: string;
  risk_factors: string[];
  recommendation: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';
const getToken = () => sessionStorage.getItem('access_token') || '';

export default function AIInsights() {
  const [activeTab, setActiveTab] = useState<'nlq' | 'anomaly' | 'predict'>('nlq');

  return (
    <div className="min-h-screen bg-[#050B18] text-white p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <SparklesIcon className="w-8 h-8 text-[#00F5FF]" />
            AI Intelligence Layer
          </h1>
          <p className="text-gray-400 mt-2">Natural language queries, anomaly root-cause analysis, and predictive forecasting</p>
        </header>

        <div className="flex gap-2 mb-6">
          {[
            { id: 'nlq' as const, label: 'Ask a Question', icon: LightBulbIcon },
            { id: 'anomaly' as const, label: 'Anomaly Center', icon: ExclamationTriangleIcon },
            { id: 'predict' as const, label: 'Predictions', icon: ChartBarIcon },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all',
                activeTab === tab.id
                  ? 'bg-primary text-white'
                  : 'bg-white/[0.03] text-gray-400 hover:bg-white/[0.06]'
              )}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'nlq' && <NLQPanel />}
        {activeTab === 'anomaly' && <AnomalyPanel />}
        {activeTab === 'predict' && <PredictPanel />}
      </div>
    </div>
  );
}

// ── NLQ Panel ──────────────────────────────────────────────────────────────

function NLQPanel() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NLQResult | null>(null);
  const [error, setError] = useState('');

  const ask = async () => {
    const token = getToken();
    if (!question.trim() || !token) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_URL}/analytics/insights/nlq`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      if (data.success) setResult(data.data);
      else setError(data.message || 'Failed to process question');
    } catch (e) {
      setError('Network error');
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <label className="block text-sm font-medium text-gray-300 mb-2">Ask anything about your data</label>
        <div className="flex gap-3">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && ask()}
            placeholder="e.g. What are my top campaigns by ROAS?"
            className="flex-1 bg-white/[0.03] border border-foreground/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-primary"
          />
          <button
            onClick={ask}
            disabled={loading || !question.trim()}
            className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-white px-6 py-3 rounded-lg font-medium flex items-center gap-2 transition-colors"
          >
            {loading ? <ArrowPathIcon className="w-5 h-5 animate-spin" /> : <PaperAirplaneIcon className="w-5 h-5" />}
            Ask
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {['Top campaigns by ROAS', 'Total spend this month', 'Which platform performs best?', 'Underperforming campaigns'].map((s) => (
            <button
              key={s}
              onClick={() => setQuestion(s)}
              className="text-xs bg-white/[0.03] hover:bg-white/[0.08] text-gray-400 hover:text-white px-3 py-1.5 rounded-full transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg p-4">{error}</div>}

      {result && (
        <div className="space-y-4">
          <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">{result.question}</h3>
              <span className="text-xs text-gray-500">{result.execution_time_ms}ms · {result.result_count} rows</span>
            </div>
            <p className="text-sm text-gray-400 mb-4">{result.explanation}</p>

            {result.results.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-foreground/10 text-gray-400">
                      {Object.keys(result.results[0]).map((k) => (
                        <th key={k} className="text-left py-2 px-3 font-medium">{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.results.map((row, i) => (
                      <tr key={i} className="border-b border-foreground/5 hover:bg-white/[0.02]">
                        {Object.values(row).map((v, j) => (
                          <td key={j} className="py-2 px-3 text-gray-300">{String(v ?? '-')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <details className="mt-4">
              <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">View generated SQL</summary>
              <pre className="mt-2 bg-black/40 rounded-lg p-3 text-xs text-gray-400 overflow-x-auto">{result.generated_sql}</pre>
            </details>
          </div>

          {result.suggestions.length > 0 && (
            <div className="flex flex-wrap gap-2">
              <span className="text-sm text-gray-500">Try:</span>
              {result.suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => { setQuestion(s); setResult(null); }}
                  className="text-sm text-[#00F5FF] hover:underline"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Anomaly Panel ──────────────────────────────────────────────────────────

function AnomalyPanel() {
  const [metric, setMetric] = useState('roas');
  const [severity, setSeverity] = useState('high');
  const [campaignId, setCampaignId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnomalyResult | null>(null);

  const analyze = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/analytics/insights/anomalies/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ metric, severity, campaign_id: campaignId ? parseInt(campaignId) : null }),
      });
      const data = await res.json();
      if (data.success) setResult(data.data);
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Metric</label>
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              className="w-full bg-white/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-white"
            >
              {['roas', 'cpc', 'ctr', 'conversions', 'spend'].map((m) => (
                <option key={m} value={m} className="bg-[#0A1628]">{m.toUpperCase()}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Severity</label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              className="w-full bg-white/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-white"
            >
              {['critical', 'high', 'medium', 'low'].map((s) => (
                <option key={s} value={s} className="bg-[#0A1628]">{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Campaign ID (optional)</label>
            <input
              value={campaignId}
              onChange={(e) => setCampaignId(e.target.value)}
              placeholder="e.g. 123"
              className="w-full bg-white/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-white placeholder-gray-500"
            />
          </div>
        </div>
        <button
          onClick={analyze}
          disabled={loading}
          className="mt-4 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
        >
          {loading ? <ArrowPathIcon className="w-5 h-5 animate-spin" /> : <ExclamationTriangleIcon className="w-5 h-5" />}
          Analyze Anomaly
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Anomaly: {result.metric.toUpperCase()}</h3>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">Confidence</span>
                <div className="w-24 h-2 bg-foreground/10 rounded-full overflow-hidden">
                  <div className="h-full bg-[#00F5FF] rounded-full" style={{ width: `${result.confidence * 100}%` }} />
                </div>
                <span className="text-sm text-[#00F5FF]">{Math.round(result.confidence * 100)}%</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-3">Root Causes</h4>
                {result.root_causes.map((rc, i) => (
                  <div key={i} className="bg-white/[0.03] border border-foreground/5 rounded-lg p-4 mb-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn(
                        'text-xs px-2 py-0.5 rounded-full font-medium',
                        rc.impact === 'high' ? 'bg-red-500/20 text-red-400' :
                        rc.impact === 'positive' ? 'bg-green-500/20 text-green-400' :
                        'bg-yellow-500/20 text-yellow-400'
                      )}>
                        {rc.impact}
                      </span>
                      <span className="font-medium">{rc.cause}</span>
                    </div>
                    <p className="text-sm text-gray-400 mt-1">{rc.detail}</p>
                  </div>
                ))}
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-3">Contributing Factors</h4>
                <ul className="space-y-2">
                  {result.contributing_factors.map((f, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                      <ChevronDownIcon className="w-4 h-4 mt-0.5 text-gray-600 rotate-[-90deg]" />
                      {f}
                    </li>
                  ))}
                </ul>

                <h4 className="text-sm font-medium text-gray-300 mt-6 mb-3">Recommended Actions</h4>
                <div className="space-y-2">
                  {result.recommended_actions.map((a, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <div className="w-5 h-5 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">{i + 1}</div>
                      <span className="text-sm text-gray-300">{a}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-foreground/10">
              <p className="text-sm text-gray-500">{result.historical_context}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Predictions Panel ───────────────────────────────────────────────────────

function PredictPanel() {
  const [campaignId, setCampaignId] = useState('');
  const [days, setDays] = useState(7);
  const [budgetScenario, setBudgetScenario] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);

  const predict = async () => {
    const token = getToken();
    if (!token || !campaignId) return;
    setLoading(true);
    try {
      const body: Record<string, unknown> = { campaign_id: parseInt(campaignId), days_ahead: days };
      if (budgetScenario) body.budget_scenario = parseFloat(budgetScenario);
      const res = await fetch(`${API_URL}/analytics/insights/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.success) setResult(data.data);
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  const trendColor = (t: string) => {
    if (t === 'improving') return 'text-green-400';
    if (t === 'declining') return 'text-red-400';
    return 'text-yellow-400';
  };

  return (
    <div className="space-y-6">
      <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Campaign ID</label>
            <input
              value={campaignId}
              onChange={(e) => setCampaignId(e.target.value)}
              placeholder="e.g. 123"
              className="w-full bg-white/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-white placeholder-gray-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Days Ahead: {days}</label>
            <input
              type="range" min={1} max={30} value={days}
              onChange={(e) => setDays(parseInt(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Hypothetical Daily Budget (USD, optional)</label>
            <input
              value={budgetScenario}
              onChange={(e) => setBudgetScenario(e.target.value)}
              placeholder="e.g. 500"
              className="w-full bg-white/[0.03] border border-foreground/10 rounded-lg px-3 py-2 text-white placeholder-gray-500"
            />
          </div>
        </div>
        <button
          onClick={predict}
          disabled={loading || !campaignId}
          className="mt-4 bg-primary hover:bg-primary/90 disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
        >
          {loading ? <ArrowPathIcon className="w-5 h-5 animate-spin" /> : <ChartBarIcon className="w-5 h-5" />}
          Generate Forecast
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          <div className="bg-white/[0.02] border border-foreground/10 rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold">{result.campaign_name}</h3>
                <p className="text-sm text-gray-400">Campaign #{result.campaign_id}</p>
              </div>
              <div className={cn('text-lg font-bold capitalize', trendColor(result.trend))}>
                {result.trend}
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                { label: 'Predicted Spend', value: `$${result.predicted_spend.toLocaleString()}`, color: 'text-gray-300' },
                { label: 'Predicted Revenue', value: `$${result.predicted_revenue.toLocaleString()}`, color: 'text-green-400' },
                { label: 'Predicted ROAS', value: `${result.predicted_roas.toFixed(2)}x`, color: result.predicted_roas >= 2 ? 'text-green-400' : 'text-yellow-400' },
                { label: 'Conversions', value: result.predicted_conversions.toLocaleString(), color: 'text-[#00F5FF]' },
              ].map((m) => (
                <div key={m.label} className="bg-white/[0.03] border border-foreground/5 rounded-lg p-4">
                  <div className="text-xs text-gray-500 mb-1">{m.label}</div>
                  <div className={cn('text-xl font-bold', m.color)}>{m.value}</div>
                </div>
              ))}
            </div>

            <div className="mb-4">
              <div className="flex justify-between text-sm text-gray-400 mb-2">
                <span>Confidence Interval</span>
                <span>${result.confidence_interval.lower.toLocaleString()} — ${result.confidence_interval.upper.toLocaleString()}</span>
              </div>
              <div className="h-3 bg-foreground/10 rounded-full overflow-hidden relative">
                <div className="absolute left-1/4 right-1/4 top-0 bottom-0 bg-[#00F5FF]/30 rounded-full" />
                <div className="absolute left-1/2 top-0 bottom-0 w-1 bg-[#00F5FF]" />
              </div>
            </div>

            <div className="bg-white/[0.03] border border-foreground/5 rounded-lg p-4 mb-4">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Recommendation</h4>
              <p className="text-sm text-gray-400">{result.recommendation}</p>
            </div>

            <div>
              <h4 className="text-sm font-medium text-gray-300 mb-2">Risk Factors</h4>
              <div className="flex flex-wrap gap-2">
                {result.risk_factors.map((r, i) => (
                  <span key={i} className="text-xs bg-yellow-500/10 text-yellow-400 px-3 py-1 rounded-full">{r}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
