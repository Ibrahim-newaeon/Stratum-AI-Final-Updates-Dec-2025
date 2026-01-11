/**
 * QuickActionsBar - Quick action buttons bar
 */

import { useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  BarChart3,
  Bell,
  Link2,
  Plus,
  RefreshCw,
  Settings,
  Sparkles,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { QuickAction } from '@/api/dashboard'

// Icon mapping for quick actions
const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  plus: Plus,
  link: Link2,
  sparkles: Sparkles,
  zap: Zap,
  settings: Settings,
  refresh: RefreshCw,
  bell: Bell,
  alert: AlertCircle,
  chart: BarChart3,
}

interface QuickActionsBarProps {
  actions: QuickAction[]
}

export function QuickActionsBar({ actions }: QuickActionsBarProps) {
  const navigate = useNavigate()

  if (actions.length === 0) {
    return null
  }

  const handleAction = (action: QuickAction) => {
    // Handle different action types
    if (action.action.startsWith('/')) {
      navigate(action.action)
    } else if (action.action.startsWith('http')) {
      window.open(action.action, '_blank')
    } else {
      // Emit custom event for action handlers
      window.dispatchEvent(new CustomEvent('quick-action', { detail: action }))
    }
  }

  const getIcon = (iconName: string) => {
    const Icon = iconMap[iconName.toLowerCase()] || Zap
    return Icon
  }

  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action) => {
        const Icon = getIcon(action.icon)

        return (
          <button
            key={action.id}
            onClick={() => handleAction(action)}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2 rounded-lg',
              'bg-card border hover:bg-muted transition-colors',
              'text-sm font-medium'
            )}
          >
            <Icon className="w-4 h-4 text-primary" />
            <span>{action.label}</span>
            {action.count !== null && action.count > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-primary/10 text-primary rounded-full font-medium">
                {action.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
