/**
 * Actions Panel
 * Aggregates actions with filters and bulk operations
 */

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { ActionCard, type Action, type ActionType } from './ActionCard'
import { AutopilotMode } from './AutopilotModeBanner'
import {
  FunnelIcon,
  SparklesIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline'

interface ActionsPanelProps {
  actions: Action[]
  autopilotMode?: AutopilotMode
  onApply?: (action: Action) => void
  onDismiss?: (action: Action) => void
  onQueue?: (action: Action) => void
  onApplyAll?: (actions: Action[]) => void
  maxActions?: number
  className?: string
}

const filterTabs: { type: ActionType | 'all'; label: string; icon: typeof SparklesIcon }[] = [
  { type: 'all', label: 'All', icon: FunnelIcon },
  { type: 'opportunity', label: 'Opportunities', icon: ArrowTrendingUpIcon },
  { type: 'risk', label: 'Risks', icon: ExclamationTriangleIcon },
  { type: 'recommendation', label: 'Recommendations', icon: SparklesIcon },
  { type: 'fix', label: 'Fixes', icon: WrenchScrewdriverIcon },
]

function getAutopilotRestrictionMessage(mode: AutopilotMode): string | null {
  switch (mode) {
    case 'limited':
      return 'Scaling capped at +10%. Some actions may be restricted.'
    case 'cuts_only':
      return 'Only pause and reduction actions are allowed.'
    case 'frozen':
      return 'All automation is paused. Fix data issues first.'
    default:
      return null
  }
}

export function ActionsPanel({
  actions,
  autopilotMode = 'normal',
  onApply,
  onDismiss,
  onQueue,
  onApplyAll,
  maxActions = 10,
  className,
}: ActionsPanelProps) {
  const [activeFilter, setActiveFilter] = useState<ActionType | 'all'>('all')

  const filteredActions = activeFilter === 'all'
    ? actions
    : actions.filter(a => a.type === activeFilter)

  const pendingActions = filteredActions.filter(a => a.status === 'pending')
  const displayActions = pendingActions.slice(0, maxActions)

  const restrictionMessage = getAutopilotRestrictionMessage(autopilotMode)
  const isActionsDisabled = autopilotMode === 'frozen'

  // Count by type
  const countByType = actions.reduce((acc, a) => {
    if (a.status === 'pending') {
      acc[a.type] = (acc[a.type] || 0) + 1
    }
    return acc
  }, {} as Record<ActionType, number>)

  return (
    <div className={cn(
      'rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden',
      className
    )}>
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-white">Actions</h3>
            <p className="text-sm text-text-muted">
              {pendingActions.length} actions pending
            </p>
          </div>
          {onApplyAll && pendingActions.length > 0 && !isActionsDisabled && (
            <button
              onClick={() => onApplyAll(pendingActions)}
              className="text-sm text-stratum-400 hover:text-stratum-300 transition-colors"
            >
              Apply all ({pendingActions.length})
            </button>
          )}
        </div>

        {/* Restriction warning */}
        {restrictionMessage && (
          <div className={cn(
            'flex items-center gap-2 mt-3 p-2 rounded-lg text-sm',
            autopilotMode === 'frozen' ? 'bg-danger/10 text-danger' : 'bg-warning/10 text-warning'
          )}>
            <ExclamationTriangleIcon className="w-4 h-4 flex-shrink-0" />
            {restrictionMessage}
          </div>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex items-center gap-1 p-2 overflow-x-auto border-b border-white/10">
        {filterTabs.map((tab) => {
          const count = tab.type === 'all'
            ? Object.values(countByType).reduce((a, b) => a + b, 0)
            : countByType[tab.type] || 0
          const Icon = tab.icon

          return (
            <button
              key={tab.type}
              onClick={() => setActiveFilter(tab.type)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors whitespace-nowrap',
                activeFilter === tab.type
                  ? 'bg-stratum-500/10 text-stratum-400'
                  : 'text-text-muted hover:text-white'
              )}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
              {count > 0 && (
                <span className={cn(
                  'text-xs px-1.5 py-0.5 rounded-full',
                  activeFilter === tab.type
                    ? 'bg-stratum-500/20'
                    : 'bg-surface-tertiary'
                )}>
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Actions list */}
      <div className="p-4 space-y-3">
        {displayActions.length > 0 ? (
          displayActions.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              onApply={onApply}
              onDismiss={onDismiss}
              onQueue={onQueue}
              disabled={isActionsDisabled}
              compact
            />
          ))
        ) : (
          <div className="text-center py-8">
            <div className="w-12 h-12 rounded-full bg-surface-tertiary flex items-center justify-center mx-auto mb-3">
              <SparklesIcon className="w-6 h-6 text-text-muted" />
            </div>
            <p className="text-text-muted">No pending actions</p>
          </div>
        )}
      </div>

      {/* Footer */}
      {pendingActions.length > maxActions && (
        <div className="p-4 border-t border-white/10">
          <button className="text-sm text-stratum-400 hover:text-stratum-300 transition-colors">
            View all {pendingActions.length} actions
          </button>
        </div>
      )}
    </div>
  )
}

export default ActionsPanel
