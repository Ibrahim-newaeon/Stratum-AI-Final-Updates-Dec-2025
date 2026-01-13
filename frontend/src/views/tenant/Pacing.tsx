/**
 * Stratum AI - Pacing & Forecasting Page
 *
 * Manages targets, pacing status, forecasts, and alerts.
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  useTargets,
  useAllPacingStatus,
  usePacingSummary,
  usePacingAlerts,
  useAlertStats,
  useAcknowledgeAlert,
  useResolveAlert,
} from '@/api/hooks'
import {
  ChartBarIcon,
  BellAlertIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PlusIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

type TabType = 'overview' | 'targets' | 'alerts' | 'forecasts'

const statusColors = {
  on_track: 'bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300',
  ahead: 'bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
  behind: 'bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300',
  at_risk: 'bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300',
  missed: 'bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300',
}

export default function Pacing() {
  useParams<{ tenantId: string }>()
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [, setShowNewTargetModal] = useState(false)

  const { data: targets } = useTargets()
  const { data: pacingStatus } = useAllPacingStatus()
  const { data: summary } = usePacingSummary()
  const { data: alerts } = usePacingAlerts({ status: 'active' })
  const { data: alertStats } = useAlertStats()
  const acknowledgeAlert = useAcknowledgeAlert()
  const resolveAlert = useResolveAlert()

  const tabs = [
    { id: 'overview' as TabType, label: 'Overview' },
    { id: 'targets' as TabType, label: 'Targets' },
    { id: 'alerts' as TabType, label: 'Alerts', badge: alertStats?.active },
    { id: 'forecasts' as TabType, label: 'Forecasts' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Pacing & Forecasting</h1>
          <p className="text-muted-foreground">
            Track campaign targets, pacing, and AI-powered forecasts
          </p>
        </div>
        <button
          onClick={() => setShowNewTargetModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <PlusIcon className="h-4 w-4" />
          New Target
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-4 py-2 border-b-2 font-medium text-sm transition-colors flex items-center gap-2',
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.label}
              {tab.badge && tab.badge > 0 && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Health Score */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground">Health Score</p>
                <p className="text-3xl font-bold text-primary">{summary.overallHealthScore}%</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground">On Track</p>
                <p className="text-2xl font-bold text-emerald-600">{summary.onTrack}</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground">Ahead</p>
                <p className="text-2xl font-bold text-blue-600">{summary.ahead}</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground">Behind</p>
                <p className="text-2xl font-bold text-amber-600">{summary.behind}</p>
              </div>
              <div className="rounded-xl border bg-card p-6 shadow-card">
                <p className="text-sm text-muted-foreground">At Risk</p>
                <p className="text-2xl font-bold text-red-600">{summary.atRisk}</p>
              </div>
            </div>
          )}

          {/* Pacing Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pacingStatus?.map((status) => (
              <div key={status.targetId} className="rounded-xl border bg-card p-6 shadow-card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium truncate">{status.targetName}</h3>
                  <span className={cn('px-2 py-1 rounded-full text-xs', statusColors[status.status])}>
                    {status.status.replace('_', ' ')}
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-muted-foreground">Progress</span>
                      <span className="font-medium">{status.pacingPct.toFixed(1)}%</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div
                        className={cn(
                          'h-2 rounded-full',
                          status.status === 'on_track' && 'bg-emerald-500',
                          status.status === 'ahead' && 'bg-blue-500',
                          status.status === 'behind' && 'bg-amber-500',
                          status.status === 'at_risk' && 'bg-red-500',
                          status.status === 'missed' && 'bg-gray-500'
                        )}
                        style={{ width: `${Math.min(status.pacingPct, 100)}%` }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Current</p>
                      <p className="font-medium">{status.currentValue.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Target</p>
                      <p className="font-medium">{status.targetValue.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Projected</p>
                      <p className="font-medium">{status.projectedValue.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Days Left</p>
                      <p className="font-medium">{status.daysRemaining}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 text-sm">
                    {status.trend === 'improving' ? (
                      <ArrowTrendingUpIcon className="h-4 w-4 text-emerald-500" />
                    ) : status.trend === 'declining' ? (
                      <ArrowTrendingDownIcon className="h-4 w-4 text-red-500" />
                    ) : null}
                    <span className="text-muted-foreground capitalize">{status.trend}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Targets Tab */}
      {activeTab === 'targets' && (
        <div className="rounded-xl border bg-card shadow-card overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium">Target</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Metric</th>
                <th className="px-4 py-3 text-left text-sm font-medium">Period</th>
                <th className="px-4 py-3 text-right text-sm font-medium">Value</th>
                <th className="px-4 py-3 text-center text-sm font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {targets?.map((target) => (
                <tr key={target.id} className="hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <p className="font-medium">{target.name}</p>
                    {target.description && (
                      <p className="text-sm text-muted-foreground truncate max-w-xs">
                        {target.description}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm capitalize">{target.metricType}</td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex items-center gap-1">
                      <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                      {new Date(target.periodStart).toLocaleDateString()} -{' '}
                      {new Date(target.periodEnd).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-medium">
                    {target.metricType === 'spend' || target.metricType === 'revenue'
                      ? `$${target.targetValue.toLocaleString()}`
                      : target.metricType === 'roas'
                      ? `${target.targetValue}x`
                      : target.targetValue.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {target.isActive ? (
                      <span className="px-2 py-1 rounded-full text-xs bg-emerald-100 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300">
                        Active
                      </span>
                    ) : (
                      <span className="px-2 py-1 rounded-full text-xs bg-gray-100 dark:bg-gray-900/20 text-gray-700 dark:text-gray-300">
                        Inactive
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Alerts Tab */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          {alerts?.length === 0 ? (
            <div className="rounded-xl border bg-card p-12 text-center">
              <CheckCircleIcon className="h-12 w-12 mx-auto text-emerald-500 mb-3" />
              <p className="text-lg font-medium">No Active Alerts</p>
              <p className="text-muted-foreground">All targets are on track</p>
            </div>
          ) : (
            alerts?.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  'rounded-xl border p-4 flex items-start justify-between gap-4',
                  alert.severity === 'critical' && 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/20',
                  alert.severity === 'warning' && 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/20',
                  alert.severity === 'info' && 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/20'
                )}
              >
                <div className="flex items-start gap-3">
                  {alert.severity === 'critical' ? (
                    <ExclamationTriangleIcon className="h-5 w-5 text-red-500 mt-0.5" />
                  ) : alert.severity === 'warning' ? (
                    <ExclamationTriangleIcon className="h-5 w-5 text-amber-500 mt-0.5" />
                  ) : (
                    <BellAlertIcon className="h-5 w-5 text-blue-500 mt-0.5" />
                  )}
                  <div>
                    <p className="font-medium">{alert.message}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Deviation: {alert.deviationPct.toFixed(1)}% | Expected: {alert.expectedValue.toLocaleString()} |
                      Actual: {alert.currentValue.toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(alert.triggeredAt).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => acknowledgeAlert.mutate({ alertId: alert.id })}
                    className="px-3 py-1 text-sm rounded-lg border hover:bg-muted"
                  >
                    Acknowledge
                  </button>
                  <button
                    onClick={() => resolveAlert.mutate({ alertId: alert.id })}
                    className="px-3 py-1 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    Resolve
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Forecasts Tab */}
      {activeTab === 'forecasts' && (
        <div className="rounded-xl border bg-card p-6 shadow-card">
          <div className="flex items-center gap-3 mb-6">
            <ChartBarIcon className="h-6 w-6 text-primary" />
            <h2 className="text-lg font-semibold">AI-Powered Forecasts</h2>
          </div>
          <p className="text-muted-foreground">
            Select a target to view its forecast predictions. Forecasts use machine learning models
            trained on your historical data to predict future performance.
          </p>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            {targets?.filter((t) => t.isActive).map((target) => (
              <button
                key={target.id}
                className="p-4 rounded-lg border text-left hover:bg-muted/50 transition-colors"
              >
                <p className="font-medium">{target.name}</p>
                <p className="text-sm text-muted-foreground capitalize">
                  {target.metricType} | {target.periodType}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
