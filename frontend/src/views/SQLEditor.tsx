// =============================================================================
// Stratum AI — SQL Query Editor (Gap #4)
// =============================================================================

import { useState } from 'react';
import { ArrowPathIcon, PlayIcon, CommandLineIcon, DocumentDuplicateIcon } from '@heroicons/react/24/outline';

interface SQLResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  execution_time_ms: number;
  query: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';
const getToken = () => sessionStorage.getItem('access_token') || '';

const SAMPLE_QUERIES = [
  'SELECT platform, SUM(total_spend_cents)/100.0 as spend\nFROM campaigns\nWHERE is_deleted = FALSE\nGROUP BY platform\nORDER BY spend DESC',
  'SELECT date, SUM(spend_cents)/100.0 as daily_spend\nFROM campaign_metrics\nWHERE date >= CURRENT_DATE - INTERVAL \'30 days\'\nGROUP BY date\nORDER BY date DESC',
  'SELECT name, roas, conversions\nFROM campaigns\nWHERE status = \'ACTIVE\'\nORDER BY roas DESC\nLIMIT 20',
];

export default function SQLEditor() {
  
  const [query, setQuery] = useState(SAMPLE_QUERIES[0]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SQLResult | null>(null);
  const [error, setError] = useState('');
  const [limit, setLimit] = useState(100);

  const runQuery = async () => {
    const token = getToken();
    if (!token || !query.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/analytics/advanced/sql`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ query, limit }),
      });
      const data = await res.json();
      if (data.success) setResult(data.data);
      else setError(data.message || 'Query failed');
    } catch (e) {
      setError('Network error');
    }
    setLoading(false);
  };

  const copyQuery = (q: string) => {
    setQuery(q);
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-[#050B18] text-white p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <CommandLineIcon className="w-8 h-8 text-[#00F5FF]" />
            SQL Query Editor
          </h1>
          <p className="text-gray-400 mt-2">Write SELECT queries against your tenant-scoped data</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Editor */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-foreground/[0.02] border border-foreground/10 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm text-gray-400">Query</label>
                <div className="flex items-center gap-3">
                  <label className="text-sm text-gray-400">Limit:</label>
                  <select
                    value={limit}
                    onChange={(e) => setLimit(parseInt(e.target.value))}
                    className="bg-foreground/[0.03] border border-foreground/10 rounded px-2 py-1 text-sm text-white"
                  >
                    {[50, 100, 250, 500, 1000].map((n) => (
                      <option key={n} value={n} className="bg-[#0A1628]">{n}</option>
                    ))}
                  </select>
                </div>
              </div>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={10}
                className="w-full bg-black/40 border border-foreground/10 rounded-lg p-4 font-mono text-sm text-gray-300 focus:outline-none focus:border-primary resize-y"
                spellCheck={false}
              />
              <div className="flex items-center justify-between mt-3">
                <div className="text-xs text-gray-500">SELECT-only · Max {limit} rows · Tenant-scoped</div>
                <button
                  onClick={runQuery}
                  disabled={loading || !query.trim()}
                  className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-white px-5 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
                >
                  {loading ? <ArrowPathIcon className="w-5 h-5 animate-spin" /> : <PlayIcon className="w-5 h-5" />}
                  Run Query
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg p-4 text-sm">
                {error}
              </div>
            )}

            {result && (
              <div className="bg-foreground/[0.02] border border-foreground/10 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm text-gray-400">
                    {result.row_count} rows · {result.execution_time_ms}ms
                  </div>
                  <button
                    onClick={() => navigator.clipboard.writeText(JSON.stringify(result.rows, null, 2))}
                    className="text-xs text-[#00F5FF] hover:underline flex items-center gap-1"
                  >
                    <DocumentDuplicateIcon className="w-3 h-3" /> Copy JSON
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-foreground/10">
                        {result.columns.map((col) => (
                          <th key={col} className="text-left py-2 px-3 text-gray-400 font-medium whitespace-nowrap">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row, i) => (
                        <tr key={i} className="border-b border-foreground/5 hover:bg-foreground/[0.02]">
                          {row.map((cell, j) => (
                            <td key={j} className="py-2 px-3 text-gray-300 whitespace-nowrap font-mono text-xs">{String(cell ?? 'NULL')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Right: Sample Queries */}
          <div className="space-y-4">
            <div className="bg-foreground/[0.02] border border-foreground/10 rounded-xl p-4">
              <h3 className="text-sm font-medium text-gray-300 mb-3">Sample Queries</h3>
              <div className="space-y-3">
                {SAMPLE_QUERIES.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => copyQuery(q)}
                    className="w-full text-left bg-foreground/[0.03] hover:bg-foreground/[0.06] border border-foreground/5 rounded-lg p-3 text-xs font-mono text-gray-400 hover:text-gray-200 transition-colors"
                  >
                    {q.split('\n')[0]}...
                  </button>
                ))}
              </div>
            </div>

            <div className="bg-foreground/[0.02] border border-foreground/10 rounded-xl p-4">
              <h3 className="text-sm font-medium text-gray-300 mb-2">Available Tables</h3>
              <div className="space-y-1 text-xs text-gray-400">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  campaigns
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  campaign_metrics
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  cdp_profiles
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-400" />
                  cdp_events
                </div>
              </div>
            </div>

            <div className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-4">
              <h3 className="text-sm font-medium text-yellow-400 mb-2">Security</h3>
              <ul className="text-xs text-gray-400 space-y-1">
                <li>• Only SELECT statements allowed</li>
                <li>• INSERT/UPDATE/DELETE blocked</li>
                <li>• Tenant ID auto-injected</li>
                <li>• Max 1,000 rows returned</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
