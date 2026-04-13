/**
 * Features Page
 * Showcases all Stratum AI platform features
 */

import { Link } from 'react-router-dom';
import { usePageContent, type FeaturesPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
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
    color: '#a855f7',
  },
  {
    icon: SignalIcon,
    title: 'Signal Health Monitoring',
    description:
      'Real-time monitoring of data quality across all connected platforms with instant anomaly detection.',
    color: '#06b6d4',
  },
  {
    icon: UserGroupIcon,
    title: 'Customer Data Platform',
    description:
      'Unified customer profiles with identity resolution, behavioral segmentation, and lifecycle tracking.',
    color: '#f97316',
  },
  {
    icon: ArrowPathIcon,
    title: 'Multi-Platform Audience Sync',
    description:
      'Push segments to Meta, Google, TikTok & Snapchat with one click. Auto-sync keeps audiences fresh.',
    color: 'var(--landing-accent-green)',
  },
  {
    icon: ChartBarIcon,
    title: 'Advanced Attribution',
    description:
      'Multi-touch attribution models with conversion path analysis and incrementality testing.',
    color: 'var(--landing-accent-blue)',
  },
  {
    icon: CpuChipIcon,
    title: 'ML-Powered Predictions',
    description:
      'Churn prediction, LTV forecasting, and next-best-action recommendations powered by machine learning.',
    color: '#ec4899',
  },
  {
    icon: BoltIcon,
    title: 'Real-Time Event Processing',
    description:
      'Process millions of events per second with sub-second latency for instant personalization.',
    color: '#eab308',
  },
  {
    icon: ChartPieIcon,
    title: 'RFM Analysis',
    description: 'Built-in Recency, Frequency, Monetary analysis for customer value segmentation.',
    color: 'var(--landing-accent-cyan)',
  },
  {
    icon: CloudArrowUpIcon,
    title: 'Flexible Data Export',
    description:
      'Export audiences as CSV or JSON with custom traits, events, and computed attributes.',
    color: '#8b5cf6',
  },
  {
    icon: DocumentChartBarIcon,
    title: 'Custom Reporting',
    description:
      'Build custom reports and dashboards with drag-and-drop widgets and scheduled exports.',
    color: '#f43f5e',
  },
  {
    icon: CubeTransparentIcon,
    title: 'Identity Graph',
    description: 'Visual identity resolution showing cross-device connections and merge history.',
    color: '#06b6d4',
  },
  {
    icon: SparklesIcon,
    title: 'AI Campaign Optimization',
    description:
      'Automatic bid adjustments, budget allocation, and creative rotation based on performance.',
    color: '#a855f7',
  },
];

export default function Features() {
  const { content } = usePageContent<FeaturesPageContent>('features');

  // Use CMS data if available, otherwise fallback
  const features = content?.features?.length
    ? content.features.map((f) => ({
        icon: iconMap[f.iconName] || SparklesIcon,
        title: f.title,
        description: f.description,
        color: f.color,
      }))
    : fallbackFeatures;

  return (
    <PageLayout>
      <SEO {...pageSEO.features} url="https://stratum-ai.com/features" />
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
            <SparklesIcon className="w-4 h-4" />
            Platform Features
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Clash Display', sans-serif" }}
          >
            <span className="text-white">Everything You Need to</span>
            <br />
            <span
              style={{ color: 'var(--landing-accent-coral)' }}
            >
              Scale Revenue Operations
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-3xl mx-auto mb-10"
            style={{ color: 'var(--landing-text)' }}
          >
            From signal health monitoring to ML-powered predictions, Stratum AI provides the
            complete toolkit for modern growth teams.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/signup"
              className="px-8 py-4 rounded-full text-lg font-semibold text-white transition-all hover:opacity-90"
              style={{
                background: 'var(--landing-accent-coral)',
                boxShadow: '0 4px 20px rgba(255, 77, 77, 0.3)',
              }}
            >
              Start Free Trial
            </Link>
            <Link
              to="/pricing"
              className="px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:bg-white/10"
              style={{
                background: 'var(--landing-surface-glass)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
              }}
            >
              View Pricing
            </Link>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="p-6 rounded-2xl transition-all hover:scale-[1.02] group"
                style={{
                  background: 'var(--landing-card)',
                  border: '1px solid var(--landing-border)',
                  borderLeft: `3px solid ${feature.color}`,
                }}
              >
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                  style={{
                    background: `${feature.color}25`,
                    border: `1px solid ${feature.color}40`,
                  }}
                >
                  <feature.icon className="w-6 h-6" style={{ color: feature.color }} />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-sm" style={{ color: 'var(--landing-text)' }}>
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="p-12 rounded-3xl"
            style={{
              background: 'var(--landing-card)',
              border: '1px solid var(--landing-border)',
            }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Ready to Transform Your Revenue Operations?
            </h2>
            <p className="text-lg mb-8" style={{ color: 'var(--landing-text)' }}>
              Join 150+ growth teams using Stratum AI to drive sustainable growth.
            </p>
            <Link
              to="/signup"
              className="inline-flex px-8 py-4 rounded-full text-lg font-semibold text-white transition-all hover:opacity-90"
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
