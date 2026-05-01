/**
 * InsightsPanel — "what needs my attention" surface.
 *
 * The dashboard home's most important card. A highlighted Card that
 * lists Insight items sorted by severity. Each item: severity-coloured
 * icon, title, body, optional primary action button.
 *
 * Severity drives the icon dot color and item ordering when callers
 * pass `sortBySeverity` (default true).
 *
 * Loading / empty / error are first-class.
 */

import { type ReactNode, useMemo } from 'react';
import { ArrowRight, AlertTriangle, AlertCircle, Info, CheckCircle2 } from 'lucide-react';
import { Card } from './Card';
import { cn } from '@/lib/utils';

export type InsightSeverity = 'critical' | 'warning' | 'info' | 'success';

export interface InsightItem {
  id: string;
  severity: InsightSeverity;
  title: string;
  body?: ReactNode;
  /** Optional CTA action — when provided, an action button is rendered. */
  action?: {
    label: string;
    onClick: () => void;
    /** href takes precedence; renders as <a> for full-page nav. */
    href?: string;
  };
}

interface InsightsPanelProps {
  title?: string;
  description?: string;
  items: InsightItem[];
  /** Cap items displayed. Default 5. */
  maxItems?: number;
  /** Sort by severity (critical → warning → info → success). Default true. */
  sortBySeverity?: boolean;
  loading?: boolean;
  error?: string;
  emptyMessage?: string;
  className?: string;
}

const SEVERITY_RANK: Record<InsightSeverity, number> = {
  critical: 0,
  warning: 1,
  info: 2,
  success: 3,
};

const SEVERITY_ICON: Record<InsightSeverity, typeof AlertTriangle> = {
  critical: AlertCircle,
  warning: AlertTriangle,
  info: Info,
  success: CheckCircle2,
};

const SEVERITY_TONE: Record<
  InsightSeverity,
  { icon: string; ring: string; bg: string }
> = {
  critical: {
    icon: 'text-danger',
    ring: 'border-danger/30',
    bg: 'bg-danger/10',
  },
  warning: {
    icon: 'text-warning',
    ring: 'border-warning/30',
    bg: 'bg-warning/10',
  },
  info: {
    icon: 'text-info',
    ring: 'border-info/30',
    bg: 'bg-info/10',
  },
  success: {
    icon: 'text-success',
    ring: 'border-success/30',
    bg: 'bg-success/10',
  },
};

function InsightRow({ item }: { item: InsightItem }) {
  const Icon = SEVERITY_ICON[item.severity];
  const tone = SEVERITY_TONE[item.severity];
  const action = item.action;

  return (
    <li className="flex gap-3 py-3 first:pt-0 last:pb-0 border-b border-border last:border-b-0">
      <div
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full inline-flex items-center justify-center',
          'border',
          tone.ring,
          tone.bg
        )}
      >
        <Icon className={cn('w-4 h-4', tone.icon)} aria-hidden="true" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-body font-medium text-foreground leading-snug">{item.title}</p>
        {item.body && (
          <p className="text-meta text-muted-foreground mt-0.5 leading-relaxed">
            {item.body}
          </p>
        )}
      </div>
      {action && (
        action.href ? (
          <a
            href={action.href}
            className={cn(
              'flex-shrink-0 inline-flex items-center gap-1 text-meta font-medium',
              'text-primary hover:text-primary/80 transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-full px-2 py-1'
            )}
          >
            {action.label}
            <ArrowRight className="w-3 h-3" aria-hidden="true" />
          </a>
        ) : (
          <button
            type="button"
            onClick={action.onClick}
            className={cn(
              'flex-shrink-0 inline-flex items-center gap-1 text-meta font-medium',
              'text-primary hover:text-primary/80 transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-full px-2 py-1'
            )}
          >
            {action.label}
            <ArrowRight className="w-3 h-3" aria-hidden="true" />
          </button>
        )
      )}
    </li>
  );
}

export function InsightsPanel({
  title = 'What needs your attention',
  description,
  items,
  maxItems = 5,
  sortBySeverity = true,
  loading = false,
  error,
  emptyMessage = "All clear — no signals require attention right now.",
  className,
}: InsightsPanelProps) {
  const displayed = useMemo(() => {
    const arr = sortBySeverity
      ? [...items].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity])
      : items;
    return arr.slice(0, maxItems);
  }, [items, sortBySeverity, maxItems]);

  return (
    <Card variant="glow" className={cn('p-6', className)}>
      <div className="mb-5">
        <h3 className="text-h3 font-medium tracking-tight text-foreground">{title}</h3>
        {description && (
          <p className="text-body text-muted-foreground mt-1">{description}</p>
        )}
      </div>

      {loading && (
        <ul className="divide-y divide-border" aria-busy="true">
          {Array.from({ length: 3 }).map((_, i) => (
            <li key={i} className="flex gap-3 py-3 first:pt-0 last:pb-0">
              <div className="w-8 h-8 rounded-full bg-muted animate-pulse" />
              <div className="flex-1 space-y-2">
                <div className="h-3 w-2/3 bg-muted rounded animate-pulse" />
                <div className="h-3 w-1/2 bg-muted rounded animate-pulse" />
              </div>
            </li>
          ))}
        </ul>
      )}

      {!loading && error && (
        <div role="alert" className="text-meta text-danger py-2">
          {error}
        </div>
      )}

      {!loading && !error && displayed.length === 0 && (
        <div className="flex items-center gap-3 py-3 text-meta text-muted-foreground">
          <CheckCircle2 className="w-4 h-4 text-success flex-shrink-0" aria-hidden="true" />
          {emptyMessage}
        </div>
      )}

      {!loading && !error && displayed.length > 0 && (
        <ul className="divide-y divide-border">
          {displayed.map((item) => (
            <InsightRow key={item.id} item={item} />
          ))}
        </ul>
      )}
    </Card>
  );
}

export default InsightsPanel;
