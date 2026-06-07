import type { MarketingSeedEntry } from './types';
import type { StatusPageContent } from '../../../src/api/cms';

const content_json: StatusPageContent = {
  services: [
    { name: 'API Gateway', status: 'operational', uptime: '99.99%', latency: '45ms' },
    { name: 'Dashboard', status: 'operational', uptime: '99.98%', latency: '120ms' },
    { name: 'Trust Engine', status: 'operational', uptime: '99.99%', latency: '85ms' },
    { name: 'CDP Pipeline', status: 'operational', uptime: '99.97%', latency: '150ms' },
    { name: 'Audience Sync', status: 'operational', uptime: '99.95%', latency: '200ms' },
    { name: 'Webhooks', status: 'operational', uptime: '99.98%', latency: '65ms' },
  ],
  incidents: [
    {
      title: 'Elevated API Latency',
      date: 'January 18, 2026 - 14:23 UTC',
      severity: 'minor',
      status: 'resolved',
      updates: [
        { time: '15:45', message: 'Issue resolved. All systems operating normally.' },
        { time: '15:10', message: 'Fix deployed. Monitoring for stability.' },
        {
          time: '14:35',
          message: 'Root cause identified as database connection pool saturation.',
        },
        { time: '14:23', message: 'Investigating elevated API response times.' },
      ],
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'status',
  title: 'System Status',
  template: 'status',
  meta_title: 'Stratum AI System Status',
  meta_description:
    'Real-time status and uptime monitoring for all Stratum AI services.',
  content_json,
};

export default entry;
