import { useNavigate } from 'react-router-dom';
import { CheckIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { usePricingTiers, useTrustBadges, type PricingTier, type TrustBadge } from '@/api/cms';

// Fallback pricing data when CMS content is not available
const fallbackPlans: PricingTier[] = [
  {
    id: '1',
    name: 'Starter',
    description: 'For teams scaling their ad operations',
    price: '$499',
    period: '/month',
    adSpend: 'Up to $100K monthly ad spend',
    features: [
      '5 ad accounts',
      'Signal health monitoring',
      'RFM customer analysis',
      'Dashboard exports',
      'Slack notifications',
      'Anomaly detection alerts',
      'Email support (48hr)',
    ],
    cta: 'Start Free Trial',
    ctaLink: '/signup',
    highlighted: false,
    displayOrder: 0,
  },
  {
    id: '2',
    name: 'Professional',
    description: 'For growing marketing teams',
    price: '$999',
    period: '/month',
    adSpend: 'Up to $500K monthly ad spend',
    features: [
      '15 ad accounts',
      'Everything in Starter',
      'Funnel builder',
      'Computed traits',
      'Trust gate audit logs',
      'Action dry-run mode',
      'Pipedrive CRM integration',
      'Priority support (24hr)',
    ],
    cta: 'Start Free Trial',
    ctaLink: '/signup',
    highlighted: true,
    badge: 'Most Popular',
    displayOrder: 1,
  },
  {
    id: '3',
    name: 'Enterprise',
    description: 'For large organizations',
    price: 'Custom',
    period: '',
    adSpend: 'Unlimited ad spend',
    features: [
      'Unlimited ad accounts',
      'Everything in Professional',
      'Predictive churn modeling',
      'Custom autopilot rules',
      'Salesforce CRM integration',
      'Custom report builder',
      'Consent management (GDPR/CCPA)',
      'Dedicated success manager (4hr)',
    ],
    cta: 'Contact Sales',
    ctaLink: '/contact',
    highlighted: false,
    displayOrder: 2,
  },
];

const fallbackTrustBadges: TrustBadge[] = [
  { id: '1', icon: '🔒', text: 'SOC 2 Compliant', displayOrder: 0 },
  { id: '2', icon: '🛡️', text: 'GDPR Ready', displayOrder: 1 },
  { id: '3', icon: '💳', text: 'No Card for Trial', displayOrder: 2 },
  { id: '4', icon: '🔄', text: 'Cancel Anytime', displayOrder: 3 },
  { id: '5', icon: '💰', text: '30-Day Money Back', displayOrder: 4 },
];

export function Pricing() {
  const navigate = useNavigate();

  // Fetch from CMS with fallback
  const { data: cmsPlans, isLoading: plansLoading } = usePricingTiers();
  const { data: cmsBadges, isLoading: badgesLoading } = useTrustBadges();

  // Use CMS data if available and has content, otherwise use fallback
  const plans = (cmsPlans && cmsPlans.length > 0) ? cmsPlans : fallbackPlans;
  const trustBadges = (cmsBadges && cmsBadges.length > 0) ? cmsBadges : fallbackTrustBadges;

  const isLoading = plansLoading || badgesLoading;

  return (
    <section className="py-32 bg-surface-primary" id="pricing">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section header */}
        <div className="text-center mb-16">
          <Badge variant="outline" className="mb-4 px-4 py-1 text-orange-400 border-orange-500/30 bg-orange-500/10">
            Pricing
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Simple, Transparent Pricing
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            Choose the plan that fits your ad spend. All plans include full access to core features.
            Start free for 14 days — no credit card required.
          </p>
        </div>

        {/* Pricing cards */}
        <div className={`grid md:grid-cols-3 gap-8 max-w-6xl mx-auto ${isLoading ? 'opacity-50' : ''}`}>
          {plans.map((plan) => (
            <Card
              key={plan.id}
              className={`relative flex flex-col ${
                plan.highlighted
                  ? 'bg-gradient-to-b from-orange-500/10 to-gray-900 border-2 border-orange-500/30 shadow-lg shadow-orange-500/10'
                  : 'bg-gray-900/50 border-white/10'
              }`}
            >
              {/* Badge */}
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
                  <Badge className="bg-gradient-to-r from-orange-500 to-orange-600 text-white border-0 px-4 py-1">
                    <SparklesIcon className="w-3 h-3 mr-1" />
                    {plan.badge}
                  </Badge>
                </div>
              )}

              <CardHeader className="pb-4">
                <CardTitle className="text-2xl text-white">{plan.name}</CardTitle>
                <CardDescription className="text-gray-400">{plan.description}</CardDescription>
              </CardHeader>

              <CardContent className="flex-1">
                {/* Price */}
                <div className="mb-4">
                  <div className="flex items-baseline gap-1">
                    <span className="text-5xl font-bold text-white">{plan.price}</span>
                    <span className="text-lg text-gray-500">{plan.period}</span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">{plan.adSpend}</p>
                </div>

                <Separator className="my-6 bg-white/10" />

                {/* Features */}
                <ul className="space-y-3">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start gap-3">
                      <CheckIcon className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-gray-300">{feature}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>

              <CardFooter className="pt-6">
                <Button
                  onClick={() => navigate(plan.ctaLink || (plan.name === 'Enterprise' ? '/contact' : '/signup'))}
                  className={`w-full py-6 text-base font-semibold ${
                    plan.highlighted
                      ? 'bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 text-white shadow-lg shadow-orange-500/30'
                      : 'bg-white/10 text-white border border-white/20 hover:bg-white/20'
                  }`}
                  size="lg"
                >
                  {plan.cta}
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>

        {/* Trust Badges */}
        <div className="mt-16 flex flex-wrap justify-center gap-4">
          {trustBadges.map((badge) => (
            <Badge
              key={badge.id}
              variant="outline"
              className="px-4 py-2 text-sm bg-gray-900/50 border-white/10 text-gray-400"
            >
              <span className="mr-2">{badge.icon}</span>
              {badge.text}
            </Badge>
          ))}
        </div>

        {/* Comparison teaser */}
        <div className="mt-16 text-center">
          <Card className="inline-block bg-gray-900/50 border-white/10 px-8 py-6">
            <div className="flex items-center gap-4">
              <div className="text-left">
                <p className="text-white font-medium">Not sure which plan is right for you?</p>
                <p className="text-sm text-gray-500">Talk to our team for a personalized recommendation.</p>
              </div>
              <Button
                variant="outline"
                className="border-orange-500/30 text-orange-400 hover:bg-orange-500/10"
                onClick={() => navigate('/contact')}
              >
                Contact Sales
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </section>
  );
}
