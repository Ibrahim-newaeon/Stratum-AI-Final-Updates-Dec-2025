import type { MarketingSeedEntry } from './types';
import type { SolutionPageContent } from '../../../src/api/cms';

const content_json: SolutionPageContent = {
  hero: {
    badge: 'Audience Sync',
    title: 'Sync audiences to',
    titleHighlight: 'every ad platform',
    description:
      'Push your CDP segments to Meta, Google, TikTok, and Snapchat with one click. Keep audiences fresh with automatic syncing.',
    ctaText: 'Start Free Trial',
    ctaLink: '/signup',
  },
  features: [
    {
      iconName: 'BoltIcon',
      title: 'One-Click Sync',
      description: 'Push segments to any platform instantly. No engineering required.',
    },
    {
      iconName: 'ClockIcon',
      title: 'Auto-Refresh',
      description: 'Configurable sync intervals keep your audiences fresh 24/7.',
    },
    {
      iconName: 'ChartBarIcon',
      title: 'Match Rate Tracking',
      description: 'Monitor match rates and optimize identifier coverage.',
    },
    {
      iconName: 'ShieldCheckIcon',
      title: 'Privacy-Safe',
      description: 'Hashed identifiers ensure PII never leaves your control.',
    },
    {
      iconName: 'CloudArrowUpIcon',
      title: 'Flexible Export',
      description: 'Export as CSV or JSON with custom attributes anytime.',
    },
    {
      iconName: 'ArrowPathIcon',
      title: 'Sync History',
      description: 'Full audit trail of all sync operations and metrics.',
    },
  ],
  steps: [
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
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'solutions-audience-sync',
  title: 'Audience Sync',
  template: 'solution',
  meta_title: 'Audience Sync — Stratum AI',
  meta_description:
    'Sync CDP segments to Meta, Google, TikTok, and Snapchat in real-time. Unified audience management across all ad platforms.',
  content_json,
};

export default entry;
