import { useNavigate } from 'react-router-dom';
import {
  AdjustmentsHorizontalIcon,
  ArrowsRightLeftIcon,
  ChartBarIcon,
  CheckIcon,
  CogIcon,
  CpuChipIcon,
  DocumentTextIcon,
  FingerPrintIcon,
  GlobeAltIcon,
  LifebuoyIcon,
  LockClosedIcon,
  ShieldCheckIcon,
  UsersIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { SmartTooltip } from '@/components/guide/SmartTooltip';
import type { TierContent, TierFeatureCategory } from '@/config/tierLandingContent';

// Tooltip content for key Stratum features (kept under 150 chars)
const featureTooltips: Record<string, string> = {
  'EMQ Signal Scoring':
    'Event Match Quality score (0-100) measuring data reliability across platforms.',
  'RFM Analysis': 'Recency, Frequency, Monetary - classic customer segmentation framework.',
  'Segment Builder': 'Visual tool to create dynamic customer segments with behavioral rules.',
  'Meta Custom Audiences': 'Push CDP segments directly to Meta Ads for targeting.',
  'Google Customer Match': 'Sync customer lists to Google Ads for personalized campaigns.',
  'Funnel Builder': 'Create step-by-step conversion funnels to track drop-off points.',
  'Predictive Churn Modeling': 'ML model that identifies customers likely to stop purchasing.',
  'Identity Graph': 'Visual map of how anonymous and known identities connect.',
  'Custom Autopilot Rules': 'Define your own automation logic with if/then conditions.',
  'API Access': 'REST API for integrating Stratum data into your own systems.',
  'Trust Gate Audit Logs': 'Complete history of why automations were allowed or blocked.',
};

interface TierFeatureGridProps {
  content: TierContent;
}

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  shield: ShieldCheckIcon,
  users: UsersIcon,
  chart: ChartBarIcon,
  document: DocumentTextIcon,
  target: AdjustmentsHorizontalIcon,
  sync: ArrowsRightLeftIcon,
  funnel: ChartBarIcon,
  plug: CogIcon,
  brain: CpuChipIcon,
  fingerprint: FingerPrintIcon,
  globe: GlobeAltIcon,
  cog: CogIcon,
  lock: LockClosedIcon,
  headset: LifebuoyIcon,
};

function CategoryCard({
  category,
  visuals,
  tierId,
}: {
  category: TierFeatureCategory;
  visuals: TierContent['visuals'];
  tierId: string;
}) {
  const navigate = useNavigate();
  const IconComponent = iconMap[category.icon] || ShieldCheckIcon;
  const gradientClass = `${visuals.gradientFrom} ${visuals.gradientTo}`;
  const hasUnavailableFeatures = category.features.some((f) => !f.included);

  return (
    <div className="group relative rounded-2xl bg-gray-900/50 border border-white/5 p-6 hover:border-white/10 transition-all">
      {/* Gradient accent */}
      <div
        className={`absolute top-0 left-0 right-0 h-1 rounded-t-2xl bg-gradient-to-r ${gradientClass}`}
      />

      {/* Icon and Title */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className={`w-10 h-10 rounded-lg bg-gradient-to-r ${gradientClass} bg-opacity-20 flex items-center justify-center`}
        >
          <IconComponent className="w-5 h-5 text-white" />
        </div>
        <h3 className="text-lg font-semibold text-white">{category.name}</h3>
      </div>

      {/* Features List */}
      <ul className="space-y-3">
        {category.features.map((feature) => {
          const hasTooltip = featureTooltips[feature.name];

          return (
            <li key={feature.name} className="flex items-start gap-3">
              {feature.included ? (
                <div className="mt-0.5 p-1 rounded-full bg-green-500/20">
                  <CheckIcon className="w-3 h-3 text-green-500" />
                </div>
              ) : (
                <div className="mt-0.5 p-1 rounded-full bg-gray-700/50">
                  <XMarkIcon className="w-3 h-3 text-gray-500" />
                </div>
              )}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  {hasTooltip ? (
                    <SmartTooltip
                      content={featureTooltips[feature.name]}
                      position="top"
                      showIcon
                      iconType="help"
                    >
                      <span
                        className={`text-sm ${feature.included ? 'text-white' : 'text-gray-500'} cursor-help`}
                      >
                        {feature.name}
                      </span>
                    </SmartTooltip>
                  ) : (
                    <span
                      className={`text-sm ${feature.included ? 'text-white' : 'text-gray-500'}`}
                    >
                      {feature.name}
                    </span>
                  )}
                  {feature.highlight && feature.included && (
                    <Badge
                      className={`text-[10px] px-1.5 py-0 bg-gradient-to-r ${gradientClass} text-white border-0`}
                    >
                      Key
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{feature.description}</p>
              </div>
            </li>
          );
        })}
      </ul>

      {/* Upgrade Prompt for Unavailable Features */}
      {hasUnavailableFeatures && tierId !== 'enterprise' && (
        <div className="mt-4 pt-4 border-t border-white/5">
          <Button
            variant="ghost"
            size="sm"
            className={`w-full ${visuals.accentColor} hover:bg-white/5`}
            onClick={() => {
              const nextTier = tierId === 'starter' ? 'professional' : 'enterprise';
              navigate(`/plans/${nextTier}`);
            }}
          >
            Unlock more in {tierId === 'starter' ? 'Professional' : 'Enterprise'}
          </Button>
        </div>
      )}
    </div>
  );
}

export function TierFeatureGrid({ content }: TierFeatureGridProps) {
  const { featureCategories, visuals, name } = content;
  const gradientClass = `${visuals.gradientFrom} ${visuals.gradientTo}`;

  const includedCount = featureCategories.reduce(
    (acc, cat) => acc + cat.features.filter((f) => f.included).length,
    0
  );

  const highlightCount = featureCategories.reduce(
    (acc, cat) => acc + cat.features.filter((f) => f.highlight && f.included).length,
    0
  );

  return (
    <section className="py-24 bg-surface-primary">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section Header */}
        <div className="text-center mb-16">
          <Badge
            variant="outline"
            className={`mb-4 px-4 py-1 ${visuals.accentColor} border-white/20 bg-white/5`}
          >
            What's Included
          </Badge>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Everything in{' '}
            <span className={`bg-gradient-to-r ${gradientClass} bg-clip-text text-transparent`}>
              {name}
            </span>
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            {includedCount} features included with {highlightCount} key differentiators
            {content.id !== 'starter' && ' — plus everything from the previous tier'}
          </p>
        </div>

        {/* Feature Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {featureCategories.map((category) => (
            <CategoryCard
              key={category.name}
              category={category}
              visuals={visuals}
              tierId={content.id}
            />
          ))}
        </div>

        {/* All Features Summary */}
        <div className="mt-16 text-center">
          <div className="inline-flex items-center gap-4 px-6 py-4 rounded-2xl bg-gray-900/50 border border-white/5">
            <div className="flex -space-x-2">
              {['bg-meta', 'bg-google', 'bg-tiktok', 'bg-snapchat'].map((bg, i) => (
                <div key={i} className={`w-8 h-8 rounded-full ${bg} border-2 border-gray-900`} />
              ))}
            </div>
            <div className="text-left">
              <div className="text-sm text-white font-medium">Works with all major platforms</div>
              <div className="text-xs text-gray-500">Meta, Google, TikTok, Snapchat + GA4</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
