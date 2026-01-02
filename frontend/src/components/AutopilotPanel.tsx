/**
 * Stratum AI - Autopilot Panel Component
 *
 * Displays and manages autopilot actions:
 * - Action queue with approval workflow
 * - Action history
 * - Autopilot status and configuration
 */

import React, { useState } from 'react'
import {
  useAutopilotStatus,
  useAutopilotActions,
  useApproveAction,
  useDismissAction,
  useApproveAllActions,
  AutopilotAction,
  ActionStatus,
  getActionTypeLabel,
  getActionStatusColor,
  getActionStatusLabel,
  getPlatformIcon,
} from '@/api/autopilot'
import { useCanFeature, useAutopilotLevel } from '@/stores/featureFlagsStore'

// =============================================================================
// Types
// =============================================================================

interface AutopilotPanelProps {
  tenantId: number
  compact?: boolean
}

interface ActionRowProps {
  action: AutopilotAction
  onApprove: (id: string) => void
  onDismiss: (id: string) => void
  isProcessing: boolean
}

// =============================================================================
// Sub-components
// =============================================================================

const StatusBadge: React.FC<{ status: ActionStatus }> = ({ status }) => {
  const colorClasses: Record<ActionStatus, string> = {
    queued: 'bg-yellow-100 text-yellow-800',
    approved: 'bg-blue-100 text-blue-800',
    applied: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    dismissed: 'bg-gray-100 text-gray-800',
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClasses[status]}`}>
      {getActionStatusLabel(status)}
    </span>
  )
}

const ActionRow: React.FC<ActionRowProps> = ({
  action,
  onApprove,
  onDismiss,
  isProcessing,
}) => {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border-b border-gray-100 last:border-0">
      <div
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-3">
          <span className="text-lg">{getPlatformIcon(action.platform)}</span>
          <div>
            <div className="font-medium text-gray-900">
              {getActionTypeLabel(action.action_type)}
            </div>
            <div className="text-sm text-gray-500">
              {action.entity_name || action.entity_id}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <StatusBadge status={action.status} />

          {action.status === 'queued' && (
            <div className="flex items-center space-x-2" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => onApprove(action.id)}
                disabled={isProcessing}
                className="px-3 py-1 text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
              >
                Approve
              </button>
              <button
                onClick={() => onDismiss(action.id)}
                disabled={isProcessing}
                className="px-3 py-1 text-sm font-medium text-gray-700 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50"
              >
                Dismiss
              </button>
            </div>
          )}

          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-3 text-sm">
          <div className="bg-gray-50 rounded-lg p-3 space-y-2">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-500">Entity Type:</span>
                <span className="ml-2 text-gray-900 capitalize">{action.entity_type}</span>
              </div>
              <div>
                <span className="text-gray-500">Platform:</span>
                <span className="ml-2 text-gray-900 capitalize">{action.platform}</span>
              </div>
              <div>
                <span className="text-gray-500">Created:</span>
                <span className="ml-2 text-gray-900">
                  {new Date(action.created_at).toLocaleString()}
                </span>
              </div>
              {action.approved_at && (
                <div>
                  <span className="text-gray-500">Approved:</span>
                  <span className="ml-2 text-gray-900">
                    {new Date(action.approved_at).toLocaleString()}
                  </span>
                </div>
              )}
              {action.applied_at && (
                <div>
                  <span className="text-gray-500">Applied:</span>
                  <span className="ml-2 text-gray-900">
                    {new Date(action.applied_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            {action.action_json && Object.keys(action.action_json).length > 0 && (
              <div>
                <div className="text-gray-500 mb-1">Details:</div>
                <pre className="bg-white border border-gray-200 rounded p-2 text-xs overflow-x-auto">
                  {JSON.stringify(action.action_json, null, 2)}
                </pre>
              </div>
            )}

            {action.error && (
              <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                <span className="text-red-700 font-medium">Error:</span>
                <span className="ml-2 text-red-600">{action.error}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

const AutopilotLevelIndicator: React.FC<{ level: number; name: string }> = ({ level, name }) => {
  const colors = {
    0: 'bg-gray-100 text-gray-800',
    1: 'bg-blue-100 text-blue-800',
    2: 'bg-purple-100 text-purple-800',
  }

  const icons = {
    0: '💡', // Suggest only
    1: '🛡️', // Guarded
    2: '✋', // Approval required
  }

  return (
    <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colors[level as keyof typeof colors] || colors[0]}`}>
      <span className="mr-2">{icons[level as keyof typeof icons] || '💡'}</span>
      {name}
    </div>
  )
}

