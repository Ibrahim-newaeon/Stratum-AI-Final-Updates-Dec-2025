/**
 * How It Works Section - Apple Glass Dark Theme
 */

import {
  CheckCircleIcon,
  CpuChipIcon,
  LinkIcon,
  RocketLaunchIcon,
} from '@heroicons/react/24/outline';

// Stratum Gold Dark theme
const theme = {
  gold: '#D4AF37',
  goldLight: 'rgba(212, 175, 55, 0.15)',
  green: '#22c55e', // Stratum Green
  orange: '#FF9F0A',
  cyan: '#14F0C6',
  bgBase: '#000000',
  bgCard: 'rgba(255, 255, 255, 0.03)',
  textPrimary: '#FFFFFF',
  textSecondary: 'rgba(255, 255, 255, 0.7)',
  textMuted: 'rgba(255, 255, 255, 0.5)',
  border: 'rgba(255, 255, 255, 0.08)',
};

export function HowItWorks() {
  const steps = [
    {
      number: '01',
      title: 'Connect Your Platforms',
      description:
        'Link Meta, Google, TikTok, Snapchat, and GA4 in minutes. OAuth-secured, no code required.',
      icon: LinkIcon,
      color: theme.cyan,
      bgColor: 'rgba(20, 240, 198, 0.1)',
    },
    {
      number: '02',
      title: 'AI Analyzes Your Data',
      description:
        'Stratum calculates EMQ scores, detects anomalies, identifies scaling opportunities, and monitors signal health.',
      icon: CpuChipIcon,
      color: theme.gold,
      bgColor: theme.goldLight,
    },
    {
      number: '03',
      title: 'Take Confident Action',
      description:
        'Review AI recommendations, approve safe automations, and scale what works with full confidence.',
      icon: RocketLaunchIcon,
      color: theme.orange,
      bgColor: 'rgba(255, 159, 10, 0.1)',
    },
  ];

  return (
    <section
      className="py-32"
      style={{
        background: theme.bgBase,
        borderTop: `1px solid ${theme.border}`,
        borderBottom: `1px solid ${theme.border}`,
      }}
    >
      <div className="max-w-7xl mx-auto px-6">
        {/* Section header - Centered */}
        <div className="text-center mb-20">
          <div className="flex justify-center mb-6">
            <div
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
              style={{
                background: theme.goldLight,
                border: '1px solid rgba(212, 175, 55, 0.3)',
              }}
            >
              <span className="text-sm font-medium" style={{ color: theme.gold }}>
                Simple Setup
              </span>
            </div>
          </div>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4 text-center">
            How it <span style={{ color: theme.gold }}>works</span>
          </h2>
          <p className="text-lg max-w-2xl mx-auto text-center" style={{ color: theme.textMuted }}>
            From connection to optimization in three simple steps
          </p>
        </div>

        {/* Steps */}
        <div className="relative">
          {/* Connection line */}
          <div
            className="hidden md:block absolute top-24 left-[16.67%] right-[16.67%] h-px"
            style={{
              background: `linear-gradient(to right, ${theme.cyan}40, ${theme.gold}40, ${theme.orange}40)`,
            }}
          />

          <div className="grid md:grid-cols-3 gap-8 md:gap-12">
            {steps.map((step, index) => (
              <div key={step.number} className="relative text-center">
                {/* Step number circle */}
                <div className="relative inline-flex items-center justify-center mb-8">
                  <div
                    className="w-20 h-20 rounded-2xl flex items-center justify-center"
                    style={{ background: step.bgColor }}
                  >
                    <step.icon className="w-10 h-10" style={{ color: step.color }} />
                  </div>
                  {/* Number badge */}
                  <div
                    className="absolute -top-2 -right-2 w-8 h-8 rounded-full flex items-center justify-center"
                    style={{
                      background: theme.bgCard,
                      backdropFilter: 'blur(40px)',
                      border: `1px solid ${theme.border}`,
                    }}
                  >
                    <span className="text-xs text-white font-bold">{step.number}</span>
                  </div>
                </div>

                {/* Content */}
                <h3 className="text-xl font-semibold text-white mb-3">{step.title}</h3>
                <p className="text-sm max-w-sm mx-auto" style={{ color: theme.textMuted }}>
                  {step.description}
                </p>

                {/* Arrow for mobile */}
                {index < steps.length - 1 && (
                  <div className="md:hidden flex justify-center my-6">
                    <svg
                      className="w-6 h-6"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      style={{ color: theme.textMuted }}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 14l-7 7m0 0l-7-7m7 7V3"
                      />
                    </svg>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Result highlight */}
        <div className="mt-20 max-w-3xl mx-auto">
          <div
            className="relative rounded-2xl p-8 overflow-hidden"
            style={{
              background: theme.bgCard,
              backdropFilter: 'blur(40px)',
              border: `1px solid ${theme.border}`,
            }}
          >
            {/* Gradient background */}
            <div
              className="absolute inset-0"
              style={{
                background: `linear-gradient(135deg, rgba(212, 175, 55, 0.05), rgba(20, 240, 198, 0.05))`,
              }}
            />

            <div className="relative flex items-start gap-6">
              <div
                className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(34, 197, 94, 0.1)' }}
              >
                <CheckCircleIcon className="w-6 h-6" style={{ color: theme.green }} />
              </div>
              <div>
                <h4 className="text-xl font-semibold text-white mb-2">The Result?</h4>
                <p className="text-sm mb-4" style={{ color: theme.textSecondary }}>
                  Teams using Stratum AI report an average{' '}
                  <span className="font-semibold" style={{ color: theme.green }}>
                    23% improvement in ROAS
                  </span>{' '}
                  within the first 90 days, with{' '}
                  <span className="font-semibold" style={{ color: theme.green }}>
                    60% less time
                  </span>{' '}
                  spent on manual optimization.
                </p>
                <div className="flex flex-wrap gap-4 text-xs" style={{ color: theme.textMuted }}>
                  <span className="flex items-center gap-2">
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ background: theme.green }}
                    />
                    Fewer false optimizations
                  </span>
                  <span className="flex items-center gap-2">
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ background: theme.green }}
                    />
                    Faster recovery from issues
                  </span>
                  <span className="flex items-center gap-2">
                    <span
                      className="w-1.5 h-1.5 rounded-full"
                      style={{ background: theme.green }}
                    />
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
