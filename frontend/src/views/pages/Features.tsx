/**
 * Features Page
 * Showcases all Stratum AI platform features
 */

import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  ChartBarIcon,
  CpuChipIcon,
  ShieldCheckIcon,
  BoltIcon,
  UserGroupIcon,
  ArrowPathIcon,
  ChartPieIcon,
  CloudArrowUpIcon,
  DocumentChartBarIcon,
  CubeTransparentIcon,
  SparklesIcon,
  SignalIcon,
} from '@heroicons/react/24/outline';

const features = [
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
    color: '#22c55e',
  },
  {
    icon: ChartBarIcon,
    title: 'Advanced Attribution',
    description:
      'Multi-touch attribution models with conversion path analysis and incrementality testing.',
    color: '#3b82f6',
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
    description:
      'Built-in Recency, Frequency, Monetary analysis for customer value segmentation.',
    color: '#14b8a6',
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
    description:
      'Visual identity resolution showing cross-device connections and merge history.',
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
  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(168, 85, 247, 0.1)',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              color: '#a855f7',
            }}
          >
            <SparklesIcon className="w-4 h-4" />
            Platform Features
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Everything You Need to</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Scale Revenue Operations
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-3xl mx-auto mb-10"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            From signal health monitoring to ML-powered predictions, Stratum AI provides the
            complete toolkit for modern growth teams.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              to="/signup"
              className="px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:opacity-90"
              style={{
                background: '#f97316',
                boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
              }}
            >
              Start Free Trial
            </Link>
            <Link
              to="/pricing"
              className="px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:bg-white/10"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
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
                className="p-6 rounded-2xl transition-all hover:scale-[1.02] group backdrop-blur-xl"
                style={{
                  background: `${feature.color}15`,
                  border: `1px solid ${feature.color}30`,
                  boxShadow: `0 8px 32px ${feature.color}10`,
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
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
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
              background:
                'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Ready to Transform Your Revenue Operations?
            </h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              Join 150+ growth teams using Stratum AI to drive sustainable growth.
            </p>
            <Link
              to="/signup"
              className="inline-flex px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:opacity-90"
              style={{
                background: '#f97316',
                boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
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
