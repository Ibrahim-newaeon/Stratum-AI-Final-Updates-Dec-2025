/**
 * TrialBanner — figma-themed 14-day-trial banner.
 *
 * Renders above the dashboard content when the tenant is on an
 * active trial. Reads live state from /api/v1/subscription/status:
 *   - is_trial === true  → renders with the days_until_expiry count
 *   - days_until_expiry <= 3 → switches to a `warning` tone (amber)
 *                              for the last-stretch upgrade nudge
 *   - days_until_expiry <= 0 → renders nothing (the standard
 *                              expiry/grace flow takes over)
 *
 * The "Upgrade now" link goes to the real /dashboard/plans page,
 * which triggers Stripe Checkout via useCreateCheckout.
 *
 * The banner is dismissible per-session (sessionStorage flag) so
 * users can hide it if they're mid-task; it returns on the next
 * page load.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, X } from 'lucide-react';
import { useSubscriptionStatus } from '@/api/subscription';
import { cn } from '@/lib/utils';

const DISMISS_KEY = 'stratum-trial-banner-dismissed';
const URGENT_THRESHOLD_DAYS = 3;

function readDismissed(): boolean {
  try {
    return sessionStorage.getItem(DISMISS_KEY) === 'true';
  } catch {
    return false;
  }
}

function writeDismissed(): void {
  try {
    sessionStorage.setItem(DISMISS_KEY, 'true');
  } catch {
    // ignore
  }
}

export function TrialBanner() {
  const [dismissed, setDismissed] = useState<boolean>(() => readDismissed());
  const sub = useSubscriptionStatus();

  // Hide entirely until we have real data — no skeleton needed; the
  // banner is supplementary to the page, not its primary content.
  if (sub.isPending || sub.isError || dismissed) return null;

  const data = sub.data;
  if (!data || !data.is_trial) return null;

  const days = data.days_until_expiry;
  if (days == null || days <= 0) return null;

  const urgent = days <= URGENT_THRESHOLD_DAYS;

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'flex items-center gap-3 px-5 py-3 rounded-2xl border',
        urgent
          ? 'bg-warning/10 border-warning/30 text-foreground'
          : 'bg-primary/8 border-primary/30 text-foreground'
      )}
    >
      <Sparkles
        aria-hidden="true"
        className={cn('w-4 h-4 flex-shrink-0', urgent ? 'text-warning' : 'text-primary')}
      />
      <div className="flex-1 min-w-0 text-body">
        <span className="font-medium">
          {urgent
            ? `Trial ending in ${days} day${days === 1 ? '' : 's'}.`
            : `${days} days left in your Starter trial.`}
        </span>
        <span className="text-muted-foreground ml-1.5">
          Upgrade to keep autopilot running and pacing intact.
        </span>
      </div>
      <Link
        to="/dashboard/plans"
        className={cn(
          'flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-full',
          'text-meta font-medium transition-all',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card',
          urgent
            ? 'bg-warning text-zinc-950 hover:brightness-110'
            : 'bg-primary text-primary-foreground hover:brightness-110'
        )}
      >
        Upgrade
      </Link>
      <button
        type="button"
        onClick={() => {
          writeDismissed();
          setDismissed(true);
        }}
        aria-label="Dismiss trial banner"
        className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

export default TrialBanner;
