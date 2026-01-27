/**
 * Tier-Specific Landing Page Content Configuration
 * Contains all content, features, testimonials, and visual treatments for each subscription tier
 */

// ============================================================================
// Type Definitions
// ============================================================================

export type TierType = 'starter' | 'professional' | 'enterprise';

export interface TierVisuals {
  primaryColor: string;
  gradientFrom: string;
  gradientTo: string;
  accentColor: string;
  badgeText?: string;
  badgeColor?: string;
}

export interface TierMetric {
  label: string;
  value: string;
  description: string;
}

export interface TierHeroContent {
  tagline: string;
  headline: string;
  highlightedText: string;
  subheadline: string;
  description: string;
  primaryCta: string;
  secondaryCta: string;
  metrics: TierMetric[];
  trustBadges: string[];
}

export interface TierFeature {
  name: string;
  description: string;
  included: boolean;
  highlight?: boolean;
}

export interface TierFeatureCategory {
  name: string;
  icon: string;
  features: TierFeature[];
}

export interface TierPricing {
  price: string;
  period: string;
  adSpendLimit: string;
  accountLimit: string;
  savings?: string;
  nextTier?: {
    name: string;
    teaser: string;
    link: string;
  };
}

export interface TierTestimonial {
  quote: string;
  author: string;
  role: string;
  company: string;
  companySize: string;
  metric?: {
    label: string;
    value: string;
  };
}

export interface TierFAQ {
  question: string;
  answer: string;
}

export interface TierContent {
  id: TierType;
  name: string;
  visuals: TierVisuals;
  hero: TierHeroContent;
  featureCategories: TierFeatureCategory[];
  pricing: TierPricing;
  testimonials: TierTestimonial[];
  faqs: TierFAQ[];
}

// ============================================================================
// Starter Tier Content
// ============================================================================

