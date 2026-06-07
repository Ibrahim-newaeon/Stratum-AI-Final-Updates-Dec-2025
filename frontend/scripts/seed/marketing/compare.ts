import type { MarketingSeedEntry } from './types';
import type { ComparisonPageContent } from '../../../src/api/cms';

const content_json: ComparisonPageContent = {
  differentiators: [
    {
      title: 'Trust-Gated Automation',
      description:
        'Only execute when signal health passes safety thresholds. No other platform offers this level of automation confidence.',
      iconName: 'ShieldCheckIcon',
    },
    {
      title: 'Identity Graph Visualization',
      description:
        'See exactly how customer identities are connected across devices and channels with interactive visualizations.',
      iconName: 'CpuChipIcon',
    },
    {
      title: 'RFM Analysis Built-in',
      description:
        'Native Recency, Frequency, Monetary analysis without additional tools or integrations.',
      iconName: 'ChartBarIcon',
    },
    {
      title: 'Signal Health Monitoring',
      description:
        'Real-time monitoring of data quality and signal reliability across all your integrations.',
      iconName: 'BoltIcon',
    },
  ],
  competitors: [
    { id: 'segment', name: 'Segment', tagline: 'CDP', color: '#52BD95' },
    { id: 'braze', name: 'Braze', tagline: 'Marketing Automation', color: '#F6C94A' },
    { id: 'mparticle', name: 'mParticle', tagline: 'CDP', color: '#E54D42' },
    { id: 'amplitude', name: 'Amplitude', tagline: 'Analytics', color: '#1E61CD' },
  ],
  features: [
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
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'compare',
  title: 'Compare',
  template: 'comparison',
  meta_title: 'Compare — How Stratum AI Compares',
  meta_description:
    'See how Stratum AI stacks up against other marketing platforms. Trust-gated automation is our unique differentiator.',
  content_json,
};

export default entry;
