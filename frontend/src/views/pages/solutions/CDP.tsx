/**
 * CDP Solution Page — landing-themed (ink + ember).
 */

import { useEffect } from 'react';
import { usePageContent, type SolutionPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import {
  MktHero,
  MktSectionHeader,
  MktFeatureCard,
  MktStat,
} from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';
import {
  ArrowPathIcon,
  ChartBarIcon,
  CubeTransparentIcon,
  ShieldCheckIcon,
  SparklesIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';

const fallbackHero = {
  badge: 'Customer Data Platform',
  title: 'Turn customer data',
  titleHighlight: 'into revenue',
  description:
    'Unify customer profiles across every touchpoint. Build powerful segments and sync them to all your ad platforms instantly.',
  ctaText: 'Start Free Trial',
  ctaLink: '/signup',
};

const fallbackStats = [
  { value: '2.5M+', label: 'Profiles Unified' },
  { value: '47%', label: 'Higher Match Rate' },
  { value: '3.2x', label: 'ROAS Improvement' },
  { value: '<100ms', label: 'Sync Latency' },
];

const fallbackFeatures = [
  {
    icon: UserGroupIcon,
    title: '360° Customer Profiles',
    description:
      'Unified view from anonymous visitor to loyal customer. Real-time enrichment from every interaction.',
  },
  {
    icon: CubeTransparentIcon,
    title: 'Identity Resolution',
    description:
      'Connect the dots across devices and channels. Visual identity graph shows every connection.',
  },
  {
    icon: ChartBarIcon,
    title: 'Smart Segmentation',
    description:
      'Build segments with behavioral rules, RFM scores, and lifecycle stages. Preview before you publish.',
  },
  {
    icon: ArrowPathIcon,
    title: 'Multi-Platform Sync',
    description:
      'Push segments to Meta, Google, TikTok & Snapchat instantly. Auto-sync keeps your audiences fresh.',
  },
  {
    icon: SparklesIcon,
    title: 'Predictive Analytics',
    description:
      'Churn prediction, LTV forecasting, and next-best-action recommendations powered by ML.',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Privacy-First',
    description:
      'Consent management, GDPR/CCPA compliance, and hashed PII for secure platform sync.',
  },
];

const iconMap: Record<string, typeof UserGroupIcon> = {
  UserGroupIcon,
  CubeTransparentIcon,
  ChartBarIcon,
  ArrowPathIcon,
  SparklesIcon,
  ShieldCheckIcon,
};

export default function CDPSolution() {
  const { page, content } = usePageContent<SolutionPageContent>('solutions-cdp');

  useEffect(() => {
    if (page?.meta_title) document.title = page.meta_title;
    if (page?.meta_description) {
      document
        .querySelector('meta[name="description"]')
        ?.setAttribute('content', page.meta_description);
    }
  }, [page?.meta_title, page?.meta_description]);

  const hero = content?.hero ?? fallbackHero;
  const stats = content?.stats?.length ? content.stats : fallbackStats;
  const features = content?.features?.length
    ? content.features.map((f) => ({
        icon: iconMap[f.iconName] ?? UserGroupIcon,
        title: f.title,
        description: f.description,
      }))
    : fallbackFeatures;

  return (
    <PageLayout>
      <SEO {...pageSEO.cdp} url="https://stratumai.app/solutions/cdp" />

      <MktHero
        badge={hero.badge}
        badgeIcon={UserGroupIcon}
        title={hero.title}
        highlight={hero.titleHighlight}
        subtitle={hero.description}
        primary={{ label: hero.ctaText, href: hero.ctaLink }}
        secondary={{ label: 'Sync audiences', href: '/solutions/audience-sync' }}
      >
        <div className="mt-16 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, i) => (
            <MktStat key={stat.label} value={stat.value} label={stat.label} delay={i * 0.05} />
          ))}
        </div>
      </MktHero>

      <section className="pb-24 lg:pb-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="What's inside"
            title="A complete"
            highlight="data foundation"
            subtitle="Everything you need to unify, understand, and activate your first-party data — privacy-first."
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
