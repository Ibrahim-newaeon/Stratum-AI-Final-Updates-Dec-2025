/**
 * CDP Anomaly Detection Dashboard Component
 * Monitor and visualize event volume anomalies
 */

import { useState } from 'react'
import {
  AlertTriangle,
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Loader2,
  BarChart3,
  Clock,
  Zap,
  Settings,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Shield,
  ChevronDown,
  Info,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useEventAnomalies,
  useAnomalySummary,
  AnomalySeverity,
  EventAnomaly,
} from '@/api/cdp'

// Severity configuration
const SEVERITY_CONFIG: Record<AnomalySeverity, {
  label: string
  color: string
  bgColor: string
  icon: React.ReactNode
}> = {
  low: {
    label: 'Low',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    icon: <Info className="w-4 h-4" />,
  },
  medium: {
    label: 'Medium',
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
    icon: <AlertCircle className="w-4 h-4" />,
  },
  high: {
    label: 'High',
    color: 'text-orange-500',
    bgColor: 'bg-orange-500/10',
    icon: <AlertTriangle className="w-4 h-4" />,
  },
  critical: {
    label: 'Critical',
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    icon: <XCircle className="w-4 h-4" />,
  },
}

// Health status configuration
const HEALTH_CONFIG = {
  healthy: {
    label: 'Healthy',
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    icon: <CheckCircle2 className="w-5 h-5" />,
  },
  fair: {
    label: 'Fair',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    icon: <Activity className="w-5 h-5" />,
  },
  degraded: {
    label: 'Degraded',
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
    icon: <AlertCircle className="w-5 h-5" />,
  },
  critical: {
    label: 'Critical',
    color: 'text-red-500',
    bgColor: 'bg-red-500/10',
    icon: <AlertTriangle className="w-5 h-5" />,
  },
  unknown: {
    label: 'Unknown',
    color: 'text-gray-500',
    bgColor: 'bg-gray-500/10',
    icon: <Info className="w-5 h-5" />,
  },
}

// Trend icon component
function TrendIcon({ trend }: { trend: 'increasing' | 'stable' | 'decreasing' }) {
  switch (trend) {
    case 'increasing':
      return <TrendingUp className="w-4 h-4 text-green-500" />
    case 'decreasing':
      return <TrendingDown className="w-4 h-4 text-red-500" />
    default:
      return <Minus className="w-4 h-4 text-gray-500" />
  }
}

// Anomaly card component
interface AnomalyCardProps {
  anomaly: EventAnomaly
}

