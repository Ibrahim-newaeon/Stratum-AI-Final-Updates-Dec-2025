// =============================================================================
// Stratum AI — Cohort Analysis (Gap #4)
// =============================================================================

import { useState } from 'react';
import { ArrowPathIcon, PlayIcon, UserGroupIcon } from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface CohortCell {
  period: number;
  value: number;
  percentage: number | null;
}

interface CohortRow {
  cohort_label: string;
  cohort_size: number;
  cells: CohortCell[];
}

interface CohortResult {
  metric: string;
  period: string;
  rows: CohortRow[];
  average_retention: number[];
  insights: string[];
}

const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';
const getToken = () => sessionStorage.getItem('access_token') || '';

const PANEL_SURFACE = 'bg-card border border-border rounded-xl p-6';
const FIELD_SURFACE =
  'bg-muted/40 border border-border rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary';

export default function CohortAnalysis() {
  const [metric, setMetric] = useState('retention');
  const [period, setPeriod] = useState('weekly');
  const [dateFrom, setDateFrom] = useState('2026-01-01');
  const [dateTo, setDateTo] = useState('2026-12-31');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CohortResult | null>(null);
  const [error, setError] = useState('');

  const analyze = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_URL}/analytics/advanced/cohorts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ metric, period, date_from: dateFrom, date_to: dateTo }),
      });
      const data = await res.json();
      if (data.success) {
        setResult(data.data);
      } else {
        setError(data.message || 'Cohort analysis failed.');
      }
    } catch (e) {
      setError('Network error — could not reach the analytics service.');
    }
    setLoading(false);
  };

  const cellColor = (pct: number | null) => {
    if (pct === null) return 'bg-muted/40 text-muted-foreground';
    if (pct > 60) return 'bg-success/20 text-success';
    if (pct > 30) return 'bg-warning/20 text-warning';
    return 'bg-danger/20 text-danger';
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <UserGroupIcon className="w-8 h-8 text-primary" />
            Cohort Analysis
          </h1>
          <p className="text-muted-foreground mt-2">Retention and behavior cohorts over time</p>
        </header>

        <div className={cn(PANEL_SURFACE, 'mb-6 flex flex-wrap gap-4 items-end')}>
          <div>
            <label className="block text-sm text-muted-foreground mb-1">Metric</label>
            <select
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              className={FIELD_SURFACE}
            >
              <option value="retention" className="bg-card">
                Retention
              </option>
              <option value="revenue" className="bg-card">
                Revenue
              </option>
              <option value="conversions" className="bg-card">
                Conversions
              </option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-muted-foreground mb-1">Period</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className={FIELD_SURFACE}
            >
              <option value="daily" className="bg-card">
                Daily
              </option>
              <option value="weekly" className="bg-card">
                Weekly
              </option>
              <option value="monthly" className="bg-card">
                Monthly
              </option>
            </select>
          </div>
          <div className="flex gap-3">
            <div>
              <label className="block text-sm text-muted-foreground mb-1">From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className={FIELD_SURFACE}
              />
            </div>
            <div>
              <label className="block text-sm text-muted-foreground mb-1">To</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className={FIELD_SURFACE}
              />
            </div>
          </div>
          <button
            onClick={analyze}
            disabled={loading}
            className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
          >
            {loading ? (
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
            ) : (
              <PlayIcon className="w-5 h-5" />
            )}
            Analyze
          </button>
        </div>

        {error && (
          <div className="bg-danger/10 border border-danger/30 text-danger rounded-lg p-4 mb-6">
            {error}
          </div>
        )}

        {!result && !loading && !error && (
          <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
            <UserGroupIcon className="w-10 h-10 mx-auto mb-3 opacity-40" />
            <p className="text-sm">Pick a metric and date range, then click Analyze.</p>
          </div>
        )}

        {result && result.rows.length === 0 && (
          <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted-foreground">
            <p className="text-sm">
              No cohort data in this window. Widen the date range or try another metric.
            </p>
          </div>
        )}

        {result && result.rows.length > 0 && (
          <div className="space-y-6">
            <div className={cn(PANEL_SURFACE, 'overflow-x-auto')}>
              <h3 className="text-lg font-semibold mb-4">
                {metric.charAt(0).toUpperCase() + metric.slice(1)} Cohorts
              </h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 px-3 text-muted-foreground font-medium">
                      Cohort
                    </th>
                    <th className="text-left py-2 px-3 text-muted-foreground font-medium">Size</th>
                    <th className="text-left py-2 px-3 text-muted-foreground font-medium">
                      Period 0
                    </th>
                    {result.rows[0]?.cells.slice(1).map((_, i) => (
                      <th key={i} className="text-left py-2 px-3 text-muted-foreground font-medium">
                        Period {i + 1}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, i) => (
                    <tr key={i} className="border-b border-border/50">
                      <td className="py-2 px-3 font-medium">{row.cohort_label}</td>
                      <td className="py-2 px-3 text-muted-foreground">{row.cohort_size}</td>
                      {row.cells.map((cell, j) => (
                        <td key={j} className="py-2 px-3">
                          <div
                            className={`inline-block px-2 py-1 rounded ${cellColor(cell.percentage)}`}
                          >
                            {cell.percentage !== null
                              ? `${cell.percentage.toFixed(1)}%`
                              : cell.value}
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {result.average_retention.length > 0 && (
              <div className={PANEL_SURFACE}>
                <h4 className="text-sm font-medium text-foreground mb-3">
                  Average Retention by Period
                </h4>
                <div className="flex items-end gap-2 h-32">
                  {result.average_retention.map((v, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <div
                        className="w-full bg-muted rounded-t relative"
                        style={{ height: `${Math.min(v * 1.5, 100)}%` }}
                      >
                        <div
                          className="absolute bottom-0 left-0 right-0 bg-primary/40 rounded-t"
                          style={{ height: '100%' }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground">P{i}</span>
                      <span className="text-xs text-foreground">{v.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.insights.length > 0 && (
              <div className={PANEL_SURFACE}>
                <h4 className="text-sm font-medium text-foreground mb-2">Insights</h4>
                {result.insights.map((insight, i) => (
                  <div key={i} className="text-sm text-muted-foreground mb-1">
                    {insight}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
