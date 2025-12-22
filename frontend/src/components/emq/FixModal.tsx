/**
 * EMQ Fix Modal
 * One-click fix system for EMQ issues
 */

import { useState, useEffect, useMemo } from 'react'
import {
  X,
  Wrench,
  CheckCircle,
  AlertTriangle,
  Loader2,
  ChevronRight,
  Zap,
  BookOpen,
  ArrowRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface RoasImpact {
  min_pct: number
  max_pct: number
  avg_pct: number
  confidence: 'high' | 'medium' | 'low'
  reasoning: string
}

interface FixSuggestion {
  issue_code: string
  one_click: boolean
  action: string
  description: string
  impact?: string
  guided_steps?: string[]
  current_value?: string
  roas_impact?: RoasImpact
}

interface FixRun {
  id: number
  platform: string
  issue_code: string
  action: string
  status: 'queued' | 'running' | 'success' | 'failed'
  error?: string | null
  applied_changes: Record<string, unknown>
  before_metrics: Record<string, unknown>
  after_metrics: Record<string, unknown>
  created_at?: string | null
  finished_at?: string | null
}

interface FixModalProps {
  open: boolean
  onClose: () => void
  platform: string
  from: string // YYYY-MM-DD
  to: string   // YYYY-MM-DD
  eventName?: string
}

function getHeaders() {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url, { credentials: 'include', headers: getHeaders() })
  if (!res.ok) throw new Error(`GET ${url} failed (${res.status})`)
  return res.json()
}

async function postJSON<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: getHeaders(),
    credentials: 'include',
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error((data as { detail?: string })?.detail || `POST ${url} failed (${res.status})`)
  return data
}

function MetricRow({ label, before, after }: { label: string; before: unknown; after: unknown }) {
  const beforeVal = typeof before === 'number' ? before.toFixed(3) : String(before ?? '-')
  const afterVal = typeof after === 'number' ? after.toFixed(3) : String(after ?? '-')

  const improved = typeof before === 'number' && typeof after === 'number' && after > before

  return (
    <div className="flex items-center justify-between py-1.5 text-sm">
      <div className="text-muted-foreground">{label}</div>
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground font-mono">{beforeVal}</span>
        <ArrowRight className="w-3 h-3 text-muted-foreground" />
        <span className={cn('font-mono', improved ? 'text-green-500' : 'text-foreground')}>
          {afterVal}
        </span>
      </div>
    </div>
  )
}

