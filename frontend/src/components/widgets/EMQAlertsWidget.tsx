/**
 * EMQ Alerts & Recommendations Widget
 * Shows actionable alerts and recommendations to improve EMQ
 */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  CheckCircle,
  Info,
  Lightbulb,
  ArrowRight,
  RefreshCw,
  TrendingUp,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface Alert {
  id: string
  severity: 'critical' | 'warning' | 'info'
  title: string
  message: string
  metric: number | null
  threshold: number | null
}

interface Recommendation {
  id: string
  priority: 'high' | 'medium' | 'low'
  category: string
  title: string
  description: string
  impact: string
  effort: string
  current?: number
  target?: number
}

interface AlertsData {
  alerts: Alert[]
  alert_count: number
}

interface RecommendationsData {
  current_emq: number
  potential_emq: number
  potential_gain: number
  recommendations: Recommendation[]
}

export function EMQAlertsWidget({ className }: { className?: string }) {
  const [alerts, setAlerts] = useState<AlertsData | null>(null)
  const [recommendations, setRecommendations] = useState<RecommendationsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'alerts' | 'recommendations'>('alerts')

  const getHeaders = () => {
    const token = localStorage.getItem('access_token')
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }
  }

  const fetchData = async () => {
    setLoading(true)
    try {
      const [alertsRes, recsRes] = await Promise.all([
        fetch('/api/v1/meta/capi/qa/alerts', { headers: getHeaders() }),
        fetch('/api/v1/meta/capi/qa/recommendations', { headers: getHeaders() }),
      ])

      if (alertsRes.ok) {
        setAlerts(await alertsRes.json())
      }
      if (recsRes.ok) {
        setRecommendations(await recsRes.json())
      }
    } catch (err) {
      console.error('Failed to fetch EMQ alerts:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="w-4 h-4 text-red-500" />
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-500" />
      case 'info':
        return <Info className="w-4 h-4 text-blue-500" />
      default:
        return <Info className="w-4 h-4 text-muted-foreground" />
    }
  }

  const getSeverityBg = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 border-red-500/20'
      case 'warning':
        return 'bg-amber-500/10 border-amber-500/20'
      case 'info':
        return 'bg-blue-500/10 border-blue-500/20'
      default:
        return 'bg-muted'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'text-red-500 bg-red-500/10'
      case 'medium':
        return 'text-amber-500 bg-amber-500/10'
      case 'low':
        return 'text-blue-500 bg-blue-500/10'
      default:
        return 'text-muted-foreground bg-muted'
    }
  }

  if (loading) {
    return (
      <div className={cn('rounded-xl border bg-card p-6', className)}>
        <div className="flex items-center gap-2 mb-4">
          <Lightbulb className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">EMQ Insights</h3>
        </div>
        <div className="flex items-center justify-center h-40">
          <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  const alertCount = alerts?.alert_count || 0
  const hasAlerts = alertCount > 0
  const hasRecommendations = (recommendations?.recommendations?.length || 0) > 0

  return (
    <div className={cn('rounded-xl border bg-card p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">EMQ Insights</h3>
          {alertCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs font-medium rounded-full bg-red-500 text-white">
              {alertCount}
            </span>
          )}
        </div>
        <Link
          to="/app/meta-capi-qa"
          className="text-xs text-primary hover:underline flex items-center gap-1"
        >
          Details
          <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-lg bg-muted/50 mb-4">
        <button
          onClick={() => setActiveTab('alerts')}
          className={cn(
            'flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
            activeTab === 'alerts'
              ? 'bg-background shadow text-foreground'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          Alerts {alertCount > 0 && `(${alertCount})`}
        </button>
        <button
          onClick={() => setActiveTab('recommendations')}
          className={cn(
            'flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
            activeTab === 'recommendations'
              ? 'bg-background shadow text-foreground'
              : 'text-muted-foreground hover:text-foreground'
          )}
        >
          Improve
        </button>
      </div>

      {/* Content */}
      {activeTab === 'alerts' ? (
        <div className="space-y-2">
          {!hasAlerts ? (
            <div className="flex flex-col items-center justify-center py-6 text-center">
              <CheckCircle className="w-8 h-8 text-green-500 mb-2" />
              <p className="text-sm font-medium text-green-600">All Good!</p>
              <p className="text-xs text-muted-foreground">No issues detected</p>
            </div>
          ) : (
            alerts?.alerts.slice(0, 3).map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  'p-3 rounded-lg border',
                  getSeverityBg(alert.severity)
                )}
              >
                <div className="flex items-start gap-2">
                  {getSeverityIcon(alert.severity)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{alert.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                      {alert.message}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {/* Potential Improvement */}
          {recommendations && recommendations.potential_gain > 0 && (
            <div className="flex items-center justify-between p-3 rounded-lg bg-green-500/10 border border-green-500/20">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium text-green-600">
                  Potential: +{recommendations.potential_gain.toFixed(1)} EMQ
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {recommendations.current_emq.toFixed(1)} → {recommendations.potential_emq.toFixed(1)}
              </span>
            </div>
          )}

          {/* Top Recommendations */}
          {!hasRecommendations ? (
            <div className="flex flex-col items-center justify-center py-6 text-center">
              <CheckCircle className="w-8 h-8 text-green-500 mb-2" />
              <p className="text-sm font-medium">Optimized!</p>
              <p className="text-xs text-muted-foreground">EMQ is well configured</p>
            </div>
          ) : (
            recommendations?.recommendations.slice(0, 3).map((rec) => (
              <div
                key={rec.id}
                className="p-3 rounded-lg border hover:bg-muted/30 transition-colors cursor-pointer group"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={cn(
                          'px-1.5 py-0.5 text-xs font-medium rounded capitalize',
                          getPriorityColor(rec.priority)
                        )}
                      >
                        {rec.priority}
                      </span>
                      <span className="text-xs text-green-500 font-medium">
                        {rec.impact}
                      </span>
                    </div>
                    <p className="text-sm font-medium">{rec.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                      {rec.description}
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors flex-shrink-0 mt-1" />
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

export default EMQAlertsWidget
