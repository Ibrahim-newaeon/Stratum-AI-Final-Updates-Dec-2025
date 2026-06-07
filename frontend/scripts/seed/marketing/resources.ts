import type { MarketingSeedEntry } from './types';
import type { ResourcesPageContent } from '../../../src/api/cms';

const content_json: ResourcesPageContent = {
  guides: [
    {
      title: 'Complete Guide to Trust-Gated Automation',
      description:
        'Learn how to set up and optimize trust gates for maximum performance.',
      iconName: 'BookOpenIcon',
      href: '#',
      tag: 'Guide',
    },
    {
      title: 'CDP Implementation Playbook',
      description:
        'Step-by-step guide to implementing your Customer Data Platform.',
      iconName: 'BookOpenIcon',
      href: '#',
      tag: 'Playbook',
    },
    {
      title: 'Signal Health Optimization',
      description: 'Best practices for maintaining healthy signal scores.',
      iconName: 'BookOpenIcon',
      href: '#',
      tag: 'Guide',
    },
    {
      title: 'Multi-Platform Audience Sync Setup',
      description:
        'Configure audience sync across Meta, Google, TikTok, and Snapchat.',
      iconName: 'BookOpenIcon',
      href: '#',
      tag: 'Tutorial',
    },
  ],
  webinars: [
    {
      title: 'Mastering Trust-Gated Automation in 2026',
      description: 'Sarah Chen, VP of Growth; Mike Rodriguez, Product Lead.',
      date: 'February 15, 2026',
      status: 'upcoming',
      href: '#',
    },
    {
      title: 'CDP Best Practices for E-Commerce',
      description: 'Lisa Park, CDO; James Liu, Head of Growth.',
      date: 'January 28, 2026',
      status: 'on-demand',
      href: '#',
    },
    {
      title: 'Predictive Analytics for Marketing Teams',
      description: 'Dr. Alex Kim, ML Engineer.',
      date: 'January 10, 2026',
      status: 'on-demand',
      href: '#',
    },
  ],
  whitepapers: [
    {
      title: 'The State of Marketing Automation 2026',
      description: 'Industry report on automation trends and best practices.',
      pages: 42,
      href: '#',
    },
    {
      title: 'Signal Health: A New Framework for Ad Optimization',
      description: 'Technical whitepaper on our signal health methodology.',
      pages: 28,
      href: '#',
    },
    {
      title: 'Privacy-First Customer Data Strategies',
      description:
        'How to build effective CDP strategies in a privacy-focused world.',
      pages: 35,
      href: '#',
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'resources',
  title: 'Resource Hub',
  template: 'resources',
  meta_title: 'Learn, grow, and succeed',
  meta_description:
    'Everything you need to master trust-gated automation and transform your marketing performance.',
  content_json,
};

export default entry;
