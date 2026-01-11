/**
 * ActivityFeed - Recent activity feed display
 */

import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Info,
  Key,
  Loader2,
  Settings,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ActivityItem } from '@/api/dashboard'

interface ActivityFeedProps {
  activities: ActivityItem[]
  loading?: boolean
  onViewAll?: () => void
}

export function ActivityFeed({ activities, loading = false, onViewAll }: ActivityFeedProps) {
  const getTypeConfig = (type: ActivityItem['type']) => {
    switch (type) {
      case 'action':
        return { icon: Zap, color: 'text-blue-500', bgColor: 'bg-blue-500/10' }
      case 'alert':
        return { icon: AlertCircle, color: 'text-yellow-500', bgColor: 'bg-yellow-500/10' }
      case 'auth':
        return { icon: Key, color: 'text-purple-500', bgColor: 'bg-purple-500/10' }
      case 'system':
        return { icon: Settings, color: 'text-muted-foreground', bgColor: 'bg-muted' }
      default:
        return { icon: Activity, color: 'text-muted-foreground', bgColor: 'bg-muted' }
    }
  }

  const getSeverityConfig = (severity: ActivityItem['severity']) => {
    switch (severity) {
      case 'success':
        return { icon: CheckCircle, color: 'text-green-500' }
      case 'warning':
        return { icon: AlertTriangle, color: 'text-yellow-500' }
      case 'error':
        return { icon: AlertCircle, color: 'text-red-500' }
      case 'info':
        return { icon: Info, color: 'text-blue-500' }
      default:
        return null
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  if (loading) {
    return (
      <div className="bg-card border rounded-lg p-5 flex items-center justify-center min-h-[200px]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="bg-card border rounded-lg">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Recent Activity</h3>
        </div>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          >
            View all
            <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>

      <div className="divide-y max-h-[400px] overflow-y-auto">
        {activities.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No recent activity</p>
          </div>
        ) : (
          activities.map((activity) => {
            const typeConfig = getTypeConfig(activity.type)
            const severityConfig = getSeverityConfig(activity.severity)
            const TypeIcon = typeConfig.icon
            const SeverityIcon = severityConfig?.icon

            return (
              <div key={activity.id} className="p-3 hover:bg-muted/50 transition-colors">
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                      typeConfig.bgColor
                    )}
                  >
                    <TypeIcon className={cn('w-4 h-4', typeConfig.color)} />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium line-clamp-1">{activity.title}</span>
                      {SeverityIcon && (
                        <SeverityIcon
                          className={cn('w-3.5 h-3.5 flex-shrink-0', severityConfig?.color)}
                        />
                      )}
                    </div>

                    {activity.description && (
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                        {activity.description}
                      </p>
                    )}

                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(activity.timestamp)}
                      </span>
                      {activity.entity_type && (
                        <>
                          <span className="text-xs text-muted-foreground">·</span>
                          <span className="text-xs text-muted-foreground capitalize">
                            {activity.entity_type}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
