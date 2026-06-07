import type { MarketingSeedEntry } from './types';
import type { CaseStudiesPageContent } from '../../../src/api/cms';

const content_json: CaseStudiesPageContent = {
  stats: [
    { value: '$50M+', label: 'Ad Spend Optimized' },
    { value: '340%', label: 'Avg. ROAS Improvement' },
    { value: '10M+', label: 'Profiles Unified' },
    { value: '500+', label: 'Companies Trust Us' },
  ],
  studies: [
    {
      company: 'Luxe Commerce',
      industry: 'E-Commerce',
      logo: 'L',
      challenge: '340% increase in ROAS with Trust-Gated Automation',
      solution:
        'How a luxury fashion retailer transformed their ad performance by only executing when signal health was optimal.',
      results: [
        { metric: 'ROAS Increase', value: '340%' },
        { metric: 'CAC Reduction', value: '45%' },
        { metric: 'Time Saved', value: '20hrs/week' },
      ],
      quote:
        'Stratum AI changed how we think about automation. The trust gates give us confidence to scale aggressively.',
      quotee: 'Sarah Chen',
    },
    {
      company: 'FinServe Global',
      industry: 'Financial Services',
      logo: 'F',
      challenge: '67% reduction in wasted ad spend',
      solution:
        'A fintech unicorn used signal health monitoring to pause campaigns before they burned budget.',
      results: [
        { metric: 'Spend Saved', value: '$2.3M' },
        { metric: 'Lead Quality', value: '+89%' },
        { metric: 'Compliance Score', value: '100%' },
      ],
      quote:
        'The visibility into signal health helped us maintain compliance while scaling our acquisition campaigns.',
      quotee: 'Marcus Webb',
    },
    {
      company: 'HealthDirect',
      industry: 'Healthcare',
      logo: 'H',
      challenge: 'Unified 2M+ patient profiles across channels',
      solution:
        'How a healthcare network used CDP to create personalized patient journeys while maintaining HIPAA compliance.',
      results: [
        { metric: 'Profiles Unified', value: '2.3M' },
        { metric: 'Engagement Rate', value: '+156%' },
        { metric: 'Match Rate', value: '94%' },
      ],
      quote:
        'The identity resolution capabilities let us personalize without compromising patient privacy.',
      quotee: 'Dr. Lisa Park',
    },
    {
      company: 'LearnPath Academy',
      industry: 'Education',
      logo: 'L',
      challenge: '5x improvement in student acquisition efficiency',
      solution:
        'An online education platform used predictive churn analysis to optimize their enrollment funnels.',
      results: [
        { metric: 'Enrollment Rate', value: '+212%' },
        { metric: 'Churn Reduction', value: '38%' },
        { metric: 'LTV Increase', value: '+67%' },
      ],
      quote:
        'Predictive churn scoring helped us intervene early and keep students engaged throughout their journey.',
      quotee: 'James Liu',
    },
    {
      company: 'Metro Retail Group',
      industry: 'Retail',
      logo: 'M',
      challenge: 'Synced 500K customer segments to 4 ad platforms',
      solution:
        'A national retail chain used Audience Sync to maintain consistent targeting across all digital channels.',
      results: [
        { metric: 'Segments Synced', value: '127' },
        { metric: 'Audience Size', value: '500K+' },
        { metric: 'Attribution Accuracy', value: '+73%' },
      ],
      quote:
        'One-click audience sync eliminated hours of manual work and kept our targeting fresh across platforms.',
      quotee: 'Amanda Torres',
    },
    {
      company: 'CloudStack Pro',
      industry: 'B2B SaaS',
      logo: 'C',
      challenge: 'Reduced sales cycle by 40% with predictive scoring',
      solution:
        'An enterprise SaaS company used ML-powered lead scoring to prioritize high-intent accounts.',
      results: [
        { metric: 'Sales Cycle', value: '-40%' },
        { metric: 'Win Rate', value: '+52%' },
        { metric: 'Pipeline Value', value: '+$4.2M' },
      ],
      quote:
        'The predictive models surfaced accounts we would have missed. It changed how our sales team prioritizes.',
      quotee: 'Robert Chang',
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'case-studies',
  title: 'Case Studies',
  template: 'case-studies',
  meta_title: 'Case Studies — Success Stories from Industry Leaders',
  meta_description:
    'Discover how companies across industries use Stratum AI to transform their marketing performance with trust-gated automation.',
  content_json,
};

export default entry;