const starterContent: TierContent = {
  id: 'starter',
  name: 'Starter',
  visuals: {
    primaryColor: 'cyan',
    gradientFrom: 'from-cyan-500',
    gradientTo: 'to-blue-500',
    accentColor: 'text-cyan-400',
  },
  hero: {
    tagline: 'Starter Plan',
    headline: 'Launch Your',
    highlightedText: 'Revenue Intelligence',
    subheadline: 'Perfect for teams starting their data-driven journey',
    description:
      'Get started with signal health monitoring, RFM customer analysis, and anomaly detection. Everything you need to understand your ad performance and make smarter decisions.',
    primaryCta: 'Start Free Trial',
    secondaryCta: 'Book Demo',
    metrics: [
      { label: 'Ad Accounts', value: '5', description: 'Connect up to 5 ad accounts' },
      { label: 'Monthly Spend', value: '$100K', description: 'Up to $100K monthly ad spend' },
      { label: 'Avg ROI Lift', value: '+18%', description: 'Average ROAS improvement' },
    ],
    trustBadges: ['14-day free trial', 'No credit card required', 'Cancel anytime'],
  },
  featureCategories: [
    {
      name: 'Signal Health',
      icon: 'shield',
      features: [
        {
          name: 'EMQ Signal Scoring',
          description: 'Real-time data quality scoring across platforms',
          included: true,
        },
        {
          name: 'Attribution Variance',
          description: 'Platform vs GA4 reconciliation with alerts',
          included: true,
        },
        {
          name: 'Freshness Monitoring',
          description: 'Know when your data is stale or delayed',
          included: true,
        },
        {
          name: 'Custom Health Rules',
          description: 'Create custom health evaluation rules',
          included: false,
        },
      ],
    },
    {
      name: 'Customer Intelligence',
      icon: 'users',
      features: [
        {
          name: 'RFM Analysis',
          description: 'Recency, Frequency, Monetary customer segmentation',
          included: true,
          highlight: true,
        },
        { name: 'Customer Profiles', description: 'Unified 360° customer view', included: true },
        {
          name: 'Lifecycle Stages',
          description: 'Track anonymous to loyal customer journey',
          included: true,
        },
        { name: 'Predictive Churn', description: 'AI-powered churn prediction', included: false },
      ],
    },
    {
      name: 'Anomaly Detection',
      icon: 'chart',
      features: [
        {
          name: 'Spend Anomalies',
          description: 'Detect unusual spend patterns',
          included: true,
          highlight: true,
        },
        {
          name: 'Performance Alerts',
          description: 'ROAS and conversion anomaly alerts',
          included: true,
        },
        { name: 'Slack Notifications', description: 'Real-time alerts in Slack', included: true },
        {
          name: 'Custom Alert Rules',
          description: 'Create custom anomaly detection rules',
          included: false,
        },
      ],
    },
    {
      name: 'Reporting',
      icon: 'document',
      features: [
        { name: 'Dashboard Exports', description: 'Export dashboard data as CSV', included: true },
        { name: 'Scheduled Reports', description: 'Weekly email summaries', included: true },
        {
          name: 'Custom Report Builder',
          description: 'Build custom reports with drag-and-drop',
          included: false,
        },
        {
          name: 'White-label Reports',
          description: 'Branded reports for clients',
          included: false,
        },
      ],
    },
  ],
  pricing: {
    price: '$499',
    period: '/month',
    adSpendLimit: 'Up to $100K monthly ad spend',
    accountLimit: '5 ad accounts',
    nextTier: {
      name: 'Professional',
      teaser: 'Need more accounts and advanced segmentation?',
      link: '/plans/professional',
    },
  },
  testimonials: [
    {
      quote:
        'Stratum helped us catch a $12K attribution gap we never knew existed. The signal health feature alone paid for the subscription in the first month.',
      author: 'Sarah Chen',
      role: 'Marketing Lead',
      company: 'GrowthBox',
      companySize: '15 employees',
      metric: { label: 'ROAS Improvement', value: '+23%' },
    },
    {
      quote:
        'Finally, a tool that tells me when NOT to trust my data. The anomaly alerts have saved us from making costly scaling mistakes multiple times.',
      author: 'Michael Torres',
      role: 'Founder',
      company: 'Bloom DTC',
      companySize: '8 employees',
      metric: { label: 'Waste Prevented', value: '$8K/mo' },
    },
  ],
  faqs: [
    {
      question: 'What happens when I hit the $100K ad spend limit?',
      answer:
        "We'll notify you when you're approaching the limit. You can upgrade to Professional at any time for higher limits. Your data and settings will transfer automatically.",
    },
    {
      question: 'Can I connect multiple ad platforms?',
      answer:
        'Yes! Starter includes connections to Meta, Google, TikTok, and Snapchat. The 5-account limit counts total accounts across all platforms.',
    },
    {
      question: 'Is there a contract or commitment?',
      answer:
        'No contracts. Starter is month-to-month billing. You can upgrade, downgrade, or cancel anytime with no penalties.',
    },
    {
      question: 'What support is included?',
      answer:
        'Starter includes email support with 48-hour response time, plus access to our knowledge base and community forum.',
    },
    {
      question: 'Can I try before I buy?',
      answer:
        'Absolutely! Every plan includes a 14-day free trial with full access to all Starter features. No credit card required to start.',
    },
  ],
};

// ============================================================================
// Professional Tier Content
// ============================================================================

