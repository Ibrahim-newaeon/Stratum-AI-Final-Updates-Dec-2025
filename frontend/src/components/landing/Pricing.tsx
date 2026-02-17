import { useNavigate } from 'react-router-dom';
import { CheckIcon } from '@heroicons/react/24/outline';

export function Pricing() {
  const navigate = useNavigate();

  const plans = [
    {
      name: 'Starter',
      description: 'For small teams getting started',
      price: '$299',
      period: '/month',
      features: [
        '2 ad platforms',
        'Up to $50K monthly ad spend',
        '3 team members',
        'Signal Health monitoring',
        'Basic anomaly detection',
        'Email support',
      ],
      cta: 'Start Free Trial',
      highlighted: false,
    },
    {
      name: 'Pro',
      description: 'For growing marketing teams',
      price: '$799',
      period: '/month',
      features: [
        'All 4 ad platforms + GA4',
        'Up to $500K monthly ad spend',
        '10 team members',
        'Full Trust Layer (EMQ + Variance)',
        'Intelligence Layer (Scaling + Fatigue)',
        'Autopilot (Limited mode)',
        'Campaign Builder',
        'Priority support',
      ],
      cta: 'Start Free Trial',
      highlighted: true,
      badge: 'Most Popular',
    },
    {
      name: 'Enterprise',
      description: 'For large organizations',
      price: 'Custom',
      period: '',
      features: [
        'Unlimited ad platforms',
        'Unlimited ad spend',
        'Unlimited team members',
        'Full USP Stack',
        'Autopilot (All modes)',
        'Custom integrations',
        'Dedicated success manager',
        'SLA guarantee',
        'SSO & advanced security',
      ],
      cta: 'Contact Sales',
      highlighted: false,
    },
  ];

  return (
    <section className="py-32 bg-surface-primary">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section header */}
        <div className="text-center mb-16">
          <h2 className="text-h1 text-white mb-4">
            Simple, transparent pricing
          </h2>
          <p className="text-body text-text-secondary max-w-2xl mx-auto">
            Start free for 14 days. No credit card required. Cancel anytime.
          </p>
        </div>

        {/* Pricing cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-2xl p-8 ${
                plan.highlighted
                  ? 'bg-gradient-to-b from-stratum-500/10 to-surface-secondary border-2 border-stratum-500/30'
                  : 'bg-surface-secondary border border-white/5'
              }`}
            >
              {/* Badge */}
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-4 py-1 rounded-full bg-gradient-stratum text-white text-meta font-medium">
                    {plan.badge}
                  </span>
                </div>
              )}

              {/* Plan header */}
              <div className="mb-8">
                <h3 className="text-h3 text-white mb-2">{plan.name}</h3>
                <p className="text-meta text-text-muted mb-4">{plan.description}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-[40px] font-bold text-white">{plan.price}</span>
                  <span className="text-body text-text-muted">{plan.period}</span>
                </div>
              </div>

              {/* Features */}
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-3">
                    <CheckIcon className="w-5 h-5 text-success flex-shrink-0 mt-0.5" />
                    <span className="text-body text-text-secondary">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <button
                onClick={() => navigate(plan.name === 'Enterprise' ? '/contact' : '/signup')}
                className={`w-full py-3 rounded-xl font-medium text-body transition-all duration-base ${
                  plan.highlighted
                    ? 'bg-gradient-stratum text-white hover:shadow-glow'
                    : 'bg-white/5 text-white border border-white/10 hover:bg-white/10'
                }`}
              >
                {plan.cta}
              </button>
            </div>
          ))}
        </div>

        {/* FAQ teaser */}
        <div className="mt-16 text-center">
          <p className="text-body text-text-muted">
            Have questions?{' '}
            <a href="#" className="text-stratum-400 hover:text-stratum-300 transition-colors">
              Check our FAQ
            </a>{' '}
            or{' '}
            <a href="#" className="text-stratum-400 hover:text-stratum-300 transition-colors">
              contact sales
            </a>
          </p>
        </div>
      </div>
    </section>
  );
}
