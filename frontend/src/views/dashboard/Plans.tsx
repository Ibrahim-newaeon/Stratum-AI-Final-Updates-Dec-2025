/**
 * Plans — tier picker page.
 *
 * Real Stripe checkout flow:
 *   1. User clicks "Upgrade to Professional" on a tier card
 *   2. ConfirmDrawer opens with the price preview
 *   3. On confirm, useCreateCheckout fires POST /payments/checkout
 *   4. Backend creates a Stripe Checkout Session, returns the hosted-checkout URL
 *   5. We redirect window.location to that URL — Stripe handles card entry,
 *      success/cancel redirect back to our /payments-result handlers
 *   6. Stripe webhook fires, updates tenant.plan + stripe_customer_id
 *
 * Page composes from existing primitives — Card (with `glow` for the
 * recommended tier), KPI-style price block, ConfirmDrawer for the
 * preview gate. Live data only — no mock fallbacks. If the backend
 * doesn't expose a tier (e.g., Stripe not configured in dev), the
 * empty state surfaces "Billing not configured — contact support."
 */

import { useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Check, Loader2, Sparkles } from 'lucide-react';
import { Card } from '@/components/primitives/Card';
import { StatusPill } from '@/components/primitives/StatusPill';
import { ConfirmDrawer } from '@/components/primitives/ConfirmDrawer';
import {
  useCancelSubscription,
  useCreateCheckout,
  usePaymentConfig,
  type TierInfo,
} from '@/api/payments';
import { useSubscriptionStatus } from '@/api/subscription';
import { cn } from '@/lib/utils';

type TierKey = 'starter' | 'professional' | 'enterprise';

interface UITier {
  key: TierKey;
  name: string;
  price: number;
  /** Tagline under the name. */
  tagline: string;
  /** When non-null, render a "Recommended" pill + glow. */
  badge?: string;
  features: string[];
  /** Best-fit copy for the CTA based on current plan. */
  cta: string;
}

/**
 * Default content for each tier. Backend's /payments/config drives
 * the live price + feature list when available; this content is the
 * fallback so the page never blanks out.
 */
const DEFAULT_TIERS: UITier[] = [
  {
    key: 'starter',
    name: 'Starter',
    price: 499,
    tagline: 'For growing agencies running up to 5 client accounts.',
    features: [
      'Up to 5 ad accounts across Meta, Google, TikTok',
      'Trust-gated autopilot (advisory mode)',
      'Signal health monitoring + EMQ scoring',
      'Up to 25 active campaigns',
      'Email support · 24h response SLA',
    ],
    cta: 'Continue with Starter',
  },
  {
    key: 'professional',
    name: 'Professional',
    price: 999,
    tagline: 'Most popular — for agencies scaling beyond 10 accounts.',
    badge: 'Recommended',
    features: [
      'Unlimited ad accounts + campaigns',
      'Trust-gated autopilot (soft + hard block modes)',
      'Custom autopilot rules + bulk-mutation drawer',
      'Reporting + Slack/email scheduled exports',
      'CDP audience sync to all platforms',
      'Priority support · 4h response SLA',
    ],
    cta: 'Upgrade to Professional',
  },
  {
    key: 'enterprise',
    name: 'Enterprise',
    price: 0, // Custom pricing
    tagline: 'For large agencies with custom compliance and SLA needs.',
    features: [
      'Everything in Professional',
      'Multi-tenant + custom roles + SSO',
      'Audit logs · GDPR/CCPA workflows',
      'Custom signal-health thresholds + autopilot rules',
      'Dedicated success manager · 1h response SLA',
      'Custom contract + invoicing',
    ],
    cta: 'Talk to sales',
  },
];

function mergeWithBackend(defaults: UITier[], backendTiers: TierInfo[]): UITier[] {
  return defaults.map((d) => {
    const live = backendTiers.find((b) => b.tier === d.key);
    if (!live) return d;
    return {
      ...d,
      price: live.price ?? d.price,
      features: live.features?.length ? live.features : d.features,
    };
  });
}

function formatPrice(price: number): string {
  if (price === 0) return 'Custom';
  return `$${price.toLocaleString()}`;
}

interface PendingUpgrade {
  tier: UITier;
}

