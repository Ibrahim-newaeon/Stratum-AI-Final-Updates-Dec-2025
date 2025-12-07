import { Plus, Pause, Play, BarChart3, Upload, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'

interface QuickActionsWidgetProps {
  className?: string
}

const actions = [
  { id: 1, label: 'New Campaign', icon: Plus, color: 'bg-primary hover:bg-primary/90' },
  { id: 2, label: 'Pause All', icon: Pause, color: 'bg-amber-500 hover:bg-amber-600' },
  { id: 3, label: 'Resume All', icon: Play, color: 'bg-green-500 hover:bg-green-600' },
  { id: 4, label: 'View Reports', icon: BarChart3, color: 'bg-blue-500 hover:bg-blue-600' },
  { id: 5, label: 'Upload Asset', icon: Upload, color: 'bg-purple-500 hover:bg-purple-600' },
  { id: 6, label: 'New Rule', icon: Zap, color: 'bg-cyan-500 hover:bg-cyan-600' },
]

export function QuickActionsWidget({ className }: QuickActionsWidgetProps) {
  return (
    <div className={cn('h-full p-4', className)}>
      <div className="grid grid-cols-2 gap-2 h-full">
        {actions.map((action) => {
          const Icon = action.icon
          return (
            <button
              key={action.id}
              className={cn(
                'flex flex-col items-center justify-center gap-2 p-3 rounded-lg text-white transition-colors',
                action.color
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="text-xs font-medium">{action.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
