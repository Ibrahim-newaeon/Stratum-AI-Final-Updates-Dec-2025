/**
 * Comparison / Battle Cards Page
 * 2026 Theme - Electric Neon / OLED-Optimized
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  CheckIcon,
  XMarkIcon,
  MinusIcon,
  ArrowRightIcon,
  ShieldCheckIcon,
  CpuChipIcon,
  BoltIcon,
  ChartBarIcon,
} from '@heroicons/react/24/outline';

type ComparisonValue = 'yes' | 'no' | 'partial' | string;

interface Competitor {
  id: string;
  name: string;
  tagline: string;
  color: string;
}

interface FeatureRow {
  feature: string;
  category: string;
  stratum: ComparisonValue;
  competitors: Record<string, ComparisonValue>;
  tooltip?: string;
}

const competitors: Competitor[] = [
  { id: 'segment', name: 'Segment', tagline: 'CDP', color: '#52BD95' },
  { id: 'braze', name: 'Braze', tagline: 'Marketing Automation', color: '#F6C94A' },
  { id: 'mparticle', name: 'mParticle', tagline: 'CDP', color: '#E54D42' },
  { id: 'amplitude', name: 'Amplitude', tagline: 'Analytics', color: '#1E61CD' },
];

const features: FeatureRow[] = [
  // Trust Engine
  { feature: 'Trust-Gated Automation', category: 'Trust Engine', stratum: 'yes', competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' }, tooltip: 'Unique to Stratum AI' },
  { feature: 'Signal Health Monitoring', category: 'Trust Engine', stratum: 'yes', competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' } },
  { feature: 'Predictive Signal Analysis', category: 'Trust Engine', stratum: 'yes', competitors: { segment: 'no', braze: 'partial', mparticle: 'no', amplitude: 'partial' } },
  { feature: 'Auto-pause on Degradation', category: 'Trust Engine', stratum: 'yes', competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' } },

  // CDP
  { feature: 'Unified Customer Profiles', category: 'CDP', stratum: 'yes', competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'partial' } },
  { feature: 'Identity Resolution', category: 'CDP', stratum: 'yes', competitors: { segment: 'yes', braze: 'partial', mparticle: 'yes', amplitude: 'no' } },
  { feature: 'Identity Graph Visualization', category: 'CDP', stratum: 'yes', competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' } },
  { feature: 'Real-time Event Ingestion', category: 'CDP', stratum: 'yes', competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'yes' } },
  { feature: 'Computed Traits', category: 'CDP', stratum: 'yes', competitors: { segment: 'yes', braze: 'partial', mparticle: 'yes', amplitude: 'partial' } },
  { feature: 'RFM Analysis Built-in', category: 'CDP', stratum: 'yes', competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' } },

  // Audience Sync
  { feature: 'Meta Custom Audiences', category: 'Audience Sync', stratum: 'yes', competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'partial' } },
  { feature: 'Google Customer Match', category: 'Audience Sync', stratum: 'yes', competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'partial' } },
  { feature: 'TikTok Audiences', category: 'Audience Sync', stratum: 'yes', competitors: { segment: 'partial', braze: 'yes', mparticle: 'partial', amplitude: 'no' } },
  { feature: 'Snapchat Audiences', category: 'Audience Sync', stratum: 'yes', competitors: { segment: 'partial', braze: 'partial', mparticle: 'partial', amplitude: 'no' } },
  { feature: 'Auto-sync Scheduling', category: 'Audience Sync', stratum: 'yes', competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'no' } },

  // Automation
  { feature: 'Custom Autopilot Rules', category: 'Automation', stratum: 'yes', competitors: { segment: 'no', braze: 'yes', mparticle: 'no', amplitude: 'no' } },
  { feature: 'A/B Testing', category: 'Automation', stratum: 'yes', competitors: { segment: 'partial', braze: 'yes', mparticle: 'partial', amplitude: 'yes' } },
  { feature: 'Predictive Churn Scoring', category: 'Automation', stratum: 'yes', competitors: { segment: 'no', braze: 'yes', mparticle: 'partial', amplitude: 'yes' } },

  // Analytics
  { feature: 'Funnel Analysis', category: 'Analytics', stratum: 'yes', competitors: { segment: 'no', braze: 'partial', mparticle: 'no', amplitude: 'yes' } },
  { feature: 'Anomaly Detection', category: 'Analytics', stratum: 'yes', competitors: { segment: 'no', braze: 'no', mparticle: 'partial', amplitude: 'yes' } },
  { feature: 'EMQ Scoring', category: 'Analytics', stratum: 'yes', competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' } },
];

const categories = [...new Set(features.map((f) => f.category))];

const renderValue = (value: ComparisonValue, isStratum = false) => {
  if (value === 'yes') {
    return (
      <div className="flex items-center justify-center">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center"
          style={{
            background: isStratum ? 'rgba(0, 255, 136, 0.2)' : 'rgba(0, 255, 136, 0.15)',
            border: `1px solid ${isStratum ? '#00FF88' : 'rgba(0, 255, 136, 0.3)'}`,
          }}
        >
          <CheckIcon className="w-4 h-4 text-[#00FF88]" />
        </div>
      </div>
    );
  }
  if (value === 'no') {
    return (
      <div className="flex items-center justify-center">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center"
          style={{ background: 'rgba(255, 71, 87, 0.15)', border: '1px solid rgba(255, 71, 87, 0.3)' }}
        >
          <XMarkIcon className="w-4 h-4 text-[#FF4757]" />
        </div>
      </div>
    );
  }
  if (value === 'partial') {
    return (
      <div className="flex items-center justify-center">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center"
          style={{ background: 'rgba(255, 183, 0, 0.15)', border: '1px solid rgba(255, 183, 0, 0.3)' }}
        >
          <MinusIcon className="w-4 h-4 text-[#FFB800]" />
        </div>
      </div>
    );
  }
  return <span className="text-gray-400 text-sm">{value}</span>;
};

const differentiators = [
  {
    title: 'Trust-Gated Automation',
    description: 'Only execute when signal health passes safety thresholds. No other platform offers this level of automation confidence.',
    icon: ShieldCheckIcon,
    color: '#8B5CF6',
  },
  {
    title: 'Identity Graph Visualization',
    description: 'See exactly how customer identities are connected across devices and channels with interactive visualizations.',
    icon: CpuChipIcon,
    color: '#00D4FF',
  },
  {
    title: 'RFM Analysis Built-in',
    description: 'Native Recency, Frequency, Monetary analysis without additional tools or integrations.',
    icon: ChartBarIcon,
    color: '#00FF88',
  },
  {
    title: 'Signal Health Monitoring',
    description: 'Real-time monitoring of data quality and signal reliability across all your integrations.',
    icon: BoltIcon,
    color: '#FF6B6B',
  },
];

export default function ComparisonPage() {
  const [selectedCompetitor, setSelectedCompetitor] = useState<string>('segment');
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  return (
    <PageLayout>
      <div className="min-h-screen">
        {/* Hero Section */}
        <section className="relative py-20 overflow-hidden">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-6"
                style={{
                  background: 'rgba(139, 92, 246, 0.1)',
                  border: '1px solid rgba(139, 92, 246, 0.2)',
                }}>
                <ChartBarIcon className="w-4 h-4 text-[#8B5CF6]" />
                <span className="text-sm font-medium text-[#8B5CF6]">Compare</span>
              </div>

              <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
                How Stratum AI{' '}
                <span style={{
                  background: 'linear-gradient(135deg, #8B5CF6 0%, #00D4FF 50%, #FF6B6B 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}>
                  Compares
                </span>
              </h1>

              <p className="text-lg text-gray-400">
                See how Stratum AI stacks up against other marketing platforms.
                Trust-gated automation is our unique differentiator.
              </p>
            </div>
          </div>
        </section>

        {/* Key Differentiators */}
        <section className="py-8">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <h2 className="text-xl font-bold text-white mb-6 text-center">What Makes Us Different</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {differentiators.map((diff) => (
                <div
                  key={diff.title}
                  className="p-5 rounded-xl"
                  style={{
                    background: `linear-gradient(135deg, ${diff.color}08 0%, transparent 100%)`,
                    border: `1px solid ${diff.color}20`,
                  }}
                >
                  <diff.icon className="w-8 h-8 mb-3" style={{ color: diff.color }} />
                  <h3 className="text-white font-semibold mb-2">{diff.title}</h3>
                  <p className="text-gray-400 text-sm">{diff.description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Competitor Selector */}
        <section className="py-8">
          <div className="max-w-5xl mx-auto px-6 lg:px-8">
            <div className="flex items-center justify-center gap-3 mb-8 flex-wrap">
              <span className="text-gray-400 text-sm">Compare with:</span>
              {competitors.map((comp) => (
                <button
                  key={comp.id}
                  onClick={() => setSelectedCompetitor(comp.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    selectedCompetitor === comp.id ? 'text-white' : 'text-gray-400'
                  }`}
                  style={{
                    background: selectedCompetitor === comp.id ? `${comp.color}20` : 'rgba(255, 255, 255, 0.04)',
                    border: `1px solid ${selectedCompetitor === comp.id ? `${comp.color}40` : 'rgba(255, 255, 255, 0.08)'}`,
                  }}
                >
                  {comp.name}
                </button>
              ))}
            </div>

            {/* Comparison Table */}
            <div
              className="rounded-2xl overflow-hidden"
              style={{
                background: 'rgba(10, 10, 15, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
              }}
            >
              {/* Header */}
              <div
                className="grid grid-cols-3 gap-4 p-4 border-b"
                style={{ borderColor: 'rgba(255, 255, 255, 0.06)' }}
              >
                <div className="text-gray-400 text-sm font-medium">Feature</div>
                <div className="text-center">
                  <span
                    className="text-sm font-bold"
                    style={{
                      background: 'linear-gradient(135deg, #8B5CF6 0%, #00D4FF 100%)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                    }}
                  >
                    Stratum AI
                  </span>
                </div>
                <div className="text-center">
                  <span
                    className="text-sm font-medium"
                    style={{ color: competitors.find((c) => c.id === selectedCompetitor)?.color }}
                  >
                    {competitors.find((c) => c.id === selectedCompetitor)?.name}
                  </span>
                </div>
              </div>

              {/* Categories & Features */}
              {categories.map((category) => (
                <div key={category}>
                  {/* Category Header */}
                  <button
                    className="w-full flex items-center justify-between p-4 border-b transition-colors hover:bg-white/5"
                    style={{ borderColor: 'rgba(255, 255, 255, 0.06)' }}
                    onClick={() => setExpandedCategory(expandedCategory === category ? null : category)}
                  >
                    <span className="text-white font-medium">{category}</span>
                    <span className="text-gray-500 text-xs">
                      {features.filter((f) => f.category === category).length} features
                    </span>
                  </button>

                  {/* Features */}
                  {(expandedCategory === category || expandedCategory === null) &&
                    features
                      .filter((f) => f.category === category)
                      .map((feature, i) => (
                        <div
                          key={feature.feature}
                          className="grid grid-cols-3 gap-4 p-4 border-b items-center"
                          style={{
                            borderColor: 'rgba(255, 255, 255, 0.03)',
                            background: i % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.02)',
                          }}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-gray-300 text-sm">{feature.feature}</span>
                            {feature.tooltip && (
                              <span
                                className="text-[10px] font-medium px-1.5 py-0.5 rounded"
                                style={{ background: 'rgba(139, 92, 246, 0.2)', color: '#A78BFA' }}
                              >
                                Unique
                              </span>
                            )}
                          </div>
                          <div>{renderValue(feature.stratum, true)}</div>
                          <div>{renderValue(feature.competitors[selectedCompetitor])}</div>
                        </div>
                      ))}
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16">
          <div className="max-w-4xl mx-auto px-6 lg:px-8">
            <div
              className="rounded-2xl p-8 md:p-12 text-center"
              style={{
                background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(0, 212, 255, 0.05) 100%)',
                border: '1px solid rgba(139, 92, 246, 0.2)',
              }}
            >
              <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
                Ready to experience the difference?
              </h2>
              <p className="text-gray-400 mb-8">
                Start with a free trial and see why trust-gated automation changes everything.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/signup"
                  className="px-8 py-4 rounded-xl font-semibold text-white transition-all duration-200 flex items-center justify-center gap-2"
                  style={{
                    background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                    boxShadow: '0 4px 20px rgba(139, 92, 246, 0.3)',
                  }}
                >
                  Start Free Trial
                  <ArrowRightIcon className="w-4 h-4" />
                </Link>
                <Link
                  to="/contact"
                  className="px-8 py-4 rounded-xl font-semibold text-white transition-all duration-200"
                  style={{
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }}
                >
                  Request Demo
                </Link>
              </div>
            </div>
          </div>
        </section>
      </div>
    </PageLayout>
  );
}
