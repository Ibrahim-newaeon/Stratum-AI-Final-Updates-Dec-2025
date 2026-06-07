import type { MarketingSeedEntry } from './types';
import type { ChangelogPageContent } from '../../../src/api/cms';

const content_json: ChangelogPageContent = {
  releases: [
    {
      version: '3.2.0',
      date: 'January 15, 2026',
      type: 'major',
      highlights: [
        'New 2026 Dashboard Theme with OLED-optimized dark mode',
        'Enhanced Trust Engine with predictive signal analysis',
        'Multi-platform Audience Sync now supports 4 ad platforms',
      ],
      changes: [
        { type: 'feature', text: 'Added electric neon color palette for 2026 theme' },
        { type: 'feature', text: 'New glassmorphism effects with enhanced blur' },
        { type: 'feature', text: 'Animation harmony system with 3 timing layers' },
        { type: 'improvement', text: 'Improved CDP profile loading performance by 40%' },
        { type: 'improvement', text: 'Enhanced Trust Gate evaluation speed' },
        { type: 'fix', text: 'Fixed segment preview count accuracy' },
        { type: 'fix', text: 'Resolved timezone issues in event tracking' },
      ],
    },
    {
      version: '3.1.0',
      date: 'December 20, 2025',
      type: 'minor',
      highlights: [
        'Predictive Churn Analysis in CDP',
        'Computed Traits for advanced segmentation',
        'RFM Analysis dashboard',
      ],
      changes: [
        { type: 'feature', text: 'Predictive churn scoring with ML models' },
        { type: 'feature', text: 'Custom computed traits with formula builder' },
        { type: 'feature', text: 'RFM (Recency, Frequency, Monetary) analysis' },
        { type: 'feature', text: 'Funnel analysis with conversion tracking' },
        { type: 'improvement', text: 'Segment builder now supports nested conditions' },
        { type: 'fix', text: 'Fixed identity merge conflicts' },
      ],
    },
    {
      version: '3.0.0',
      date: 'November 1, 2025',
      type: 'major',
      highlights: [
        'Complete CDP (Customer Data Platform) launch',
        'Audience Sync to Meta, Google, TikTok, Snapchat',
        'Identity Graph visualization',
      ],
      changes: [
        { type: 'feature', text: 'Full CDP with unified customer profiles' },
        { type: 'feature', text: 'Real-time event ingestion and processing' },
        { type: 'feature', text: 'Cross-device identity resolution' },
        { type: 'feature', text: 'One-click audience sync to ad platforms' },
        { type: 'security', text: 'Enhanced encryption for PII data' },
        { type: 'improvement', text: 'New onboarding flow for faster setup' },
      ],
    },
    {
      version: '2.5.0',
      date: 'September 15, 2025',
      type: 'minor',
      highlights: [
        'Custom Autopilot Rules builder',
        'A/B Testing framework',
        'Enhanced reporting exports',
      ],
      changes: [
        { type: 'feature', text: 'Visual rule builder for custom automations' },
        { type: 'feature', text: 'Built-in A/B testing with statistical analysis' },
        { type: 'feature', text: 'Scheduled report exports in PDF/CSV' },
        { type: 'improvement', text: 'Campaign performance insights' },
        { type: 'fix', text: 'Fixed duplicate webhook deliveries' },
      ],
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'changelog',
  title: 'Changelog',
  template: 'changelog',
  meta_title: "Changelog — What's New in Stratum AI",
  meta_description:
    'Stay up to date with the latest features, improvements, and fixes.',
  content_json,
};

export default entry;
