/**
 * QuickActionsBar - Quick action buttons bar
 */

import { useNavigate } from 'react-router-dom';
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
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { QuickAction } from '@/api/dashboard';

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
};

interface QuickActionsBarProps {
  actions: QuickAction[];
}

export function QuickActionsBar({ actions }: QuickActionsBarProps) {
  const navigate = useNavigate();

  if (actions.length === 0) {
    return null;
  }

  const handleAction = (action: QuickAction) => {
    // Handle different action types
    if (action.action.startsWith('/')) {
      navigate(action.action);
    } else if (action.action.startsWith('http')) {
      window.open(action.action, '_blank');
    } else {
      // Emit custom event for action handlers
      window.dispatchEvent(new CustomEvent('quick-action', { detail: action }));
    }
  };

  const getIcon = (iconName: string) => {
    const Icon = iconMap[iconName.toLowerCase()] || Zap;
    return Icon;
  };

  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action) => {
        const Icon = getIcon(action.icon);

        return (
          <button
            key={action.id}
            onClick={() => handleAction(action)}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2.5 rounded-xl',
              'bg-white/[0.04] border border-white/[0.07]',
              'hover:bg-white/[0.08] hover:border-primary/20',
              'transition-all duration-200 text-sm font-medium group'
            )}
          >
            <Icon className="w-4 h-4 text-primary group-hover:scale-110 transition-transform" />
            <span>{action.label}</span>
            {action.count !== null && action.count > 0 && (
              <span className="ml-0.5 px-2 py-0.5 text-[11px] bg-primary/15 text-primary rounded-full font-semibold tabular-nums">
                {action.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