export function FixModal({ open, onClose, platform, from, to, eventName }: FixModalProps) {
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState<FixSuggestion[]>([])
  const [selected, setSelected] = useState<FixSuggestion | null>(null)
  const [run, setRun] = useState<FixRun | null>(null)
  const [error, setError] = useState<string | null>(null)

  const suggestionsUrl = useMemo(() => {
    const params = new URLSearchParams({ platform, from, to })
    if (eventName) params.set('event_name', eventName)
    return `/api/v1/qa/fixes/suggestions?${params.toString()}`
  }, [platform, from, to, eventName])

  // Fetch suggestions when modal opens
  useEffect(() => {
    if (!open) return
    setLoading(true)
    setError(null)
    setRun(null)
    setSelected(null)

    fetchJSON<{ items: FixSuggestion[] }>(suggestionsUrl)
      .then((d) => setSuggestions(d.items || []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [open, suggestionsUrl])

  // Poll for run status updates
  useEffect(() => {
    if (!run?.id) return
    if (run.status === 'success' || run.status === 'failed') return

    const interval = setInterval(() => {
      fetchJSON<FixRun>(`/api/v1/qa/fixes/run/${run.id}`)
        .then(setRun)
        .catch(() => {})
    }, 1500)

    return () => clearInterval(interval)
  }, [run?.id, run?.status])

  async function applyFix(s: FixSuggestion) {
    setError(null)
    setLoading(true)
    try {
      const res = await postJSON<{ fix_run_id: number }>('/api/v1/qa/fixes/apply', {
        platform,
        issue_code: s.issue_code,
        dry_run: false,
      })

      const fixRunId = res.fix_run_id
      const fresh = await fetchJSON<FixRun>(`/api/v1/qa/fixes/run/${fixRunId}`)
      setRun(fresh)
    } catch (e) {
      setError((e as Error)?.message || 'Failed to apply fix')
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-4xl rounded-2xl bg-card border shadow-xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <div className="text-lg font-semibold flex items-center gap-2">
              <Wrench className="w-5 h-5 text-primary" />
              One-Click Fix
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Platform: {platform} | Range: {from} to {to}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-4 overflow-y-auto flex-1">
          {/* Left: Suggestions */}
          <div className="rounded-xl border bg-muted/30 p-4">
            <div className="text-sm font-semibold mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              Detected Issues
            </div>

            {loading && (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            )}

            {error && !loading && (
              <div className="text-sm text-red-500 py-4">{error}</div>
            )}

            {!loading && suggestions.length === 0 && !error && (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <CheckCircle className="w-8 h-8 text-green-500 mb-2" />
                <p className="text-sm font-medium text-green-600">All Good!</p>
                <p className="text-xs text-muted-foreground">No issues detected</p>
              </div>
            )}

            <div className="space-y-2">
              {suggestions.map((s) => (
                <button
                  key={s.issue_code}
                  className={cn(
                    'w-full text-left rounded-xl border p-3 transition-all',
                    selected?.issue_code === s.issue_code
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50 bg-background'
                  )}
                  onClick={() => setSelected(s)}
                >
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-medium">{s.issue_code.replace(/_/g, ' ')}</div>
                    <div className="flex items-center gap-2">
                      {s.roas_impact && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 font-medium">
                          +{s.roas_impact.min_pct}-{s.roas_impact.max_pct}% ROAS
                        </span>
                      )}
                      <span
                        className={cn(
                          'text-xs px-2 py-0.5 rounded-full',
                          s.one_click
                            ? 'bg-green-500/10 text-green-600'
                            : 'bg-amber-500/10 text-amber-600'
                        )}
                      >
                        {s.one_click ? 'One-click' : 'Guided'}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">{s.description}</div>
                  {s.current_value && (
                    <div className="text-xs text-amber-500 mt-1">Current: {s.current_value}</div>
                  )}
                  {s.roas_impact && (
                    <div className="mt-2 p-2 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
                      <div className="flex items-center gap-1 text-xs text-emerald-600 font-medium mb-1">
                        <span>ROAS Impact:</span>
                        <span className={cn(
                          'px-1.5 py-0.5 rounded text-[10px]',
                          s.roas_impact.confidence === 'high' ? 'bg-emerald-500/20' :
                          s.roas_impact.confidence === 'medium' ? 'bg-yellow-500/20 text-yellow-600' :
                          'bg-gray-500/20 text-gray-600'
                        )}>
                          {s.roas_impact.confidence} confidence
                        </span>
                      </div>
                      <div className="text-[11px] text-muted-foreground leading-relaxed">
                        {s.roas_impact.reasoning}
                      </div>
                    </div>
                  )}
                </button>
              ))}
            </div>

            {/* Action Button */}
            {selected && (
              <div className="mt-4">
                {selected.one_click ? (
                  <button
                    disabled={loading}
                    className="w-full rounded-xl bg-gradient-stratum hover:opacity-90 disabled:opacity-60 text-white py-2.5 text-sm font-semibold flex items-center justify-center gap-2 shadow-glow"
                    onClick={() => applyFix(selected)}
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Zap className="w-4 h-4" />
                    )}
                    Apply Fix
                  </button>
                ) : (
                  <div className="rounded-xl border bg-muted/50 p-3">
                    <div className="font-semibold text-sm mb-2 flex items-center gap-2">
                      <BookOpen className="w-4 h-4 text-primary" />
                      Guided Steps Required
                    </div>
                    <ul className="space-y-1">
                      {(selected.guided_steps || []).map((step, i) => (
                        <li key={i} className="text-xs text-muted-foreground flex gap-2">
                          <ChevronRight className="w-3 h-3 mt-0.5 flex-shrink-0" />
                          {step}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right: Fix Run Status */}
          <div className="rounded-xl border bg-muted/30 p-4">
            <div className="text-sm font-semibold mb-3 flex items-center gap-2">
              <Wrench className="w-4 h-4 text-primary" />
              Fix Run
            </div>

            {!run && (
              <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
                <Wrench className="w-8 h-8 mb-2 opacity-30" />
                <p className="text-sm">No fix applied yet</p>
                <p className="text-xs">Select an issue and click Apply</p>
              </div>
            )}

            {run && (
              <div className="space-y-4">
                {/* Status Badge */}
                <div className="flex items-center justify-between">
                  <div className="text-sm">Run #{run.id}</div>
                  <span
                    className={cn(
                      'text-xs px-2 py-1 rounded-full font-medium',
                      run.status === 'success' && 'bg-green-500/10 text-green-600',
                      run.status === 'failed' && 'bg-red-500/10 text-red-600',
                      (run.status === 'queued' || run.status === 'running') &&
                        'bg-blue-500/10 text-blue-600'
                    )}
                  >
                    {run.status === 'running' && (
                      <Loader2 className="w-3 h-3 animate-spin inline mr-1" />
                    )}
                    {run.status}
                  </span>
                </div>

                {/* Error Message */}
                {run.error && (
                  <div className="text-sm text-red-500 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                    {run.error}
                  </div>
                )}

                {/* Applied Changes */}
                <div className="rounded-xl border bg-background p-3">
                  <div className="text-xs text-muted-foreground mb-2">Applied Changes</div>
                  <pre className="text-xs whitespace-pre-wrap font-mono">
                    {JSON.stringify(run.applied_changes || {}, null, 2)}
                  </pre>
                </div>

                {/* Before/After Metrics */}
                <div className="rounded-xl border bg-background p-3">
                  <div className="text-xs text-muted-foreground mb-2">Before → After</div>

                  <MetricRow
                    label="Success Rate"
                    before={run.before_metrics?.success_rate}
                    after={run.after_metrics?.success_rate}
                  />
                  <MetricRow
                    label="Avg Score"
                    before={run.before_metrics?.avg_score}
                    after={run.after_metrics?.avg_score}
                  />
                  <MetricRow
                    label="Duplicate Rate"
                    before={run.before_metrics?.duplicate_rate}
                    after={run.after_metrics?.duplicate_rate}
                  />

                  {run.before_metrics?.coverage && (
                    <>
                      <div className="text-xs text-muted-foreground mt-2 mb-1">Coverage</div>
                      <MetricRow
                        label="Email"
                        before={(run.before_metrics.coverage as Record<string, number>)?.em}
                        after={(run.after_metrics?.coverage as Record<string, number>)?.em}
                      />
                      <MetricRow
                        label="Cookie (_fbp)"
                        before={(run.before_metrics.coverage as Record<string, number>)?.fbp}
                        after={(run.after_metrics?.coverage as Record<string, number>)?.fbp}
                      />
                      <MetricRow
                        label="IP"
                        before={(run.before_metrics.coverage as Record<string, number>)?.ip}
                        after={(run.after_metrics?.coverage as Record<string, number>)?.ip}
                      />
                    </>
                  )}

                  {/* ROAS Projection */}
                  {run.after_metrics?.projected_roas && (
                    <div className="mt-3 p-3 rounded-lg bg-gradient-to-r from-emerald-500/10 to-green-500/10 border border-emerald-500/20">
                      <div className="text-xs text-emerald-600 font-semibold mb-2">Projected ROAS Impact</div>
                      <div className="flex items-center justify-between">
                        <div className="text-sm text-muted-foreground">ROAS</div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-muted-foreground">
                            {(run.before_metrics?.projected_roas as number)?.toFixed(2)}x
                          </span>
                          <ArrowRight className="w-3 h-3 text-emerald-500" />
                          <span className="font-mono text-emerald-600 font-semibold">
                            {(run.after_metrics?.projected_roas as number)?.toFixed(2)}x
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-600 font-medium">
                            +{run.after_metrics?.roas_improvement_pct as number}%
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default FixModal
