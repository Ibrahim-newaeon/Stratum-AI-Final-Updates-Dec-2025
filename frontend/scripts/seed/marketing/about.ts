import type { MarketingSeedEntry } from './types';
import type { AboutPageContent } from '../../../src/api/cms';

const content_json: AboutPageContent = {
  mission:
    "We're on a mission to help growth teams make smarter decisions with AI-powered intelligence and trust-gated automation.",
  team: [
    { name: 'Sarah Chen', role: 'CEO & Co-Founder', image: 'SC' },
    { name: 'Marcus Rodriguez', role: 'CTO & Co-Founder', image: 'MR' },
    { name: 'Emily Watson', role: 'VP of Product', image: 'EW' },
    { name: 'David Kim', role: 'VP of Engineering', image: 'DK' },
    { name: 'Lisa Thompson', role: 'VP of Sales', image: 'LT' },
    { name: 'James Park', role: 'VP of Customer Success', image: 'JP' },
  ],
  values: [
    {
      title: 'Trust First',
      description:
        'We build systems that earn and maintain trust through transparency and reliability.',
    },
    {
      title: 'Customer Obsessed',
      description: 'Every decision starts with how it impacts our customers success.',
    },
    {
      title: 'Data Driven',
      description: 'We practice what we preach - decisions backed by evidence, not assumptions.',
    },
    {
      title: 'Move Fast, Stay Safe',
      description: 'Speed matters, but not at the cost of quality or security.',
    },
  ],
  stats: [
    { value: '150+', label: 'Growth Teams' },
    { value: '$2B+', label: 'Ad Spend Managed' },
    { value: '50+', label: 'Integrations' },
    { value: '99.9%', label: 'Uptime' },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'about',
  title: 'About Us',
  template: 'about',
  meta_title: 'About Us',
  meta_description:
    "We're on a mission to help growth teams make smarter decisions with AI-powered intelligence and trust-gated automation.",
  content_json,
};

export default entry;
