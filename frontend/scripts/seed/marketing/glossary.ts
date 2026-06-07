import type { MarketingSeedEntry } from './types';
import type { GlossaryPageContent } from '../../../src/api/cms';

const content_json: GlossaryPageContent = {
  categories: [
    {
      id: 'trust-engine',
      name: 'Trust Engine',
      iconName: 'ShieldCheckIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'Signal Health',
          definition:
            'Composite score (0-100) measuring the reliability and quality of incoming data signals.',
        },
        {
          term: 'Trust Gate',
          definition:
            'Decision checkpoint that evaluates whether automation should execute based on signal health thresholds.',
        },
        {
          term: 'Autopilot',
          definition:
            'Automated actions that execute when trust gates pass. Includes budget adjustments, campaign pausing, and optimization.',
        },
        {
          term: 'HEALTHY_THRESHOLD',
          definition:
            'Minimum signal health score (70.0) required for autopilot to execute automatically.',
        },
        {
          term: 'EMQ (Event Match Quality)',
          definition:
            'Score measuring how well conversion events match platform requirements for attribution.',
        },
      ],
    },
    {
      id: 'cdp',
      name: 'CDP (Customer Data Platform)',
      iconName: 'UserGroupIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'Profile',
          definition:
            'Unified customer record combining all known identifiers, traits, and event history.',
        },
        {
          term: 'Lifecycle Stage',
          definition: 'Customer journey stage based on behavior and purchase history.',
        },
        {
          term: 'Identity Resolution',
          definition:
            'Process of merging multiple identifiers into a single customer profile across devices and channels.',
        },
        {
          term: 'Segment',
          definition:
            'Dynamic or static group of profiles based on traits, behaviors, or computed attributes.',
        },
        {
          term: 'Computed Trait',
          definition: 'Derived attribute calculated from profile events and properties.',
        },
        {
          term: 'RFM Analysis',
          definition:
            'Recency, Frequency, Monetary scoring model for customer value segmentation.',
        },
        {
          term: 'Consent Type',
          definition: 'User permission categories for data processing compliance.',
        },
      ],
    },
    {
      id: 'audience-sync',
      name: 'Audience Sync',
      iconName: 'ArrowPathIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'Platform Audience',
          definition:
            'Audience created on ad platform (Meta, Google, TikTok, Snapchat) from CDP segment.',
        },
        {
          term: 'Sync Status',
          definition: 'Current state of audience synchronization job.',
        },
        {
          term: 'Match Rate',
          definition:
            'Percentage of hashed identifiers that the ad platform successfully matched to users (0-100%).',
        },
        {
          term: 'Sync Operation',
          definition: 'Type of sync action being performed.',
        },
        {
          term: 'Auto-Sync Interval',
          definition:
            'Frequency of automatic audience updates. Range: 1 hour to 1 week. Default: 24 hours.',
        },
      ],
    },
    {
      id: 'capi',
      name: 'CAPI (Conversions API)',
      iconName: 'BoltIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'Conversions API',
          definition:
            'Server-to-server connection sending conversion events directly to ad platforms, bypassing browser limitations.',
        },
        {
          term: 'PII Hashing',
          definition:
            'SHA256 one-way hashing of personally identifiable information (email, phone) before sending to platforms.',
        },
        {
          term: 'Delivery Status',
          definition: 'Result of sending event to platform.',
        },
        {
          term: 'Dead Letter Queue (DLQ)',
          definition:
            'Storage for failed events awaiting retry. Events are retained for 7 days by default.',
        },
        {
          term: 'Event Deduplication',
          definition:
            'Prevention of duplicate event processing using event IDs. Default TTL: 24 hours.',
        },
        {
          term: 'EMQ Score Components',
          definition: 'Breakdown of Event Match Quality scoring (total 100 points).',
        },
      ],
    },
    {
      id: 'analytics',
      name: 'Analytics & Metrics',
      iconName: 'ChartBarIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'ROAS',
          definition:
            'Return on Ad Spend. Revenue divided by ad spend. A ROAS of 3.0 means $3 revenue per $1 spent.',
        },
        {
          term: 'CPA',
          definition: 'Cost Per Acquisition. Total spend divided by number of conversions.',
        },
        {
          term: 'CAC',
          definition:
            'Customer Acquisition Cost. Total marketing spend divided by new customers acquired.',
        },
        {
          term: 'LTV',
          definition:
            'Lifetime Value. Predicted total revenue a customer will generate over their relationship.',
        },
        {
          term: 'CVR',
          definition: 'Conversion Rate. Percentage of clicks that result in conversions.',
        },
        {
          term: 'CTR',
          definition: 'Click-Through Rate. Percentage of impressions that result in clicks.',
        },
        {
          term: 'CPM',
          definition:
            'Cost Per Mille (thousand impressions). Spend divided by impressions, multiplied by 1000.',
        },
        {
          term: 'Frequency',
          definition:
            'Average number of times each user sees your ad. High frequency can indicate ad fatigue.',
        },
        {
          term: 'Creative Fatigue',
          definition:
            'Decline in performance as audiences see the same creative repeatedly.',
        },
      ],
    },
    {
      id: 'pacing',
      name: 'Pacing & Forecasting',
      iconName: 'SignalIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'Pacing',
          definition:
            'Comparison of actual spend/performance vs. target for the period. Expressed as percentage.',
        },
        {
          term: 'Target Period',
          definition: 'Time frame for pacing targets.',
        },
        {
          term: 'Pacing Alerts',
          definition: 'Notifications when spend or performance deviates from targets.',
        },
        {
          term: 'Scaling Actions',
          definition: 'Recommended actions based on campaign performance score.',
        },
      ],
    },
    {
      id: 'crm',
      name: 'CRM Integration',
      iconName: 'CurrencyDollarIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'Writeback',
          definition:
            'Syncing Stratum AI data (ad performance, attribution) back to CRM records.',
        },
        {
          term: 'Identity Matching',
          definition:
            'Linking CRM contacts to ad platform audiences using email/phone matching.',
        },
        {
          term: 'Pipeline ROAS',
          definition:
            'Return on ad spend calculated using CRM pipeline value instead of just revenue.',
        },
        {
          term: 'Deal Stages',
          definition: 'CRM pipeline stages for tracking sales progression.',
        },
        {
          term: 'Attribution Model',
          definition: 'Method for assigning conversion credit to marketing touchpoints.',
        },
      ],
    },
    {
      id: 'experiments',
      name: 'A/B Testing & Experiments',
      iconName: 'BeakerIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'Experiment Status',
          definition: 'Current state of an A/B test or experiment.',
        },
        {
          term: 'Statistical Significance',
          definition:
            'Confidence level that results are not due to random chance. Typically 95% threshold.',
        },
        {
          term: 'Control/Variant',
          definition:
            'Control is the baseline (original), Variant is the test version being compared.',
        },
      ],
    },
    {
      id: 'system',
      name: 'System & Configuration',
      iconName: 'Cog6ToothIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'Service Status',
          definition: 'Operational state of platform services.',
        },
        {
          term: 'Alert Severity',
          definition: 'Priority level for system and performance alerts.',
        },
        {
          term: 'Data Freshness',
          definition:
            'How recently data was last updated. Stale data (>48 hours) may impact accuracy.',
        },
        {
          term: 'Webhook',
          definition: 'HTTP callback that sends real-time notifications when events occur.',
        },
      ],
    },
    {
      id: 'platforms',
      name: 'Ad Platforms',
      iconName: 'CpuChipIcon',
      color: '#FF5A1F',
      terms: [
        {
          term: 'Supported Platforms',
          definition: 'Ad networks integrated with Stratum AI.',
        },
        {
          term: 'Entity Hierarchy',
          definition: 'Structural levels within ad platforms.',
        },
        {
          term: 'Conversion Window',
          definition:
            'Time period after click/view during which conversions are attributed.',
        },
        {
          term: 'Custom Audience',
          definition:
            'Platform audience created from your customer data (email, phone lists).',
        },
        {
          term: 'Lookalike/Similar Audience',
          definition:
            'Platform-generated audience of users similar to your custom audience.',
        },
      ],
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'glossary',
  title: 'Glossary',
  template: 'glossary',
  meta_title: 'Platform Terminology',
  meta_description:
    'Complete reference of terms, metrics, and values used across Stratum AI.',
  content_json,
};

export default entry;