const professionalContent: TierContent = {
  id: 'professional',
  name: 'Professional',
  visuals: {
    primaryColor: 'orange',
    gradientFrom: 'from-orange-500',
    gradientTo: 'to-amber-500',
    accentColor: 'text-orange-400',
    badgeText: 'Most Popular',
    badgeColor: 'bg-orange-500',
  },
  hero: {
    tagline: 'Professional Plan',
    headline: 'Scale With',
    highlightedText: 'Confidence',
    subheadline: 'The complete toolkit for growing marketing teams',
    description:
      'Everything in Starter plus funnel builder, segment builder, multi-platform audience sync, and CRM integrations. Trust-gated automation that scales with your business.',
    primaryCta: 'Start Free Trial',
    secondaryCta: 'Book Demo',
    metrics: [
      { label: 'Ad Accounts', value: '15', description: 'Connect up to 15 ad accounts' },
      { label: 'Monthly Spend', value: '$500K', description: 'Up to $500K monthly ad spend' },
      { label: 'Avg ROI Lift', value: '+34%', description: 'Average ROAS improvement' },
    ],
    trustBadges: ['14-day free trial', 'No credit card required', 'Priority support'],
  },
  featureCategories: [
    {
      name: 'Advanced Segmentation',
      icon: 'target',
      features: [
        {
          name: 'Segment Builder',
          description: 'Visual drag-and-drop segment creation',
          included: true,
          highlight: true,
        },
        {
          name: 'Behavioral Conditions',
          description: 'Segment by events, traits, and behaviors',
          included: true,
        },
        {
          name: 'Dynamic Segments',
          description: 'Auto-updating segments in real-time',
          included: true,
        },
        {
          name: 'Segment Preview',
          description: 'Preview audience size before activation',
          included: true,
        },
      ],
    },
    {
      name: 'Audience Sync',
      icon: 'sync',
      features: [
        {
          name: 'Meta Custom Audiences',
          description: 'Sync segments to Meta Ads',
          included: true,
          highlight: true,
        },
        {
          name: 'Google Customer Match',
          description: 'Sync segments to Google Ads',
          included: true,
          highlight: true,
        },
        {
          name: 'Auto-Sync Scheduling',
          description: 'Keep audiences fresh automatically',
          included: true,
        },
        { name: 'TikTok & Snapchat Sync', description: 'Full 4-platform sync', included: false },
      ],
    },
    {
      name: 'Funnel Analytics',
      icon: 'funnel',
      features: [
        {
          name: 'Funnel Builder',
          description: 'Create custom conversion funnels',
          included: true,
          highlight: true,
        },
        { name: 'Drop-off Analysis', description: 'Identify where users abandon', included: true },
        {
          name: 'Computed Traits',
          description: 'Create derived customer attributes',
          included: true,
        },
        { name: 'Cohort Analysis', description: 'Compare user cohorts over time', included: true },
      ],
    },
    {
      name: 'Integrations',
      icon: 'plug',
      features: [
        { name: 'Pipedrive CRM', description: 'Two-way sync with Pipedrive', included: true },
        { name: 'Slack Notifications', description: 'Advanced alert workflows', included: true },
        { name: 'Webhook Events', description: 'Send events to custom endpoints', included: true },
        {
          name: 'Salesforce CRM',
          description: 'Enterprise Salesforce integration',
          included: false,
        },
      ],
    },
    {
      name: 'Trust & Automation',
      icon: 'shield',
      features: [
        {
          name: 'Trust Gate Audit Logs',
          description: 'Full history of automation decisions',
          included: true,
        },
        {
          name: 'Action Dry-Run Mode',
          description: 'Preview actions before execution',
          included: true,
        },
        {
          name: 'Approval Workflows',
          description: 'Require approval for certain actions',
          included: true,
        },
        {
          name: 'Custom Autopilot Rules',
          description: 'Create custom automation rules',
          included: false,
        },
      ],
    },
  ],
  pricing: {
    price: '$999',
    period: '/month',
    adSpendLimit: 'Up to $500K monthly ad spend',
    accountLimit: '15 ad accounts',
    savings: 'Save $1,188/year with annual billing',
    nextTier: {
      name: 'Enterprise',
      teaser: 'Need unlimited accounts and custom automations?',
      link: '/plans/enterprise',
    },
  },
  testimonials: [
    {
      quote:
        'The segment builder changed how we think about audiences. We went from generic retargeting to hyper-specific segments that actually convert.',
      author: 'David Park',
      role: 'Head of Growth',
      company: 'Fintech Pro',
      companySize: '45 employees',
      metric: { label: 'CAC Reduction', value: '-28%' },
    },
    {
      quote:
        'Syncing our CDP segments directly to Meta and Google saved our team hours every week. The match rates are consistently above 70%.',
      author: 'Jessica Liu',
      role: 'Performance Marketing Manager',
      company: 'StyleHub',
      companySize: '120 employees',
      metric: { label: 'Match Rate', value: '73%' },
    },
    {
      quote:
        'Trust Gate audit logs give us the confidence to let automations run. We can see exactly why every decision was made.',
      author: 'Robert Kim',
      role: 'VP Marketing',
      company: 'CloudScale',
      companySize: '85 employees',
      metric: { label: 'Time Saved', value: '12hr/wk' },
    },
  ],
  faqs: [
    {
      question: "What's the difference between Starter and Professional?",
      answer:
        'Professional adds segment builder, funnel analytics, Meta/Google audience sync, CRM integrations, and trust gate audit logs. You also get 3x the ad accounts and 5x the spend limit.',
    },
    {
      question: 'How does audience sync work?',
      answer:
        'Create a segment in Stratum, then push it directly to Meta or Google with one click. Set up auto-sync to keep audiences fresh daily, weekly, or on custom schedules.',
    },
    {
      question: 'Can I upgrade from Starter mid-cycle?',
      answer:
        "Yes! Upgrade anytime and we'll prorate the difference. All your data, segments, and settings transfer automatically.",
    },
    {
      question: "What's included in priority support?",
      answer:
        'Professional includes priority email support with 24-hour response time, live chat during business hours, and access to monthly office hours with our team.',
    },
    {
      question: 'Is there a limit on segments I can create?',
      answer:
        'No limits! Create as many segments as you need. Professional includes unlimited segment creation, audience syncs, and funnel definitions.',
    },
  ],
};

