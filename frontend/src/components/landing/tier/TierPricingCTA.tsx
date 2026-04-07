import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, CheckIcon, SparklesIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { SmartTooltip } from '@/components/guide/SmartTooltip';
import type { TierContent } from '@/config/tierLandingContent';

// Tooltip content for pricing terms
const pricingTooltips = {
  adSpendLimit: 'Total monthly ad spend across all connected accounts. Upgrade when you exceed.',
  accountLimit: 'Number of ad platform accounts (Meta, Google, TikTok, Snapchat) you can connect.',
  savings: 'Save by committing to annual billing. Cancel anytime with prorated refund.',
  soc2: 'SOC 2 Type II certified. Your data security is audited annually.',
  gdpr: 'Full GDPR compliance with consent management and data deletion.',
  noCard: "Start your trial instantly. Add payment only when you're ready to continue.",
  cancel: 'No contracts or commitments. Downgrade or cancel with one click.',
};

interface TierPricingCTAProps {
  content: TierContent;
}

export function TierPricingCTA({ content }: TierPricingCTAProps) {
  const navigate = useNavigate();
  const { pricing, visuals, name, id, hero, featureCategories } = content;
  const gradientClass = `${visuals.gradientFrom} ${visuals.gradientTo}`;

  // Get key features for pricing card
  const keyFeatures = featureCategories
    .flatMap((cat) => cat.features)
    .filter((f) => f.highlight && f.included)
    .slice(0, 5);

  const handlePrimaryCta = () => {
    if (id === 'enterprise') {
      navigate('/contact');
    } else {
      navigate(`/signup?tier=${id}`);
    }
  };

  const trustBadges = [
    { icon: '🔒', text: 'SOC 2 Compliant', tooltip: pricingTooltips.soc2 },
    { icon: '🛡️', text: 'GDPR Ready', tooltip: pricingTooltips.gdpr },
    { icon: '💳', text: 'No Card for Trial', tooltip: pricingTooltips.noCard },
    { icon: '🔄', text: 'Cancel Anytime', tooltip: pricingTooltips.cancel },
  ];

  return (
    <section className="py-24 bg-surface-primary" id="pricing">
      <div className="max-w-5xl mx-auto px-6">
        {/* Section Header */}
        <div className="text-center mb-12">
          <Badge
            variant="outline"
            className={`mb-4 px-4 py-1 ${visuals.accentColor} border-white/20 bg-white/5`}
          >
            Pricing
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Ready to{' '}
            <span className={`bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}>
              get started
            </span>
            ?
          </h2>
          <p className="text-lg text-gray-400 max-w-xl mx-auto">
            {id === 'enterprise'
              ? "Custom pricing tailored to your organization's needs."
              : 'Start your 14-day free trial today. No credit card required.'}
          </p>
        </div>

        {/* Pricing Card */}
        <Card className="relative overflow-hidden bg-gradient-to-b from-gray-900 to-gray-950 border-2 border-white/10 shadow-xl">
          {/* Gradient accent */}
          <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${gradientClass}`} />

          {/* Badge */}
          {visuals.badgeText && (
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
              <Badge className={`bg-gradient-to-r ${gradientClass} text-white border-0 px-4 py-1`}>
                <SparklesIcon className="w-3 h-3 mr-1" />
                {visuals.badgeText}
              </Badge>
            </div>
          )}

          <CardContent className="p-8 md:p-12">
            <div className="grid md:grid-cols-2 gap-8 items-center">
              {/* Left: Pricing Info */}
              <div>
                <div className="mb-6">
                  <div className="text-sm text-gray-500 mb-2">{name} Plan</div>
                  <div className="flex items-baseline gap-2">
                    <span
                      className={`text-6xl font-bold bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}
                    >
                      {pricing.price}
                    </span>
                    {pricing.period && (
                      <span className="text-xl text-gray-500">{pricing.period}</span>
                    )}
                  </div>
                  <SmartTooltip
                    content={pricingTooltips.adSpendLimit}
                    position="right"
                    showIcon
                    iconType="info"
                  >
                    <span className="text-sm text-gray-500 mt-2 cursor-help">
                      {pricing.adSpendLimit}
                    </span>
                  </SmartTooltip>
                  <SmartTooltip
                    content={pricingTooltips.accountLimit}
                    position="right"
                    showIcon
                    iconType="info"
                  >
                    <span className="text-sm text-gray-500 cursor-help">
                      {pricing.accountLimit}
                    </span>
                  </SmartTooltip>
                  {pricing.savings && (
                    <SmartTooltip content={pricingTooltips.savings} position="right">
                      <Badge
                        variant="outline"
                        className="mt-3 text-green-400 border-green-500/30 bg-green-500/10 cursor-help"
                      >
                        {pricing.savings}
                      </Badge>
                    </SmartTooltip>
                  )}
                </div>

                {/* CTAs */}
                <div className="flex flex-col sm:flex-row gap-3">
                  <Button
                    onClick={handlePrimaryCta}
                    size="lg"
                    className={`group bg-gradient-to-r ${gradientClass} hover:opacity-90 text-white font-semibold px-8 py-6 text-lg`}
                  >
                    {hero.primaryCta}
                    <ArrowRightIcon className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
                  </Button>
                  <Button
                    variant="outline"
                    size="lg"
                    className="border-white/20 text-white hover:bg-white/10"
                    onClick={() => navigate('/contact')}
                  >
                    Talk to Sales
                  </Button>
                </div>
              </div>

              {/* Right: Key Features */}
              <div>
                <div className="text-sm text-gray-500 mb-4">Key features:</div>
                <ul className="space-y-3">
                  {keyFeatures.map((feature) => (
                    <li key={feature.name} className="flex items-start gap-3">
                      <div
                        className={`mt-0.5 p-1 rounded-full bg-gradient-to-r ${gradientClass} bg-opacity-20`}
                      >
                        <CheckIcon className="w-3 h-3 text-white" />
                      </div>
                      <div>
                        <span className="text-sm text-white font-medium">{feature.name}</span>
                        <p className="text-xs text-gray-500">{feature.description}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <Separator className="my-8 bg-white/10" />

            {/* Trust Badges */}
            <div className="flex flex-wrap justify-center gap-4">
              {trustBadges.map((badge, i) => (
                <SmartTooltip key={i} content={badge.tooltip} position="top">
                  <Badge
                    variant="outline"
                    className="px-4 py-2 text-sm bg-gray-900/50 border-white/10 text-gray-400 cursor-help"
                  >
                    <span className="mr-2">{badge.icon}</span>
                    {badge.text}
                  </Badge>
                </SmartTooltip>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Next Tier Prompt */}
        {pricing.nextTier && (
          <div className="mt-12 text-center">
            <Card className="inline-block bg-gray-900/50 border-white/10 px-8 py-6">
              <div className="flex flex-col sm:flex-row items-center gap-4">
                <div className="text-left">
                  <p className="text-white font-medium">{pricing.nextTier.teaser}</p>
                  <p className="text-sm text-gray-500">
                    See what's included in {pricing.nextTier.name}.
                  </p>
                </div>
                <Button
                  variant="outline"
                  className={`${visuals.accentColor} border-white/20 hover:bg-white/5`}
                  onClick={() => navigate(pricing.nextTier!.link)}
                >
                  View {pricing.nextTier.name}
                </Button>
              </div>
            </Card>
          </div>
        )}

        {/* Compare All Plans */}
        <div className="mt-8 text-center">
          <Button
            variant="link"
            className="text-gray-500 hover:text-gray-300"
            onClick={() => navigate('/#pricing')}
          >
            Compare all plans
          </Button>
        </div>
      </div>
    </section>
  );
}
