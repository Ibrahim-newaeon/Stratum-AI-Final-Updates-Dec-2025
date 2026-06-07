/**
 * Comparison / Battle Cards Page — landing-themed (ink + ember).
 */

import { useState } from 'react';
import { usePageContent, type ComparisonPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import {
  MktHero,
  MktSectionHeader,
  MktCard,
  MktFeatureCard,
} from '@/components/landing/marketing';
import {
  BoltIcon,
  ChartBarIcon,
  CheckIcon,
  CpuChipIcon,
  MinusIcon,
  ShieldCheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

const diffIconMap: Record<string, typeof ShieldCheckIcon> = {
  ShieldCheckIcon,
  CpuChipIcon,
  ChartBarIcon,
  BoltIcon,
};

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

const fallbackCompetitors: Competitor[] = [
  { id: 'segment', name: 'Segment', tagline: 'CDP', color: '#52BD95' },
  { id: 'braze', name: 'Braze', tagline: 'Marketing Automation', color: '#F6C94A' },
  { id: 'mparticle', name: 'mParticle', tagline: 'CDP', color: '#E54D42' },
  { id: 'amplitude', name: 'Amplitude', tagline: 'Analytics', color: '#1E61CD' },
];

const fallbackFeatures: FeatureRow[] = [
  // Trust Engine
  {
    feature: 'Trust-Gated Automation',
    category: 'Trust Engine',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' },
    tooltip: 'Unique to Stratum AI',
  },
  {
    feature: 'Signal Health Monitoring',
    category: 'Trust Engine',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' },
  },
  {
    feature: 'Predictive Signal Analysis',
    category: 'Trust Engine',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'partial', mparticle: 'no', amplitude: 'partial' },
  },
  {
    feature: 'Auto-pause on Degradation',
    category: 'Trust Engine',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' },
  },

  // CDP
  {
    feature: 'Unified Customer Profiles',
    category: 'CDP',
    stratum: 'yes',
    competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'partial' },
  },
  {
    feature: 'Identity Resolution',
    category: 'CDP',
    stratum: 'yes',
    competitors: { segment: 'yes', braze: 'partial', mparticle: 'yes', amplitude: 'no' },
  },
  {
    feature: 'Identity Graph Visualization',
    category: 'CDP',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' },
  },
  {
    feature: 'Real-time Event Ingestion',
    category: 'CDP',
    stratum: 'yes',
    competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'yes' },
  },
  {
    feature: 'Computed Traits',
    category: 'CDP',
    stratum: 'yes',
    competitors: { segment: 'yes', braze: 'partial', mparticle: 'yes', amplitude: 'partial' },
  },
  {
    feature: 'RFM Analysis Built-in',
    category: 'CDP',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' },
  },

  // Audience Sync
  {
    feature: 'Meta Custom Audiences',
    category: 'Audience Sync',
    stratum: 'yes',
    competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'partial' },
  },
  {
    feature: 'Google Customer Match',
    category: 'Audience Sync',
    stratum: 'yes',
    competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'partial' },
  },
  {
    feature: 'TikTok Audiences',
    category: 'Audience Sync',
    stratum: 'yes',
    competitors: { segment: 'partial', braze: 'yes', mparticle: 'partial', amplitude: 'no' },
  },
  {
    feature: 'Snapchat Audiences',
    category: 'Audience Sync',
    stratum: 'yes',
    competitors: { segment: 'partial', braze: 'partial', mparticle: 'partial', amplitude: 'no' },
  },
  {
    feature: 'Auto-sync Scheduling',
    category: 'Audience Sync',
    stratum: 'yes',
    competitors: { segment: 'yes', braze: 'yes', mparticle: 'yes', amplitude: 'no' },
  },

  // Automation
  {
    feature: 'Custom Autopilot Rules',
    category: 'Automation',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'yes', mparticle: 'no', amplitude: 'no' },
  },
  {
    feature: 'A/B Testing',
    category: 'Automation',
    stratum: 'yes',
    competitors: { segment: 'partial', braze: 'yes', mparticle: 'partial', amplitude: 'yes' },
  },
  {
    feature: 'Predictive Churn Scoring',
    category: 'Automation',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'yes', mparticle: 'partial', amplitude: 'yes' },
  },

  // Analytics
  {
    feature: 'Funnel Analysis',
    category: 'Analytics',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'partial', mparticle: 'no', amplitude: 'yes' },
  },
  {
    feature: 'Anomaly Detection',
    category: 'Analytics',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'no', mparticle: 'partial', amplitude: 'yes' },
  },
  {
    feature: 'EMQ Scoring',
    category: 'Analytics',
    stratum: 'yes',
    competitors: { segment: 'no', braze: 'no', mparticle: 'no', amplitude: 'no' },
  },
];

// categories is computed inside the component after CMS resolution

const renderValue = (value: ComparisonValue) => {
  if (value === 'yes') {
    return (
      <div className="flex items-center justify-center">
        <div className="w-6 h-6 rounded-full flex items-center justify-center bg-success/15 border border-success/30">
          <CheckIcon className="w-4 h-4 text-success" />
        </div>
      </div>
    );
  }
  if (value === 'no') {
    return (
      <div className="flex items-center justify-center">
        <div className="w-6 h-6 rounded-full flex items-center justify-center bg-muted border border-border">
          <XMarkIcon className="w-4 h-4 text-muted-foreground" />
        </div>
      </div>
    );
  }
  if (value === 'partial') {
    return (
      <div className="flex items-center justify-center">
        <div className="w-6 h-6 rounded-full flex items-center justify-center bg-warning/15 border border-warning/30">
          <MinusIcon className="w-4 h-4 text-warning" />
        </div>
      </div>
    );
  }
  return <span className="text-body text-muted-foreground">{value}</span>;
};

