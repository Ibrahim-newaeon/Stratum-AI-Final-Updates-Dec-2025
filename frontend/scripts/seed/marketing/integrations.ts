import type { MarketingSeedEntry } from './types';
import type { IntegrationsPageContent } from '../../../src/api/cms';

const content_json: IntegrationsPageContent = {
  categories: [
    {
      name: 'Ad Platforms',
      description: 'Connect your advertising accounts across every major channel.',
      platforms: [
        {
          name: 'Meta Ads',
          description: 'Facebook & Instagram advertising',
          iconName: 'M',
          color: 'primary',
        },
        {
          name: 'Google Ads',
          description: 'Search, Display & YouTube',
          iconName: 'G',
          color: 'primary',
        },
        {
          name: 'TikTok Ads',
          description: 'TikTok advertising platform',
          iconName: 'T',
          color: 'primary',
        },
        {
          name: 'Snapchat Ads',
          description: 'Snapchat marketing API',
          iconName: 'S',
          color: 'primary',
        },
        {
          name: 'LinkedIn Ads',
          description: 'B2B advertising',
          iconName: 'L',
          color: 'primary',
        },
        {
          name: 'Twitter/X Ads',
          description: 'Twitter advertising',
          iconName: 'X',
          color: 'primary',
        },
      ],
    },
    {
      name: 'Analytics & Attribution',
      description: 'Unify analytics and attribution data from your stack.',
      platforms: [
        {
          name: 'Google Analytics',
          description: 'Web analytics',
          iconName: 'GA',
          color: 'primary',
        },
        {
          name: 'Mixpanel',
          description: 'Product analytics',
          iconName: 'MP',
          color: 'primary',
        },
        {
          name: 'Amplitude',
          description: 'Digital analytics',
          iconName: 'A',
          color: 'primary',
        },
        {
          name: 'Segment',
          description: 'Customer data platform',
          iconName: 'SG',
          color: 'primary',
        },
      ],
    },
    {
      name: 'CRM & Sales',
      description: 'Sync contacts and pipeline data with your CRM.',
      platforms: [
        {
          name: 'Salesforce',
          description: 'CRM platform',
          iconName: 'SF',
          color: 'primary',
        },
        {
          name: 'HubSpot',
          description: 'Marketing & sales',
          iconName: 'HS',
          color: 'primary',
        },
        {
          name: 'Pipedrive',
          description: 'Sales CRM',
          iconName: 'PD',
          color: 'primary',
        },
      ],
    },
    {
      name: 'E-commerce',
      description: 'Pull orders and revenue from your storefront.',
      platforms: [
        {
          name: 'Shopify',
          description: 'E-commerce platform',
          iconName: 'SH',
          color: 'primary',
        },
        {
          name: 'WooCommerce',
          description: 'WordPress commerce',
          iconName: 'WC',
          color: 'primary',
        },
        {
          name: 'Magento',
          description: 'Adobe Commerce',
          iconName: 'MG',
          color: 'primary',
        },
      ],
    },
    {
      name: 'Communication',
      description: 'Route alerts and customer messages where your team works.',
      platforms: [
        {
          name: 'Slack',
          description: 'Team messaging',
          iconName: 'SL',
          color: 'primary',
        },
        {
          name: 'WhatsApp Business',
          description: 'Customer messaging',
          iconName: 'WA',
          color: 'primary',
        },
        {
          name: 'Intercom',
          description: 'Customer messaging',
          iconName: 'IC',
          color: 'primary',
        },
      ],
    },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'integrations',
  title: 'Integrations',
  template: 'integrations',
  meta_title: 'Integrations',
  meta_description:
    'Connect Stratum AI with Meta, Google, TikTok, Snapchat, and 30+ marketing platforms. Unified data, one dashboard.',
  content_json,
};

export default entry;
