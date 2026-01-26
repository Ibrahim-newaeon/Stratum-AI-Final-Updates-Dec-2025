/**
 * Audience Sync Launch Announcement Page
 * Linked from the landing page announcement strip
 */

import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  ArrowLeftIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  CloudArrowUpIcon,
  UserGroupIcon,
  ChartBarIcon,
  ClockIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

const platforms = [
  {
    name: 'Meta',
    logo: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2.04c-5.5 0-10 4.49-10 10.02 0 5 3.66 9.15 8.44 9.9v-7H7.9v-2.9h2.54V9.85c0-2.51 1.49-3.89 3.78-3.89 1.09 0 2.23.19 2.23.19v2.47h-1.26c-1.24 0-1.63.77-1.63 1.56v1.88h2.78l-.45 2.9h-2.33v7a10 10 0 008.44-9.9c0-5.53-4.5-10.02-10-10.02z" />
      </svg>
    ),
    description: 'Custom Audiences API',
  },
  {
    name: 'Google',
    logo: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
      </svg>
    ),
    description: 'Customer Match API',
  },
  {
    name: 'TikTok',
    logo: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.31-4.64 2.93 2.93 0 01.88.13V9.4a6.84 6.84 0 00-1-.05A6.33 6.33 0 005 20.1a6.34 6.34 0 0010.86-4.43v-7a8.16 8.16 0 004.77 1.52v-3.4a4.85 4.85 0 01-1-.1z" />
      </svg>
    ),
    description: 'DMP Custom Audience API',
  },
  {
    name: 'Snapchat',
    logo: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.206.793c.99 0 4.347.276 5.93 3.821.529 1.193.403 3.219.299 4.847l-.003.06c-.012.18-.022.345-.03.51.075.045.203.09.401.09.3-.016.659-.12 1.033-.301a.602.602 0 01.257-.06c.09 0 .18.015.27.045.18.06.36.18.42.36.12.27.06.63-.18.81a3.56 3.56 0 01-1.59.63c-.09.015-.18.03-.27.06-.12.03-.18.09-.18.21 0 .06.015.12.045.18.333.72.78 1.38 1.35 1.95.45.45.96.81 1.515 1.065.165.075.333.135.495.18.24.06.48.18.54.45.09.36-.12.72-.39.87a2.84 2.84 0 01-.795.315c-.27.06-.54.12-.81.21-.22.07-.37.14-.52.27a.865.865 0 00-.24.39c-.075.255-.06.465-.06.63 0 .135-.03.24-.09.3a.44.44 0 01-.285.12c-.06.015-.12.015-.195.015-.225 0-.51-.045-.855-.135a6.27 6.27 0 00-1.515-.195c-.435 0-.84.045-1.2.135-.69.165-1.26.525-1.815.87l-.135.09c-.42.27-.855.54-1.365.69-.39.12-.765.165-1.11.165-.345 0-.72-.045-1.11-.165a4.3 4.3 0 01-1.365-.69l-.135-.09c-.555-.345-1.125-.705-1.815-.87a5.49 5.49 0 00-1.2-.135 6.3 6.3 0 00-1.515.195c-.345.09-.63.135-.855.135-.075 0-.135 0-.195-.015a.44.44 0 01-.285-.12.474.474 0 01-.09-.3c0-.165.015-.375-.06-.63a.865.865 0 00-.24-.39c-.15-.13-.3-.2-.52-.27-.27-.09-.54-.15-.81-.21a2.84 2.84 0 01-.795-.315c-.27-.15-.48-.51-.39-.87.06-.27.3-.39.54-.45.162-.045.33-.105.495-.18a5.07 5.07 0 001.515-1.065c.57-.57 1.017-1.23 1.35-1.95.03-.06.045-.12.045-.18 0-.12-.06-.18-.18-.21-.09-.03-.18-.045-.27-.06a3.56 3.56 0 01-1.59-.63c-.24-.18-.3-.54-.18-.81.06-.18.24-.3.42-.36a.6.6 0 01.27-.045c.09 0 .18.015.257.06.374.181.733.285 1.033.301.198 0 .326-.045.401-.09a34.31 34.31 0 01-.033-.57c-.104-1.628-.23-3.654.299-4.847C7.859 1.069 11.216.793 12.206.793z" />
      </svg>
    ),
    description: 'Audience Match SAM API',
  },
];

const features = [
  {
    icon: CloudArrowUpIcon,
    title: 'One-Click Sync',
    description: 'Push your CDP segments to all ad platforms with a single click. No manual exports or uploads required.',
    color: '#f97316',
  },
  {
    icon: ClockIcon,
    title: 'Auto-Refresh',
    description: 'Keep audiences fresh with configurable sync intervals from 1 hour to 1 week. Set it and forget it.',
    color: '#06b6d4',
  },
  {
    icon: UserGroupIcon,
    title: 'Smart Matching',
    description: 'Hashed identifier matching for emails, phones, and MAIDs ensures privacy while maximizing match rates.',
    color: '#22c55e',
  },
  {
    icon: ChartBarIcon,
    title: 'Match Rate Analytics',
    description: 'Track match rates, profiles synced, and audience health across all platforms in one dashboard.',
    color: '#a855f7',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Privacy-First',
    description: 'All PII is hashed before transmission. GDPR and CCPA compliant by design.',
    color: '#3b82f6',
  },
];

