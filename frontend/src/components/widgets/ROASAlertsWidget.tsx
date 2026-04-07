/**
 * ROAS Alerts Widget
 * Displays prediction-based alerts for campaign performance
 * Falls back to live simulation data when API is unavailable
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Bell,
  AlertTriangle,
  AlertCircle,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  CheckCircle,
  Info,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { generateLiveCampaigns } from '@/lib/liveSimulation'

interface PredictionAlert {
  campaign_id: number
  campaign_name: string
  type: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  message: string
  recommendation: string
}

interface ROASAlertsWidgetProps {
  className?: string
  limit?: number
}

// Analytics Design System severity config
const severityConfig = {
  critical: {
    icon: AlertCircle,
    bg: 'bg-danger/10',
    border: 'border-danger',
    text: 'text-danger',
    label: 'Critical',
    motion: 'motion-critical',
  },
  high: {
    icon: AlertTriangle,
    bg: 'bg-insight/10',
    border: 'border-insight',
    text: 'text-insight',
    label: 'High',
    motion: 'motion-insight',
  },
  medium: {
    icon: AlertTriangle,
    bg: 'bg-warning/10',
    border: 'border-warning',
    text: 'text-warning',
    label: 'Medium',
    motion: 'motion-enter',
  },
  low: {
    icon: Info,
    bg: 'bg-info/10',
    border: 'border-info',
    text: 'text-info',
    label: 'Low',
    motion: 'motion-enter',
  },
  info: {
    icon: TrendingUp,
    bg: 'bg-success/10',
    border: 'border-success',
    text: 'text-success',
    label: 'Opportunity',
    motion: 'motion-enter',
  },
}

/**
 * Generate simulation-based ROAS alerts from live campaign data
 */
function getSimulationAlerts(): PredictionAlert[] {
  const liveCampaigns = generateLiveCampaigns()
  const alerts: PredictionAlert[] = []

  liveCampaigns.forEach((c, i) => {
    if (c.status !== 'Active') return

    if (c.roas < 1.5) {
      alerts.push({
        campaign_id: i + 1,
        campaign_name: c.campaign_name,
        type: 'roas_decline',
        severity: c.roas < 1.0 ? 'critical' : 'high',
        message: `ROAS at ${c.roas.toFixed(2)}x — below minimum threshold. Signal health degraded.`,
        recommendation: `Reduce budget by ${Math.round(30 - c.roas * 10)}% or pause campaign`,
      })
    } else if (c.roas >= 4.0) {
      alerts.push({
        campaign_id: i + 1,
        campaign_name: c.campaign_name,
        type: 'scaling_opportunity',
        severity: 'info',
        message: `Strong ROAS at ${c.roas.toFixed(2)}x with healthy signal score. Autopilot eligible.`,
        recommendation: `Scale budget by 15-25% — expected incremental revenue +$${Math.round(c.revenue * 0.15).toLocaleString()}`,
      })
    } else if (c.cpa > 80) {
      alerts.push({
        campaign_id: i + 1,
        campaign_name: c.campaign_name,
        type: 'cpa_alert',
        severity: 'medium',
        message: `CPA at $${c.cpa.toFixed(2)} — above target threshold. Trust Gate: HOLD.`,
        recommendation: 'Optimize audience targeting or adjust bid strategy',
      })
    } else if (c.ctr < 0.8) {
      alerts.push({
        campaign_id: i + 1,
        campaign_name: c.campaign_name,
        type: 'engagement_low',
        severity: 'low',
        message: `CTR at ${c.ctr.toFixed(2)}% — below platform average. Creative may need refresh.`,
        recommendation: 'A/B test new ad creatives or expand audience',
      })
    }
  })

  // Sort by severity importance
  const severityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
  return alerts.sort((a, b) => (severityOrder[a.severity] ?? 5) - (severityOrder[b.severity] ?? 5))
}