function AnomalyCard({ anomaly }: AnomalyCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const severityConfig = SEVERITY_CONFIG[anomaly.severity]

  return (
    <div
      className={cn(
        'p-4 rounded-xl border transition-all',
        severityConfig.bgColor.replace('/10', '/5')
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className={cn('p-2 rounded-lg', severityConfig.bgColor, severityConfig.color)}>
            {severityConfig.icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-semibold">{anomaly.source_name}</h4>
              <span className={cn(
                'px-2 py-0.5 rounded-full text-xs font-medium',
                severityConfig.bgColor,
                severityConfig.color
              )}>
                {severityConfig.label}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              {anomaly.metric}: {anomaly.direction === 'high' ? 'Higher' : 'Lower'} than expected
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className={cn(
            'text-2xl font-bold',
            anomaly.pct_change >= 0 ? 'text-red-500' : 'text-green-500'
          )}>
            {anomaly.pct_change >= 0 ? '+' : ''}{anomaly.pct_change.toFixed(1)}%
          </div>
          <div className="text-xs text-muted-foreground">from baseline</div>
        </div>
      </div>

      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 mt-3 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ChevronDown className={cn('w-4 h-4 transition-transform', isExpanded && 'rotate-180')} />
        Technical Details
      </button>

      {isExpanded && (
        <div className="mt-3 p-3 rounded-lg bg-muted/50 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground block">Z-Score</span>
            <span className="font-medium">{anomaly.zscore.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-muted-foreground block">Current Value</span>
            <span className="font-medium">{anomaly.current_value.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted-foreground block">Baseline Mean</span>
            <span className="font-medium">{anomaly.baseline_mean.toFixed(1)}</span>
          </div>
          <div>
            <span className="text-muted-foreground block">Baseline Std</span>
            <span className="font-medium">{anomaly.baseline_std.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export function AnomalyDashboard() {
  const [windowDays, setWindowDays] = useState(7)
  const [zscoreThreshold, setZscoreThreshold] = useState(2.0)
  const [showSettings, setShowSettings] = useState(false)

  const { data: summary, isLoading: summaryLoading, refetch: refetchSummary } = useAnomalySummary()
  const {
    data: anomalies,
    isLoading: anomaliesLoading,
    refetch: refetchAnomalies
  } = useEventAnomalies({ window_days: windowDays, zscore_threshold: zscoreThreshold })

  const isLoading = summaryLoading || anomaliesLoading

  const handleRefresh = () => {
    refetchSummary()
    refetchAnomalies()
  }

  const healthConfig = HEALTH_CONFIG[summary?.health_status || 'unknown']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Activity className="w-6 h-6 text-primary" />
            Anomaly Detection
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Monitor event volume anomalies and data quality
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={cn(
              'flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors',
              showSettings ? 'bg-primary/10 border-primary' : 'hover:bg-muted'
            )}
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Refresh
          </button>
        </div>
      </div>

      {/* Settings panel */}
      {showSettings && (
        <div className="p-4 rounded-xl border bg-card">
          <h3 className="font-medium mb-4">Detection Settings</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">Analysis Window</label>
              <select
                value={windowDays}
                onChange={(e) => setWindowDays(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border bg-background"
              >
                <option value={3}>3 days</option>
                <option value={7}>7 days</option>
                <option value={14}>14 days</option>
                <option value={30}>30 days</option>
              </select>
              <p className="text-xs text-muted-foreground mt-1">
                Historical data used for baseline calculation
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">Z-Score Threshold</label>
              <select
                value={zscoreThreshold}
                onChange={(e) => setZscoreThreshold(Number(e.target.value))}
                className="w-full px-3 py-2 rounded-lg border bg-background"
              >
                <option value={1.5}>1.5 (More sensitive)</option>
                <option value={2.0}>2.0 (Standard)</option>
                <option value={2.5}>2.5 (Less sensitive)</option>
                <option value={3.0}>3.0 (Critical only)</option>
              </select>
              <p className="text-xs text-muted-foreground mt-1">
                Lower values detect more anomalies
              </p>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : (
        <>
          {/* Health status banner */}
          {summary && (
            <div className={cn(
              'p-6 rounded-xl border flex items-center justify-between',
              healthConfig.bgColor
            )}>
              <div className="flex items-center gap-4">
                <div className={cn('p-3 rounded-xl bg-background', healthConfig.color)}>
                  {healthConfig.icon}
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">System Health</div>
                  <div className={cn('text-2xl font-bold', healthConfig.color)}>
                    {healthConfig.label}
                  </div>
                </div>
              </div>
              <div className="text-right text-sm text-muted-foreground">
                <Clock className="w-4 h-4 inline mr-1" />
                As of {new Date(summary.as_of).toLocaleString()}
              </div>
            </div>
          )}

          {/* Summary stats */}
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-4 rounded-xl border bg-card">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <Zap className="w-4 h-4" />
                  Events Today
                </div>
                <div className="text-2xl font-bold">{summary.events_today.toLocaleString()}</div>
              </div>
              <div className="p-4 rounded-xl border bg-card">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <BarChart3 className="w-4 h-4" />
                  Events (7d)
                </div>
                <div className="text-2xl font-bold">{summary.events_7d.toLocaleString()}</div>
              </div>
              <div className="p-4 rounded-xl border bg-card">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <TrendIcon trend={summary.volume_trend} />
                  WoW Change
                </div>
                <div className={cn(
                  'text-2xl font-bold',
                  summary.wow_change_pct >= 0 ? 'text-green-500' : 'text-red-500'
                )}>
                  {summary.wow_change_pct >= 0 ? '+' : ''}{summary.wow_change_pct.toFixed(1)}%
                </div>
              </div>
              <div className="p-4 rounded-xl border bg-card">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <Activity className="w-4 h-4" />
                  Volume Trend
                </div>
                <div className="text-2xl font-bold capitalize flex items-center gap-2">
                  <TrendIcon trend={summary.volume_trend} />
                  {summary.volume_trend}
                </div>
              </div>
              <div className="p-4 rounded-xl border bg-card">
                <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                  <Shield className="w-4 h-4" />
                  Avg EMQ Score
                </div>
                <div className="text-2xl font-bold">
                  {summary.avg_emq_score ? summary.avg_emq_score.toFixed(1) : '-'}
                </div>
              </div>
            </div>
          )}

          {/* Anomalies section */}
          {anomalies && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-primary" />
                  Detected Anomalies
                  {anomalies.anomaly_count > 0 && (
                    <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-sm font-medium">
                      {anomalies.anomaly_count}
                    </span>
                  )}
                </h3>
                <div className="text-sm text-muted-foreground">
                  {anomalies.total_sources_analyzed} sources analyzed
                </div>
              </div>

              {/* Alert banners for critical/high */}
              {(anomalies.has_critical || anomalies.has_high) && (
                <div className={cn(
                  'mb-4 p-4 rounded-lg flex items-center gap-3',
                  anomalies.has_critical ? 'bg-red-500/10' : 'bg-orange-500/10'
                )}>
                  <AlertTriangle className={cn(
                    'w-5 h-5',
                    anomalies.has_critical ? 'text-red-500' : 'text-orange-500'
                  )} />
                  <div>
                    <div className="font-medium">
                      {anomalies.has_critical ? 'Critical Anomalies Detected' : 'High Severity Anomalies Detected'}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Immediate attention may be required to investigate unusual data patterns
                    </p>
                  </div>
                </div>
              )}

              {anomalies.anomaly_count === 0 ? (
                <div className="text-center py-12 bg-card border rounded-xl">
                  <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
                  <h3 className="font-semibold mb-2">No Anomalies Detected</h3>
                  <p className="text-sm text-muted-foreground">
                    All event volumes are within expected ranges for the past {anomalies.analysis_period_days} days
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Group by severity */}
                  {['critical', 'high', 'medium', 'low'].map((severity) => {
                    const severityAnomalies = anomalies.anomalies.filter(
                      a => a.severity === severity
                    )
                    if (severityAnomalies.length === 0) return null

                    return (
                      <div key={severity}>
                        <h4 className={cn(
                          'text-sm font-medium mb-2 capitalize',
                          SEVERITY_CONFIG[severity as AnomalySeverity].color
                        )}>
                          {severity} Severity ({severityAnomalies.length})
                        </h4>
                        <div className="space-y-3">
                          {severityAnomalies.map((anomaly, index) => (
                            <AnomalyCard key={index} anomaly={anomaly} />
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Info section */}
          <div className="p-4 rounded-xl border bg-muted/30">
            <h3 className="font-semibold mb-3">Understanding Anomaly Detection</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <div className="font-medium mb-1">How it works</div>
                <p className="text-muted-foreground">
                  We use Z-score statistical analysis to compare current event volumes against historical baselines.
                  Significant deviations are flagged as anomalies.
                </p>
              </div>
              <div>
                <div className="font-medium mb-1">Severity Levels</div>
                <ul className="text-muted-foreground space-y-1">
                  <li><span className="text-red-500 font-medium">Critical:</span> Z-score {'>'} 4 (extremely unusual)</li>
                  <li><span className="text-orange-500 font-medium">High:</span> Z-score {'>'} 3 (very unusual)</li>
                  <li><span className="text-amber-500 font-medium">Medium:</span> Z-score {'>'} 2.5 (unusual)</li>
                  <li><span className="text-blue-500 font-medium">Low:</span> Z-score {'>'} threshold (slightly unusual)</li>
                </ul>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default AnomalyDashboard
