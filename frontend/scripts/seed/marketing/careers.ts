import type { MarketingSeedEntry } from './types';
import type { CareersPageContent } from '../../../src/api/cms';

const content_json: CareersPageContent = {
  positions: [
    {
      title: 'Senior Backend Engineer',
      department: 'Engineering',
      location: 'Remote (US/EU)',
      type: 'Full-time',
      salary: '$180K - $220K',
      description: 'Build and scale the core trust-gated automation platform and APIs.',
    },
    {
      title: 'Senior Frontend Engineer',
      department: 'Engineering',
      location: 'Remote (US/EU)',
      type: 'Full-time',
      salary: '$170K - $210K',
      description: 'Craft the data-dense dashboard and marketing experiences in React and TypeScript.',
    },
    {
      title: 'ML Engineer',
      department: 'Engineering',
      location: 'Remote (US/EU)',
      type: 'Full-time',
      salary: '$190K - $240K',
      description: 'Develop the models behind signal health scoring and predictive analytics.',
    },
    {
      title: 'Product Manager',
      department: 'Product',
      location: 'San Francisco, CA',
      type: 'Full-time',
      salary: '$160K - $200K',
      description: 'Own the roadmap for revenue intelligence and trust-gated automation features.',
    },
    {
      title: 'Account Executive',
      department: 'Sales',
      location: 'New York, NY',
      type: 'Full-time',
      salary: '$120K - $150K + Commission',
      description: 'Drive new business with growth teams and marketing agencies.',
    },
    {
      title: 'Customer Success Manager',
      department: 'Customer Success',
      location: 'Remote (US)',
      type: 'Full-time',
      salary: '$100K - $130K',
      description: 'Partner with customers to ensure adoption and long-term success on Stratum AI.',
    },
  ],
  benefits: [
    { title: 'Competitive salary + equity', description: '', iconName: 'SparklesIcon' },
    { title: 'Unlimited PTO', description: '', iconName: 'SparklesIcon' },
    { title: 'Remote-first culture', description: '', iconName: 'SparklesIcon' },
    { title: 'Health, dental & vision', description: '', iconName: 'SparklesIcon' },
    { title: '401(k) matching', description: '', iconName: 'SparklesIcon' },
    { title: 'Learning & development budget', description: '', iconName: 'SparklesIcon' },
    { title: 'Home office stipend', description: '', iconName: 'SparklesIcon' },
    { title: 'Annual team retreats', description: '', iconName: 'SparklesIcon' },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'careers',
  title: 'Careers',
  template: 'careers',
  meta_title: 'Careers',
  meta_description:
    'Join the Stratum AI team. Help build the future of trust-gated marketing automation.',
  content_json,
};

export default entry;
