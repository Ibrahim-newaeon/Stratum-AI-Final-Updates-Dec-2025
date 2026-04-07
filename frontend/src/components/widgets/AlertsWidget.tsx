import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useDashboardSimulation } from '@/contexts/DashboardSimulationContext'

interface AlertsWidgetProps {
  className?: string
}

// Analytics Design System status colors
const alertConfig = {
  warning: { icon: AlertTriangle, color: 'text-warning', bg: 'bg-warning/10' },
  success: { icon: CheckCircle, color: 'text-success', bg: 'bg-success/10' },
  good: { icon: CheckCircle, color: 'text-success', bg: 'bg-success/10' },
  error: { icon: XCircle, color: 'text-danger', bg: 'bg-danger/10', motion: 'motion-critical' },
  critical: { icon: XCircle, color: 'text-danger', bg: 'bg-danger/10', motion: 'motion-critical' },
  info: { icon: Info, color: 'text-info', bg: 'bg-info/10' },
}

export function AlertsWidget({ className }: AlertsWidgetProps) {
  const { alerts } = useDashboardSimulation()

  if (!alerts || alerts.length === 0) {
    return (
      <div className={cn('h-full p-4 flex items-center justify-center', className)}>
        <div className="text-center text-muted-foreground">
          <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
          <p className="text-sm">All clear — no alerts</p>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('h-full p-4 overflow-auto', className)}>
      <div className="space-y-3">
        {alerts.map((alert, index) => {
          const config = alertConfig[alert.severity as keyof typeof alertConfig] || alertConfig.info
          const Icon = config.icon
          const motionClass = 'motion' in config ? config.motion : 'motion-enter'
          return (
            <div
              key={alert.id}
              className={cn(
                'flex items-start gap-3 p-3 rounded-lg border border-transparent',
                config.bg,
                motionClass
              )}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <Icon className={cn('w-5 h-5 flex-shrink-0 mt-0.5', config.color)} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{alert.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{alert.message}</p>
                <p className="text-xs text-muted-foreground mt-1">{alert.time}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
