import { useMemo } from 'react';
import {
  Brain,
  ShieldCheck,
  TrendingUp,
  RefreshCw,
  Activity,
  PieChart,
  Sparkles,
  Zap,
  Target,
  BarChart3,
  Layers,
  Globe,
  type LucideIcon,
} from 'lucide-react';
import { useFeatureLayers } from '@/api/cms';

const ICON_MAP: Record<string, LucideIcon> = {
  BrainIcon: Brain,
  ShieldCheckIcon: ShieldCheck,
  TrendingUpIcon: TrendingUp,
  RefreshCwIcon: RefreshCw,
  ActivityIcon: Activity,
  PieChartIcon: PieChart,
  SparklesIcon: Sparkles,
  ZapIcon: Zap,
  TargetIcon: Target,
  BarChart3Icon: BarChart3,
  LayersIcon: Layers,
  GlobeIcon: Globe,
  ChartBarIcon: BarChart3,
};

const DEFAULT_FEATURES = [
  {
    icon: Brain,
    title: 'Unified Intelligence',
    description:
      'A single command center that unifies your data across every ad platform. No more fragmented dashboards.',
  },
  {
    icon: ShieldCheck,
    title: 'Trust-Gated Automation',
    description:
      'We only automate what the data supports. Built-in guardrails ensure every action is grounded in trust.',
  },
  {
    icon: TrendingUp,
    title: 'Predictive Optimization',
    description:
      'Partner with AI that forecasts performance trends and surfaces opportunities before they peak.',
  },
  {
    icon: RefreshCw,
    title: 'Cross-Platform Sync',
    description:
      'Seamlessly synchronize audiences, creatives, and budgets across Meta, Google, TikTok, and Snapchat.',
  },
  {
    icon: Activity,
    title: 'Real-Time Signals',
    description:
      'Instant alerts on spend anomalies, creative fatigue, and performance shifts that demand attention.',
  },
  {
    icon: PieChart,
    title: 'Revenue Attribution',
    description:
      'Understand exactly how every touchpoint contributes to revenue with transparent, reliable attribution.',
  },
];

export function Features() {
  const { data: layers } = useFeatureLayers();

  const features = useMemo(() => {
    if (!layers || layers.length === 0) return DEFAULT_FEATURES;
    // Flatten all features from all layers
    const cmsFeatures = layers.flatMap((layer) =>
      layer.features.map((f) => ({
        icon: ICON_MAP[f.iconName] || Sparkles,
        title: f.title,
        description: f.description,
      }))
    );
    return cmsFeatures.length > 0 ? cmsFeatures : DEFAULT_FEATURES;
  }, [layers]);

  return (
    <section id="product" className="py-24 lg:py-32 bg-background">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        {/* Section header */}
        <div className="text-center mb-16 lg:mb-20">
          <h2 className="text-display-sm text-text-primary mb-4 animate-enter">
            Intelligence you can{' '}
            <span className="text-gradient-primary">trust and scale</span>
          </h2>
          <p
            className="text-body text-text-secondary max-w-2xl mx-auto animate-enter"
            style={{ animationDelay: '0.1s' }}
          >
            Every feature is designed around partnership — giving you control,
            transparency, and confidence at every step.
          </p>
        </div>

        {/* Feature cards */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <div
              key={feature.title}
              className="group relative rounded-2xl bg-card border border-border p-8 hover:border-stratum-500/20 transition-colors duration-200 animate-enter"
              style={{ animationDelay: `${0.1 + index * 0.05}s` }}
            >
              {/* Icon */}
              <div className="w-12 h-12 rounded-xl bg-stratum-500/10 border border-stratum-500/20 flex items-center justify-center mb-6">
                <feature.icon className="w-6 h-6 text-stratum-400" />
              </div>

              {/* Title */}
              <h3 className="text-h3 text-text-primary mb-2">
                {feature.title}
              </h3>
              <p className="text-body text-text-secondary leading-relaxed">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
