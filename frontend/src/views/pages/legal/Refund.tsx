/**
 * Refund & Cancellation Policy Page
 *
 * Required for Paddle merchant verification, which checks that a live,
 * publicly reachable refund/cancellation policy exists before approving an
 * account to take payments.
 *
 * The terms stated here mirror what the billing code actually does, so the
 * page cannot drift into promising behaviour the product does not have:
 *
 * - 14-day trial, granted once per tenant. `payments._trial_days_for_tenant`
 *   returns 0 once `Tenant.trial_ends_at` is set, which registration does at
 *   signup — so a cancel-and-resubscribe does not earn a second trial.
 * - Monthly billing. `TIER_PRICING` in `core/tiers.py` is monthly for every
 *   tier; there is no annual plan to describe.
 * - Cancellation takes effect at period end. Both gateways default to it:
 *   `paddle_service.cancel_subscription(at_period_end=True)` and the Stripe
 *   equivalent. Access continues until the paid period ends, which is why
 *   PAST_DUE and a scheduled cancellation both remain entitling states.
 * - Upgrades prorate by default (`update_subscription_tier(prorate=True)`).
 */

import { usePublicPage } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { MktHero, MktCard } from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';
import { sanitizeHtml } from '@/lib/sanitize';
import { ReceiptRefundIcon } from '@heroicons/react/24/outline';

export default function Refund() {
  const { data: page } = usePublicPage('refund');
  const hasCMSContent = !!(page?.content && page.content.length > 0);

  const seoTitle = page?.meta_title || pageSEO.refund.title;
  const seoDescription = page?.meta_description || pageSEO.refund.description;

  return (
    <PageLayout>
      <SEO
        {...pageSEO.refund}
        title={seoTitle}
        description={seoDescription}
        url="https://stratumai.app/refund-policy"
      />
      {/* Hero Section */}
      <MktHero
        badge="Legal"
        badgeIcon={ReceiptRefundIcon}
        title="Refund &"
        highlight="Cancellation"
        subtitle="Last updated: September 2, 2026"
      />

      {/* Content */}
      {hasCMSContent ? (
        <section className="pb-24">
          <div className="max-w-4xl mx-auto px-6">
            <MktCard className="p-8 md:p-10">
              <div
                className="space-y-4 text-body text-muted-foreground [&_h2]:text-h2 [&_h2]:text-foreground [&_h2]:font-semibold [&_h2]:mt-6 [&_h2]:mb-3 [&_h3]:text-h3 [&_h3]:text-foreground [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-6 [&_a]:text-secondary"
                dangerouslySetInnerHTML={{ __html: sanitizeHtml(page!.content!) }}
              />
            </MktCard>
          </div>
        </section>
      ) : (
        <section className="pb-24">
          <div className="max-w-4xl mx-auto px-6">
            <MktCard className="p-8 md:p-10">
              <div className="space-y-8">
                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">1. Free Trial</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    Every new account includes a 14-day free trial. You are not charged during the
                    trial, and you may cancel at any point before it ends without being billed. The
                    trial is offered once per account; cancelling and resubscribing does not start a
                    new trial period.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">2. Billing</h2>
                  <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                    <li>Subscriptions are billed monthly in advance</li>
                    <li>
                      Your first charge occurs when the trial ends, unless you cancel before then
                    </li>
                    <li>Renewal occurs automatically on the same day each month</li>
                    <li>All prices are in US dollars, exclusive of any applicable sales tax or VAT</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">3. Cancellation</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    You may cancel your subscription at any time from Billing Settings in your
                    dashboard, or by contacting support. Cancellations take effect at the end of your
                    current billing period.
                  </p>
                  <p className="text-body text-muted-foreground leading-relaxed mt-3">
                    You keep full access to your plan until that period ends — cancelling does not
                    cut off access immediately, and no further charges are made after it takes
                    effect. You may reactivate before the period ends to keep the subscription
                    running without interruption.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">4. Refunds</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    Because cancellation takes effect at the end of a billing period you have already
                    paid for, subscription fees are generally non-refundable and partial months are
                    not pro-rated on cancellation.
                  </p>
                  <p className="text-body text-muted-foreground leading-relaxed mt-3">
                    We will nonetheless issue a refund where any of the following applies:
                  </p>
                  <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground mt-3">
                    <li>You were charged after cancelling, or charged more than once for a period</li>
                    <li>
                      A sustained service failure prevented you from meaningfully using the platform
                    </li>
                    <li>The charge was not authorised by an account administrator</li>
                    <li>You were billed following a trial you had already cancelled</li>
                  </ul>
                  <p className="text-body text-muted-foreground leading-relaxed mt-3">
                    Request a refund within 30 days of the charge by contacting{' '}
                    <strong className="text-foreground">billing@stratumai.app</strong> with your
                    account name and the invoice in question. We aim to respond within 2 business
                    days, and approved refunds are returned to the original payment method, typically
                    within 5&ndash;10 business days depending on your bank.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">
                    5. Plan Changes and Proration
                  </h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    Upgrading takes effect immediately, and you are charged a prorated amount for the
                    remainder of the current billing period. Downgrading takes effect at the start of
                    your next billing period, so you retain the higher tier for the period you have
                    already paid for. Downgrades do not generate a refund of the difference.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">6. Failed Payments</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    If a payment fails, we retry it over a short dunning period and email the account
                    administrator. Your access continues during this window so a expired card does
                    not interrupt live campaign automation. If payment is not recovered, the
                    subscription is cancelled and the account returns to the free plan; your data is
                    retained and access is restored on resubscription.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">
                    7. Annual and Enterprise Agreements
                  </h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    Enterprise plans are billed under a separate written agreement. Where its refund
                    or cancellation terms differ from this page, that agreement governs.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">8. Contact</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    For any billing, cancellation, or refund question:
                    <br />
                    <strong className="text-foreground">Email:</strong> billing@stratumai.app
                  </p>
                </section>
              </div>
            </MktCard>
          </div>
        </section>
      )}
    </PageLayout>
  );
}
