// =============================================================================
// Stratum AI — Funnel Analysis (Gap #4)
// =============================================================================

import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  ArrowPathIcon,
  PlusIcon,
  TrashIcon,
  PlayIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';

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

const PANEL_SURFACE = 'bg-card border border-border rounded-xl p-6';
const FIELD_SURFACE =
  'w-full bg-muted/40 border border-border rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary';

export default function FunnelAnalysis() {
  const [name, setName] = useState('Purchase Funnel');
  const [steps, setSteps] = useState<string[]>(['impression', 'click', 'conversion']);
  const [dateFrom, setDateFrom] = useState('2026-01-01');
  const [dateTo, setDateTo] = useState('2026-12-31');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FunnelResult | null>(null);
  const [error, setError] = useState('');

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
    setError('');
    try {
      const res = await fetch(`${API_URL}/analytics/advanced/funnel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({
          name,
          steps: steps.filter(Boolean),
          date_from: dateFrom,
          date_to: dateTo,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setResult(data.data);
      } else {
        setError(data.message || 'Funnel analysis failed.');
      }
    } catch (e) {
      setError('Network error — could not reach the analytics service.');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-6">
    <div className="min-h-screen bg-background text-white p-6">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <FunnelIcon className="w-8 h-8 text-primary" />
            Funnel Analysis
          </h1>
          <p className="text-muted-foreground mt-2">
            Multi-step conversion funnels with drop-off visualization
          </p>
        </header>

        <div className={cn(PANEL_SURFACE, 'mb-6')}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm text-muted-foreground mb-1">Funnel Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={FIELD_SURFACE}
              />
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-sm text-muted-foreground mb-1">From</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className={FIELD_SURFACE}
                />
              </div>
              <div className="flex-1">
                <label className="block text-sm text-muted-foreground mb-1">To</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className={FIELD_SURFACE}
                />
              </div>
            </div>
          </div>

          <label className="block text-sm text-muted-foreground mb-2">Steps (in order)</label>
          {steps.map((s, i) => (
            <div key={i} className="flex gap-2 mb-2">
              <span className="text-muted-foreground/60 w-6 text-center pt-2">{i + 1}</span>
              <select
                value={s}
                onChange={(e) => updateStep(i, e.target.value)}
                className={cn(FIELD_SURFACE, 'flex-1')}
              >
                <option value="" className="bg-card">
                  Select event...
                </option>
                {['impression', 'click', 'landing', 'add_to_cart', 'conversion', 'purchase'].map(
                  (opt) => (
                    <option key={opt} value={opt} className="bg-card">
                      {opt}
                    </option>
                  )
                )}
                <option value="" className="bg-card">Select event...</option>
                {['impression', 'click', 'landing', 'add_to_cart', 'conversion', 'purchase'].map((opt) => (
                  <option key={opt} value={opt} className="bg-card">{opt}</option>
                ))}
              </select>
              {steps.length > 2 && (
                <button
                  onClick={() => removeStep(i)}
                  className="text-danger hover:text-danger/80 p-2"
                  aria-label={`Remove step ${i + 1}`}
                >
                  <TrashIcon className="w-5 h-5" />
                </button>
              )}
            </div>
          ))}
          <button
            onClick={addStep}
            className="text-sm text-primary flex items-center gap-1 mt-2 hover:underline"
          >
          <button onClick={addStep} className="text-sm text-primary flex items-center gap-1 mt-2 hover:underline">
            <PlusIcon className="w-4 h-4" /> Add step
          </button>

          <button
            onClick={analyze}
            disabled={loading || steps.filter(Boolean).length < 2}
            className="mt-4 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
          >
            {loading ? (
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
            ) : (
              <PlayIcon className="w-5 h-5" />
            )}
            Analyze Funnel
          </button>
        </div>

        {error && (
          <div className="bg-danger/10 border border-danger/30 text-danger rounded-lg p-4 mb-6">
            {error}
          </div>
        )}

        {!result && !loading && !error && (
          <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
            <FunnelIcon className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">
              Pick at least two steps and a date range, then click Analyze Funnel.
            </p>
          </div>
        )}

        {result && result.steps.length === 0 && (
          <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
            <p className="text-sm">
              No funnel data in this window. Try different events or a wider date range.
            </p>
          </div>
        )}

        {result && result.steps.length > 0 && (
          <div className="space-y-6">
            <div className={PANEL_SURFACE}>
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold">{result.name}</h3>
                <div className="text-right">
                  <div className="text-2xl font-bold">
                    {result.overall_conversion_rate.toFixed(2)}%
                  </div>
                  <div className="text-xs text-muted-foreground">overall conversion</div>
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
                        <span className="text-sm text-muted-foreground">
                          {step.count.toLocaleString()}
                        </span>
                      </div>
                      <div className="h-10 bg-muted rounded-lg overflow-hidden relative">
                        <div
                          className={cn(
                            'h-full rounded-lg transition-all flex items-center px-3',
                            i === 0
                              ? 'bg-primary'
                              : i === result.steps.length - 1
                                ? 'bg-success'
                                : 'bg-info'
                            i === 0 ? 'bg-primary' :
                            i === result.steps.length - 1 ? 'bg-green-400' :
                            'bg-primary'
                          )}
                          style={{ width: `${widthPct}%` }}
                        >
                          <span className="text-xs font-bold text-primary-foreground whitespace-nowrap">
                            {step.conversion_rate_from_previous
                              ? `${step.conversion_rate_from_previous.toFixed(1)}%`
                              : '100%'}
                          </span>
                        </div>
                      </div>
                      {step.drop_off_count > 0 && (
                        <div className="text-xs text-danger mt-1">
                          ↓ {step.drop_off_count.toLocaleString()} dropped (
                          {step.drop_off_rate.toFixed(1)}%)
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {result.insights.length > 0 && (
                <div className="mt-6 pt-4 border-t border-border">
                  <h4 className="text-sm font-medium text-foreground mb-2">Insights</h4>
                  {result.insights.map((insight, i) => (
                    <div key={i} className="text-sm text-muted-foreground mb-1">
                      {insight}
                    </div>
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