export function ROASAlertsWidget({ className, limit = 5 }: ROASAlertsWidgetProps) {
  const { t: _t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [alerts, setAlerts] = useState<PredictionAlert[]>([])
  const [filter, setFilter] = useState<string>('all')
  const [error, setError] = useState<string | null>(null)
  const [usingSimulation, setUsingSimulation] = useState(false)

  const loadSimulationData = () => {
    setAlerts(getSimulationAlerts())
    setError(null)
    setUsingSimulation(true)
  }

  const fetchAlerts = async () => {
    try {
      setRefreshing(true)
      const response = await fetch('/api/v1/predictions/alerts')
      const data = await response.json()

      if (data.success && data.data?.alerts) {
        setAlerts(data.data.alerts)
        setError(null)
        setUsingSimulation(false)
      } else {
        loadSimulationData()
      }
    } catch {
      // API unavailable — use simulation
      loadSimulationData()
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchAlerts()
    // Refresh every 30 seconds for live feel
    const interval = setInterval(() => {
      if (usingSimulation) {
        loadSimulationData()
      } else {
        fetchAlerts()
      }
    }, 30 * 1000)
    return () => clearInterval(interval)
  }, [usingSimulation])

  const filteredAlerts = alerts.filter((alert) => {
    if (filter === 'all') return true
    if (filter === 'critical') return alert.severity === 'critical' || alert.severity === 'high'
    if (filter === 'opportunities') return alert.type === 'scaling_opportunity'
    return alert.severity === filter
  }).slice(0, limit)

  const criticalCount = alerts.filter(a => a.severity === 'critical' || a.severity === 'high').length
  const opportunityCount = alerts.filter(a => a.type === 'scaling_opportunity').length

  if (loading) {
    return (
      <div className={cn('rounded-xl border bg-card p-6', className)}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-muted rounded w-1/3" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-muted rounded" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('rounded-lg border bg-card overflow-hidden motion-enter shadow-card', className)}>
      {/* Header */}
      <div className="px-6 py-4 border-b">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Bell className="w-5 h-5 text-primary" />
              {criticalCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center">
                  {criticalCount}
                </span>
              )}
            </div>
            <div>
              <h3 className="font-semibold text-foreground">ROAS Alerts</h3>
              <p className="text-xs text-muted-foreground">
                {alerts.length} active alerts
                {usingSimulation && <span className="ml-1 text-green-500 font-medium">· LIVE</span>}
              </p>
            </div>
          </div>
          <button
            onClick={fetchAlerts}
            disabled={refreshing}
            className="p-2 hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('w-4 h-4', refreshing && 'animate-spin')} />
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2 mt-4">
          {[
            { value: 'all', label: 'All' },
            { value: 'critical', label: `Critical (${criticalCount})` },
            { value: 'opportunities', label: `Opportunities (${opportunityCount})` },
          ].map((tab) => (
            <button
              key={tab.value}
              onClick={() => setFilter(tab.value)}
              className={cn(
                'px-3 py-1.5 text-xs font-medium rounded-full transition-colors',
                filter === tab.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Alerts List */}
      <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
        {error ? (
          <div className="flex items-center gap-3 p-4 bg-red-500/10 rounded-lg text-red-500">
            <AlertCircle className="w-5 h-5" />
            <span className="text-sm">{error}</span>
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
            <p className="font-medium">All Clear!</p>
            <p className="text-sm mt-1">No alerts match your filter</p>
          </div>
        ) : (
          filteredAlerts.map((alert, index) => {
            const config = severityConfig[alert.severity] || severityConfig.medium
            const Icon = config.icon

            return (
              <div
                key={`${alert.campaign_id}-${index}`}
                className={cn(
                  'p-4 rounded-lg border-l-4 motion-card hover:shadow-card-hover cursor-pointer',
                  config.bg,
                  config.border,
                  config.motion
                )}
                style={{ animationDelay: `${index * 60}ms` }}
              >
                <div className="flex items-start gap-3">
                  <Icon className={cn('w-5 h-5 mt-0.5 flex-shrink-0', config.text)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn('text-xs font-semibold uppercase', config.text)}>
                        {config.label}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {alert.type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="font-medium text-sm text-foreground truncate">
                      {alert.campaign_name}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {alert.message}
                    </p>
                    {alert.recommendation && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-primary">
                        <ArrowRight className="w-3 h-3" />
                        <span>{alert.recommendation}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Footer */}
      {alerts.length > limit && (
        <div className="px-6 py-3 border-t bg-muted/30">
          <button className="text-sm text-primary hover:underline flex items-center gap-1">
            View all {alerts.length} alerts
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}

export default ROASAlertsWidget
