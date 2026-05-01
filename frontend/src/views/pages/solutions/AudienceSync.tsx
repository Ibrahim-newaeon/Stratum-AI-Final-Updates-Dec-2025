/**
 * Audience Sync Solution Page
 * Multi-platform audience synchronization
 */

import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { usePageContent, type SolutionPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { SEO } from '@/components/common/SEO';
import {
  ArrowPathIcon,
  BoltIcon,
  ChartBarIcon,
  ClockIcon,
  CloudArrowUpIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

const fallbackHero = {
  badge: 'Audience Sync',
  title: 'Sync Audiences to',
  titleHighlight: 'Every Ad Platform',
  description:
    'Push your CDP segments to Meta, Google, TikTok, and Snapchat with one click. Keep audiences fresh with automatic syncing.',
  ctaText: 'Start Free Trial',
  ctaLink: '/signup',
};

const fallbackSteps = [
  {
    step: 1,
    title: 'Build Your Segment',
    description:
      'Create segments in the CDP using behavioral rules, RFM scores, or lifecycle stages.',
  },
  {
    step: 2,
    title: 'Connect Platforms',
    description:
      'Authenticate your ad accounts with a few clicks. No engineering required.',
  },
  {
    step: 3,
    title: 'Sync & Optimize',
    description:
      'Push to platforms instantly. Set auto-refresh intervals to keep audiences fresh.',
  },
];

const platforms = [
  { name: 'Meta', description: 'Custom Audiences API' },
  { name: 'Google', description: 'Customer Match API' },
  { name: 'TikTok', description: 'DMP Custom Audience' },
  { name: 'Snapchat', description: 'SAM Audience Match' },
];

const fallbackFeatures = [
  {
    icon: BoltIcon,
    iconName: 'BoltIcon',
    title: 'One-Click Sync',
    description: 'Push segments to any platform instantly. No engineering required.',
    color: '#f97316',
  },
  {
    icon: ClockIcon,
    iconName: 'ClockIcon',
    title: 'Auto-Refresh',
    description: 'Configurable sync intervals keep your audiences fresh 24/7.',
    color: '#06b6d4',
  },
  {
    icon: ChartBarIcon,
    iconName: 'ChartBarIcon',
    title: 'Match Rate Tracking',
    description: 'Monitor match rates and optimize identifier coverage.',
    color: 'var(--landing-accent-green)',
  },
  {
    icon: ShieldCheckIcon,
    iconName: 'ShieldCheckIcon',
    title: 'Privacy-Safe',
    description: 'Hashed identifiers ensure PII never leaves your control.',
    color: '#a855f7',
  },
  {
    icon: CloudArrowUpIcon,
    iconName: 'CloudArrowUpIcon',
    title: 'Flexible Export',
    description: 'Export as CSV or JSON with custom attributes anytime.',
    color: 'var(--landing-accent-blue)',
  },
  {
    icon: ArrowPathIcon,
    iconName: 'ArrowPathIcon',
    title: 'Sync History',
    description: 'Full audit trail of all sync operations and metrics.',
    color: '#ec4899',
  },
];

/** Map icon name strings from CMS to actual icon components */
const iconMap: Record<string, typeof BoltIcon> = {
  BoltIcon,
  ClockIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  CloudArrowUpIcon,
  ArrowPathIcon,
};

export default function AudienceSyncSolution() {
  const { page, content } = usePageContent<SolutionPageContent>('solutions-audience-sync');

  // SEO: override document title / meta description when CMS provides them
  useEffect(() => {
    if (page?.meta_title) document.title = page.meta_title;
    if (page?.meta_description) {
      document
        .querySelector('meta[name="description"]')
        ?.setAttribute('content', page.meta_description);
    }
  }, [page?.meta_title, page?.meta_description]);

  // CMS data with hardcoded fallback
  const hero = content?.hero ?? fallbackHero;
  const steps = content?.steps?.length ? content.steps : fallbackSteps;
  const features = content?.features?.length
    ? content.features.map((f) => ({
        ...f,
        icon: iconMap[f.iconName] ?? BoltIcon,
        color: '#f97316',
      }))
    : fallbackFeatures;

  return (
    <PageLayout>
      <SEO title="Audience Sync" description="Sync CDP segments to Meta, Google, TikTok, and Snapchat in real-time. Unified audience management across all ad platforms." url="https://stratum-ai.com/solutions/audience-sync" />
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(255, 179, 71, 0.1)',
              border: '1px solid rgba(255, 179, 71, 0.3)',
              color: 'var(--landing-accent-warm)',
            }}
          >
            <ArrowPathIcon className="w-4 h-4" />
            {hero.badge}
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "Geist, system-ui, sans-serif" }}
          >
            <span className="text-white">{hero.title}</span>
            <br />
            <span
              style={{ color: 'var(--landing-accent-coral)' }}
            >
              {hero.titleHighlight}
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-3xl mx-auto mb-10"
            style={{ color: 'var(--landing-text)' }}
          >
            {hero.description}
          </p>
          <Link
            to={hero.ctaLink}
            className="inline-flex px-8 py-4 rounded-full text-lg font-semibold text-white transition-opacity hover:opacity-90"
            style={{
              background: 'var(--landing-accent-coral)',
              boxShadow: '0 4px 20px rgba(255, 77, 77, 0.3)',
            }}
          >
            {hero.ctaText}
          </Link>
        </div>
      </section>

      {/* Supported Platforms */}
      <section className="py-12 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-8">Supported Platforms</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {platforms.map((platform) => (
              <div
                key={platform.name}
                className="p-6 rounded-2xl text-center transition-transform hover:scale-[1.02] group"
                style={{
                  background: 'var(--landing-card)',
                  border: '1px solid var(--landing-border)',
                }}
              >
                <div
                  className="w-14 h-14 rounded-xl flex items-center justify-center font-bold text-xl mx-auto mb-3 transition-colors"
                  style={{
                    background: 'linear-gradient(135deg, #FF5A1F 0%, #FF8A4A 100%)',
                    color: 'var(--landing-text-white-mid)',
                  }}
                >
                  {platform.name[0]}
                </div>
                <h3 className="font-semibold text-white">{platform.name}</h3>
                <p className="text-xs mt-1" style={{ color: 'var(--landing-text-dim)' }}>
                  {platform.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-16">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {steps.map((item) => (
              <div key={item.step} className="text-center">
                <div
                  className="w-16 h-16 rounded-2xl flex items-center justify-center text-2xl font-bold mx-auto mb-4"
                  style={{
                    background: 'var(--landing-accent-coral)',
                    color: '#fff',
                  }}
                >
                  {item.step}
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">{item.title}</h3>
                <p style={{ color: 'var(--landing-text)' }}>{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="p-6 rounded-2xl transition-transform hover:scale-[1.02]"
                style={{
                  background: 'var(--landing-card)',
                  border: '1px solid var(--landing-border)',
                  borderLeft: `3px solid ${feature.color}`,
                }}
              >
                <feature.icon className="w-10 h-10 mb-4" style={{ color: feature.color }} />
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-sm" style={{ color: 'var(--landing-text)' }}>
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="p-12 rounded-3xl"
            style={{
              background: 'var(--landing-card)',
              border: '1px solid var(--landing-border)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">Start Syncing Audiences Today</h2>
            <p className="text-lg mb-8" style={{ color: 'var(--landing-text)' }}>
              Free 14-day trial. No credit card required.
            </p>
            <Link
              to="/signup"
              className="inline-flex px-8 py-4 rounded-full text-lg font-semibold text-white transition-opacity hover:opacity-90"
              style={{
                background: 'var(--landing-accent-coral)',
                boxShadow: '0 4px 20px rgba(255, 77, 77, 0.3)',
              }}
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
