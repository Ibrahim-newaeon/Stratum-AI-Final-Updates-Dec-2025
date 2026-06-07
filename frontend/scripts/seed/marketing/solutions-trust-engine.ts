import type { MarketingSeedEntry } from './types';
import type { SolutionPageContent } from '../../../src/api/cms';

const content_json: SolutionPageContent = {
  hero: {
    badge: 'Trust Engine',
    title: 'Automation with',
    titleHighlight: 'built-in safety',
    description:
      'The Trust Engine ensures automations only execute when your data is healthy. No more blind optimization based on bad signals.',
    ctaText: 'Start Free Trial',
    ctaLink: '/signup',
  },
  features: [
    {
      iconName: 'XCircleIcon',
      title: 'Prevent Bad Decisions',
      description: 'Never optimize on corrupted data',
    },
    {
      iconName: 'CheckCircleIcon',
      title: 'Reduce Manual Oversight',
      description: 'Automated safety checks 24/7',
    },
    {
      iconName: 'ShieldCheckIcon',
      title: 'Audit Trail',
      description: 'Full logging of all gate decisions',
    },
    {
      iconName: 'BoltIcon',
      title: 'Customizable Thresholds',
      description: 'Set your own risk tolerance',
    },
  ],
  steps: [
    { step: 1, title: 'Signal Health Check', description: 'Continuous monitoring of data quality' },
    { step: 2, title: 'Trust Gate', description: 'Pass / Hold / Block decision' },
    { step: 3, title: 'Automation Decision', description: 'Execute only when safe' },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'solutions-trust-engine',
  title: 'Trust Engine',
  template: 'solution',
  meta_title: 'Trust Engine — Stratum AI',
  meta_description:
    'Signal health monitoring and trust-gated automation. Ensure your automations only execute when data is reliable.',
  content_json,
};

export default entry;
