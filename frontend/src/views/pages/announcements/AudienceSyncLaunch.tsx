/**
 * Audience Sync Launch Announcement Page — landing-themed (ink + ember).
 */

import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import {
  MktHero,
  MktSectionHeader,
  MktFeatureCard,
  MktCard,
} from '@/components/landing/marketing';
import { SEO } from '@/components/common/SEO';
import {
  ArrowPathIcon,
  ChartBarIcon,
  ClockIcon,
  CloudArrowUpIcon,
  ShieldCheckIcon,
  UserGroupIcon,
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
    description:
      'Push your CDP segments to all ad platforms with a single click. No manual exports or uploads required.',
  },
  {
    icon: ClockIcon,
    title: 'Auto-Refresh',
    description:
      'Keep audiences fresh with configurable sync intervals from 1 hour to 1 week. Set it and forget it.',
  },
  {
    icon: UserGroupIcon,
    title: 'Smart Matching',
    description:
      'Hashed identifier matching for emails, phones, and MAIDs ensures privacy while maximizing match rates.',
  },
  {
    icon: ChartBarIcon,
    title: 'Match Rate Analytics',
    description:
      'Track match rates, profiles synced, and audience health across all platforms in one dashboard.',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Privacy-First',
    description: 'All PII is hashed before transmission. GDPR and CCPA compliant by design.',
  },
];

const steps = [
  {
    step: '1',
    title: 'Connect Your Ad Accounts',
    description:
      'Authorize Stratum to access your Meta, Google, TikTok, and Snapchat ad accounts with secure OAuth.',
  },
  {
    step: '2',
    title: 'Select a CDP Segment',
    description:
      'Choose from your existing segments or create a new one with our powerful segment builder.',
  },
  {
    step: '3',
    title: 'Configure Sync Settings',
    description:
      'Set your sync frequency, choose identifier types (email, phone, MAID), and enable auto-refresh.',
  },
  {
    step: '4',
    title: 'Launch & Monitor',
    description:
      'Hit sync and watch your audiences populate across platforms. Track match rates and audience health in real-time.',
  },
];

export default function AudienceSyncLaunch() {
  return (
    <PageLayout>
      <SEO
        title="Audience Sync Launch"
        description="Push your CDP segments to Meta, Google, TikTok, and Snapchat with one click. Keep your audiences fresh with automated syncing and maximize ad targeting precision."
        url="https://stratumai.app/announcements/audience-sync-launch"
      />

      <MktHero
        badge="New Feature"
        badgeIcon={ArrowPathIcon}
        title="Multi-Platform"
        highlight="Audience Sync"
        subtitle="Push your CDP segments to Meta, Google, TikTok, and Snapchat with one click. Keep your audiences fresh with automated syncing and maximize your ad targeting precision."
        primary={{ label: 'Start Free Trial', href: '/signup' }}
        secondary={{ label: 'Learn More', href: '/solutions/audience-sync' }}
      >
        <div className="mt-16 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {platforms.map((platform, i) => (
            <MktCard key={platform.name} delay={i * 0.05} className="p-5 text-center">
              <div className="w-12 h-12 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center mx-auto mb-3 text-secondary">
                {platform.logo}
              </div>
              <p className="text-h3 text-foreground font-semibold">{platform.name}</p>
              <p className="mt-1 text-meta uppercase text-muted-foreground">
                {platform.description}
              </p>
            </MktCard>
          ))}
        </div>
      </MktHero>

      {/* Features */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="Why Audience Sync"
            title="Targeting that stays"
            highlight="fresh"
            subtitle="Stop wasting time with manual exports and CSV uploads. Stratum's Audience Sync keeps your targeting fresh and your campaigns optimized."
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <MktFeatureCard
                key={feature.title}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
                delay={(i % 3) * 0.05}
              />
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="How it works" title="Live in" highlight="four steps" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((item, i) => (
              <MktCard key={item.step} delay={i * 0.05} className="p-8">
                <div className="w-11 h-11 rounded-full bg-secondary/10 border border-secondary/20 flex items-center justify-center mb-5">
                  <span className="text-h3 font-semibold text-secondary">{item.step}</span>
                </div>
                <h3 className="text-h3 text-foreground font-semibold mb-2">{item.title}</h3>
                <p className="text-body text-muted-foreground leading-relaxed">
                  {item.description}
                </p>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
