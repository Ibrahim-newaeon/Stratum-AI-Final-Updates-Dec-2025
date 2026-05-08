// =============================================================================
// Stratum AI — SQL Query Editor (Gap #4)
// =============================================================================

import { useState } from 'react';
import {
  ArrowPathIcon,
  PlayIcon,
  CommandLineIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface SQLResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  execution_time_ms: number;
  query: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'https://api.stratumai.app/api/v1';
const getToken = () => sessionStorage.getItem('access_token') || '';

const PANEL_SURFACE = 'bg-card border border-border rounded-xl p-4';
const FIELD_SURFACE =
  'bg-muted/40 border border-border rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary';

const SAMPLE_QUERIES = [
  'SELECT platform, SUM(total_spend_cents)/100.0 as spend\nFROM campaigns\nWHERE is_deleted = FALSE\nGROUP BY platform\nORDER BY spend DESC',
  "SELECT date, SUM(spend_cents)/100.0 as daily_spend\nFROM campaign_metrics\nWHERE date >= CURRENT_DATE - INTERVAL '30 days'\nGROUP BY date\nORDER BY date DESC",
  "SELECT name, roas, conversions\nFROM campaigns\nWHERE status = 'ACTIVE'\nORDER BY roas DESC\nLIMIT 20",
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
      setError('Network error — could not reach the analytics service.');
    }
    setLoading(false);
  };

  const copyQuery = (q: string) => {
    setQuery(q);
    setResult(null);
    setError('');
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-6">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <CommandLineIcon className="w-8 h-8 text-primary" />
            SQL Query Editor
          </h1>
          <p className="text-muted-foreground mt-2">
            Write SELECT queries against your tenant-scoped data
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Editor */}
          <div className="lg:col-span-2 space-y-4">
            <div className={PANEL_SURFACE}>
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm text-muted-foreground">Query</label>
                <div className="flex items-center gap-3">
                  <label className="text-sm text-muted-foreground">Limit:</label>
                  <select
                    value={limit}
                    onChange={(e) => setLimit(parseInt(e.target.value))}
                    className={cn(FIELD_SURFACE, 'px-2 py-1 text-sm')}
                  >
                    {[50, 100, 250, 500, 1000].map((n) => (
                      <option key={n} value={n} className="bg-card">
                        {n}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={10}
                className="w-full bg-muted/60 border border-border rounded-lg p-4 font-mono text-sm text-foreground focus:outline-none focus:border-primary resize-y"
                spellCheck={false}
              />
              <div className="flex items-center justify-between mt-3">
                <div className="text-xs text-muted-foreground">
                  SELECT-only · Max {limit} rows · Tenant-scoped
                </div>
                <button
                  onClick={runQuery}
                  disabled={loading || !query.trim()}
                  className="bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground px-5 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
                >
                  {loading ? (
                    <ArrowPathIcon className="w-5 h-5 animate-spin" />
                  ) : (
                    <PlayIcon className="w-5 h-5" />
                  )}
                  Run Query
                </button>
              </div>
            </div>

            {error && (
              <div className="bg-danger/10 border border-danger/30 text-danger rounded-lg p-4 text-sm">
                {error}
              </div>
            )}

            {!result && !loading && !error && (
              <div className="rounded-xl border border-dashed border-border p-10 text-center text-muted-foreground">
                <CommandLineIcon className="w-10 h-10 mx-auto mb-3 opacity-40" />
                <p className="text-sm">Run a query to see results.</p>
              </div>
            )}

            {result && result.rows.length === 0 && (
              <div className="rounded-xl border border-dashed border-border p-10 text-center text-muted-foreground">
                <p className="text-sm">Query returned 0 rows.</p>
              </div>
            )}

            {result && result.rows.length > 0 && (
              <div className={PANEL_SURFACE}>
                <div className="flex items-center justify-between mb-3">
                  <div className="text-sm text-muted-foreground">
                    {result.row_count} rows · {result.execution_time_ms}ms
                  </div>
                  <button
                    onClick={() =>
                      navigator.clipboard.writeText(JSON.stringify(result.rows, null, 2))
                    }
                    className="text-xs text-primary hover:underline flex items-center gap-1"
                  >
                    <DocumentDuplicateIcon className="w-3 h-3" /> Copy JSON
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        {result.columns.map((col) => (
                          <th
                            key={col}
                            className="text-left py-2 px-3 text-muted-foreground font-medium whitespace-nowrap"
                          >
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row, i) => (
                        <tr key={i} className="border-b border-border/50 hover:bg-muted/40">
                          {row.map((cell, j) => (
                            <td
                              key={j}
                              className="py-2 px-3 text-foreground whitespace-nowrap font-mono text-xs"
                            >
                              {String(cell ?? 'NULL')}
                            </td>
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
            <div className={PANEL_SURFACE}>
              <h3 className="text-sm font-medium text-foreground mb-3">Sample Queries</h3>
              <div className="space-y-3">
                {SAMPLE_QUERIES.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => copyQuery(q)}
                    className="w-full text-left bg-muted/40 hover:bg-muted/60 border border-border/50 rounded-lg p-3 text-xs font-mono text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {q.split('\n')[0]}...
                  </button>
                ))}
              </div>
            </div>

            <div className={PANEL_SURFACE}>
              <h3 className="text-sm font-medium text-foreground mb-2">Available Tables</h3>
              <div className="space-y-1 text-xs text-muted-foreground">
                {['campaigns', 'campaign_metrics', 'cdp_profiles', 'cdp_events'].map((t) => (
                  <div key={t} className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-success" />
                    {t}
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-warning/10 border border-warning/30 rounded-xl p-4">
              <h3 className="text-sm font-medium text-warning mb-2">Security</h3>
              <ul className="text-xs text-muted-foreground space-y-1">
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
