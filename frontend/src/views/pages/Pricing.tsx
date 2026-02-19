/**
 * Pricing Page
 * Displays pricing tiers for Stratum AI
 */

import { Link } from 'react-router-dom';
import { usePageContent, type PricingPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CheckIcon } from '@heroicons/react/24/outline';
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

  // Use CMS data if available, otherwise fallback
  const tiers = content?.tiers?.length
    ? content.tiers.map((t) => ({
        name: t.name,
        price: t.price,
        period: t.period,
        description: t.description,
        features: t.features,
        cta: t.cta,
        href: t.highlighted ? '/signup?plan=professional' : t.name === 'Enterprise' ? '/contact' : `/signup?plan=${t.name.toLowerCase()}`,
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
      <SEO {...pageSEO.pricing} title={seoTitle} description={seoDescription} url="https://stratum-ai.com/pricing" />
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Simple, Transparent</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Pricing
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            Choose the plan that fits your team. All plans include a 14-day free trial.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {tiers.map((tier) => (
              <div
                key={tier.name}
                className={`relative p-8 rounded-3xl transition-all hover:scale-[1.02] ${
                  tier.highlighted ? 'ring-2' : ''
                }`}
                style={{
                  background: tier.highlighted
                    ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)'
                    : 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                {tier.highlighted && (
                  <div
                    className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-semibold"
                    style={{
                      background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
                      color: '#ffffff',
                    }}
                  >
                    Most Popular
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="text-xl font-semibold text-white mb-2">{tier.name}</h3>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold text-white">{tier.price}</span>
                    <span style={{ color: 'rgba(255, 255, 255, 0.5)' }}>{tier.period}</span>
                  </div>
                  <p className="mt-3 text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                    {tier.description}
                  </p>
                </div>

                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-3">
                      <CheckIcon
                        className="w-5 h-5 flex-shrink-0 mt-0.5"
                        style={{ color: '#34c759' }}
                      />
                      <span className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.8)' }}>
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                <Link
                  to={tier.href}
                  className="block w-full py-3 px-6 rounded-xl text-center font-semibold transition-all"
                  style={{
                    background: tier.highlighted ? '#f97316' : 'rgba(255, 255, 255, 0.06)',
                    color: '#ffffff',
                    border: tier.highlighted ? 'none' : '1px solid rgba(255, 255, 255, 0.12)',
                    boxShadow: tier.highlighted ? '0 4px 20px rgba(249, 115, 22, 0.4)' : 'none',
                  }}
                >
                  {tier.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-12">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            {faqs.map((faq) => (
              <div
                key={faq.q}
                className="p-6 rounded-2xl"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <h3 className="text-lg font-semibold text-white mb-2">{faq.q}</h3>
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  {faq.a}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