// =============================================================================
// Main Component
// =============================================================================

export const AutopilotPanel: React.FC<AutopilotPanelProps> = ({
  tenantId,
  compact = false,
}) => {
  const autopilotLevel = useAutopilotLevel()
  const [statusFilter, setStatusFilter] = useState<ActionStatus | ''>('')

  const { data: status, isLoading: statusLoading } = useAutopilotStatus(tenantId)
  const { data: actionsData, isLoading: actionsLoading, refetch } = useAutopilotActions(
    tenantId,
    statusFilter ? { status: statusFilter } : undefined
  )

  const approveAction = useApproveAction(tenantId)
  const dismissAction = useDismissAction(tenantId)
  const approveAll = useApproveAllActions(tenantId)

  const isProcessing = approveAction.isPending || dismissAction.isPending || approveAll.isPending

  if (autopilotLevel === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="text-center">
          <div className="text-4xl mb-3">💡</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Autopilot: Suggest Only</h3>
          <p className="text-gray-600">
            Autopilot is in suggest-only mode. You'll see recommendations but no actions will be queued for execution.
          </p>
        </div>
      </div>
    )
  }

  if (statusLoading || actionsLoading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/4" />
          <div className="h-20 bg-gray-200 rounded" />
          <div className="h-20 bg-gray-200 rounded" />
        </div>
      </div>
    )
  }

  const actions = actionsData?.actions || []
  const queuedActions = actions.filter((a) => a.status === 'queued')

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h3 className="text-lg font-semibold text-gray-900">Autopilot Actions</h3>
            {status && (
              <AutopilotLevelIndicator
                level={status.autopilot_level}
                name={status.autopilot_level_name}
              />
            )}
          </div>

          <div className="flex items-center space-x-3">
            {queuedActions.length > 0 && (
              <button
                onClick={() => approveAll.mutate(queuedActions.map((a) => a.id))}
                disabled={isProcessing}
                className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                Approve All ({queuedActions.length})
              </button>
            )}

            <button
              onClick={() => refetch()}
              className="p-2 text-gray-500 hover:text-gray-700"
              title="Refresh"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="mt-3 flex items-center space-x-2">
          <span className="text-sm text-gray-500">Filter:</span>
          {(['', 'queued', 'approved', 'applied', 'failed', 'dismissed'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setStatusFilter(filter)}
              className={`px-3 py-1 text-sm rounded-full ${
                statusFilter === filter
                  ? 'bg-blue-100 text-blue-800 font-medium'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {filter === '' ? 'All' : getActionStatusLabel(filter)}
            </button>
          ))}
        </div>
      </div>

      {/* Pending Actions Alert */}
      {status && status.pending_actions > 0 && (
        <div className="px-6 py-3 bg-yellow-50 border-b border-yellow-200">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-yellow-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="text-yellow-800 font-medium">
              {status.pending_actions} action{status.pending_actions > 1 ? 's' : ''} pending approval
            </span>
          </div>
        </div>
      )}

      {/* Actions List */}
      <div className="divide-y divide-gray-100">
        {actions.length === 0 ? (
          <div className="px-6 py-8 text-center">
            <div className="text-gray-400 text-4xl mb-3">🤖</div>
            <div className="text-gray-600">No actions {statusFilter ? `with status "${statusFilter}"` : ''}</div>
            <div className="text-sm text-gray-500 mt-1">
              Actions will appear here when recommendations are generated.
            </div>
          </div>
        ) : (
          actions.map((action) => (
            <ActionRow
              key={action.id}
              action={action}
              onApprove={(id) => approveAction.mutate(id)}
              onDismiss={(id) => dismissAction.mutate(id)}
              isProcessing={isProcessing}
            />
          ))
        )}
      </div>

      {/* Caps Info */}
      {status && status.caps && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-600">
          <div className="flex items-center space-x-4">
            <span className="font-medium">Auto-execution caps:</span>
            <span>Max ${status.caps.max_daily_budget_change}/day budget change</span>
            <span>•</span>
            <span>Max {status.caps.max_budget_pct_change}% change</span>
            <span>•</span>
            <span>Max {status.caps.max_actions_per_day} actions/day</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default AutopilotPanel
