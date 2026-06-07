/**
 * Pricing Page — landing-themed (ink + ember).
 */

import { Link } from 'react-router-dom';
import { Check } from 'lucide-react';
import { usePageContent, type PricingPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { MktHero, MktSectionHeader, MktCard } from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';

const fallbackTiers = [
  {
    name: 'Starter',
    price: '$499',
    period: '/month',
    description: 'Perfect for growing teams getting started with revenue intelligence.',
    features: [
      'Up to 100K monthly events',
      '5 team members',
      '3 ad platform connections',
      'Basic signal health monitoring',
      'Standard attribution models',
      'Email support',
    ],
    cta: 'Start Free Trial',
    href: '/signup?plan=starter',
    highlighted: false,
  },
  {
    name: 'Professional',
    price: '$1,499',
    period: '/month',
    description: 'For scaling teams that need advanced automation and insights.',
    features: [
      'Up to 1M monthly events',
      '15 team members',
      'Unlimited platform connections',
      'Advanced signal health + alerts',
      'Trust-Gated Autopilot',
      'CDP with audience sync',
      'Custom attribution models',
      'ML predictions & forecasting',
      'Priority support',
    ],
    cta: 'Start Free Trial',
    href: '/signup?plan=professional',
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    description: 'For large organizations with complex requirements.',
    features: [
      'Unlimited events',
      'Unlimited team members',
      'All Professional features',
      'Custom integrations',
      'Dedicated account manager',
      'SLA guarantee',
      'On-premise deployment option',
      'Advanced security & compliance',
      'Custom training & onboarding',
    ],
    cta: 'Contact Sales',
    href: '/contact',
    highlighted: false,
  },
];

const fallbackFaqs = [
  {
    q: 'What counts as a monthly event?',
    a: 'Events include any data point tracked through our platform: page views, purchases, form submissions, API calls, and more.',
  },
  {
    q: 'Can I change plans later?',
    a: 'Yes, you can upgrade or downgrade your plan at any time. Changes take effect on your next billing cycle.',
  },
  {
    q: 'Is there a free trial?',
    a: 'Yes, all plans include a 14-day free trial with full access to all features. No credit card required.',
  },
  {
    q: 'What payment methods do you accept?',
    a: 'We accept all major credit cards, ACH transfers, and wire transfers for annual Enterprise plans.',
  },
];

export default function Pricing() {
  const { page, content } = usePageContent<PricingPageContent>('pricing');

  const tiers = content?.tiers?.length
    ? content.tiers.map((t) => ({
        name: t.name,
        price: t.price,
        period: t.period,
        description: t.description,
        features: t.features,
        cta: t.cta,
        href: t.highlighted
          ? '/signup?plan=professional'
          : t.name === 'Enterprise'
            ? '/contact'
            : `/signup?plan=${t.name.toLowerCase()}`,
        highlighted: t.highlighted,
      }))
    : fallbackTiers;

  const faqs = content?.faqs?.length
    ? content.faqs.map((f) => ({ q: f.question, a: f.answer }))
    : fallbackFaqs;

  const seoTitle = page?.meta_title || pageSEO.pricing.title;
  const seoDescription = page?.meta_description || pageSEO.pricing.description;

  return (
    <PageLayout>
      <SEO
        {...pageSEO.pricing}
        title={seoTitle}
        description={seoDescription}
        url="https://stratumai.app/pricing"
      />

      <MktHero
        badge="Pricing"
        title="Simple, transparent"
        highlight="pricing"
        subtitle="Start with a 14-day free trial — no credit card required. Scale up as your revenue operations grow."
      />

      {/* Tiers */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            {tiers.map((tier, i) => (
              <MktCard
                key={tier.name}
                delay={i * 0.06}
                className={`relative p-8 ${
                  tier.highlighted
                    ? 'border-secondary/40 shadow-glow lg:-mt-4 lg:mb-4'
                    : ''
                }`}
              >
                {tier.highlighted ? (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 inline-flex items-center px-3 py-1 rounded-full bg-stratum-500 text-primary-foreground text-meta uppercase font-semibold">
                    Most popular
                  </span>
                ) : null}
                <h3 className="text-h2 text-foreground font-semibold">{tier.name}</h3>
                <p className="mt-2 text-body text-muted-foreground min-h-[2.75rem]">
                  {tier.description}
                </p>
                <div className="mt-6 flex items-baseline gap-1">
                  <span className="text-display-sm text-foreground font-medium">
                    {tier.price}
                  </span>
                  {tier.period ? (
                    <span className="text-body text-muted-foreground">{tier.period}</span>
                  ) : null}
                </div>
                <Link
                  to={tier.href}
                  className={`mt-6 inline-flex w-full items-center justify-center px-6 py-3 rounded-full text-body font-semibold transition-all duration-200 ${
                    tier.highlighted
                      ? 'bg-stratum-500 text-primary-foreground hover:brightness-110 hover:shadow-glow'
                      : 'bg-card border border-border text-foreground hover:bg-foreground/5'
                  }`}
                >
                  {tier.cta}
                </Link>
                <ul className="mt-8 space-y-3">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <Check className="w-4 h-4 mt-0.5 flex-shrink-0 text-secondary" />
                      <span className="text-body text-muted-foreground">{feature}</span>
                    </li>
                  ))}
                </ul>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-24 lg:py-28">
        <div className="max-w-3xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="FAQ" title="Questions," highlight="answered" />
          <div className="space-y-4">
            {faqs.map((faq, i) => (
              <MktCard key={faq.q} delay={i * 0.05} className="p-6">
                <h3 className="text-h3 text-foreground font-semibold mb-2">{faq.q}</h3>
                <p className="text-body text-muted-foreground leading-relaxed">{faq.a}</p>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
