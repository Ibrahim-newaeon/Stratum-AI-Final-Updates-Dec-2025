// =============================================================================
// Stratum AI — Funnel Analysis (Gap #4)
// =============================================================================

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { ArrowPathIcon, PlusIcon, TrashIcon, PlayIcon, FunnelIcon } from '@heroicons/react/24/outline';

interface FunnelStep {
  step_name: string;
  step_order: number;
  event_type: string;
  count: number;
  conversion_rate_from_previous: number | null;
  drop_off_count: number;
  drop_off_rate: number;
}

interface FunnelResult {
  name: string;
  total_entries: number;
  total_conversions: number;
  overall_conversion_rate: number;
  steps: FunnelStep[];
  insights: string[];
}

const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';
const getToken = () => sessionStorage.getItem('access_token') || '';

export default function FunnelAnalysis() {
  
  const [name, setName] = useState('Purchase Funnel');
  const [steps, setSteps] = useState<string[]>(['impression', 'click', 'conversion']);
  const [dateFrom, setDateFrom] = useState('2026-01-01');
  const [dateTo, setDateTo] = useState('2026-12-31');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FunnelResult | null>(null);

  const addStep = () => setSteps([...steps, '']);
  const removeStep = (i: number) => setSteps(steps.filter((_, idx) => idx !== i));
  const updateStep = (i: number, v: string) => {
    const s = [...steps];
    s[i] = v;
    setSteps(s);
  };

  const analyze = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/analytics/advanced/funnel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ name, steps: steps.filter(Boolean), date_from: dateFrom, date_to: dateTo }),
      });
      const data = await res.json();
      if (data.success) setResult(data.data);
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-[#050B18] text-white p-6">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <FunnelIcon className="w-8 h-8 text-[#00F5FF]" />
            Funnel Analysis
          </h1>
          <p className="text-gray-400 mt-2">Multi-step conversion funnels with drop-off visualization</p>
        </header>

        <div className="bg-white/[0.02] border border-white/10 rounded-xl p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Funnel Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} className="w-full bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white" />
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-sm text-gray-400 mb-1">From</label>
                <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="w-full bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white" />
              </div>
              <div className="flex-1">
                <label className="block text-sm text-gray-400 mb-1">To</label>
                <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="w-full bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white" />
              </div>
            </div>
          </div>

          <label className="block text-sm text-gray-400 mb-2">Steps (in order)</label>
          {steps.map((s, i) => (
            <div key={i} className="flex gap-2 mb-2">
              <span className="text-gray-500 w-6 text-center pt-2">{i + 1}</span>
              <select
                value={s}
                onChange={(e) => updateStep(i, e.target.value)}
                className="flex-1 bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white"
              >
                <option value="" className="bg-[#0A1628]">Select event...</option>
                {['impression', 'click', 'landing', 'add_to_cart', 'conversion', 'purchase'].map((opt) => (
                  <option key={opt} value={opt} className="bg-[#0A1628]">{opt}</option>
                ))}
              </select>
              {steps.length > 2 && (
                <button onClick={() => removeStep(i)} className="text-red-400 hover:text-red-300 p-2">
                  <TrashIcon className="w-5 h-5" />
                </button>
              )}
            </div>
          ))}
          <button onClick={addStep} className="text-sm text-[#00F5FF] flex items-center gap-1 mt-2 hover:underline">
            <PlusIcon className="w-4 h-4" /> Add step
          </button>

          <button
            onClick={analyze}
            disabled={loading || steps.filter(Boolean).length < 2}
            className="mt-4 bg-primary hover:bg-[#ff4d85] disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
          >
            {loading ? <ArrowPathIcon className="w-5 h-5 animate-spin" /> : <PlayIcon className="w-5 h-5" />}
            Analyze Funnel
          </button>
        </div>

        {result && (
          <div className="space-y-6">
            <div className="bg-white/[0.02] border border-white/10 rounded-xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold">{result.name}</h3>
                <div className="text-right">
                  <div className="text-2xl font-bold">{result.overall_conversion_rate.toFixed(2)}%</div>
                  <div className="text-xs text-gray-500">overall conversion</div>
                </div>
              </div>

              {/* Funnel Bars */}
              <div className="space-y-4">
                {result.steps.map((step, i) => {
                  const maxCount = result.steps[0]?.count || 1;
                  const widthPct = (step.count / maxCount) * 100;
                  return (
                    <div key={i} className="relative">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium">{step.step_name}</span>
                        <span className="text-sm text-gray-400">{step.count.toLocaleString()}</span>
                      </div>
                      <div className="h-10 bg-white/5 rounded-lg overflow-hidden relative">
                        <div
                          className={cn(
                            'h-full rounded-lg transition-all flex items-center px-3',
                            i === 0 ? 'bg-[#00F5FF]' :
                            i === result.steps.length - 1 ? 'bg-green-400' :
                            'bg-primary'
                          )}
                          style={{ width: `${widthPct}%` }}
                        >
                          <span className="text-xs font-bold text-black whitespace-nowrap">
                            {step.conversion_rate_from_previous ? `${step.conversion_rate_from_previous.toFixed(1)}%` : '100%'}
                          </span>
                        </div>
                      </div>
                      {step.drop_off_count > 0 && (
                        <div className="text-xs text-red-400 mt-1">
                          ↓ {step.drop_off_count.toLocaleString()} dropped ({step.drop_off_rate.toFixed(1)}%)
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {result.insights.length > 0 && (
                <div className="mt-6 pt-4 border-t border-white/10">
                  <h4 className="text-sm font-medium text-gray-300 mb-2">Insights</h4>
                  {result.insights.map((insight, i) => (
                    <div key={i} className="text-sm text-gray-400 mb-1">{insight}</div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
