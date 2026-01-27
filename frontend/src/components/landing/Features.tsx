import {
  ArrowTrendingUpIcon,
  BoltIcon,
  ChartBarIcon,
  CheckBadgeIcon,
  ClockIcon,
  CpuChipIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import { type FeatureLayer, useFeatureLayers } from '@/api/cms';

// Icon mapping for CMS content
const iconMap: Record<string, React.ComponentType<React.SVGProps<SVGSVGElement>>> = {
  ShieldCheckIcon,
  SparklesIcon,
  BoltIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CpuChipIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  CheckBadgeIcon,
};

// Apple Glass Dark theme
const theme = {
  primary: '#0A84FF',
  primaryLight: 'rgba(10, 132, 255, 0.15)',
  green: '#30D158',
  greenLight: 'rgba(48, 209, 88, 0.15)',
  orange: '#FF9F0A',
  orangeLight: 'rgba(255, 159, 10, 0.15)',
  purple: '#BF5AF2',
  purpleLight: 'rgba(191, 90, 242, 0.15)',
  teal: '#64D2FF',
  bgBase: '#000000',
  bgCard: 'rgba(255, 255, 255, 0.03)',
  textPrimary: '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  border: 'rgba(255, 255, 255, 0.08)',
  borderHover: 'rgba(255, 255, 255, 0.15)',
};

// Fallback data when CMS content is not available
const fallbackLayers: FeatureLayer[] = [
  {
    id: 'trust',
    name: 'Trust Layer',
    description: 'Know when to trust your data',
    color: theme.green,
    bgColor: theme.greenLight,
    borderColor: 'rgba(48, 209, 88, 0.3)',
    iconName: 'ShieldCheckIcon',
    displayOrder: 0,
    features: [
      {
        id: '1',
        iconName: 'ChartBarIcon',
        title: 'Signal Health (EMQ)',
        description: 'Real-time data quality scoring across all platforms',
        displayOrder: 0,
      },
      {
        id: '2',
        iconName: 'ExclamationTriangleIcon',
        title: 'Attribution Variance',
        description: 'Platform vs GA4 reconciliation with alerts',
        displayOrder: 1,
      },
      {
        id: '3',
        iconName: 'ClockIcon',
        title: 'Freshness Monitoring',
        description: 'Know when your data is stale or delayed',
        displayOrder: 2,
      },
    ],
  },
  {
    id: 'intelligence',
    name: 'Intelligence Layer',
    description: 'AI that explains itself',
    color: theme.primary,
    bgColor: theme.primaryLight,
    borderColor: 'rgba(10, 132, 255, 0.3)',
    iconName: 'SparklesIcon',
    displayOrder: 1,
    features: [
      {
        id: '4',
        iconName: 'CpuChipIcon',
        title: 'Scaling Score',
        description: 'Know exactly which campaigns to scale, watch, or fix',
        displayOrder: 0,
      },
      {
        id: '5',
        iconName: 'ArrowTrendingUpIcon',
        title: 'Creative Fatigue',
        description: 'Detect declining performance before it impacts ROAS',
        displayOrder: 1,
      },
      {
        id: '6',
        iconName: 'CheckBadgeIcon',
        title: 'Anomaly Detection',
        description: 'Catch unusual spend or performance shifts instantly',
        displayOrder: 2,
      },
    ],
  },
  {
    id: 'execution',
    name: 'Execution Layer',
    description: 'Automate with guardrails',
    color: theme.orange,
    bgColor: theme.orangeLight,
    borderColor: 'rgba(255, 159, 10, 0.3)',
    iconName: 'BoltIcon',
    displayOrder: 2,
    features: [
      {
        id: '7',
        iconName: 'BoltIcon',
        title: 'Autopilot Modes',
        description: 'Normal, Limited, Cuts-Only, or Frozen based on signal quality',
        displayOrder: 0,
      },
      {
        id: '8',
        iconName: 'ShieldCheckIcon',
        title: 'Action Queue',
        description: 'Review, approve, or dismiss recommended actions',
        displayOrder: 1,
      },
      {
        id: '9',
        iconName: 'ChartBarIcon',
        title: 'Campaign Builder',
        description: 'Draft, approve, and publish campaigns with version control',
        displayOrder: 2,
      },
    ],
  },
];

function getIcon(iconName: string): React.ComponentType<React.SVGProps<SVGSVGElement>> {
  return iconMap[iconName] || SparklesIcon;
}

export function Features() {
  // Fetch from CMS with fallback to hardcoded data
  const { data: cmsLayers, isLoading } = useFeatureLayers();

  // Use CMS data if available and has content, otherwise use fallback
  const layers = cmsLayers && cmsLayers.length > 0 ? cmsLayers : fallbackLayers;

  return (
    <section className="py-32" style={{ background: theme.bgBase }}>
      <div className="max-w-7xl mx-auto px-6">
        {/* Section header */}
        <div className="text-center mb-20">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-6"
            style={{
              background: theme.primaryLight,
              border: `1px solid rgba(10, 132, 255, 0.3)`,
            }}
          >
            <SparklesIcon className="w-4 h-4" style={{ color: theme.primary }} />
            <span className="text-sm" style={{ color: theme.primary }}>The USP Stack</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Three layers.{' '}
            <span style={{ color: theme.primary }}>
              One intelligent system.
            </span>
          </h2>
          <p className="text-lg max-w-2xl mx-auto" style={{ color: theme.textSecondary }}>
            Trust your data before you act on it. Get AI recommendations you can explain. Automate
            only when it's safe.
          </p>
        </div>

        {/* Feature cards */}
        <div className={`grid md:grid-cols-3 gap-8 ${isLoading ? 'opacity-50' : ''}`}>
          {layers.map((layer, index) => {
            const LayerIcon = getIcon(layer.iconName);
            return (
              <div
                key={layer.id}
                className="motion-card group relative rounded-3xl p-8 transition-all duration-300 hover:-translate-y-1"
                style={{
                  animationDelay: `${index * 0.1}s`,
                  background: theme.bgCard,
                  backdropFilter: 'blur(40px)',
                  WebkitBackdropFilter: 'blur(40px)',
                  border: `1px solid ${theme.border}`,
                }}
              >
                {/* Gradient accent */}
                <div
                  className="absolute top-0 left-0 right-0 h-1 rounded-t-3xl"
                  style={{ background: layer.color }}
                />

                {/* Icon */}
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center mb-6"
                  style={{
                    background: layer.bgColor,
                    border: `1px solid ${layer.borderColor}`,
                  }}
                >
                  <LayerIcon className="w-7 h-7 text-white" />
                </div>

                {/* Title */}
                <h3 className="text-xl font-semibold text-white mb-2">{layer.name}</h3>
                <p className="text-base mb-8" style={{ color: theme.textMuted }}>{layer.description}</p>

                {/* Features list */}
                <ul className="space-y-4">
                  {layer.features.map((feature) => {
                    const FeatureIcon = getIcon(feature.iconName);
                    return (
                      <li key={feature.id} className="flex items-start gap-3">
                        <div
                          className="mt-0.5 p-1.5 rounded-xl"
                          style={{ background: 'rgba(255, 255, 255, 0.05)' }}
                        >
                          <FeatureIcon className="w-4 h-4" style={{ color: theme.textSecondary }} />
                        </div>
                        <div>
                          <div className="text-base text-white font-medium">{feature.title}</div>
                          <div className="text-sm" style={{ color: theme.textMuted }}>{feature.description}</div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>

        {/* Bottom highlight */}
        <div className="mt-20 text-center">
          <div
            className="inline-flex items-center gap-4 px-6 py-4 rounded-2xl"
            style={{
              background: theme.bgCard,
              backdropFilter: 'blur(40px)',
              WebkitBackdropFilter: 'blur(40px)',
              border: `1px solid ${theme.border}`,
            }}
          >
            <div className="flex -space-x-2">
              {[
                { bg: '#1877F2' }, // Meta
                { bg: '#4285F4' }, // Google
                { bg: '#000000', border: 'rgba(255,255,255,0.2)' }, // TikTok
                { bg: '#FFFC00' }, // Snapchat
              ].map((item, i) => (
                <div
                  key={i}
                  className="w-8 h-8 rounded-full"
                  style={{
                    background: item.bg,
                    border: item.border ? `2px solid ${item.border}` : '2px solid rgba(0,0,0,0.3)',
                  }}
                />
              ))}
            </div>
            <div className="text-left">
              <div className="text-base text-white font-medium">Works with your entire stack</div>
              <div className="text-sm" style={{ color: theme.textMuted }}>Meta, Google, TikTok, Snapchat + GA4</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
