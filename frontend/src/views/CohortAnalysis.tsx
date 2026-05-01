// =============================================================================
// Stratum AI — Cohort Analysis (Gap #4)
// =============================================================================

import { useState } from 'react';
import { ArrowPathIcon, PlayIcon, UserGroupIcon } from '@heroicons/react/24/outline';

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

export default function CohortAnalysis() {
  
  const [metric, setMetric] = useState('retention');
  const [period, setPeriod] = useState('weekly');
  const [dateFrom, setDateFrom] = useState('2026-01-01');
  const [dateTo, setDateTo] = useState('2026-12-31');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CohortResult | null>(null);

  const analyze = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/analytics/advanced/cohorts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ metric, period, date_from: dateFrom, date_to: dateTo }),
      });
      const data = await res.json();
      if (data.success) setResult(data.data);
    } catch (e) { /* ignore */ }
    setLoading(false);
  };

  const cellColor = (pct: number | null) => {
    if (pct === null) return 'bg-white/[0.02]';
    const intensity = pct / 100;
    if (intensity > 0.6) return 'bg-green-500/30 text-green-300';
    if (intensity > 0.3) return 'bg-yellow-500/20 text-yellow-300';
    return 'bg-red-500/20 text-red-300';
  };

  return (
    <div className="min-h-screen bg-[#050B18] text-white p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <UserGroupIcon className="w-8 h-8 text-[#00F5FF]" />
            Cohort Analysis
          </h1>
          <p className="text-gray-400 mt-2">Retention and behavior cohorts over time</p>
        </header>

        <div className="bg-white/[0.02] border border-white/10 rounded-xl p-6 mb-6 flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Metric</label>
            <select value={metric} onChange={(e) => setMetric(e.target.value)} className="bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white">
              <option value="retention" className="bg-[#0A1628]">Retention</option>
              <option value="revenue" className="bg-[#0A1628]">Revenue</option>
              <option value="conversions" className="bg-[#0A1628]">Conversions</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Period</label>
            <select value={period} onChange={(e) => setPeriod(e.target.value)} className="bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white">
              <option value="daily" className="bg-[#0A1628]">Daily</option>
              <option value="weekly" className="bg-[#0A1628]">Weekly</option>
              <option value="monthly" className="bg-[#0A1628]">Monthly</option>
            </select>
          </div>
          <div className="flex gap-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">From</label>
              <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">To</label>
              <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="bg-white/[0.03] border border-white/10 rounded-lg px-3 py-2 text-white" />
            </div>
          </div>
          <button
            onClick={analyze}
            disabled={loading}
            className="bg-primary hover:bg-[#ff4d85] disabled:opacity-50 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
          >
            {loading ? <ArrowPathIcon className="w-5 h-5 animate-spin" /> : <PlayIcon className="w-5 h-5" />}
            Analyze
          </button>
        </div>

        {result && (
          <div className="space-y-6">
            <div className="bg-white/[0.02] border border-white/10 rounded-xl p-6 overflow-x-auto">
              <h3 className="text-lg font-semibold mb-4">{metric.charAt(0).toUpperCase() + metric.slice(1)} Cohorts</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Cohort</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Size</th>
                    <th className="text-left py-2 px-3 text-gray-400 font-medium">Period 0</th>
                    {result.rows[0]?.cells.slice(1).map((_, i) => (
                      <th key={i} className="text-left py-2 px-3 text-gray-400 font-medium">Period {i + 1}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row, i) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-2 px-3 font-medium">{row.cohort_label}</td>
                      <td className="py-2 px-3 text-gray-400">{row.cohort_size}</td>
                      {row.cells.map((cell, j) => (
                        <td key={j} className="py-2 px-3">
                          <div className={`inline-block px-2 py-1 rounded ${cellColor(cell.percentage)}`}>
                            {cell.percentage !== null ? `${cell.percentage.toFixed(1)}%` : cell.value}
                          </div>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {result.average_retention.length > 0 && (
              <div className="bg-white/[0.02] border border-white/10 rounded-xl p-6">
                <h4 className="text-sm font-medium text-gray-300 mb-3">Average Retention by Period</h4>
                <div className="flex items-end gap-2 h-32">
                  {result.average_retention.map((v, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <div className="w-full bg-white/10 rounded-t relative" style={{ height: `${Math.min(v * 1.5, 100)}%` }}>
                        <div className="absolute bottom-0 left-0 right-0 bg-[#00F5FF]/40 rounded-t" style={{ height: '100%' }} />
                      </div>
                      <span className="text-xs text-gray-500">P{i}</span>
                      <span className="text-xs text-gray-400">{v.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.insights.length > 0 && (
              <div className="bg-white/[0.02] border border-white/10 rounded-xl p-6">
                <h4 className="text-sm font-medium text-gray-300 mb-2">Insights</h4>
                {result.insights.map((insight, i) => (
                  <div key={i} className="text-sm text-gray-400 mb-1">{insight}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
