import type { MarketingSeedEntry } from './types';
import type { FeaturesPageContent } from '../../../src/api/cms';

const content_json: FeaturesPageContent = {
  features: [
    {
      iconName: 'ShieldCheckIcon',
      title: 'Trust-Gated Autopilot',
      description:
        'Automations only execute when signal health passes safety thresholds. No more blind optimization.',
      color: 'primary',
    },
    {
      iconName: 'SignalIcon',
      title: 'Signal Health Monitoring',
      description:
        'Real-time monitoring of data quality across all connected platforms with instant anomaly detection.',
      color: 'primary',
    },
    {
      iconName: 'UserGroupIcon',
      title: 'Customer Data Platform',
      description:
        'Unified customer profiles with identity resolution, behavioral segmentation, and lifecycle tracking.',
      color: 'primary',
    },
    {
      iconName: 'ArrowPathIcon',
      title: 'Multi-Platform Audience Sync',
      description:
        'Push segments to Meta, Google, TikTok & Snapchat with one click. Auto-sync keeps audiences fresh.',
      color: 'primary',
    },
    {
      iconName: 'ChartBarIcon',
      title: 'Advanced Attribution',
      description:
        'Multi-touch attribution models with conversion path analysis and incrementality testing.',
      color: 'primary',
    },
    {
      iconName: 'CpuChipIcon',
      title: 'ML-Powered Predictions',
      description:
        'Churn prediction, LTV forecasting, and next-best-action recommendations powered by machine learning.',
      color: 'primary',
    },
    {
      iconName: 'BoltIcon',
      title: 'Real-Time Event Processing',
      description:
        'Process millions of events per second with sub-second latency for instant personalization.',
      color: 'primary',
    },
    {
      iconName: 'ChartPieIcon',
      title: 'RFM Analysis',
      description:
        'Built-in Recency, Frequency, Monetary analysis for customer value segmentation.',
      color: 'primary',
    },
    {
      iconName: 'CloudArrowUpIcon',
      title: 'Flexible Data Export',
      description:
        'Export audiences as CSV or JSON with custom traits, events, and computed attributes.',
      color: 'primary',
    },
    {
      iconName: 'DocumentChartBarIcon',
      title: 'Custom Reporting',
      description:
        'Build custom reports and dashboards with drag-and-drop widgets and scheduled exports.',
      color: 'primary',
    },
    {
      iconName: 'CubeTransparentIcon',
      title: 'Identity Graph',
      description:
        'Visual identity resolution showing cross-device connections and merge history.',
      color: 'primary',
    },
    {
      iconName: 'SparklesIcon',
      title: 'AI Campaign Optimization',
      description:
        'Automatic bid adjustments, budget allocation, and creative rotation based on performance.',
      color: 'primary',
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'features',
  title: 'Features',
  template: 'features',
  meta_title: 'Features',
  meta_description:
    'Explore Stratum AI features: Trust Engine, Signal Health monitoring, CDP with audience sync, predictive analytics, and more.',
  content_json,
};

export default entry;
