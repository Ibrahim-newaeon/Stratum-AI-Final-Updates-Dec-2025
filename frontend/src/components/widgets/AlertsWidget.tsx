import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AlertsWidgetProps {
  className?: string;
}

const mockAlerts = [
  {
    id: 1,
    type: 'warning',
    message: 'Summer Sale campaign ROAS dropped below 3.0',
    time: '2h ago',
  },
  { id: 2, type: 'success', message: 'Brand Awareness hit budget milestone', time: '4h ago' },
  { id: 3, type: 'error', message: 'TikTok API rate limit reached', time: '6h ago' },
  { id: 4, type: 'info', message: 'New competitor detected: AcmeCorp', time: '1d ago' },
];

// Analytics Design System status colors
const alertConfig = {
  warning: { icon: AlertTriangle, color: 'text-warning', bg: 'bg-warning/10' },
  success: { icon: CheckCircle, color: 'text-success', bg: 'bg-success/10' },
  error: { icon: XCircle, color: 'text-danger', bg: 'bg-danger/10', motion: 'motion-critical' },
  info: { icon: Info, color: 'text-info', bg: 'bg-info/10' },
};

export function AlertsWidget({ className }: AlertsWidgetProps) {
  return (
    <div className={cn('h-full p-4 overflow-auto', className)}>
      <div className="space-y-3">
        {mockAlerts.map((alert, index) => {
          const config = alertConfig[alert.type as keyof typeof alertConfig];
          const Icon = config.icon;
          const motionClass = 'motion' in config ? config.motion : 'motion-enter';
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
                <p className="text-sm text-body">{alert.message}</p>
                <p className="text-xs text-text-muted mt-1">{alert.time}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
