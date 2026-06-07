import type { MarketingSeedEntry } from './types';
import type { ApiDocsPageContent } from '../../../src/api/cms';

const content_json: ApiDocsPageContent = {
  sections: [
    {
      title: 'Getting Started',
      description: 'Learn the basics and set up your first integration.',
      iconName: 'BookOpenIcon',
      href: '#getting-started',
    },
    {
      title: 'API Reference',
      description: 'Complete reference for all API endpoints.',
      iconName: 'CodeBracketIcon',
      href: '#api-reference',
    },
    {
      title: 'SDKs & Libraries',
      description: 'Official SDKs for JavaScript, Python, and more.',
      iconName: 'CommandLineIcon',
      href: '#sdks',
    },
    {
      title: 'Webhooks',
      description: 'Real-time event notifications for your app.',
      iconName: 'CubeIcon',
      href: '#webhooks',
    },
  ],
  endpoints: [
    { method: 'GET', path: '/api/v1/signals', description: 'List all signals', category: 'Signals' },
    {
      method: 'POST',
      path: '/api/v1/signals',
      description: 'Create a new signal',
      category: 'Signals',
    },
    {
      method: 'GET',
      path: '/api/v1/signals/:id/health',
      description: 'Get signal health score',
      category: 'Signals',
    },
    {
      method: 'GET',
      path: '/api/v1/automations',
      description: 'List all automations',
      category: 'Automations',
    },
    {
      method: 'POST',
      path: '/api/v1/automations/execute',
      description: 'Execute automation',
      category: 'Automations',
    },
    {
      method: 'GET',
      path: '/api/v1/cdp/profiles',
      description: 'Search customer profiles',
      category: 'CDP',
    },
    {
      method: 'POST',
      path: '/api/v1/cdp/segments',
      description: 'Create a segment',
      category: 'CDP',
    },
    {
      method: 'POST',
      path: '/api/v1/audience-sync',
      description: 'Sync audience to platform',
      category: 'Audience Sync',
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'api-docs',
  title: 'API Reference',
  template: 'api-docs',
  meta_title: 'API Documentation',
  meta_description:
    'Build on the Stratum API — REST endpoints for signals, automations, the CDP, and audience sync, with SDKs and real-time webhooks.',
  content_json,
};

export default entry;
