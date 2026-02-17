/**
 * EMQ Timeline
 * Displays incident timeline with recovery hours and status changes
 */

import { cn } from '@/lib/utils'
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'

export interface TimelineEvent {
  id: string
  type: 'incident_opened' | 'incident_closed' | 'degradation' | 'recovery' | 'update'
  title: string
  description?: string
  timestamp: Date
  platform?: string
  severity?: 'critical' | 'high' | 'medium' | 'low'
  recoveryHours?: number
  emqImpact?: number
}

interface EmqTimelineProps {
  events: TimelineEvent[]
  maxEvents?: number
  showRecoveryTime?: boolean
  className?: string
}

const eventConfig = {
  incident_opened: {
    icon: ExclamationTriangleIcon,
    color: 'text-danger',
    bgColor: 'bg-danger/10',
    lineColor: 'bg-danger',
  },
  incident_closed: {
    icon: CheckCircleIcon,
    color: 'text-success',
    bgColor: 'bg-success/10',
    lineColor: 'bg-success',
  },
  degradation: {
    icon: ExclamationTriangleIcon,
    color: 'text-warning',
    bgColor: 'bg-warning/10',
    lineColor: 'bg-warning',
  },
  recovery: {
    icon: ArrowPathIcon,
    color: 'text-success',
    bgColor: 'bg-success/10',
    lineColor: 'bg-success',
  },
  update: {
    icon: ClockIcon,
    color: 'text-text-secondary',
    bgColor: 'bg-surface-tertiary',
    lineColor: 'bg-white/20',
  },
}

function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffHours < 1) {
    const diffMins = Math.floor(diffMs / (1000 * 60))
    return `${diffMins}m ago`
  }
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function EmqTimeline({
  events,
  maxEvents = 10,
  showRecoveryTime = true,
  className,
}: EmqTimelineProps) {
  const displayEvents = events.slice(0, maxEvents)

  return (
    <div className={cn(
      'rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden',
      className
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-surface-tertiary">
            <ClockIcon className="w-5 h-5 text-text-secondary" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Incident Timeline</h3>
            <p className="text-sm text-text-muted">
              Recent data quality events
            </p>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="p-4">
        <div className="relative">
          {displayEvents.map((event, index) => {
            const config = eventConfig[event.type]
            const Icon = config.icon
            const isLast = index === displayEvents.length - 1

            return (
              <div key={event.id} className="relative pb-6 last:pb-0">
                {/* Connector line */}
                {!isLast && (
                  <div
                    className={cn(
                      'absolute left-4 top-8 bottom-0 w-0.5 -translate-x-1/2',
                      config.lineColor
                    )}
                  />
                )}

                <div className="flex gap-4">
                  {/* Icon */}
                  <div className={cn(
                    'relative z-10 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
                    config.bgColor
                  )}>
                    <Icon className={cn('w-4 h-4', config.color)} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 pt-0.5">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-medium text-white">
                          {event.title}
                        </h4>
                        {event.description && (
                          <p className="text-sm text-text-muted mt-0.5">
                            {event.description}
                          </p>
                        )}
                      </div>
                      <span className="text-xs text-text-muted whitespace-nowrap">
                        {formatRelativeTime(event.timestamp)}
                      </span>
                    </div>

                    {/* Meta info */}
                    <div className="flex items-center gap-3 mt-2">
                      {event.platform && (
                        <span className="text-xs bg-surface-tertiary text-text-muted px-2 py-0.5 rounded">
                          {event.platform}
                        </span>
                      )}
                      {event.severity && (
                        <span className={cn(
                          'text-xs px-2 py-0.5 rounded',
                          event.severity === 'critical' && 'bg-danger/10 text-danger',
                          event.severity === 'high' && 'bg-orange-500/10 text-orange-400',
                          event.severity === 'medium' && 'bg-warning/10 text-warning',
                          event.severity === 'low' && 'bg-surface-tertiary text-text-muted',
                        )}>
                          {event.severity}
                        </span>
                      )}
                      {showRecoveryTime && event.recoveryHours !== undefined && (
                        <span className="text-xs text-text-muted flex items-center gap-1">
                          <ArrowPathIcon className="w-3 h-3" />
                          Recovered in {event.recoveryHours}h
                        </span>
                      )}
                      {event.emqImpact !== undefined && (
                        <span className={cn(
                          'text-xs',
                          event.emqImpact > 0 ? 'text-success' : 'text-danger'
                        )}>
                          {event.emqImpact > 0 ? '+' : ''}{event.emqImpact} EMQ
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {events.length > maxEvents && (
          <button className="mt-4 text-sm text-stratum-400 hover:text-stratum-300 transition-colors">
            View all {events.length} events
          </button>
        )}
      </div>
    </div>
  )
}

export default EmqTimeline
