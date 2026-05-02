/**
 * OutcomeNudge — outcome-triggered upgrade nudge.
 *
 * Renders a small inline card on the dashboard home when:
 *   1. Tenant is on Starter or in trial (Pro/Enterprise users already
 *      paid; nudging them is annoying, not converting).
 *   2. Autopilot's delivered ≥ MIN_VALUE_CENTS in the last 7 days
 *      (small numbers feel desperate — "$14 saved" loses credibility).
 *   3. Autopilot fired ≥ MIN_DECISIONS decisions in the period
 *      (small samples are unreliable claims).
 *   4. Frequency cap respected: max 1 nudge per session, ≥ 7 days
 *      since last dismiss.
 *
 * Click "Upgrade" → triggers the global useUpgradePrompt() with the
 * outcome context preserved, opening the existing Stripe-checkout
 * drawer (same machinery as the limit-triggered + plans-page flow).
 *
 * Phase A: backend estimator returns 0 cents for everyone, so this
 * component renders nothing in production. The wiring is ready;
 * Phase B's counterfactual numbers will start lighting it up.
 */

import { useMemo, useState } from 'react';
import { Sparkles, X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useAutopilotOutcomeSummary } from '@/api/autopilot';
import { useSubscriptionStatus } from '@/api/subscription';
import { Card } from '@/components/primitives/Card';
import { useUpgradePrompt } from '@/components/billing/UpgradePromptProvider';
import { cn } from '@/lib/utils';

const MIN_VALUE_CENTS = 100_00; // $100 minimum to feel real
const MIN_DECISIONS = 3; // 3+ data points so the claim has support
const DISMISS_KEY = 'stratum-outcome-nudge-dismissed-at';
const DISMISS_COOLDOWN_DAYS = 7;
const SESSION_SHOWN_KEY = 'stratum-outcome-nudge-session-shown';

function readDismissedAt(): Date | null {
  try {
    const raw = localStorage.getItem(DISMISS_KEY);
    if (!raw) return null;
    const d = new Date(raw);
    return Number.isNaN(d.getTime()) ? null : d;
  } catch {
    return null;
  }
}

function writeDismissedNow(): void {
  try {
    localStorage.setItem(DISMISS_KEY, new Date().toISOString());
  } catch {
    // ignore
  }
}

function readSessionShown(): boolean {
  try {
    return sessionStorage.getItem(SESSION_SHOWN_KEY) === 'true';
  } catch {
    return false;
  }
}

function writeSessionShown(): void {
  try {
    sessionStorage.setItem(SESSION_SHOWN_KEY, 'true');
  } catch {
    // ignore
  }
}

function isInCooldown(dismissedAt: Date | null): boolean {
  if (!dismissedAt) return false;
  const ms = Date.now() - dismissedAt.getTime();
  return ms < DISMISS_COOLDOWN_DAYS * 24 * 60 * 60 * 1000;
}

function formatDollars(cents: number): string {
  const dollars = Math.round(cents / 100);
  return `$${dollars.toLocaleString()}`;
}

export function OutcomeNudge() {
  const { user } = useAuth();
  const tenantId = user?.tenant_id ?? 0;

  const sub = useSubscriptionStatus();
  const outcomes = useAutopilotOutcomeSummary(tenantId, '7d');
  const { triggerUpgrade } = useUpgradePrompt();

  // Latch the "shown this session" flag in state so re-renders don't
  // flicker the card. Read once on mount; we don't care about cross-tab
  // syncing for a frequency cap.
  const [hiddenInSession, setHiddenInSession] = useState<boolean>(() => readSessionShown());

  const eligibility = useMemo(() => {
    // Tenant tier gate — only Starter / trial users see the nudge.
    const plan = (sub.data?.plan ?? '').toLowerCase();
    const tier = (sub.data?.tier ?? '').toLowerCase();
    const isTrial = sub.data?.is_trial === true;
    const eligibleTier = isTrial || plan === 'starter' || tier === 'starter';

    // Outcome thresholds.
    const totalCents = outcomes.data?.total_value_cents ?? 0;
    const count = outcomes.data?.decisions_count ?? 0;
    const meetsValue = totalCents >= MIN_VALUE_CENTS;
    const meetsSample = count >= MIN_DECISIONS;

    // Cooldown / session gate.
    const dismissedAt = readDismissedAt();
    const inCooldown = isInCooldown(dismissedAt);

    return {
      eligible: eligibleTier && meetsValue && meetsSample && !inCooldown,
      totalCents,
      count,
    };
  }, [sub.data, outcomes.data]);

  if (sub.isPending || outcomes.isPending) return null;
  if (sub.isError || outcomes.isError) return null;
  if (!eligibility.eligible) return null;
  if (hiddenInSession) return null;

  // Mark the session — caller is responsible for re-renders.
  writeSessionShown();

  const valueText = formatDollars(eligibility.totalCents);

  return (
    <Card variant="glow" className="p-5">
      <div className="flex items-start gap-3">
        <Sparkles aria-hidden="true" className="w-4 h-4 mt-1 flex-shrink-0 text-primary" />
        <div className="flex-1 min-w-0">
          <p className="text-body text-foreground">
            <span className="font-medium">Stratum's saved you at least {valueText} this week.</span>{' '}
            <span className="text-muted-foreground">
              Upgrade to Professional to unlock hard-block enforcement and prevent more wasted
              spend.
            </span>
          </p>
          <p
            className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono mt-2"
            aria-label="Number of autopilot decisions in the period"
          >
            Based on {eligibility.count} autopilot decisions · last 7 days
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            triggerUpgrade({
              message: `Stratum's autopilot has delivered ${valueText} of value over the last 7 days. Upgrade to Professional to unlock hard-block enforcement, custom rules, and unlimited campaigns.`,
              suggestedTier: 'professional',
              currentTier: sub.data?.tier ?? sub.data?.plan ?? 'starter',
            });
          }}
          className={cn(
            'flex-shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-full',
            'bg-primary text-primary-foreground text-meta font-medium',
            'transition-all hover:brightness-110',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card'
          )}
        >
          See what Pro unlocks
        </button>
        <button
          type="button"
          onClick={() => {
            writeDismissedNow();
            setHiddenInSession(true);
          }}
          aria-label="Dismiss outcome nudge"
          className="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </Card>
  );
}

export default OutcomeNudge;
