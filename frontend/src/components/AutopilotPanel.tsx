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
    queued: 'bg-amber-500/15 text-amber-700 dark:text-amber-400',
    approved: 'bg-blue-500/15 text-blue-700 dark:text-blue-400',
    applied: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400',
    failed: 'bg-red-500/15 text-red-700 dark:text-red-400',
    dismissed: 'bg-muted text-muted-foreground',
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClasses[status]}`}
      role="status"
    >
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
    <div className="border-b border-border last:border-0">
      <button
        type="button"
        className="w-full px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-muted/50 transition-colors focus:outline-none focus-visible:bg-muted"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        aria-label={`${getActionTypeLabel(action.action_type)} - ${action.entity_name || action.entity_id}`}
      >
        <div className="flex items-center space-x-3">
          <span className="text-lg" aria-hidden="true">{getPlatformIcon(action.platform)}</span>
          <div className="text-left">
            <div className="font-medium text-foreground">
              {getActionTypeLabel(action.action_type)}
            </div>
            <div className="text-sm text-muted-foreground">
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
                className="px-3 py-1 text-sm font-medium text-white bg-emerald-600 rounded hover:bg-emerald-700 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
                aria-label={`Approve action: ${getActionTypeLabel(action.action_type)}`}
              >
                Approve
              </button>
              <button
                onClick={() => onDismiss(action.id)}
                disabled={isProcessing}
                className="px-3 py-1 text-sm font-medium text-foreground bg-muted rounded hover:bg-muted/80 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                aria-label={`Dismiss action: ${getActionTypeLabel(action.action_type)}`}
              >
                Dismiss
              </button>
            </div>
          )}

          <svg
            className={`w-5 h-5 text-muted-foreground transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-3 text-sm motion-enter">
          <div className="bg-muted/50 rounded-lg p-3 space-y-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <span className="text-muted-foreground">Entity Type:</span>
                <span className="ml-2 text-foreground capitalize">{action.entity_type}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Platform:</span>
                <span className="ml-2 text-foreground capitalize">{action.platform}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Created:</span>
                <span className="ml-2 text-foreground">
                  {new Date(action.created_at).toLocaleString()}
                </span>
              </div>
              {action.approved_at && (
                <div>
                  <span className="text-muted-foreground">Approved:</span>
                  <span className="ml-2 text-foreground">
                    {new Date(action.approved_at).toLocaleString()}
                  </span>
                </div>
              )}
              {action.applied_at && (
                <div>
                  <span className="text-muted-foreground">Applied:</span>
                  <span className="ml-2 text-foreground">
                    {new Date(action.applied_at).toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            {action.action_json && Object.keys(action.action_json).length > 0 && (
              <div>
                <div className="text-muted-foreground mb-1">Details:</div>
                <pre className="bg-card border border-border rounded p-2 text-xs overflow-x-auto text-foreground">
                  {JSON.stringify(action.action_json, null, 2)}
                </pre>
              </div>
            )}

            {action.error && (
              <div className="mt-2 p-2 bg-red-500/10 border border-red-500/30 rounded" role="alert">
                <span className="text-red-600 dark:text-red-400 font-medium">Error:</span>
                <span className="ml-2 text-red-600 dark:text-red-400">{action.error}</span>
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
    0: 'bg-muted text-muted-foreground',
    1: 'bg-blue-500/15 text-blue-700 dark:text-blue-400',
    2: 'bg-primary/15 text-primary',
  }

  const icons = {
    0: '💡', // Suggest only
    1: '🛡️', // Guarded
    2: '✋', // Approval required
  }

  return (
    <div
      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${colors[level as keyof typeof colors] || colors[0]}`}
      role="status"
      aria-label={`Autopilot level: ${name}`}
    >
      <span className="mr-2" aria-hidden="true">{icons[level as keyof typeof icons] || '💡'}</span>
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
      <div className="bg-card rounded-lg border border-border p-6">
        <div className="text-center">
          <div className="text-4xl mb-3" aria-hidden="true">💡</div>
          <h3 className="text-lg font-medium text-foreground mb-2">Autopilot: Suggest Only</h3>
          <p className="text-muted-foreground">
            Autopilot is in suggest-only mode. You'll see recommendations but no actions will be queued for execution.
          </p>
        </div>
      </div>
    )
  }

  if (statusLoading || actionsLoading) {
    return (
      <div className="bg-card rounded-lg border border-border p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 skeleton w-1/4" />
          <div className="h-20 skeleton" />
          <div className="h-20 skeleton" />
        </div>
      </div>
    )
  }

  const actions = actionsData?.actions || []
  const queuedActions = actions.filter((a) => a.status === 'queued')

  return (
    <div className="bg-card rounded-lg border border-border overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h3 className="text-lg font-semibold text-foreground">Autopilot Actions</h3>
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
                className="px-4 py-2 text-sm font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2"
                aria-label={`Approve all ${queuedActions.length} pending actions`}
              >
                Approve All ({queuedActions.length})
              </button>
            )}

            <button
              onClick={() => refetch()}
              className="p-2 text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
              aria-label="Refresh actions list"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">Filter:</span>
          {(['', 'queued', 'approved', 'applied', 'failed', 'dismissed'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setStatusFilter(filter)}
              className={`px-3 py-1 text-sm rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                statusFilter === filter
                  ? 'bg-primary/15 text-primary font-medium'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
              aria-pressed={statusFilter === filter}
            >
              {filter === '' ? 'All' : getActionStatusLabel(filter)}
            </button>
          ))}
        </div>
      </div>

      {/* Pending Actions Alert */}
      {status && status.pending_actions > 0 && (
        <div className="px-6 py-3 bg-amber-500/10 border-b border-amber-500/30" role="alert">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-amber-500 mr-2" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="text-amber-700 dark:text-amber-400 font-medium">
              {status.pending_actions} action{status.pending_actions > 1 ? 's' : ''} pending approval
            </span>
          </div>
        </div>
      )}

      {/* Actions List */}
      <div className="divide-y divide-border">
        {actions.length === 0 ? (
          <div className="px-6 py-8 text-center">
            <div className="text-muted-foreground text-4xl mb-3" aria-hidden="true">🤖</div>
            <div className="text-foreground">No actions {statusFilter ? `with status "${statusFilter}"` : ''}</div>
            <div className="text-sm text-muted-foreground mt-1">
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
        <div className="px-6 py-3 bg-muted/50 border-t border-border text-sm text-muted-foreground">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
            <span className="font-medium text-foreground">Auto-execution caps:</span>
            <span>Max ${status.caps.max_daily_budget_change}/day budget change</span>
            <span className="hidden sm:inline">•</span>
            <span>Max {status.caps.max_budget_pct_change}% change</span>
            <span className="hidden sm:inline">•</span>
            <span>Max {status.caps.max_actions_per_day} actions/day</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default AutopilotPanel
