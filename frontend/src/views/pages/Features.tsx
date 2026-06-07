/**
 * Features Page — landing-themed (ink + ember).
 * Showcases all Stratum AI platform features.
 */

import { usePageContent, type FeaturesPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import {
  MktHero,
  MktSectionHeader,
  MktFeatureCard,
} from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';
import {
  ArrowPathIcon,
  BoltIcon,
  ChartBarIcon,
  ChartPieIcon,
  CloudArrowUpIcon,
  CpuChipIcon,
  CubeTransparentIcon,
  DocumentChartBarIcon,
  ShieldCheckIcon,
  SignalIcon,
  SparklesIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';

const iconMap: Record<string, typeof ShieldCheckIcon> = {
  ShieldCheckIcon,
  SignalIcon,
  UserGroupIcon,
  ArrowPathIcon,
  ChartBarIcon,
  CpuChipIcon,
  BoltIcon,
  ChartPieIcon,
  CloudArrowUpIcon,
  DocumentChartBarIcon,
  CubeTransparentIcon,
  SparklesIcon,
};

const fallbackFeatures = [
  {
    icon: ShieldCheckIcon,
    title: 'Trust-Gated Autopilot',
    description:
      'Automations only execute when signal health passes safety thresholds. No more blind optimization.',
  },
  {
    icon: SignalIcon,
    title: 'Signal Health Monitoring',
    description:
      'Real-time monitoring of data quality across all connected platforms with instant anomaly detection.',
  },
  {
    icon: UserGroupIcon,
    title: 'Customer Data Platform',
    description:
      'Unified customer profiles with identity resolution, behavioral segmentation, and lifecycle tracking.',
  },
  {
    icon: ArrowPathIcon,
    title: 'Multi-Platform Audience Sync',
    description:
      'Push segments to Meta, Google, TikTok & Snapchat with one click. Auto-sync keeps audiences fresh.',
  },
  {
    icon: ChartBarIcon,
    title: 'Advanced Attribution',
    description:
      'Multi-touch attribution models with conversion path analysis and incrementality testing.',
  },
  {
    icon: CpuChipIcon,
    title: 'ML-Powered Predictions',
    description:
      'Churn prediction, LTV forecasting, and next-best-action recommendations powered by machine learning.',
  },
  {
    icon: BoltIcon,
    title: 'Real-Time Event Processing',
    description:
      'Process millions of events per second with sub-second latency for instant personalization.',
  },
  {
    icon: ChartPieIcon,
    title: 'RFM Analysis',
    description:
      'Built-in Recency, Frequency, Monetary analysis for customer value segmentation.',
  },
  {
    icon: CloudArrowUpIcon,
    title: 'Flexible Data Export',
    description:
      'Export audiences as CSV or JSON with custom traits, events, and computed attributes.',
  },
  {
    icon: DocumentChartBarIcon,
    title: 'Custom Reporting',
    description:
      'Build custom reports and dashboards with drag-and-drop widgets and scheduled exports.',
  },
  {
    icon: CubeTransparentIcon,
    title: 'Identity Graph',
    description:
      'Visual identity resolution showing cross-device connections and merge history.',
  },
  {
    icon: SparklesIcon,
    title: 'AI Campaign Optimization',
    description:
      'Automatic bid adjustments, budget allocation, and creative rotation based on performance.',
  },
];

export default function Features() {
  const { content } = usePageContent<FeaturesPageContent>('features');

  const features = content?.features?.length
    ? content.features.map((f) => ({
        icon: iconMap[f.iconName] || SparklesIcon,
        title: f.title,
        description: f.description,
      }))
    : fallbackFeatures;

  return (
    <PageLayout>
      <SEO {...pageSEO.features} url="https://stratumai.app/features" />

      <MktHero
        badge="Platform Features"
        badgeIcon={SparklesIcon}
        title="Everything you need to"
        highlight="scale revenue operations"
        subtitle="From signal-health monitoring to ML-powered predictions, Stratum AI provides the complete toolkit for modern growth teams."
        primary={{ label: 'Start Free Trial', href: '/signup' }}
        secondary={{ label: 'View Pricing', href: '/pricing' }}
      />

      <section className="pb-24 lg:pb-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="Capabilities"
            title="One platform,"
            highlight="every signal"
            subtitle="Each capability is wired into the same trust layer — so automation only acts on data you can rely on."
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
