/**
 * Changelog / Release Notes Page
 * 2026 Theme - Electric Neon / OLED-Optimized
 */

import { PageLayout } from '@/components/landing/PageLayout';
import {
  SparklesIcon,
  WrenchScrewdriverIcon,
  BugAntIcon,
  RocketLaunchIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

const releases = [
  {
    version: '3.2.0',
    date: 'January 15, 2026',
    type: 'major',
    highlights: [
      'New 2026 Dashboard Theme with OLED-optimized dark mode',
      'Enhanced Trust Engine with predictive signal analysis',
      'Multi-platform Audience Sync now supports 4 ad platforms',
    ],
    changes: [
      { type: 'feature', text: 'Added electric neon color palette for 2026 theme' },
      { type: 'feature', text: 'New glassmorphism effects with enhanced blur' },
      { type: 'feature', text: 'Animation harmony system with 3 timing layers' },
      { type: 'improvement', text: 'Improved CDP profile loading performance by 40%' },
      { type: 'improvement', text: 'Enhanced Trust Gate evaluation speed' },
      { type: 'fix', text: 'Fixed segment preview count accuracy' },
      { type: 'fix', text: 'Resolved timezone issues in event tracking' },
    ],
  },
  {
    version: '3.1.0',
    date: 'December 20, 2025',
    type: 'minor',
    highlights: [
      'Predictive Churn Analysis in CDP',
      'Computed Traits for advanced segmentation',
      'RFM Analysis dashboard',
    ],
    changes: [
      { type: 'feature', text: 'Predictive churn scoring with ML models' },
      { type: 'feature', text: 'Custom computed traits with formula builder' },
      { type: 'feature', text: 'RFM (Recency, Frequency, Monetary) analysis' },
      { type: 'feature', text: 'Funnel analysis with conversion tracking' },
      { type: 'improvement', text: 'Segment builder now supports nested conditions' },
      { type: 'fix', text: 'Fixed identity merge conflicts' },
    ],
  },
  {
    version: '3.0.0',
    date: 'November 1, 2025',
    type: 'major',
    highlights: [
      'Complete CDP (Customer Data Platform) launch',
      'Audience Sync to Meta, Google, TikTok, Snapchat',
      'Identity Graph visualization',
    ],
    changes: [
      { type: 'feature', text: 'Full CDP with unified customer profiles' },
      { type: 'feature', text: 'Real-time event ingestion and processing' },
      { type: 'feature', text: 'Cross-device identity resolution' },
      { type: 'feature', text: 'One-click audience sync to ad platforms' },
      { type: 'security', text: 'Enhanced encryption for PII data' },
      { type: 'improvement', text: 'New onboarding flow for faster setup' },
    ],
  },
  {
    version: '2.5.0',
    date: 'September 15, 2025',
    type: 'minor',
    highlights: [
      'Custom Autopilot Rules builder',
      'A/B Testing framework',
      'Enhanced reporting exports',
    ],
    changes: [
      { type: 'feature', text: 'Visual rule builder for custom automations' },
      { type: 'feature', text: 'Built-in A/B testing with statistical analysis' },
      { type: 'feature', text: 'Scheduled report exports in PDF/CSV' },
      { type: 'improvement', text: 'Campaign performance insights' },
      { type: 'fix', text: 'Fixed duplicate webhook deliveries' },
    ],
  },
];

const getTypeIcon = (type: string) => {
  switch (type) {
    case 'feature':
      return <SparklesIcon className="w-4 h-4 text-[#00FF88]" />;
    case 'improvement':
      return <RocketLaunchIcon className="w-4 h-4 text-[#00D4FF]" />;
    case 'fix':
      return <BugAntIcon className="w-4 h-4 text-[#FFB800]" />;
    case 'security':
      return <ShieldCheckIcon className="w-4 h-4 text-[#8B5CF6]" />;
    default:
      return <WrenchScrewdriverIcon className="w-4 h-4 text-gray-400" />;
  }
};

const getTypeLabel = (type: string) => {
  switch (type) {
    case 'feature':
      return { text: 'New', color: '#00FF88' };
    case 'improvement':
      return { text: 'Improved', color: '#00D4FF' };
    case 'fix':
      return { text: 'Fixed', color: '#FFB800' };
    case 'security':
      return { text: 'Security', color: '#8B5CF6' };
    default:
      return { text: 'Changed', color: '#94A3B8' };
  }
};

export default function ChangelogPage() {
  return (
    <PageLayout>
      <div className="min-h-screen">
        {/* Hero Section */}
        <section className="relative py-20 overflow-hidden">
          <div className="max-w-4xl mx-auto px-6 lg:px-8 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-6"
              style={{
                background: 'rgba(0, 255, 136, 0.1)',
                border: '1px solid rgba(0, 255, 136, 0.2)',
              }}>
              <SparklesIcon className="w-4 h-4 text-[#00FF88]" />
              <span className="text-sm font-medium text-[#00FF88]">Changelog</span>
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
              What's New in{' '}
              <span style={{
                background: 'linear-gradient(135deg, #8B5CF6 0%, #00D4FF 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>
                Stratum AI
              </span>
            </h1>

            <p className="text-lg text-gray-400">
              Stay up to date with the latest features, improvements, and fixes.
            </p>
          </div>
        </section>

        {/* Releases Timeline */}
        <section className="py-16">
          <div className="max-w-4xl mx-auto px-6 lg:px-8">
            <div className="space-y-12">
              {releases.map((release, index) => (
                <div key={release.version} className="relative">
                  {/* Timeline line */}
                  {index < releases.length - 1 && (
                    <div
                      className="absolute left-[15px] top-12 bottom-0 w-px"
                      style={{ background: 'rgba(139, 92, 246, 0.2)' }}
                    />
                  )}

                  {/* Version header */}
                  <div className="flex items-start gap-4 mb-6">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{
                        background: release.type === 'major'
                          ? 'linear-gradient(135deg, #8B5CF6 0%, #00D4FF 100%)'
                          : 'rgba(139, 92, 246, 0.2)',
                        border: '2px solid rgba(139, 92, 246, 0.4)',
                      }}
                    >
                      <span className="text-white text-xs font-bold">
                        {release.type === 'major' ? 'M' : 'm'}
                      </span>
                    </div>

                    <div>
                      <div className="flex items-center gap-3">
                        <h2 className="text-2xl font-bold text-white">v{release.version}</h2>
                        {release.type === 'major' && (
                          <span
                            className="px-2 py-0.5 rounded text-xs font-medium"
                            style={{
                              background: 'rgba(139, 92, 246, 0.2)',
                              color: '#A78BFA',
                            }}
                          >
                            Major Release
                          </span>
                        )}
                      </div>
                      <p className="text-gray-500 text-sm">{release.date}</p>
                    </div>
                  </div>

                  {/* Highlights */}
                  {release.highlights && (
                    <div
                      className="ml-12 mb-6 p-4 rounded-xl"
                      style={{
                        background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(0, 212, 255, 0.04) 100%)',
                        border: '1px solid rgba(139, 92, 246, 0.15)',
                      }}
                    >
                      <h3 className="text-sm font-semibold text-[#8B5CF6] mb-3">Highlights</h3>
                      <ul className="space-y-2">
                        {release.highlights.map((highlight, i) => (
                          <li key={i} className="flex items-start gap-2 text-white text-sm">
                            <span className="text-[#00D4FF] mt-1">•</span>
                            {highlight}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Changes list */}
                  <div className="ml-12 space-y-3">
                    {release.changes.map((change, i) => {
                      const label = getTypeLabel(change.type);
                      return (
                        <div
                          key={i}
                          className="flex items-start gap-3 p-3 rounded-lg transition-colors hover:bg-white/5"
                          style={{
                            background: 'rgba(10, 10, 15, 0.4)',
                            border: '1px solid rgba(255, 255, 255, 0.04)',
                          }}
                        >
                          {getTypeIcon(change.type)}
                          <span
                            className="text-xs font-medium px-2 py-0.5 rounded"
                            style={{
                              background: `${label.color}15`,
                              color: label.color,
                            }}
                          >
                            {label.text}
                          </span>
                          <span className="text-gray-300 text-sm flex-1">{change.text}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Subscribe CTA */}
        <section className="py-16">
          <div className="max-w-2xl mx-auto px-6 lg:px-8 text-center">
            <div
              className="p-8 rounded-2xl"
              style={{
                background: 'rgba(10, 10, 15, 0.6)',
                border: '1px solid rgba(139, 92, 246, 0.15)',
              }}
            >
              <h3 className="text-xl font-bold text-white mb-2">Stay Updated</h3>
              <p className="text-gray-400 mb-6">
                Get notified when we release new features and improvements.
              </p>
              <div className="flex gap-3 max-w-md mx-auto">
                <input
                  type="email"
                  placeholder="Enter your email"
                  className="flex-1 px-4 py-3 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#8B5CF6]/50"
                  style={{
                    background: 'rgba(0, 0, 0, 0.4)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }}
                />
                <button
                  className="px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200"
                  style={{
                    background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                  }}
                >
                  Subscribe
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </PageLayout>
  );
}
