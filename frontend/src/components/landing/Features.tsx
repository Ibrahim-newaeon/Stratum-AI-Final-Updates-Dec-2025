import {
  ShieldCheckIcon,
  SparklesIcon,
  BoltIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CpuChipIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  CheckBadgeIcon,
} from '@heroicons/react/24/outline';
import { useFeatureLayers, type FeatureLayer } from '@/api/cms';

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

// Fallback data when CMS content is not available
const fallbackLayers: FeatureLayer[] = [
  {
    id: 'trust',
    name: 'Trust Layer',
    description: 'Know when to trust your data',
    color: 'from-green-500 to-emerald-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/20',
    iconName: 'ShieldCheckIcon',
    displayOrder: 0,
    features: [
      { id: '1', iconName: 'ChartBarIcon', title: 'Signal Health (EMQ)', description: 'Real-time data quality scoring across all platforms', displayOrder: 0 },
      { id: '2', iconName: 'ExclamationTriangleIcon', title: 'Attribution Variance', description: 'Platform vs GA4 reconciliation with alerts', displayOrder: 1 },
      { id: '3', iconName: 'ClockIcon', title: 'Freshness Monitoring', description: 'Know when your data is stale or delayed', displayOrder: 2 },
    ],
  },
  {
    id: 'intelligence',
    name: 'Intelligence Layer',
    description: 'AI that explains itself',
    color: 'from-stratum-500 to-cyan-500',
    bgColor: 'bg-stratum-500/10',
    borderColor: 'border-stratum-500/20',
    iconName: 'SparklesIcon',
    displayOrder: 1,
    features: [
      { id: '4', iconName: 'CpuChipIcon', title: 'Scaling Score', description: 'Know exactly which campaigns to scale, watch, or fix', displayOrder: 0 },
      { id: '5', iconName: 'ArrowTrendingUpIcon', title: 'Creative Fatigue', description: 'Detect declining performance before it impacts ROAS', displayOrder: 1 },
      { id: '6', iconName: 'CheckBadgeIcon', title: 'Anomaly Detection', description: 'Catch unusual spend or performance shifts instantly', displayOrder: 2 },
    ],
  },
  {
    id: 'execution',
    name: 'Execution Layer',
    description: 'Automate with guardrails',
    color: 'from-amber-500 to-orange-500',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/20',
    iconName: 'BoltIcon',
    displayOrder: 2,
    features: [
      { id: '7', iconName: 'BoltIcon', title: 'Autopilot Modes', description: 'Normal, Limited, Cuts-Only, or Frozen based on signal quality', displayOrder: 0 },
      { id: '8', iconName: 'ShieldCheckIcon', title: 'Action Queue', description: 'Review, approve, or dismiss recommended actions', displayOrder: 1 },
      { id: '9', iconName: 'ChartBarIcon', title: 'Campaign Builder', description: 'Draft, approve, and publish campaigns with version control', displayOrder: 2 },
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
  const layers = (cmsLayers && cmsLayers.length > 0) ? cmsLayers : fallbackLayers;

  return (
    <section className="py-32 bg-surface-primary">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section header */}
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-stratum-500/10 border border-stratum-500/20 mb-6">
            <SparklesIcon className="w-4 h-4 text-stratum-400" />
            <span className="text-meta text-stratum-400">The USP Stack</span>
          </div>
          <h2 className="text-h1 text-white mb-4">
            Three layers.{' '}
            <span className="bg-gradient-stratum bg-clip-text text-transparent">
              One intelligent system.
            </span>
          </h2>
          <p className="text-body text-text-secondary max-w-2xl mx-auto">
            Trust your data before you act on it. Get AI recommendations you can explain.
            Automate only when it's safe.
          </p>
        </div>

        {/* Feature cards */}
        <div className={`grid md:grid-cols-3 gap-8 ${isLoading ? 'opacity-50' : ''}`}>
          {layers.map((layer, index) => {
            const LayerIcon = getIcon(layer.iconName);
            return (
              <div
                key={layer.id}
                className="motion-card group relative rounded-2xl bg-surface-secondary border border-white/5 p-8 hover:border-white/10 transition-all duration-base"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                {/* Gradient accent */}
                <div className={`absolute top-0 left-0 right-0 h-1 rounded-t-2xl bg-gradient-to-r ${layer.color}`} />

                {/* Icon */}
                <div className={`w-14 h-14 rounded-xl ${layer.bgColor} ${layer.borderColor} border flex items-center justify-center mb-6`}>
                  <LayerIcon className="w-7 h-7 text-white" />
                </div>

                {/* Title */}
                <h3 className="text-h3 text-white mb-2">{layer.name}</h3>
                <p className="text-body text-text-muted mb-8">{layer.description}</p>

                {/* Features list */}
                <ul className="space-y-4">
                  {layer.features.map((feature) => {
                    const FeatureIcon = getIcon(feature.iconName);
                    return (
                      <li key={feature.id} className="flex items-start gap-3">
                        <div className="mt-0.5 p-1.5 rounded-lg bg-white/5">
                          <FeatureIcon className="w-4 h-4 text-text-secondary" />
                        </div>
                        <div>
                          <div className="text-body text-white font-medium">{feature.title}</div>
                          <div className="text-meta text-text-muted">{feature.description}</div>
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
          <div className="inline-flex items-center gap-4 px-6 py-4 rounded-2xl bg-surface-secondary border border-white/5">
            <div className="flex -space-x-2">
              {['bg-meta', 'bg-google', 'bg-tiktok', 'bg-snapchat'].map((bg, i) => (
                <div key={i} className={`w-8 h-8 rounded-full ${bg} border-2 border-surface-secondary`} />
              ))}
            </div>
            <div className="text-left">
              <div className="text-body text-white font-medium">Works with your entire stack</div>
              <div className="text-meta text-text-muted">Meta, Google, TikTok, Snapchat + GA4</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
