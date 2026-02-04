import { BarChart3, Pause, Play, Plus, Upload, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';

interface QuickActionsWidgetProps {
  className?: string;
}

const actions = [
  {
    id: 1,
    label: 'New Campaign',
    icon: Plus,
    color: 'bg-primary hover:bg-primary/90 focus-visible:ring-primary',
  },
  {
    id: 2,
    label: 'Pause All',
    icon: Pause,
    color:
      'bg-amber-500/90 hover:bg-amber-500 dark:bg-amber-600 dark:hover:bg-amber-500 focus-visible:ring-amber-500',
  },
  {
    id: 3,
    label: 'Resume All',
    icon: Play,
    color:
      'bg-emerald-500/90 hover:bg-emerald-500 dark:bg-emerald-600 dark:hover:bg-emerald-500 focus-visible:ring-emerald-500',
  },
  {
    id: 4,
    label: 'View Reports',
    icon: BarChart3,
    color:
      'bg-blue-500/90 hover:bg-blue-500 dark:bg-blue-600 dark:hover:bg-blue-500 focus-visible:ring-blue-500',
  },
  {
    id: 5,
    label: 'Upload Asset',
    icon: Upload,
    color:
      'bg-violet-500/90 hover:bg-violet-500 dark:bg-violet-600 dark:hover:bg-violet-500 focus-visible:ring-violet-500',
  },
  {
    id: 6,
    label: 'New Rule',
    icon: Zap,
    color:
      'bg-cyan-500/90 hover:bg-cyan-500 dark:bg-cyan-600 dark:hover:bg-cyan-500 focus-visible:ring-cyan-500',
  },
];

export function QuickActionsWidget({ className }: QuickActionsWidgetProps) {
  return (
    <div className={cn('h-full p-4', className)}>
      <div className="grid grid-cols-2 gap-2 h-full">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <button
              key={action.id}
              className={cn(
                'flex flex-col items-center justify-center gap-2 p-3 rounded-lg text-white transition-all duration-200',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
                'active:scale-95 motion-card',
                action.color
              )}
              aria-label={action.label}
            >
              <Icon className="w-5 h-5" aria-hidden="true" />
              <span className="text-xs font-medium">{action.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
