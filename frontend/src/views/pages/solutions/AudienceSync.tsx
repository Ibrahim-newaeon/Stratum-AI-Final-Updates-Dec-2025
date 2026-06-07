/**
 * Audience Sync Solution Page — landing-themed (ink + ember).
 */

import { useEffect } from 'react';
import { usePageContent, type SolutionPageContent } from '@/api/cms';
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
  BoltIcon,
  ChartBarIcon,
  ClockIcon,
  CloudArrowUpIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

const fallbackHero = {
  badge: 'Audience Sync',
  title: 'Sync audiences to',
  titleHighlight: 'every ad platform',
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
    description: 'Authenticate your ad accounts with a few clicks. No engineering required.',
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
    title: 'One-Click Sync',
    description: 'Push segments to any platform instantly. No engineering required.',
  },
  {
    icon: ClockIcon,
    title: 'Auto-Refresh',
    description: 'Configurable sync intervals keep your audiences fresh 24/7.',
  },
  {
    icon: ChartBarIcon,
    title: 'Match Rate Tracking',
    description: 'Monitor match rates and optimize identifier coverage.',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Privacy-Safe',
    description: 'Hashed identifiers ensure PII never leaves your control.',
  },
  {
    icon: CloudArrowUpIcon,
    title: 'Flexible Export',
    description: 'Export as CSV or JSON with custom attributes anytime.',
  },
  {
    icon: ArrowPathIcon,
    title: 'Sync History',
    description: 'Full audit trail of all sync operations and metrics.',
  },
];

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

  useEffect(() => {
    if (page?.meta_title) document.title = page.meta_title;
    if (page?.meta_description) {
      document
        .querySelector('meta[name="description"]')
        ?.setAttribute('content', page.meta_description);
    }
  }, [page?.meta_title, page?.meta_description]);

  const hero = content?.hero ?? fallbackHero;
  const steps = content?.steps?.length ? content.steps : fallbackSteps;
  const features = content?.features?.length
    ? content.features.map((f) => ({
        icon: iconMap[f.iconName] ?? BoltIcon,
        title: f.title,
        description: f.description,
      }))
    : fallbackFeatures;

  return (
    <PageLayout>
      <SEO
        title="Audience Sync"
        description="Sync CDP segments to Meta, Google, TikTok, and Snapchat in real-time. Unified audience management across all ad platforms."
        url="https://stratumai.app/solutions/audience-sync"
      />

      <MktHero
        badge={hero.badge}
        badgeIcon={ArrowPathIcon}
        title={hero.title}
        highlight={hero.titleHighlight}
        subtitle={hero.description}
        primary={{ label: hero.ctaText, href: hero.ctaLink }}
        secondary={{ label: 'Explore the CDP', href: '/solutions/cdp' }}
      >
        <div className="mt-16 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {platforms.map((platform, i) => (
            <MktCard key={platform.name} delay={i * 0.05} className="p-5 text-center">
              <p className="text-h3 text-foreground font-semibold">{platform.name}</p>
              <p className="mt-1 text-meta uppercase text-muted-foreground">
                {platform.description}
              </p>
            </MktCard>
          ))}
        </div>
      </MktHero>

      {/* How it works */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="How it works" title="Live in" highlight="three steps" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {steps.map((s, i) => (
              <MktCard key={s.title} delay={i * 0.06} className="p-8">
                <div className="w-11 h-11 rounded-full bg-secondary/10 border border-secondary/20 flex items-center justify-center mb-5">
                  <span className="text-h3 font-semibold text-secondary">{s.step}</span>
                </div>
                <h3 className="text-h3 text-foreground font-semibold mb-2">{s.title}</h3>
                <p className="text-body text-muted-foreground leading-relaxed">
                  {s.description}
                </p>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="Capabilities"
            title="Built for"
            highlight="confident activation"
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

      <CTA />
    </PageLayout>
  );
}