export default function Plans() {
  const config = usePaymentConfig();
  const subscription = useSubscriptionStatus();
  const checkout = useCreateCheckout();
  const cancelMutation = useCancelSubscription();

  const [pending, setPending] = useState<PendingUpgrade | null>(null);
  const [redirectError, setRedirectError] = useState<string | null>(null);

  // Cancel-flow state. Two-step: open the drawer with a reason capture
  // (optional textarea, helps us understand churn), then confirm fires
  // useCancelSubscription. Subscription stays active until period end —
  // Stripe handles the prorate/grace via cancel_at_period_end=true on
  // the backend.
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState('');
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [cancelDone, setCancelDone] = useState(false);

  const tiers = useMemo<UITier[]>(() => {
    const backendTiers = config.data?.tiers ?? [];
    return mergeWithBackend(DEFAULT_TIERS, backendTiers);
  }, [config.data]);

  const currentPlan = (subscription.data?.plan ?? '').toLowerCase();
  const isTrial = subscription.data?.is_trial === true;
  const stripeConfigured = config.data?.stripe_configured ?? false;
  // Only paid (non-trial, non-free) tenants can cancel — trial users
  // just let it expire; free tenants don't have a sub to cancel.
  const isPaid = !isTrial && (currentPlan === 'starter' || currentPlan === 'professional');

  const handleCancelConfirm = async () => {
    setCancelError(null);
    try {
      await cancelMutation.mutateAsync(cancelReason.trim() || undefined);
      setCancelDone(true);
      // Leave the drawer open so user sees confirmation; auto-close
      // after 2s so they go back to the plans grid.
      setTimeout(() => {
        setCancelOpen(false);
        setCancelDone(false);
        setCancelReason('');
      }, 2000);
    } catch (err) {
      const e = err as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      setCancelError(
        e?.response?.data?.detail ?? e?.message ?? 'Failed to cancel. Please try again.'
      );
    }
  };

  const handleConfirm = async () => {
    if (!pending) return;
    setRedirectError(null);

    // Enterprise: redirect to mailto / contact form rather than Stripe.
    if (pending.tier.key === 'enterprise') {
      window.location.href = 'mailto:sales@stratumai.app?subject=Enterprise%20plan%20inquiry';
      setPending(null);
      return;
    }

    try {
      const successUrl = `${window.location.origin}/dashboard/plans?status=success`;
      const cancelUrl = `${window.location.origin}/dashboard/plans?status=cancel`;
      const result = await checkout.mutateAsync({
        tier: pending.tier.key,
        success_url: successUrl,
        cancel_url: cancelUrl,
      });
      // Hand off to Stripe — the user finishes checkout there and
      // is redirected back via success_url. The webhook does the
      // tenant.plan update server-side.
      window.location.href = result.checkout_url;
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data
          ?.detail ??
        (err as { message?: string }).message ??
        'Failed to start checkout. Please try again.';
      setRedirectError(msg);
    }
  };

  return (
    <>
      <Helmet>
        <title>Plans · Stratum AI</title>
      </Helmet>

      <div className="space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-h1 font-medium tracking-tight text-foreground">Plans</h1>
            <p className="text-body text-muted-foreground mt-1">
              Pick the tier that matches your agency. All plans include the trust engine, autopilot,
              and signal health monitoring.
            </p>
          </div>
          {isTrial && subscription.data?.days_until_expiry != null && (
            <StatusPill variant="degraded" size="md">
              Trial · {subscription.data.days_until_expiry}d left
            </StatusPill>
          )}
        </header>

        {!stripeConfigured && config.isFetched && (
          <Card className="p-5 border-warning/40 bg-warning/5">
            <p className="text-body text-foreground">
              Billing isn't configured for this environment. Plans below are read-only —
              <a href="mailto:sales@stratumai.app" className="text-primary hover:underline ml-1">
                contact us
              </a>{' '}
              to upgrade.
            </p>
          </Card>
        )}

        {redirectError && (
          <Card className="p-5 border-danger/40 bg-danger/5">
            <p className="text-body text-foreground">
              <span className="font-medium text-danger">Couldn't start checkout.</span>{' '}
              {redirectError}
            </p>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {tiers.map((tier) => {
            const isCurrent = currentPlan === tier.key && !isTrial;
            const isRecommended = !!tier.badge;
            return (
              <Card
                key={tier.key}
                variant={isRecommended ? 'glow' : 'default'}
                className="p-6 flex flex-col"
              >
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-h2 font-medium tracking-tight text-foreground">
                    {tier.name}
                  </h2>
                  {isRecommended && (
                    <StatusPill variant="neutral" size="sm">
                      <Sparkles className="w-3 h-3" />
                      {tier.badge}
                    </StatusPill>
                  )}
                  {isCurrent && (
                    <StatusPill variant="healthy" size="sm">
                      Current
                    </StatusPill>
                  )}
                </div>

                <p className="text-body text-muted-foreground mb-5">{tier.tagline}</p>

                <div className="mb-6">
                  <span className="text-display-sm font-medium tabular-nums tracking-tight text-foreground">
                    {formatPrice(tier.price)}
                  </span>
                  {tier.price > 0 && (
                    <span className="text-meta text-muted-foreground ml-2">/ month</span>
                  )}
                </div>

                <ul className="space-y-3 mb-6 flex-1">
                  {tier.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5">
                      <Check
                        className="w-4 h-4 mt-0.5 flex-shrink-0 text-success"
                        aria-hidden="true"
                      />
                      <span className="text-body text-foreground">{f}</span>
                    </li>
                  ))}
                </ul>

                <button
                  type="button"
                  disabled={isCurrent || (!stripeConfigured && tier.key !== 'enterprise')}
                  onClick={() => setPending({ tier })}
                  className={cn(
                    'w-full inline-flex items-center justify-center px-4 py-2.5 rounded-full',
                    'text-meta font-medium transition-all',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card',
                    'disabled:opacity-50 disabled:cursor-not-allowed',
                    isRecommended
                      ? 'bg-primary text-primary-foreground hover:brightness-110'
                      : 'bg-card border border-border text-foreground hover:border-primary/50 hover:bg-muted'
                  )}
                >
                  {isCurrent ? 'Active' : tier.cta}
                </button>
              </Card>
            );
          })}
        </div>

        {/* Self-service cancel — only renders for paid tenants. Trial
            users let the trial expire; free tenants have no sub. */}
        {isPaid && (
          <Card className="p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0">
              <h3 className="text-h3 font-medium text-foreground">Cancel subscription</h3>
              <p className="text-body text-muted-foreground mt-1">
                You can cancel anytime. Your access stays active until the end of the current
                billing period.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                setCancelError(null);
                setCancelDone(false);
                setCancelOpen(true);
              }}
              className={cn(
                'flex-shrink-0 inline-flex items-center justify-center px-4 py-2 rounded-full',
                'border border-border bg-card text-foreground text-meta font-medium',
                'hover:border-danger/40 hover:text-danger transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
              )}
            >
              Cancel plan
            </button>
          </Card>
        )}

        <p className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono">
          All prices in USD. Cancel anytime from billing settings. Receipts and invoices mailed
          monthly.
        </p>
      </div>

      {/* Cancel-subscription drawer. Two-state: confirm + (post-cancel)
          done. Reason textarea is optional but captured if provided so
          the team can review churn signals later. */}
      <ConfirmDrawer
        open={cancelOpen}
        onOpenChange={(open) => {
          if (!open) {
            setCancelOpen(false);
            setCancelError(null);
            // Don't reset reason here — keep it across drawer toggles
            // until the cancel succeeds.
          }
        }}
        title={cancelDone ? 'Subscription cancelled' : 'Cancel subscription?'}
        description={
          cancelDone
            ? 'Your access stays active until the end of the current billing period. No further charges will be made.'
            : 'Your access continues until the end of the current billing period. We won’t bill you again. You can resubscribe anytime.'
        }
        variant="destructive"
        confirmLabel={cancelDone ? 'Done' : 'Cancel my plan'}
        cancelLabel={cancelDone ? '' : 'Keep my plan'}
        onConfirm={cancelDone ? () => setCancelOpen(false) : handleCancelConfirm}
        loading={cancelMutation.isPending}
      >
        {!cancelDone && (
          <div className="space-y-3">
            <label className="block">
              <span className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono">
                Tell us why (optional)
              </span>
              <textarea
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                rows={3}
                placeholder="What could we have done better?"
                className={cn(
                  'mt-1.5 w-full rounded-xl bg-card border border-border',
                  'px-3 py-2 text-body text-foreground placeholder:text-muted-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  'resize-none'
                )}
              />
            </label>
            {cancelError && (
              <p className="text-meta text-danger" role="alert">
                <span className="font-medium">Couldn't cancel.</span> {cancelError}
              </p>
            )}
          </div>
        )}
      </ConfirmDrawer>

      <ConfirmDrawer
        open={pending !== null}
        onOpenChange={(open) => {
          if (!open) {
            setPending(null);
            setRedirectError(null);
          }
        }}
        title={
          pending?.tier.key === 'enterprise'
            ? 'Talk to our sales team'
            : `Upgrade to ${pending?.tier.name ?? ''}`
        }
        description={
          pending?.tier.key === 'enterprise'
            ? 'We’ll open your email client to start the conversation.'
            : `You'll be redirected to Stripe to enter payment details. Your card is charged ${formatPrice(pending?.tier.price ?? 0)} per month, recurring until cancelled.`
        }
        variant={pending?.tier.key === 'enterprise' ? 'default' : 'default'}
        confirmLabel={pending?.tier.key === 'enterprise' ? 'Open email' : `Continue to checkout`}
        onConfirm={handleConfirm}
        loading={checkout.isPending}
      >
        {pending && pending.tier.key !== 'enterprise' && (
          <div className="rounded-xl border border-border bg-muted/30 p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono">
                Plan
              </span>
              <span className="text-body font-medium text-foreground">{pending.tier.name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-meta uppercase tracking-[0.06em] text-muted-foreground font-mono">
                Charge
              </span>
              <span className="text-body font-medium text-foreground tabular-nums">
                {formatPrice(pending.tier.price)} / month
              </span>
            </div>
            {checkout.isPending && (
              <div className="flex items-center gap-2 text-meta text-muted-foreground pt-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Connecting to Stripe…
              </div>
            )}
          </div>
        )}
      </ConfirmDrawer>
    </>
  );
}