export default function AudienceSyncLaunch() {
  return (
    <PageLayout>
      {/* Back Link */}
      <div className="py-6 px-6">
        <div className="max-w-4xl mx-auto">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-sm transition-colors"
            style={{ color: 'rgba(255, 255, 255, 0.6)' }}
          >
            <ArrowLeftIcon className="w-4 h-4" />
            Back to Home
          </Link>
        </div>
      </div>

      {/* Hero */}
      <section className="py-12 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(6, 182, 212, 0.2) 100%)',
              border: '1px solid rgba(168, 85, 247, 0.3)',
            }}
          >
            <span
              className="w-2 h-2 rounded-full animate-pulse"
              style={{ background: '#22c55e' }}
            />
            <span style={{ color: '#a855f7' }}>New Feature</span>
          </div>

          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Multi-Platform</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Audience Sync
            </span>
          </h1>

          <p
            className="text-lg md:text-xl max-w-2xl mx-auto mb-8"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            Push your CDP segments to Meta, Google, TikTok, and Snapchat with one click.
            Keep your audiences fresh with automated syncing and maximize your ad targeting precision.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/signup"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl font-semibold text-white transition-all hover:scale-105"
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
                boxShadow: '0 4px 20px rgba(168, 85, 247, 0.4)',
              }}
            >
              Start Free Trial
              <ArrowRightIcon className="w-5 h-5" />
            </Link>
            <Link
              to="/solutions/audience-sync"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl font-semibold transition-all"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#ffffff',
              }}
            >
              Learn More
            </Link>
          </div>
        </div>
      </section>

      {/* Supported Platforms */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-12">
            Sync to All Major Ad Platforms
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {platforms.map((platform) => (
              <div
                key={platform.name}
                className="p-6 rounded-2xl text-center transition-all hover:scale-105 group"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <div
                  className="w-16 h-16 rounded-xl mx-auto mb-4 flex items-center justify-center transition-colors"
                  style={{ background: 'rgba(255, 255, 255, 0.08)', color: 'rgba(255, 255, 255, 0.7)' }}
                >
                  {platform.logo}
                </div>
                <h3 className="text-lg font-semibold text-white mb-1">{platform.name}</h3>
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                  {platform.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-4">
            Why Audience Sync?
          </h2>
          <p
            className="text-center max-w-2xl mx-auto mb-12"
            style={{ color: 'rgba(255, 255, 255, 0.6)' }}
          >
            Stop wasting time with manual exports and CSV uploads. Stratum's Audience Sync
            keeps your targeting fresh and your campaigns optimized.
          </p>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="p-6 rounded-2xl backdrop-blur-xl transition-all hover:scale-[1.02]"
                style={{
                  background: `${feature.color}15`,
                  border: `1px solid ${feature.color}30`,
                  boxShadow: `0 8px 32px ${feature.color}10`,
                }}
              >
                <feature.icon
                  className="w-10 h-10 mb-4"
                  style={{ color: feature.color }}
                />
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-12">
            How It Works
          </h2>

          <div className="space-y-8">
            {[
              {
                step: '1',
                title: 'Connect Your Ad Accounts',
                description: 'Authorize Stratum to access your Meta, Google, TikTok, and Snapchat ad accounts with secure OAuth.',
              },
              {
                step: '2',
                title: 'Select a CDP Segment',
                description: 'Choose from your existing segments or create a new one with our powerful segment builder.',
              },
              {
                step: '3',
                title: 'Configure Sync Settings',
                description: 'Set your sync frequency, choose identifier types (email, phone, MAID), and enable auto-refresh.',
              },
              {
                step: '4',
                title: 'Launch & Monitor',
                description: 'Hit sync and watch your audiences populate across platforms. Track match rates and audience health in real-time.',
              },
            ].map((item) => (
              <div key={item.step} className="flex gap-6 items-start">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{
                    background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
                  }}
                >
                  <span className="text-white font-bold text-lg">{item.step}</span>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                  <p style={{ color: 'rgba(255, 255, 255, 0.6)' }}>{item.description}</p>
                </div>
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
              background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Ready to Supercharge Your Targeting?
            </h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              Start your 14-day free trial and sync your first audience in minutes.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/signup"
                className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl font-semibold text-white transition-all hover:scale-105"
                style={{
                  background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
                  boxShadow: '0 4px 20px rgba(168, 85, 247, 0.4)',
                }}
              >
                Start Free Trial
                <ArrowRightIcon className="w-5 h-5" />
              </Link>
              <Link
                to="/contact"
                className="inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl font-semibold transition-all"
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#ffffff',
                }}
              >
                Talk to Sales
              </Link>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