// ============================================================================
// Enterprise Tier Content
// ============================================================================

const enterpriseContent: TierContent = {
  id: 'enterprise',
  name: 'Enterprise',
  visuals: {
    primaryColor: 'purple',
    gradientFrom: 'from-purple-500',
    gradientTo: 'to-indigo-500',
    accentColor: 'text-purple-400',
    badgeText: 'Custom Solutions',
    badgeColor: 'bg-purple-500',
  },
  hero: {
    tagline: 'Enterprise Plan',
    headline: 'Enterprise-Grade',
    highlightedText: 'Revenue Intelligence',
    subheadline: 'For organizations that demand the best',
    description:
      'Unlimited accounts, predictive churn modeling, identity graph visualization, 4-platform audience sync, custom autopilot rules, API access, and dedicated success management.',
    primaryCta: 'Contact Sales',
    secondaryCta: 'Book Demo',
    metrics: [
      { label: 'Ad Accounts', value: 'Unlimited', description: 'No limits on ad accounts' },
      { label: 'Monthly Spend', value: 'Unlimited', description: 'No spend caps' },
      { label: 'Avg ROI Lift', value: '+52%', description: 'Average ROAS improvement' },
    ],
    trustBadges: ['Custom pricing', 'Dedicated success manager', 'SLA guarantee'],
  },
  featureCategories: [
    {
      name: 'Predictive Intelligence',
      icon: 'brain',
      features: [
        {
          name: 'Predictive Churn Modeling',
          description: 'AI-powered customer churn prediction',
          included: true,
          highlight: true,
        },
        {
          name: 'LTV Prediction',
          description: 'Forecast customer lifetime value',
          included: true,
          highlight: true,
        },
        {
          name: 'Propensity Scoring',
          description: 'Predict conversion likelihood',
          included: true,
        },
        {
          name: 'Model Explainability',
          description: 'SHAP/LIME insights into predictions',
          included: true,
        },
      ],
    },
    {
      name: 'Identity Resolution',
      icon: 'fingerprint',
      features: [
        {
          name: 'Identity Graph',
          description: 'Visual identity resolution interface',
          included: true,
          highlight: true,
        },
        {
          name: 'Cross-Device Tracking',
          description: 'Unify users across devices',
          included: true,
        },
        {
          name: 'Profile Merge History',
          description: 'Full audit trail of identity merges',
          included: true,
        },
        { name: 'Canonical Identity', description: 'Golden record management', included: true },
      ],
    },
    {
      name: 'Full Platform Sync',
      icon: 'globe',
      features: [
        { name: 'Meta Custom Audiences', description: 'Sync segments to Meta Ads', included: true },
        {
          name: 'Google Customer Match',
          description: 'Sync segments to Google Ads',
          included: true,
        },
        {
          name: 'TikTok DMP Audiences',
          description: 'Sync segments to TikTok Ads',
          included: true,
          highlight: true,
        },
        {
          name: 'Snapchat SAM Audiences',
          description: 'Sync segments to Snapchat Ads',
          included: true,
          highlight: true,
        },
      ],
    },
    {
      name: 'Custom Automation',
      icon: 'cog',
      features: [
        {
          name: 'Custom Autopilot Rules',
          description: 'Create your own automation logic',
          included: true,
          highlight: true,
        },
        {
          name: 'API Access',
          description: 'Full REST API for custom integrations',
          included: true,
          highlight: true,
        },
        { name: 'Webhook Subscriptions', description: 'Real-time event streaming', included: true },
        {
          name: 'Custom Health Rules',
          description: 'Define your own signal health criteria',
          included: true,
        },
      ],
    },
    {
      name: 'Compliance & Security',
      icon: 'lock',
      features: [
        {
          name: 'GDPR Consent Management',
          description: 'Full consent tracking and management',
          included: true,
        },
        {
          name: 'CCPA Compliance',
          description: 'California privacy law compliance',
          included: true,
        },
        { name: 'SOC 2 Type II', description: 'Enterprise security certification', included: true },
        { name: 'SSO/SAML', description: 'Single sign-on integration', included: true },
      ],
    },
    {
      name: 'Enterprise Support',
      icon: 'headset',
      features: [
        {
          name: 'Dedicated Success Manager',
          description: '4-hour response time',
          included: true,
          highlight: true,
        },
        {
          name: 'Custom Report Builder',
          description: 'White-label custom reports',
          included: true,
        },
        {
          name: 'Salesforce Integration',
          description: 'Two-way Salesforce CRM sync',
          included: true,
        },
        { name: 'Custom Onboarding', description: 'Tailored implementation plan', included: true },
      ],
    },
  ],
  pricing: {
    price: 'Custom',
    period: '',
    adSpendLimit: 'Unlimited monthly ad spend',
    accountLimit: 'Unlimited ad accounts',
  },
  testimonials: [
    {
      quote:
        'Predictive churn modeling identified $2.3M in at-risk revenue. We intervened early and retained 78% of those customers.',
      author: 'Amanda Foster',
      role: 'CMO',
      company: 'RetailMax',
      companySize: '500+ employees',
      metric: { label: 'Revenue Retained', value: '$1.8M' },
    },
    {
      quote:
        'The identity graph finally solved our cross-device attribution problem. We can now see the complete customer journey across web, mobile, and in-store.',
      author: 'James Wilson',
      role: 'VP Data & Analytics',
      company: 'OmniChannel Corp',
      companySize: '1200 employees',
      metric: { label: 'Attribution Accuracy', value: '+45%' },
    },
    {
      quote:
        'Custom autopilot rules let us encode our exact playbook. The system now makes the same decisions our best media buyer would make, 24/7.',
      author: 'Catherine Li',
      role: 'Director of Performance',
      company: 'Global Brands Inc',
      companySize: '800 employees',
      metric: { label: 'ROAS Improvement', value: '+67%' },
    },
  ],
  faqs: [
    {
      question: 'How is Enterprise pricing determined?',
      answer:
        'Enterprise pricing is based on your specific needs: ad spend volume, number of users, integrations required, and support level. Contact our sales team for a custom quote.',
    },
    {
      question: "What's included in the dedicated success manager?",
      answer:
        'Your dedicated success manager provides 4-hour response time, quarterly business reviews, custom training sessions, and direct access to our product team for feature requests.',
    },
    {
      question: 'Can we get a custom SLA?',
      answer:
        "Yes! Enterprise plans include customizable SLAs for uptime, response times, and data processing. We'll work with your team to define the right guarantees.",
    },
    {
      question: 'How does the API access work?',
      answer:
        'Enterprise includes full REST API access with rate limits appropriate for your usage. You can integrate Stratum data into your own tools, dashboards, and workflows.',
    },
    {
      question: 'Do you support on-premise deployment?',
      answer:
        'We offer a hybrid deployment option for Enterprise customers with strict data residency requirements. Contact sales to discuss your specific needs.',
    },
  ],
};

// ============================================================================
// Export Content Map
// ============================================================================

export const tierContent: Record<TierType, TierContent> = {
  starter: starterContent,
  professional: professionalContent,
  enterprise: enterpriseContent,
};

export const validTiers: TierType[] = ['starter', 'professional', 'enterprise'];

export function isValidTier(tier: string): tier is TierType {
  return validTiers.includes(tier as TierType);
}

export function getTierContent(tier: string): TierContent | null {
  if (isValidTier(tier)) {
    return tierContent[tier];
  }
  return null;
}
