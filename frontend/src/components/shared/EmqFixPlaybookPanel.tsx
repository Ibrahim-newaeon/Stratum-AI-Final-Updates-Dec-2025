/**
 * EMQ Fix Playbook Panel
 * Displays ranked fixes with owners and priority levels
 */

import { cn } from '@/lib/utils'
import {
  WrenchScrewdriverIcon,
  UserCircleIcon,
  ClockIcon,
  CheckCircleIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline'

export interface PlaybookItem {
  id: string
  title: string
  description: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  owner?: string
  estimatedImpact: number // Expected EMQ improvement
  estimatedTime?: string // e.g., "15 min", "1 hour"
  platform?: string
  status: 'pending' | 'in_progress' | 'completed'
  actionUrl?: string
}

interface EmqFixPlaybookPanelProps {
  items: PlaybookItem[]
  onItemClick?: (item: PlaybookItem) => void
  onAssign?: (item: PlaybookItem) => void
  onApply?: (item: PlaybookItem) => void
  maxItems?: number
  showEstimates?: boolean
  className?: string
}

const priorityConfig = {
  critical: {
    color: 'text-danger',
    bgColor: 'bg-danger/10',
    borderColor: 'border-danger/30',
    label: 'Critical',
  },
  high: {
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
    label: 'High',
  },
  medium: {
    color: 'text-warning',
    bgColor: 'bg-warning/10',
    borderColor: 'border-warning/30',
    label: 'Medium',
  },
  low: {
    color: 'text-text-secondary',
    bgColor: 'bg-surface-tertiary',
    borderColor: 'border-white/10',
    label: 'Low',
  },
}

export function EmqFixPlaybookPanel({
  items,
  onItemClick,
  onAssign,
  onApply,
  maxItems = 5,
  showEstimates = true,
  className,
}: EmqFixPlaybookPanelProps) {
  const displayItems = items.slice(0, maxItems)
  const remainingCount = items.length - maxItems

  return (
    <div className={cn(
      'rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden',
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-stratum-500/10">
            <WrenchScrewdriverIcon className="w-5 h-5 text-stratum-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Fix Playbook</h3>
            <p className="text-sm text-text-muted">
              {items.filter(i => i.status === 'pending').length} fixes pending
            </p>
          </div>
        </div>
      </div>

      {/* Items */}
      <div className="divide-y divide-white/5">
        {displayItems.map((item, index) => {
          const priority = priorityConfig[item.priority]
          const isCompleted = item.status === 'completed'

          return (
            <div
              key={item.id}
              className={cn(
                'p-4 transition-colors',
                !isCompleted && 'hover:bg-white/5 cursor-pointer',
                isCompleted && 'opacity-60'
              )}
              onClick={() => !isCompleted && onItemClick?.(item)}
            >
              <div className="flex items-start gap-4">
                {/* Priority number */}
                <div className={cn(
                  'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm',
                  isCompleted ? 'bg-success/10 text-success' : priority.bgColor,
                  isCompleted ? '' : priority.color
                )}>
                  {isCompleted ? (
                    <CheckCircleIcon className="w-5 h-5" />
                  ) : (
                    index + 1
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className={cn(
                        'font-medium',
                        isCompleted ? 'text-text-muted line-through' : 'text-white'
                      )}>
                        {item.title}
                      </h4>
                      <p className="text-sm text-text-muted mt-0.5 line-clamp-2">
                        {item.description}
                      </p>
                    </div>

                    {/* Priority badge */}
                    <span className={cn(
                      'flex-shrink-0 text-xs px-2 py-0.5 rounded-full',
                      priority.bgColor,
                      priority.color
                    )}>
                      {priority.label}
                    </span>
                  </div>

                  {/* Meta row */}
                  <div className="flex items-center gap-4 mt-3">
                    {item.owner ? (
                      <div className="flex items-center gap-1.5 text-xs text-text-muted">
                        <UserCircleIcon className="w-4 h-4" />
                        <span>{item.owner}</span>
                      </div>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onAssign?.(item)
                        }}
                        className="flex items-center gap-1.5 text-xs text-stratum-400 hover:text-stratum-300"
                      >
                        <UserCircleIcon className="w-4 h-4" />
                        <span>Assign</span>
                      </button>
                    )}

                    {showEstimates && item.estimatedTime && (
                      <div className="flex items-center gap-1.5 text-xs text-text-muted">
                        <ClockIcon className="w-4 h-4" />
                        <span>{item.estimatedTime}</span>
                      </div>
                    )}

                    {showEstimates && (
                      <div className="flex items-center gap-1 text-xs text-success">
                        <span>+{item.estimatedImpact} EMQ</span>
                      </div>
                    )}

                    {item.platform && (
                      <span className="text-xs text-text-muted bg-surface-tertiary px-2 py-0.5 rounded">
                        {item.platform}
                      </span>
                    )}

                    {item.actionUrl && (
                      <a
                        href={item.actionUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1 text-xs text-stratum-400 hover:text-stratum-300"
                      >
                        <ArrowTopRightOnSquareIcon className="w-3.5 h-3.5" />
                      </a>
                    )}

                    {/* Apply button */}
                    {!isCompleted && onApply && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onApply(item)
                        }}
                        className="ml-auto px-3 py-1 text-xs font-medium rounded-lg bg-stratum-500 text-white hover:bg-stratum-600 transition-colors"
                      >
                        Apply Fix
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Footer - show more */}
      {remainingCount > 0 && (
        <div className="p-4 border-t border-white/10">
          <button className="text-sm text-stratum-400 hover:text-stratum-300 transition-colors">
            View {remainingCount} more fixes
          </button>
        </div>
      )}
    </div>
  )
}

export default EmqFixPlaybookPanel
