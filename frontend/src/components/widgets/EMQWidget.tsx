/**
 * EMQ (Event Match Quality) Widget
 * Shows Meta CAPI event quality metrics on the dashboard
 */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Signal,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  RefreshCw,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface EMQStats {
  total_events: number
  avg_emq: number
  excellent_count: number
  good_count: number
  fair_count: number
  poor_count: number
}

interface EMQWidgetProps {
  className?: string
}

export function EMQWidget({ className }: EMQWidgetProps) {
  const [stats, setStats] = useState<EMQStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = localStorage.getItem('access_token')
      const headers: HeadersInit = {}
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const res = await fetch('/api/v1/meta/capi/qa/stats', {
        credentials: 'include',
        headers,
      })

      if (res.ok) {
        const data = await res.json()
        setStats(data)
      } else {
        setError('Failed to load EMQ data')
      }
    } catch (err) {
      setError('Connection error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
    // Refresh every 5 minutes
    const interval = setInterval(fetchStats, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const getEMQColor = (emq: number) => {
    if (emq >= 8) return 'text-green-500'
    if (emq >= 6) return 'text-blue-500'
    if (emq >= 4) return 'text-amber-500'
    return 'text-red-500'
  }

  const getEMQBgColor = (emq: number) => {
    if (emq >= 8) return 'bg-green-500/10'
    if (emq >= 6) return 'bg-blue-500/10'
    if (emq >= 4) return 'bg-amber-500/10'
    return 'bg-red-500/10'
  }

  const getEMQLabel = (emq: number) => {
    if (emq >= 8) return 'Excellent'
    if (emq >= 6) return 'Good'
    if (emq >= 4) return 'Fair'
    return 'Poor'
  }

  if (loading) {
    return (
      <div className={cn('rounded-xl border bg-card p-6', className)}>
        <div className="flex items-center gap-2 mb-4">
          <Signal className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Event Match Quality</h3>
        </div>
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className={cn('rounded-xl border bg-card p-6', className)}>
        <div className="flex items-center gap-2 mb-4">
          <Signal className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Event Match Quality</h3>
        </div>
        <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
          <AlertTriangle className="w-8 h-8 mb-2 opacity-50" />
          <p className="text-sm">{error || 'No data available'}</p>
          <button
            onClick={fetchStats}
            className="mt-2 text-xs text-primary hover:underline"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  const avgEMQ = stats.avg_emq || 0
  const totalEvents = stats.total_events || 0
  const excellentPct = totalEvents > 0 ? Math.round((stats.excellent_count / totalEvents) * 100) : 0
  const goodPct = totalEvents > 0 ? Math.round((stats.good_count / totalEvents) * 100) : 0
  const fairPct = totalEvents > 0 ? Math.round((stats.fair_count / totalEvents) * 100) : 0
  const poorPct = totalEvents > 0 ? Math.round((stats.poor_count / totalEvents) * 100) : 0

  return (
    <div className={cn('rounded-xl border bg-card p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Signal className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Event Match Quality</h3>
        </div>
        <Link
          to="/app/meta-capi-qa"
          className="text-xs text-primary hover:underline flex items-center gap-1"
        >
          View Details
          <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      {/* Main Score */}
      <div className="flex items-center gap-4 mb-4">
        <div
          className={cn(
            'w-16 h-16 rounded-xl flex items-center justify-center',
            getEMQBgColor(avgEMQ)
          )}
        >
          <span className={cn('text-2xl font-bold', getEMQColor(avgEMQ))}>
            {avgEMQ.toFixed(1)}
          </span>
        </div>
        <div>
          <p className={cn('font-medium', getEMQColor(avgEMQ))}>
            {getEMQLabel(avgEMQ)}
          </p>
          <p className="text-sm text-muted-foreground">
            {totalEvents.toLocaleString()} events tracked
          </p>
        </div>
      </div>

      {/* Quality Distribution */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Quality Distribution</span>
        </div>

        {/* Progress Bar */}
        <div className="h-2 rounded-full overflow-hidden flex bg-muted">
          {excellentPct > 0 && (
            <div
              className="bg-green-500 h-full"
              style={{ width: `${excellentPct}%` }}
              title={`Excellent: ${excellentPct}%`}
            />
          )}
          {goodPct > 0 && (
            <div
              className="bg-blue-500 h-full"
              style={{ width: `${goodPct}%` }}
              title={`Good: ${goodPct}%`}
            />
          )}
          {fairPct > 0 && (
            <div
              className="bg-amber-500 h-full"
              style={{ width: `${fairPct}%` }}
              title={`Fair: ${fairPct}%`}
            />
          )}
          {poorPct > 0 && (
            <div
              className="bg-red-500 h-full"
              style={{ width: `${poorPct}%` }}
              title={`Poor: ${poorPct}%`}
            />
          )}
        </div>

        {/* Legend */}
        <div className="grid grid-cols-4 gap-2 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-muted-foreground">{excellentPct}%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-blue-500" />
            <span className="text-muted-foreground">{goodPct}%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-amber-500" />
            <span className="text-muted-foreground">{fairPct}%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-red-500" />
            <span className="text-muted-foreground">{poorPct}%</span>
          </div>
        </div>
      </div>

      {/* Quick Status */}
      <div className="mt-4 pt-4 border-t">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Meta CAPI Status</span>
          <span className="flex items-center gap-1 text-green-500">
            <CheckCircle className="w-4 h-4" />
            Active
          </span>
        </div>
      </div>
    </div>
  )
}

export default EMQWidget
