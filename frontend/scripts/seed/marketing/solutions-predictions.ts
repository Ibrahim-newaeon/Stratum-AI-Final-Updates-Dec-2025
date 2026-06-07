import type { MarketingSeedEntry } from './types';
import type { SolutionPageContent } from '../../../src/api/cms';

const content_json: SolutionPageContent = {
  hero: {
    badge: 'ML Predictions',
    title: 'Predict the future,',
    titleHighlight: 'act today',
    description:
      'Machine learning models trained on your data deliver actionable predictions for churn, LTV, revenue, and optimal customer actions.',
    ctaText: 'Start Free Trial',
    ctaLink: '/signup',
  },
  features: [
    {
      iconName: 'UserMinusIcon',
      title: 'Churn Prediction',
      description:
        'Identify at-risk customers before they leave. Get actionable retention recommendations.',
    },
    {
      iconName: 'CurrencyDollarIcon',
      title: 'LTV Forecasting',
      description:
        'Predict customer lifetime value at acquisition. Optimize acquisition spend accordingly.',
    },
    {
      iconName: 'ArrowTrendingUpIcon',
      title: 'Revenue Forecasting',
      description: 'Accurate revenue predictions based on historical patterns and market signals.',
    },
    {
      iconName: 'LightBulbIcon',
      title: 'Next-Best-Action',
      description: 'AI-powered recommendations for the optimal next engagement for each customer.',
    },
  ],
  steps: [
    { step: 1, title: 'Connect Data', description: 'Link your customer and event data' },
    { step: 2, title: 'Train Models', description: 'ML models learn from your patterns' },
    { step: 3, title: 'Get Predictions', description: 'Real-time scores for every customer' },
    { step: 4, title: 'Take Action', description: 'Automated workflows based on predictions' },
  ],
};

const entry: MarketingSeedEntry = {
  slug: 'solutions-predictions',
  title: 'Predictive Analytics',
  template: 'solution',
  meta_title: 'Predictive Analytics — Stratum AI',
  meta_description:
    'ML-powered predictions for ROAS, churn risk, and budget optimization. Make data-driven decisions with confidence.',
  content_json,
};

export default entry;
