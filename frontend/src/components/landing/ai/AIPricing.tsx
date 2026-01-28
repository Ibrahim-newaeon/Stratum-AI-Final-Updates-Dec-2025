/**
 * AI Pricing Section - Tiered AI Feature Access
 * 2026 Design: Glass cards with gradient accents
 */

import { motion, useInView } from 'framer-motion';
import { useRef, useState } from 'react';
import {
  ArrowRightIcon,
  BuildingOffice2Icon,
  CheckIcon,
  InformationCircleIcon,
  RocketLaunchIcon,
  SparklesIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

type BillingCycle = 'monthly' | 'annual';

interface PricingFeature {
  name: string;
  starter: boolean | string;
  professional: boolean | string;
  enterprise: boolean | string;
  tooltip?: string;
}

const pricingTiers = [
  {
    id: 'starter',
    name: 'Starter',
    description: 'For growing teams getting started with AI-powered revenue ops',
    icon: RocketLaunchIcon,
    monthlyPrice: 299,
    annualPrice: 249,
    color: 'from-blue-500 to-cyan-500',
    bgColor: 'from-blue-500/5 to-cyan-500/5',
    borderColor: 'border-blue-500/20',
    popular: false,
    cta: 'Start Free Trial',
    limits: {
      profiles: '50K',
      events: '500K/mo',
      platforms: 2,
      users: 3,
    },
  },
  {
    id: 'professional',
    name: 'Professional',
    description: 'For scaling teams that need full AI capabilities',
    icon: SparklesIcon,
    monthlyPrice: 799,
    annualPrice: 649,
    color: 'from-purple-500 to-violet-500',
    bgColor: 'from-purple-500/10 to-violet-500/5',
    borderColor: 'border-purple-500/30',
    popular: true,
    cta: 'Start Free Trial',
    limits: {
      profiles: '500K',
      events: '5M/mo',
      platforms: 4,
      users: 10,
    },
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    description: 'For large organizations with custom requirements',
    icon: BuildingOffice2Icon,
    monthlyPrice: null,
    annualPrice: null,
    color: 'from-orange-500 to-amber-500',
    bgColor: 'from-orange-500/5 to-amber-500/5',
    borderColor: 'border-orange-500/20',
    popular: false,
    cta: 'Contact Sales',
    limits: {
      profiles: 'Unlimited',
      events: 'Unlimited',
      platforms: 'All',
      users: 'Unlimited',
    },
  },
];

const featureCategories = [
  {
    category: 'AI Models',
    features: [
      { name: 'ROAS Predictor', starter: false, professional: true, enterprise: true },
      { name: 'Conversion Predictor', starter: false, professional: true, enterprise: true },
      {
        name: 'LTV Predictor',
        starter: 'Basic',
        professional: true,
        enterprise: true,
        tooltip: 'Starter: 30-day only. Pro+: All timeframes',
      },
      { name: 'Churn Predictor', starter: false, professional: true, enterprise: true },
      { name: 'Creative Lifecycle', starter: false, professional: true, enterprise: true },
      {
        name: 'ROAS Forecaster',
        starter: false,
        professional: '30-day',
        enterprise: true,
        tooltip: 'Enterprise: Up to 365-day forecasts',
      },
    ],
  },
  {
    category: 'Trust Engine',
    features: [
      { name: 'Signal Health Scoring', starter: true, professional: true, enterprise: true },
      { name: 'Trust-Gated Autopilot', starter: false, professional: true, enterprise: true },
      {
        name: 'Anomaly Detection',
        starter: 'Basic',
        professional: true,
        enterprise: true,
        tooltip: 'Starter: Z-score only. Pro+: ML-enhanced',
      },
      { name: 'Custom Thresholds', starter: false, professional: true, enterprise: true },
    ],
  },
  {
    category: 'CDP Features',
    features: [
      { name: 'Identity Resolution', starter: true, professional: true, enterprise: true },
      { name: 'Visual Identity Graph', starter: false, professional: true, enterprise: true },
      {
        name: 'RFM Segmentation',
        starter: '5 segments',
        professional: '11 segments',
        enterprise: '11 + custom',
      },
      {
        name: 'Event Processing',
        starter: 'Real-time',
        professional: 'Real-time',
        enterprise: 'Real-time + replay',
      },
    ],
  },
  {
    category: 'Audience Activation',
    features: [
      {
        name: 'Platform Sync',
        starter: '2 platforms',
        professional: '4 platforms',
        enterprise: 'All + custom',
      },
      {
        name: 'Auto-Sync Scheduling',
        starter: 'Daily',
        professional: 'Hourly',
        enterprise: 'Real-time',
      },
      { name: 'Match Rate Tracking', starter: true, professional: true, enterprise: true },
      {
        name: 'Custom Exports',
        starter: 'CSV',
        professional: 'CSV + JSON',
        enterprise: 'All formats + API',
      },
    ],
  },
  {
    category: 'Analytics & Tools',
    features: [
      { name: 'What-If Simulator', starter: false, professional: true, enterprise: true },
      {
        name: 'A/B Testing',
        starter: false,
        professional: 'Basic',
        enterprise: 'Advanced + power analysis',
      },
      { name: 'Model Explainability (SHAP)', starter: false, professional: true, enterprise: true },
      { name: 'Budget Optimizer', starter: false, professional: true, enterprise: true },
    ],
  },
  {
    category: 'Support & Security',
    features: [
      {
        name: 'Support',
        starter: 'Email',
        professional: 'Priority + Chat',
        enterprise: 'Dedicated CSM',
      },
      { name: 'SLA', starter: '99.5%', professional: '99.9%', enterprise: '99.99%' },
      { name: 'SSO/SAML', starter: false, professional: true, enterprise: true },
      { name: 'Custom Training', starter: false, professional: false, enterprise: true },
    ],
  },
];

const FeatureValue = ({ value }: { value: boolean | string }) => {
  if (value === true) {
    return (
      <div className="flex items-center justify-center">
        <div className="w-5 h-5 rounded-full bg-green-500/20 flex items-center justify-center">
          <CheckIcon className="w-3 h-3 text-green-400" />
        </div>
      </div>
    );
  }
  if (value === false) {
    return (
      <div className="flex items-center justify-center">
        <div className="w-5 h-5 rounded-full bg-gray-500/20 flex items-center justify-center">
          <XMarkIcon className="w-3 h-3 text-gray-500" />
        </div>
      </div>
    );
  }
  return <span className="text-xs text-gray-300 text-center">{value}</span>;
};

export default function AIPricing() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });
  const [billingCycle, setBillingCycle] = useState<BillingCycle>('annual');
  const [showAllFeatures, setShowAllFeatures] = useState(false);

  return (
    <section id="pricing" className="relative py-32 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-purple-500/[0.02] to-transparent" />

      <div className="relative z-10 max-w-7xl mx-auto px-6" ref={ref}>
        {/* Section Header - Centered */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          {/* Badge - Centered above hero */}
          <div className="flex justify-center mb-8">
            <div
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
              style={{
                background: 'rgba(34, 197, 94, 0.15)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
              }}
            >
              <SparklesIcon className="w-4 h-4" style={{ color: '#22c55e' }} />
              <span className="text-sm font-medium" style={{ color: '#22c55e' }}>AI-Powered Pricing</span>
            </div>
          </div>

          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6 text-center">
            <span className="text-white">Pay for the AI</span>
            <br />
            <span style={{ color: '#22c55e' }}>
              Power You Need
            </span>
          </h2>

          <p className="text-lg max-w-2xl mx-auto mb-10 text-center" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
            All plans include the core platform. Upgrade for advanced AI models and higher limits.
          </p>

          {/* Billing Toggle */}
          <div className="inline-flex items-center gap-4 p-1.5 rounded-full bg-white/[0.03] border border-white/[0.05]">
            <button
              onClick={() => setBillingCycle('monthly')}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                billingCycle === 'monthly'
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingCycle('annual')}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-all ${
                billingCycle === 'annual'
                  ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Annual
              <span className="ml-2 text-xs bg-green-400/20 text-green-400 px-2 py-0.5 rounded-full">
                Save 20%
              </span>
            </button>
          </div>
        </motion.div>

        {/* Pricing Cards */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16"
        >
          {pricingTiers.map((tier, index) => {
            const price = billingCycle === 'monthly' ? tier.monthlyPrice : tier.annualPrice;

            return (
              <motion.div
                key={tier.id}
                initial={{ opacity: 0, y: 20 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                transition={{ delay: 0.1 * index, duration: 0.6 }}
                className={`relative rounded-3xl bg-gradient-to-b ${tier.bgColor} border ${tier.borderColor} backdrop-blur-xl overflow-hidden ${
                  tier.popular ? 'ring-2 ring-purple-500/50 scale-[1.02]' : ''
                }`}
              >
                {/* Popular Badge */}
                {tier.popular && (
                  <div className="absolute top-0 left-0 right-0 bg-gradient-to-r from-purple-500 to-violet-500 text-center py-2">
                    <span className="text-xs font-semibold text-white uppercase tracking-wider">
                      Most Popular
                    </span>
                  </div>
                )}

                <div className={`p-8 ${tier.popular ? 'pt-14' : ''}`}>
                  {/* Icon & Name */}
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`p-2 rounded-xl bg-gradient-to-br ${tier.color}`}>
                      <tier.icon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h3 className="text-xl font-semibold text-white">{tier.name}</h3>
                    </div>
                  </div>

                  <p className="text-sm text-gray-400 mb-6">{tier.description}</p>

                  {/* Price */}
                  <div className="mb-6">
                    {price ? (
                      <div className="flex items-baseline gap-2">
                        <span className="text-4xl font-bold text-white">${price}</span>
                        <span className="text-gray-500">/month</span>
                      </div>
                    ) : (
                      <div className="text-2xl font-bold text-white">Custom Pricing</div>
                    )}
                    {billingCycle === 'annual' && price && (
                      <div className="text-xs text-gray-500 mt-1">
                        Billed annually (${price * 12}/year)
                      </div>
                    )}
                  </div>

                  {/* CTA Button */}
                  <a
                    href={tier.id === 'enterprise' ? '/contact' : '/signup'}
                    className={`block w-full py-3 px-6 rounded-xl text-center font-medium transition-all ${
                      tier.popular
                        ? 'bg-gradient-to-r from-purple-500 to-violet-500 text-white hover:opacity-90'
                        : 'bg-white/[0.05] border border-white/10 text-white hover:bg-white/10'
                    }`}
                  >
                    {tier.cta}
                    {tier.id !== 'enterprise' && (
                      <ArrowRightIcon className="inline-block w-4 h-4 ml-2" />
                    )}
                  </a>

                  {/* Limits */}
                  <div className="mt-6 pt-6 border-t border-white/[0.05] grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-lg font-semibold text-white">{tier.limits.profiles}</div>
                      <div className="text-xs text-gray-500">Profiles</div>
                    </div>
                    <div>
                      <div className="text-lg font-semibold text-white">{tier.limits.events}</div>
                      <div className="text-xs text-gray-500">Events</div>
                    </div>
                    <div>
                      <div className="text-lg font-semibold text-white">
                        {tier.limits.platforms}
                      </div>
                      <div className="text-xs text-gray-500">Platforms</div>
                    </div>
                    <div>
                      <div className="text-lg font-semibold text-white">{tier.limits.users}</div>
                      <div className="text-xs text-gray-500">Users</div>
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </motion.div>

        {/* Feature Comparison Toggle */}
        <div className="text-center mb-8">
          <button
            onClick={() => setShowAllFeatures(!showAllFeatures)}
            className="inline-flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300 transition-colors"
          >
            {showAllFeatures ? 'Hide' : 'Show'} detailed feature comparison
            <motion.svg
              animate={{ rotate: showAllFeatures ? 180 : 0 }}
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </motion.svg>
          </button>
        </div>

        {/* Detailed Feature Comparison */}
        <motion.div
          initial={false}
          animate={{
            height: showAllFeatures ? 'auto' : 0,
            opacity: showAllFeatures ? 1 : 0,
          }}
          transition={{ duration: 0.4 }}
          className="overflow-hidden"
        >
          <div className="rounded-3xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl overflow-hidden">
            {/* Header */}
            <div className="grid grid-cols-4 gap-4 p-6 border-b border-white/[0.05] bg-white/[0.02]">
              <div className="text-sm font-medium text-gray-400">Feature</div>
              <div className="text-sm font-medium text-center text-blue-400">Starter</div>
              <div className="text-sm font-medium text-center text-purple-400">Professional</div>
              <div className="text-sm font-medium text-center text-orange-400">Enterprise</div>
            </div>

            {/* Feature Categories */}
            {featureCategories.map((category) => (
              <div key={category.category}>
                <div className="px-6 py-3 bg-white/[0.02] border-b border-white/[0.05]">
                  <span className="text-sm font-semibold text-white">{category.category}</span>
                </div>
                {category.features.map((feature, index) => (
                  <div
                    key={feature.name}
                    className={`grid grid-cols-4 gap-4 px-6 py-4 items-center ${
                      index < category.features.length - 1 ? 'border-b border-white/[0.03]' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-300">{feature.name}</span>
                      {feature.tooltip && (
                        <div className="group relative">
                          <InformationCircleIcon className="w-4 h-4 text-gray-500 cursor-help" />
                          <div className="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 border border-white/10 rounded-lg text-xs text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                            {feature.tooltip}
                          </div>
                        </div>
                      )}
                    </div>
                    <FeatureValue value={feature.starter} />
                    <FeatureValue value={feature.professional} />
                    <FeatureValue value={feature.enterprise} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </motion.div>

        {/* Enterprise CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.4, duration: 0.6 }}
          className="mt-16 text-center"
        >
          <p className="text-gray-400 mb-4">
            Need custom integrations, dedicated support, or volume pricing?
          </p>
          <a
            href="/contact"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 text-white font-medium hover:opacity-90 transition-opacity"
          >
            Talk to Sales
            <ArrowRightIcon className="w-4 h-4" />
          </a>
        </motion.div>
      </div>
    </section>
  );
}
