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

export function Features() {
  const layers = [
    {
      name: 'Trust Layer',
      description: 'Know when to trust your data',
      color: 'from-green-500 to-emerald-500',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/20',
      icon: ShieldCheckIcon,
      features: [
        { icon: ChartBarIcon, title: 'Signal Health (EMQ)', description: 'Real-time data quality scoring across all platforms' },
        { icon: ExclamationTriangleIcon, title: 'Attribution Variance', description: 'Platform vs GA4 reconciliation with alerts' },
        { icon: ClockIcon, title: 'Freshness Monitoring', description: 'Know when your data is stale or delayed' },
      ],
    },
    {
      name: 'Intelligence Layer',
      description: 'AI that explains itself',
      color: 'from-stratum-500 to-cyan-500',
      bgColor: 'bg-stratum-500/10',
      borderColor: 'border-stratum-500/20',
      icon: SparklesIcon,
      features: [
        { icon: CpuChipIcon, title: 'Scaling Score', description: 'Know exactly which campaigns to scale, watch, or fix' },
        { icon: ArrowTrendingUpIcon, title: 'Creative Fatigue', description: 'Detect declining performance before it impacts ROAS' },
        { icon: CheckBadgeIcon, title: 'Anomaly Detection', description: 'Catch unusual spend or performance shifts instantly' },
      ],
    },
    {
      name: 'Execution Layer',
      description: 'Automate with guardrails',
      color: 'from-amber-500 to-orange-500',
      bgColor: 'bg-amber-500/10',
      borderColor: 'border-amber-500/20',
      icon: BoltIcon,
      features: [
        { icon: BoltIcon, title: 'Autopilot Modes', description: 'Normal, Limited, Cuts-Only, or Frozen based on signal quality' },
        { icon: ShieldCheckIcon, title: 'Action Queue', description: 'Review, approve, or dismiss recommended actions' },
        { icon: ChartBarIcon, title: 'Campaign Builder', description: 'Draft, approve, and publish campaigns with version control' },
      ],
    },
  ];

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
        <div className="grid md:grid-cols-3 gap-8">
          {layers.map((layer, index) => (
            <div
              key={layer.name}
              className="motion-card group relative rounded-2xl bg-surface-secondary border border-white/5 p-8 hover:border-white/10 transition-all duration-base"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {/* Gradient accent */}
              <div className={`absolute top-0 left-0 right-0 h-1 rounded-t-2xl bg-gradient-to-r ${layer.color}`} />

              {/* Icon */}
              <div className={`w-14 h-14 rounded-xl ${layer.bgColor} ${layer.borderColor} border flex items-center justify-center mb-6`}>
                <layer.icon className="w-7 h-7 text-white" />
              </div>

              {/* Title */}
              <h3 className="text-h3 text-white mb-2">{layer.name}</h3>
              <p className="text-body text-text-muted mb-8">{layer.description}</p>

              {/* Features list */}
              <ul className="space-y-4">
                {layer.features.map((feature) => (
                  <li key={feature.title} className="flex items-start gap-3">
                    <div className="mt-0.5 p-1.5 rounded-lg bg-white/5">
                      <feature.icon className="w-4 h-4 text-text-secondary" />
                    </div>
                    <div>
                      <div className="text-body text-white font-medium">{feature.title}</div>
                      <div className="text-meta text-text-muted">{feature.description}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
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
