/**
 * Stratum AI - Signal Health Panel Component
 *
 * Displays detailed signal health metrics per platform.
 * Shows EMQ scores, event loss, data freshness, and API health.
 */

import React, { useState } from 'react'
import {
  useSignalHealth,
  SignalHealthData,
  PlatformHealthRow,
  MetricCard,
  getStatusColor,
  getStatusLabel,
} from '@/api/trustLayer'
import { useCanFeature } from '@/stores/featureFlagsStore'

// =============================================================================
// Types
// =============================================================================

interface SignalHealthPanelProps {
  tenantId: number
  date?: string
  compact?: boolean
}

// =============================================================================
// Sub-components
// =============================================================================

const MetricCardComponent: React.FC<{ card: MetricCard }> = ({ card }) => {
  const statusColors: Record<string, string> = {
    ok: 'border-green-200 bg-green-50',
    risk: 'border-yellow-200 bg-yellow-50',
    degraded: 'border-orange-200 bg-orange-50',
    neutral: 'border-gray-200 bg-gray-50',
  }

  const valueColors: Record<string, string> = {
    ok: 'text-green-700',
    risk: 'text-yellow-700',
    degraded: 'text-orange-700',
    neutral: 'text-gray-700',
  }

  return (
    <div className={`rounded-lg border p-4 ${statusColors[card.status]}`}>
      <div className="text-sm font-medium text-gray-600">{card.title}</div>
      <div className={`text-2xl font-bold mt-1 ${valueColors[card.status]}`}>
        {card.value}
      </div>
      {card.description && (
        <div className="text-xs text-gray-500 mt-1">{card.description}</div>
      )}
    </div>
  )
}

