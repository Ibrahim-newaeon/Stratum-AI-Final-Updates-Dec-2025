/**
 * SignalStrip — alert-summary chips + bulk-acknowledge action.
 *
 * Three chips: 🔴 trust holds  ·  🟡 signal/pacing  ·  🔵 autopilot pending
 * Clicking a chip drives the FocusPane (selected-alert routing).
 *
 * If alerts = 0, the strip collapses to a single "All clear" chip in
 * a hairline-only treatment so the home doesn't feel empty.
 *
 * "Acknowledge" is intentionally NOT one-click destructive — it opens a
 * preview drawer (out of scope for this commit; the button currently
 * defers to an onAcknowledgeAll handler the parent owns).
 */

import { CheckCircle2, Bell } from 'lucide-react';
import { Card } from '@/components/primitives/Card';
import { StatusPill } from '@/components/primitives/StatusPill';
import { cn } from '@/lib/utils';
import type { AlertSummary, FocusKey } from './types';

interface SignalStripProps {
  summaries: AlertSummary[];
  selectedFocus: FocusKey;
  onSelectFocus: (focus: FocusKey) => void;
  onAcknowledgeAll?: () => void;
  loading?: boolean;
}

const SEVERITY_VARIANT = {
  critical: 'unhealthy' as const,
  warning: 'degraded' as const,
  info: 'neutral' as const,
};

function ChipButton({
  active,
  onClick,
  children,
  className,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'rounded-full transition-all duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card',
        active
          ? 'ring-2 ring-primary/50 ring-offset-2 ring-offset-card'
          : 'opacity-80 hover:opacity-100',
        className
      )}
    >
      {children}
    </button>
  );
}

export function SignalStrip({
  summaries,
  selectedFocus,
  onSelectFocus,
  onAcknowledgeAll,
  loading,
}: SignalStripProps) {
  const totalCount = summaries.reduce((sum, s) => sum + s.count, 0);
  const allClear = !loading && totalCount === 0;

  if (allClear) {
    return (
      <Card className="px-5 py-3 flex items-center gap-3">
        <CheckCircle2 className="w-5 h-5 text-success flex-shrink-0" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          <p className="text-body font-medium text-foreground">All clear.</p>
          <p className="text-meta text-muted-foreground">
            No alerts require attention. Trust gate operational; autopilot running.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="px-5 py-3 flex flex-wrap items-center gap-3">
      <Bell
        className={cn(
          'w-4 h-4 flex-shrink-0',
          totalCount > 0 ? 'text-primary' : 'text-muted-foreground'
        )}
        aria-hidden="true"
      />

      <div className="flex flex-wrap items-center gap-2 flex-1 min-w-0">
        {loading
          ? Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="h-6 w-24 rounded-full bg-muted/50 animate-pulse"
                aria-hidden="true"
              />
            ))
          : summaries.map((s) => (
              <ChipButton
                key={s.focus}
                active={s.focus === selectedFocus}
                onClick={() => onSelectFocus(s.focus)}
              >
                <StatusPill
                  variant={SEVERITY_VARIANT[s.severity]}
                  size="sm"
                  pulse={s.severity === 'critical'}
                >
                  <span className="tabular-nums">{s.count}</span>
                  <span className="ml-1.5 normal-case tracking-normal">{s.label}</span>
                </StatusPill>
              </ChipButton>
            ))}
      </div>

      {onAcknowledgeAll && totalCount > 0 && !loading && (
        <button
          type="button"
          onClick={onAcknowledgeAll}
          className={cn(
            'flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-full',
            'text-meta font-medium border border-border',
            'text-foreground hover:bg-muted transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
          )}
        >
          Acknowledge all
        </button>
      )}
    </Card>
  );
}

export default SignalStrip;