const fallbackDifferentiators = [
  {
    title: 'Trust-Gated Automation',
    description:
      'Only execute when signal health passes safety thresholds. No other platform offers this level of automation confidence.',
    icon: ShieldCheckIcon,
  },
  {
    title: 'Identity Graph Visualization',
    description:
      'See exactly how customer identities are connected across devices and channels with interactive visualizations.',
    icon: CpuChipIcon,
  },
  {
    title: 'RFM Analysis Built-in',
    description:
      'Native Recency, Frequency, Monetary analysis without additional tools or integrations.',
    icon: ChartBarIcon,
  },
  {
    title: 'Signal Health Monitoring',
    description:
      'Real-time monitoring of data quality and signal reliability across all your integrations.',
    icon: BoltIcon,
  },
];

export default function ComparisonPage() {
  const { content } = usePageContent<ComparisonPageContent>('compare');
  const [selectedCompetitor, setSelectedCompetitor] = useState<string>('segment');
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  // Use CMS data if available, otherwise fallback
  const competitors: Competitor[] = content?.competitors?.length
    ? content.competitors
    : fallbackCompetitors;

  const features: FeatureRow[] = content?.features?.length
    ? content.features.map((f) => ({
        feature: f.feature,
        category: f.category,
        stratum: f.stratum as ComparisonValue,
        competitors: f.competitors as Record<string, ComparisonValue>,
        tooltip: f.tooltip,
      }))
    : fallbackFeatures;

  const differentiators = content?.differentiators?.length
    ? content.differentiators.map((d) => ({
        title: d.title,
        description: d.description,
        icon: diffIconMap[d.iconName] || ShieldCheckIcon,
      }))
    : fallbackDifferentiators;

  const categories = [...new Set(features.map((f) => f.category))];

  const selectedCompetitorName =
    competitors.find((c) => c.id === selectedCompetitor)?.name ?? '';

  return (
    <PageLayout>
      <MktHero
        badge="Compare"
        badgeIcon={ChartBarIcon}
        title="How Stratum AI"
        highlight="compares"
        subtitle="See how Stratum AI stacks up against other marketing platforms. Trust-gated automation is our unique differentiator."
      />

      {/* Key Differentiators */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="Why Stratum" title="What makes us" highlight="different" />
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {differentiators.map((diff, i) => (
              <MktFeatureCard
                key={diff.title}
                icon={diff.icon}
                title={diff.title}
                description={diff.description}
                delay={(i % 4) * 0.05}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="py-24 lg:py-28">
        <div className="max-w-5xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="Feature Matrix"
            title="Stratum AI vs."
            highlight="the field"
          />

          {/* Competitor Selector */}
          <div className="flex items-center justify-center gap-3 mb-8 flex-wrap">
            <span className="text-meta uppercase text-muted-foreground">Compare with:</span>
            {competitors.map((comp) => (
              <button
                key={comp.id}
                onClick={() => setSelectedCompetitor(comp.id)}
                className={`px-4 py-2 rounded-full text-body font-medium transition-colors duration-200 border ${
                  selectedCompetitor === comp.id
                    ? 'bg-secondary/10 border-secondary/40 text-secondary'
                    : 'bg-card border-border text-muted-foreground hover:bg-foreground/5'
                }`}
              >
                {comp.name}
              </button>
            ))}
          </div>

          {/* Comparison Table */}
          <MktCard className="overflow-hidden">
            {/* Header */}
            <div className="grid grid-cols-3 gap-4 p-4 border-b border-border">
              <div className="text-meta uppercase text-muted-foreground">Feature</div>
              <div className="text-center">
                <span className="text-meta uppercase text-secondary font-semibold">
                  Stratum AI
                </span>
              </div>
              <div className="text-center">
                <span className="text-meta uppercase text-muted-foreground">
                  {selectedCompetitorName}
                </span>
              </div>
            </div>

            {/* Categories & Features */}
            {categories.map((category) => (
              <div key={category}>
                {/* Category Header */}
                <button
                  className="w-full flex items-center justify-between p-4 border-b border-border transition-colors hover:bg-foreground/5"
                  onClick={() =>
                    setExpandedCategory(expandedCategory === category ? null : category)
                  }
                >
                  <span className="text-foreground font-medium">{category}</span>
                  <span className="text-micro uppercase text-muted-foreground">
                    {features.filter((f) => f.category === category).length} features
                  </span>
                </button>

                {/* Features */}
                {(expandedCategory === category || expandedCategory === null) &&
                  features
                    .filter((f) => f.category === category)
                    .map((feature) => (
                      <div
                        key={feature.feature}
                        className="grid grid-cols-3 gap-4 p-4 border-b border-border items-center"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-body text-muted-foreground">{feature.feature}</span>
                          {feature.tooltip && (
                            <span className="text-micro uppercase font-medium px-1.5 py-0.5 rounded-full bg-secondary/10 text-secondary">
                              Unique
                            </span>
                          )}
                        </div>
                        <div>{renderValue(feature.stratum)}</div>
                        <div>{renderValue(feature.competitors[selectedCompetitor])}</div>
                      </div>
                    ))}
              </div>
            ))}
          </MktCard>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
