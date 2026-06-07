import type { MarketingSeedEntry } from './types';
import type { PricingPageContent } from '../../../src/api/cms';

const content_json: PricingPageContent = {
  tiers: [
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
      highlighted: true,
      badge: 'Most popular',
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
      highlighted: false,
    },
  ],
  faqs: [
    {
      question: 'What counts as a monthly event?',
      answer:
        'Events include any data point tracked through our platform: page views, purchases, form submissions, API calls, and more.',
    },
    {
      question: 'Can I change plans later?',
      answer:
        'Yes, you can upgrade or downgrade your plan at any time. Changes take effect on your next billing cycle.',
    },
    {
      question: 'Is there a free trial?',
      answer:
        'Yes, all plans include a 14-day free trial with full access to all features. No credit card required.',
    },
    {
      question: 'What payment methods do you accept?',
      answer:
        'We accept all major credit cards, ACH transfers, and wire transfers for annual Enterprise plans.',
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'pricing',
  title: 'Pricing',
  template: 'pricing',
  meta_title: 'Pricing',
  meta_description:
    'Simple, transparent pricing for Stratum AI. Start with a 14-day free trial. Plans from $499/month for growing teams.',
  content_json,
};

export default entry;
