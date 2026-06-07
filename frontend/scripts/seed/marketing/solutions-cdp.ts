import type { MarketingSeedEntry } from './types';
import type { SolutionPageContent } from '../../../src/api/cms';

const content_json: SolutionPageContent = {
  hero: {
    badge: 'Customer Data Platform',
    title: 'Turn customer data',
    titleHighlight: 'into revenue',
    description:
      'Unify customer profiles across every touchpoint. Build powerful segments and sync them to all your ad platforms instantly.',
    ctaText: 'Start Free Trial',
    ctaLink: '/signup',
  },
  stats: [
    { value: '2.5M+', label: 'Profiles Unified', description: 'Customer profiles unified across sources.' },
    { value: '47%', label: 'Higher Match Rate', description: 'Improvement in audience match rate.' },
    { value: '3.2x', label: 'ROAS Improvement', description: 'Average return on ad spend lift.' },
    { value: '<100ms', label: 'Sync Latency', description: 'Time to push segments to platforms.' },
  ],
  features: [
    {
      iconName: 'UserGroupIcon',
      title: '360° Customer Profiles',
      description:
        'Unified view from anonymous visitor to loyal customer. Real-time enrichment from every interaction.',
    },
    {
      iconName: 'CubeTransparentIcon',
      title: 'Identity Resolution',
      description:
        'Connect the dots across devices and channels. Visual identity graph shows every connection.',
    },
    {
      iconName: 'ChartBarIcon',
      title: 'Smart Segmentation',
      description:
        'Build segments with behavioral rules, RFM scores, and lifecycle stages. Preview before you publish.',
    },
    {
      iconName: 'ArrowPathIcon',
      title: 'Multi-Platform Sync',
      description:
        'Push segments to Meta, Google, TikTok & Snapchat instantly. Auto-sync keeps your audiences fresh.',
    },
    {
      iconName: 'SparklesIcon',
      title: 'Predictive Analytics',
      description:
        'Churn prediction, LTV forecasting, and next-best-action recommendations powered by ML.',
    },
    {
      iconName: 'ShieldCheckIcon',
      title: 'Privacy-First',
      description:
        'Consent management, GDPR/CCPA compliance, and hashed PII for secure platform sync.',
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'solutions-cdp',
  title: 'Customer Data Platform',
  template: 'solution',
  meta_title: 'Customer Data Platform — Stratum AI',
  meta_description:
    'Unify customer profiles across every touchpoint. Build powerful segments and sync them to all your ad platforms instantly.',
  content_json,
};

export default entry;
