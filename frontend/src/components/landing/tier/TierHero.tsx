import { useNavigate } from 'react-router-dom';
import { ArrowRightIcon, CheckIcon, PlayIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { SmartTooltip } from '@/components/guide/SmartTooltip';
import type { TierContent } from '@/config/tierLandingContent';

// Tooltip content for tier metrics
const metricTooltips: Record<string, string> = {
  'Ad Accounts': 'Number of ad platform accounts you can connect (Meta, Google, TikTok, Snapchat).',
  'Monthly Spend': 'Maximum combined monthly ad spend across all connected accounts.',
  'Avg ROI Lift': 'Average ROAS improvement seen by customers on this tier.',
};

interface TierHeroProps {
  content: TierContent;
}

export function TierHero({ content }: TierHeroProps) {
  const navigate = useNavigate();
  const { hero, visuals, name: _name } = content;

  const gradientClass = `${visuals.gradientFrom} ${visuals.gradientTo}`;

  const handlePrimaryCta = () => {
    if (content.id === 'enterprise') {
      navigate('/contact');
    } else {
      navigate(`/signup?tier=${content.id}`);
    }
  };

  return (
    <section className="relative min-h-[85vh] flex items-center justify-center overflow-hidden bg-surface-primary">
      {/* Background gradient effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div
          className={`absolute -top-1/2 -left-1/4 w-[800px] h-[800px] rounded-full bg-gradient-to-br ${gradientClass} opacity-20 blur-3xl`}
        />
        <div
          className={`absolute -bottom-1/2 -right-1/4 w-[600px] h-[600px] rounded-full bg-gradient-to-tl ${gradientClass} opacity-15 blur-3xl`}
        />
        <div
          className={`absolute top-1/4 right-1/3 w-[400px] h-[400px] rounded-full bg-gradient-to-r ${gradientClass} opacity-5 blur-2xl`}
        />
      </div>

      {/* Grid pattern overlay */}
      <div
        className="absolute inset-0 opacity-[0.02]"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                           linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '64px 64px',
        }}
      />

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-24 text-center">
        {/* Tier Badge */}
        <div className="mb-8">
          <Badge
            variant="outline"
            className={`px-4 py-2 text-sm bg-gradient-to-r ${gradientClass} bg-opacity-10 border-white/20 ${visuals.accentColor}`}
          >
            <span
              className={`w-2 h-2 rounded-full bg-gradient-to-r ${gradientClass} animate-pulse mr-2 inline-block`}
            />
            {hero.tagline}
          </Badge>
          {visuals.badgeText && (
            <Badge className={`ml-3 px-3 py-1 ${visuals.badgeColor} text-white border-0`}>
              {visuals.badgeText}
            </Badge>
          )}
        </div>

        {/* Main headline */}
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white leading-tight mb-6">
          {hero.headline}{' '}
          <span className={`bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}>
            {hero.highlightedText}
          </span>
        </h1>

        {/* Subheadline */}
        <p className="text-xl md:text-2xl text-gray-400 mb-4">{hero.subheadline}</p>

        {/* Description */}
        <p className="max-w-3xl mx-auto text-base text-gray-500 mb-8">{hero.description}</p>

        {/* Metrics Preview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto mb-8">
          {hero.metrics.map((metric, i) => (
            <Card key={i} className="bg-gray-900/50 border-white/10">
              <CardContent className="p-4 text-center">
                <div
                  className={`text-3xl font-bold bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}
                >
                  {metric.value}
                </div>
                <SmartTooltip
                  content={metricTooltips[metric.label] || metric.description}
                  position="bottom"
                  showIcon
                  iconType="info"
                >
                  <span className="text-sm text-gray-400 mt-1 cursor-help border-b border-dashed border-gray-600">
                    {metric.label}
                  </span>
                </SmartTooltip>
                <div className="text-xs text-gray-600 mt-0.5">{metric.description}</div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-8">
          <Button
            onClick={handlePrimaryCta}
            size="lg"
            className={`group bg-gradient-to-r ${gradientClass} hover:opacity-90 text-white font-semibold px-8 py-6 text-lg shadow-lg transition-all`}
          >
            {hero.primaryCta}
            <ArrowRightIcon className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
          </Button>

          <Button
            variant="outline"
            size="lg"
            className="group border-white/20 text-white hover:bg-white/10 px-8 py-6 text-lg"
            onClick={() => navigate('/contact')}
          >
            <PlayIcon className="w-5 h-5 mr-2" />
            {hero.secondaryCta}
          </Button>
        </div>

        {/* Trust Badges */}
        <div className="flex flex-wrap items-center justify-center gap-6">
          {hero.trustBadges.map((badge, i) => (
            <div key={i} className="flex items-center gap-2 text-gray-400">
              <CheckIcon className="w-4 h-4 text-green-500" />
              <span className="text-sm">{badge}</span>
            </div>
          ))}
        </div>

        {/* Plan Navigation */}
        <div className="mt-12 pt-8 border-t border-white/10">
          <p className="text-sm text-gray-500 mb-4">Compare plans:</p>
          <div className="flex items-center justify-center gap-4">
            {['starter', 'professional', 'enterprise'].map((tier) => (
              <Button
                key={tier}
                variant={tier === content.id ? 'default' : 'ghost'}
                size="sm"
                onClick={() => navigate(`/plans/${tier}`)}
                className={
                  tier === content.id
                    ? `bg-gradient-to-r ${gradientClass} text-white`
                    : 'text-gray-400 hover:text-white'
                }
              >
                {tier.charAt(0).toUpperCase() + tier.slice(1)}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