const PlatformRow: React.FC<{ row: PlatformHealthRow }> = ({ row }) => {
  const statusColors: Record<string, string> = {
    ok: 'bg-green-100 text-green-800',
    risk: 'bg-yellow-100 text-yellow-800',
    degraded: 'bg-orange-100 text-orange-800',
    critical: 'bg-red-100 text-red-800',
    no_data: 'bg-gray-100 text-gray-800',
  }

  const platformIcons: Record<string, string> = {
    meta: '📘',
    google: '🔴',
    tiktok: '🎵',
    snapchat: '👻',
  }

  const getMetricStatus = (value: number | undefined, thresholds: { good: number; risk: number }, inverse = false) => {
    if (value === undefined) return 'neutral'
    if (inverse) {
      if (value <= thresholds.good) return 'ok'
      if (value <= thresholds.risk) return 'risk'
      return 'degraded'
    }
    if (value >= thresholds.good) return 'ok'
    if (value >= thresholds.risk) return 'risk'
    return 'degraded'
  }

  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="py-3 px-4">
        <div className="flex items-center space-x-2">
          <span className="text-lg">{platformIcons[row.platform] || '📊'}</span>
          <div>
            <div className="font-medium text-gray-900 capitalize">{row.platform}</div>
            {row.account_id && (
              <div className="text-xs text-gray-500">{row.account_id}</div>
            )}
          </div>
        </div>
      </td>
      <td className="py-3 px-4 text-center">
        {row.emq_score !== undefined ? (
          <span className={`inline-flex items-center px-2 py-1 rounded text-sm font-medium ${
            getMetricStatus(row.emq_score, { good: 90, risk: 80 }) === 'ok'
              ? 'bg-green-100 text-green-800'
              : getMetricStatus(row.emq_score, { good: 90, risk: 80 }) === 'risk'
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-orange-100 text-orange-800'
          }`}>
            {row.emq_score.toFixed(0)}%
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td className="py-3 px-4 text-center">
        {row.event_loss_pct !== undefined ? (
          <span className={`inline-flex items-center px-2 py-1 rounded text-sm font-medium ${
            getMetricStatus(row.event_loss_pct, { good: 5, risk: 10 }, true) === 'ok'
              ? 'bg-green-100 text-green-800'
              : getMetricStatus(row.event_loss_pct, { good: 5, risk: 10 }, true) === 'risk'
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-orange-100 text-orange-800'
          }`}>
            {row.event_loss_pct.toFixed(1)}%
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td className="py-3 px-4 text-center">
        {row.freshness_minutes !== undefined ? (
          <span className={`inline-flex items-center px-2 py-1 rounded text-sm font-medium ${
            getMetricStatus(row.freshness_minutes, { good: 60, risk: 180 }, true) === 'ok'
              ? 'bg-green-100 text-green-800'
              : getMetricStatus(row.freshness_minutes, { good: 60, risk: 180 }, true) === 'risk'
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-orange-100 text-orange-800'
          }`}>
            {row.freshness_minutes} min
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td className="py-3 px-4 text-center">
        {row.api_error_rate !== undefined ? (
          <span className={`inline-flex items-center px-2 py-1 rounded text-sm font-medium ${
            getMetricStatus(row.api_error_rate, { good: 2, risk: 5 }, true) === 'ok'
              ? 'bg-green-100 text-green-800'
              : getMetricStatus(row.api_error_rate, { good: 2, risk: 5 }, true) === 'risk'
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-orange-100 text-orange-800'
          }`}>
            {(100 - row.api_error_rate).toFixed(1)}%
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>
      <td className="py-3 px-4 text-center">
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[row.status]}`}>
          {getStatusLabel(row.status)}
        </span>
      </td>
    </tr>
  )
}

// =============================================================================
// Main Component
// =============================================================================

export const SignalHealthPanel: React.FC<SignalHealthPanelProps> = ({
  tenantId,
  date,
  compact = false,
}) => {
  const canSignalHealth = useCanFeature('signal_health')
  const [expanded, setExpanded] = useState(!compact)

  const { data, isLoading, error, refetch } = useSignalHealth(tenantId, date)

  if (!canSignalHealth) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 text-center">
        <div className="text-gray-500">
          Signal Health feature is not enabled for your plan.
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/4" />
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-lg border border-red-200 p-6">
        <div className="text-red-700">Failed to load signal health data.</div>
        <button
          onClick={() => refetch()}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          Try again
        </button>
      </div>
    )
  }

  if (!data) {
    return null
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div
        className="px-6 py-4 border-b border-gray-200 flex items-center justify-between cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-3">
          <h3 className="text-lg font-semibold text-gray-900">Signal Health</h3>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            data.status === 'ok' ? 'bg-green-100 text-green-800' :
            data.status === 'risk' ? 'bg-yellow-100 text-yellow-800' :
            data.status === 'degraded' ? 'bg-orange-100 text-orange-800' :
            data.status === 'critical' ? 'bg-red-100 text-red-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {getStatusLabel(data.status)}
          </span>
          {data.automation_blocked && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
              Automation Blocked
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-500">{data.date}</span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
      </div>

      {/* Content */}
      {expanded && (
        <div className="p-6 space-y-6">
          {/* Metric Cards */}
          {data.cards.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {data.cards.map((card, index) => (
                <MetricCardComponent key={index} card={card} />
              ))}
            </div>
          )}

          {/* Platform Table */}
          {data.platform_rows.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="py-3 px-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Platform
                    </th>
                    <th className="py-3 px-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      EMQ Score
                    </th>
                    <th className="py-3 px-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Event Loss
                    </th>
                    <th className="py-3 px-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Freshness
                    </th>
                    <th className="py-3 px-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      API Health
                    </th>
                    <th className="py-3 px-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.platform_rows.map((row, index) => (
                    <PlatformRow key={index} row={row} />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Issues & Actions */}
          {(data.issues.length > 0 || data.actions.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.issues.length > 0 && (
                <div className="bg-red-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-red-800 mb-2">Issues Detected</h4>
                  <ul className="space-y-1">
                    {data.issues.map((issue, index) => (
                      <li key={index} className="text-sm text-red-700 flex items-start">
                        <span className="mr-2">•</span>
                        {issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {data.actions.length > 0 && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-blue-800 mb-2">Recommended Actions</h4>
                  <ul className="space-y-1">
                    {data.actions.map((action, index) => (
                      <li key={index} className="text-sm text-blue-700 flex items-start">
                        <span className="mr-2">•</span>
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Empty State */}
          {data.platform_rows.length === 0 && data.cards.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-400 text-4xl mb-3">📊</div>
              <div className="text-gray-600">No signal health data available for this date.</div>
              <div className="text-sm text-gray-500 mt-1">
                Data will appear after the daily sync runs.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SignalHealthPanel
