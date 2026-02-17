import {
  LinkIcon,
  CpuChipIcon,
  RocketLaunchIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

export function HowItWorks() {
  const steps = [
    {
      number: '01',
      title: 'Connect Your Platforms',
      description: 'Link Meta, Google, TikTok, Snapchat, and GA4 in minutes. OAuth-secured, no code required.',
      icon: LinkIcon,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
    },
    {
      number: '02',
      title: 'AI Analyzes Your Data',
      description: 'Stratum calculates EMQ scores, detects anomalies, identifies scaling opportunities, and monitors signal health.',
      icon: CpuChipIcon,
      color: 'text-stratum-400',
      bgColor: 'bg-stratum-500/10',
    },
    {
      number: '03',
      title: 'Take Confident Action',
      description: 'Review AI recommendations, approve safe automations, and scale what works with full confidence.',
      icon: RocketLaunchIcon,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
    },
  ];

  return (
    <section className="py-32 bg-surface-secondary border-y border-white/5">
      <div className="max-w-7xl mx-auto px-6">
        {/* Section header */}
        <div className="text-center mb-20">
          <h2 className="text-h1 text-white mb-4">
            How it works
          </h2>
          <p className="text-body text-text-secondary max-w-2xl mx-auto">
            From connection to optimization in three simple steps
          </p>
        </div>

        {/* Steps */}
        <div className="relative">
          {/* Connection line */}
          <div className="hidden md:block absolute top-24 left-[16.67%] right-[16.67%] h-px bg-gradient-to-r from-cyan-500/50 via-stratum-500/50 to-amber-500/50" />

          <div className="grid md:grid-cols-3 gap-8 md:gap-12">
            {steps.map((step, index) => (
              <div key={step.number} className="relative text-center">
                {/* Step number circle */}
                <div className="relative inline-flex items-center justify-center mb-8">
                  <div className={`w-20 h-20 rounded-2xl ${step.bgColor} flex items-center justify-center`}>
                    <step.icon className={`w-10 h-10 ${step.color}`} />
                  </div>
                  {/* Number badge */}
                  <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-surface-primary border border-white/10 flex items-center justify-center">
                    <span className="text-meta text-white font-bold">{step.number}</span>
                  </div>
                </div>

                {/* Content */}
                <h3 className="text-h3 text-white mb-3">{step.title}</h3>
                <p className="text-body text-text-muted max-w-sm mx-auto">{step.description}</p>

                {/* Arrow for mobile */}
                {index < steps.length - 1 && (
                  <div className="md:hidden flex justify-center my-6">
                    <svg className="w-6 h-6 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Result highlight */}
        <div className="mt-20 max-w-3xl mx-auto">
          <div className="relative rounded-2xl bg-surface-primary border border-white/10 p-8 overflow-hidden">
            {/* Gradient background */}
            <div className="absolute inset-0 bg-gradient-to-br from-stratum-500/5 to-cyan-500/5" />

            <div className="relative flex items-start gap-6">
              <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-success/10 flex items-center justify-center">
                <CheckCircleIcon className="w-6 h-6 text-success" />
              </div>
              <div>
                <h4 className="text-h3 text-white mb-2">The Result?</h4>
                <p className="text-body text-text-secondary mb-4">
                  Teams using Stratum AI report an average <span className="text-success font-semibold">23% improvement in ROAS</span> within
                  the first 90 days, with <span className="text-success font-semibold">60% less time</span> spent on manual optimization.
                </p>
                <div className="flex flex-wrap gap-4 text-meta text-text-muted">
                  <span className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-success" />
                    Fewer false optimizations
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-success" />
                    Faster recovery from issues
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-success" />
                    Stable platform learning
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
