/**
 * TrialBanner — figma-themed trial / expired banner.
 *
 * Three states (read live from /api/v1/subscription/status):
 *
 *   1. Active trial (is_trial && days > 3)
 *      Ember-tinted, dismissible per session.
 *      "{N} days left in your Starter trial."
 *
 *   2. Trial ending soon (is_trial && days <= 3)
 *      Warning-amber, dismissible per session.
 *      "Trial ending in {N} day(s)."
 *
 *   3. Expired / grace / cancelled (is_access_restricted)
 *      Danger-tinted, NOT dismissible — the banner stays sticky
 *      because autopilot has dropped to advisory mode and the
 *      user needs to know decisions are no longer firing.
 *      "Trial ended. Autopilot is in advisory mode."
 *
 * The "Upgrade" link goes to /dashboard/plans which triggers real
 * Stripe Checkout via useCreateCheckout.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertOctagon, Sparkles, X } from 'lucide-react';
import { useSubscriptionStatus } from '@/api/subscription';
import { cn } from '@/lib/utils';

const DISMISS_KEY = 'stratum-trial-banner-dismissed';
const URGENT_THRESHOLD_DAYS = 3;

type BannerState =
  | { kind: 'trial'; days: number; urgent: boolean }
  | { kind: 'expired'; reason: string }
  | { kind: 'hidden' };

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

  if (sub.isPending || sub.isError) return null;
  const data = sub.data;
  if (!data) return null;

  // Determine which state to render. Expired beats trial — once
  // restricted, the sticky expired banner takes over regardless
  // of the dismissed flag.
  let state: BannerState = { kind: 'hidden' };
  if (data.is_access_restricted) {
    state = {
      kind: 'expired',
      reason:
        data.restriction_reason ??
        'Trial ended. Autopilot is in advisory mode until you reactivate.',
    };
  } else if (data.is_trial && data.days_until_expiry != null && data.days_until_expiry > 0) {
    state = {
      kind: 'trial',
      days: data.days_until_expiry,
      urgent: data.days_until_expiry <= URGENT_THRESHOLD_DAYS,
    };
  }

  if (state.kind === 'hidden') return null;
  if (state.kind === 'trial' && dismissed) return null;

  const isExpired = state.kind === 'expired';
  const urgent = state.kind === 'trial' && state.urgent;

  const Icon = isExpired ? AlertOctagon : Sparkles;
  const containerTone = isExpired
    ? 'bg-danger/10 border-danger/40 text-foreground'
    : urgent
      ? 'bg-warning/10 border-warning/30 text-foreground'
      : 'bg-primary/8 border-primary/30 text-foreground';
  const iconTone = isExpired ? 'text-danger' : urgent ? 'text-warning' : 'text-primary';
  const ctaTone = isExpired
    ? 'bg-danger text-white hover:brightness-110'
    : urgent
      ? 'bg-warning text-zinc-950 hover:brightness-110'
      : 'bg-primary text-primary-foreground hover:brightness-110';

  const headline =
    state.kind === 'expired'
      ? 'Trial ended.'
      : urgent && state.kind === 'trial'
        ? `Trial ending in ${state.days} day${state.days === 1 ? '' : 's'}.`
        : state.kind === 'trial'
          ? `${state.days} days left in your Starter trial.`
          : '';

  const body =
    state.kind === 'expired'
      ? state.reason
      : 'Upgrade to keep autopilot running and pacing intact.';

  return (
    <div
      role={isExpired ? 'alert' : 'status'}
      aria-live={isExpired ? 'assertive' : 'polite'}
      className={cn('flex items-center gap-3 px-5 py-3 rounded-2xl border', containerTone)}
    >
      <Icon aria-hidden="true" className={cn('w-4 h-4 flex-shrink-0', iconTone)} />
      <div className="flex-1 min-w-0 text-body">
        <span className="font-medium">{headline}</span>
        <span className="text-muted-foreground ml-1.5">{body}</span>
      </div>
      <Link
        to="/dashboard/plans"
        className={cn(
          'flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-full',
          'text-meta font-medium transition-all',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card',
          ctaTone
        )}
      >
        {isExpired ? 'Reactivate' : 'Upgrade'}
      </Link>
      {!isExpired && (
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
      )}
    </div>
  );
}

export default TrialBanner;
