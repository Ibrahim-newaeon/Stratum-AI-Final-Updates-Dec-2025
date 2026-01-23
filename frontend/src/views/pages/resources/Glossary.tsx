/**
 * Glossary Page - Platform Terminology & Values
 * 2026 Theme - Electric Neon / OLED-Optimized
 */

import { useState } from 'react';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  BookOpenIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  ChartBarIcon,
  ArrowPathIcon,
  BoltIcon,
  CpuChipIcon,
  SignalIcon,
  CurrencyDollarIcon,
  BeakerIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline';

interface GlossaryTerm {
  term: string;
  definition: string;
  values?: { value: string; description: string }[];
  example?: string;
}

interface GlossaryCategory {
  id: string;
  title: string;
  icon: typeof BookOpenIcon;
  color: string;
  description: string;
  terms: GlossaryTerm[];
}

const glossaryData: GlossaryCategory[] = [
  {
    id: 'trust-engine',
    title: 'Trust Engine',
    icon: ShieldCheckIcon,
    color: '#8B5CF6',
    description: 'Core decision-making component that evaluates signal health before automation execution.',
    terms: [
      {
        term: 'Signal Health',
        definition: 'Composite score (0-100) measuring the reliability and quality of incoming data signals.',
        values: [
          { value: 'HEALTHY (70-100)', description: 'Full autopilot enabled, automation executes normally' },
          { value: 'DEGRADED (40-69)', description: 'Alert only, manual intervention may be needed' },
          { value: 'CRITICAL (0-39)', description: 'Manual intervention required, automation blocked' },
        ],
      },
      {
        term: 'Trust Gate',
        definition: 'Decision checkpoint that evaluates whether automation should execute based on signal health thresholds.',
        values: [
          { value: 'PASS', description: 'Signal health meets threshold, automation executes' },
          { value: 'HOLD', description: 'Signal health marginal, requires confirmation' },
          { value: 'BLOCK', description: 'Signal health below threshold, automation blocked' },
        ],
      },
      {
        term: 'Autopilot',
        definition: 'Automated actions that execute when trust gates pass. Includes budget adjustments, campaign pausing, and optimization.',
        values: [
          { value: 'ADVISORY', description: 'Warn only, no blocking actions' },
          { value: 'SOFT_BLOCK', description: 'Warn and require user confirmation' },
          { value: 'HARD_BLOCK', description: 'Prevent action entirely, log overrides' },
        ],
      },
      {
        term: 'HEALTHY_THRESHOLD',
        definition: 'Minimum signal health score (70.0) required for autopilot to execute automatically.',
        example: 'If signal health is 72, autopilot proceeds. If 68, it holds for review.',
      },
      {
        term: 'EMQ (Event Match Quality)',
        definition: 'Score measuring how well conversion events match platform requirements for attribution.',
        values: [
          { value: 'emq_healthy: 90+', description: 'Excellent match quality, optimal attribution' },
          { value: 'emq_risk: 80-89', description: 'Good quality, minor optimization needed' },
          { value: 'Below 80', description: 'Poor quality, attribution accuracy impacted' },
        ],
      },
    ],
  },
  {
    id: 'cdp',
    title: 'CDP (Customer Data Platform)',
    icon: UserGroupIcon,
    color: '#00D4FF',
    description: 'Unified customer data infrastructure for profiles, segments, and identity resolution.',
    terms: [
      {
        term: 'Profile',
        definition: 'Unified customer record combining all known identifiers, traits, and event history.',
      },
      {
        term: 'Lifecycle Stage',
        definition: 'Customer journey stage based on behavior and purchase history.',
        values: [
          { value: 'ANONYMOUS', description: 'Unknown visitor, no identifying information' },
          { value: 'KNOWN', description: 'Identified user (email/phone collected)' },
          { value: 'CUSTOMER', description: 'Has completed at least one purchase' },
          { value: 'CHURNED', description: 'Inactive for defined period (typically 90 days)' },
        ],
      },
      {
        term: 'Identity Resolution',
        definition: 'Process of merging multiple identifiers into a single customer profile across devices and channels.',
        values: [
          { value: 'external_id (100)', description: 'Highest priority - customer ID from your system' },
          { value: 'email (80)', description: 'High priority - verified email address' },
          { value: 'phone (70)', description: 'High priority - verified phone number' },
          { value: 'device_id (40)', description: 'Medium priority - device fingerprint' },
          { value: 'anonymous_id (10)', description: 'Lowest priority - cookie/session ID' },
        ],
      },
      {
        term: 'Segment',
        definition: 'Dynamic or static group of profiles based on traits, behaviors, or computed attributes.',
        values: [
          { value: 'STATIC', description: 'Manually defined membership list' },
          { value: 'DYNAMIC', description: 'Rule-based, automatically updated' },
          { value: 'COMPUTED', description: 'ML/algorithm-based grouping' },
        ],
      },
      {
        term: 'Computed Trait',
        definition: 'Derived attribute calculated from profile events and properties.',
        values: [
          { value: 'count', description: 'Count of events (e.g., total_purchases)' },
          { value: 'sum', description: 'Sum of values (e.g., lifetime_revenue)' },
          { value: 'average', description: 'Average value (e.g., avg_order_value)' },
          { value: 'first/last', description: 'First or last occurrence (e.g., first_purchase_date)' },
          { value: 'unique_count', description: 'Count of unique values (e.g., products_purchased)' },
        ],
      },
      {
        term: 'RFM Analysis',
        definition: 'Recency, Frequency, Monetary scoring model for customer value segmentation.',
        values: [
          { value: 'VIP', description: 'Highest value - recent, frequent, high spend' },
          { value: 'HIGH_VALUE', description: 'High value customers' },
          { value: 'MEDIUM_VALUE', description: 'Average value customers' },
          { value: 'LOW_VALUE', description: 'Lower value, opportunity for growth' },
          { value: 'AT_RISK', description: 'Previously active, now showing churn signals' },
        ],
      },
      {
        term: 'Consent Type',
        definition: 'User permission categories for data processing compliance.',
        values: [
          { value: 'analytics', description: 'Permission for analytics/tracking' },
          { value: 'ads', description: 'Permission for advertising targeting' },
          { value: 'email', description: 'Permission for email marketing' },
          { value: 'sms', description: 'Permission for SMS marketing' },
        ],
      },
    ],
  },
  {
    id: 'audience-sync',
    title: 'Audience Sync',
    icon: ArrowPathIcon,
    color: '#00FF88',
    description: 'Push CDP segments to ad platforms for targeting and suppression.',
    terms: [
      {
        term: 'Platform Audience',
        definition: 'Audience created on ad platform (Meta, Google, TikTok, Snapchat) from CDP segment.',
      },
      {
        term: 'Sync Status',
        definition: 'Current state of audience synchronization job.',
        values: [
          { value: 'PENDING', description: 'Queued for sync' },
          { value: 'PROCESSING', description: 'Currently syncing to platform' },
          { value: 'COMPLETED', description: 'Successfully synchronized' },
          { value: 'FAILED', description: 'Sync failed, check error logs' },
          { value: 'PARTIAL', description: 'Some records failed to sync' },
        ],
      },
      {
        term: 'Match Rate',
        definition: 'Percentage of hashed identifiers that the ad platform successfully matched to users (0-100%).',
        example: 'A 65% match rate means 65% of emails sent were matched to platform user accounts.',
      },
      {
        term: 'Sync Operation',
        definition: 'Type of sync action being performed.',
        values: [
          { value: 'CREATE', description: 'Create new audience on platform' },
          { value: 'UPDATE', description: 'Add/remove users from existing audience' },
          { value: 'REPLACE', description: 'Replace entire audience membership' },
          { value: 'DELETE', description: 'Remove audience from platform' },
        ],
      },
      {
        term: 'Auto-Sync Interval',
        definition: 'Frequency of automatic audience updates. Range: 1 hour to 1 week. Default: 24 hours.',
      },
    ],
  },
  {
    id: 'capi',
    title: 'CAPI (Conversions API)',
    icon: BoltIcon,
    color: '#FFB800',
    description: 'Server-side event delivery to ad platforms for improved attribution.',
    terms: [
      {
        term: 'Conversions API',
        definition: 'Server-to-server connection sending conversion events directly to ad platforms, bypassing browser limitations.',
      },
      {
        term: 'PII Hashing',
        definition: 'SHA256 one-way hashing of personally identifiable information (email, phone) before sending to platforms.',
      },
      {
        term: 'Delivery Status',
        definition: 'Result of sending event to platform.',
        values: [
          { value: 'success', description: 'Event delivered successfully' },
          { value: 'failed', description: 'Delivery failed' },
          { value: 'retrying', description: 'Retry in progress' },
          { value: 'rate_limited', description: 'Platform rate limit exceeded' },
        ],
      },
      {
        term: 'Dead Letter Queue (DLQ)',
        definition: 'Storage for failed events awaiting retry. Events are retained for 7 days by default.',
        values: [
          { value: 'pending', description: 'Awaiting retry attempt' },
          { value: 'retrying', description: 'Currently being retried' },
          { value: 'recovered', description: 'Successfully delivered after retry' },
          { value: 'expired', description: 'Retry window expired' },
        ],
      },
      {
        term: 'Event Deduplication',
        definition: 'Prevention of duplicate event processing using event IDs. Default TTL: 24 hours.',
      },
      {
        term: 'EMQ Score Components',
        definition: 'Breakdown of Event Match Quality scoring (total 100 points).',
        values: [
          { value: 'Identifier Quality (40pts)', description: 'Quality of user identifiers (email, phone, etc.)' },
          { value: 'Data Completeness (25pts)', description: 'Completeness of event data fields' },
          { value: 'Timeliness (20pts)', description: 'Recency of event delivery' },
          { value: 'Context Richness (15pts)', description: 'Additional context (geo, device, campaign)' },
        ],
      },
    ],
  },
  {
    id: 'analytics',
    title: 'Analytics & Metrics',
    icon: ChartBarIcon,
    color: '#FF6B6B',
    description: 'Performance metrics, KPIs, and calculated values for campaign optimization.',
    terms: [
      {
        term: 'ROAS',
        definition: 'Return on Ad Spend. Revenue divided by ad spend. A ROAS of 3.0 means $3 revenue per $1 spent.',
        example: 'ROAS = Revenue / Spend = $30,000 / $10,000 = 3.0x',
      },
      {
        term: 'CPA',
        definition: 'Cost Per Acquisition. Total spend divided by number of conversions.',
        example: 'CPA = Spend / Conversions = $10,000 / 200 = $50',
      },
      {
        term: 'CAC',
        definition: 'Customer Acquisition Cost. Total marketing spend divided by new customers acquired.',
      },
      {
        term: 'LTV',
        definition: 'Lifetime Value. Predicted total revenue a customer will generate over their relationship.',
      },
      {
        term: 'CVR',
        definition: 'Conversion Rate. Percentage of clicks that result in conversions.',
        example: 'CVR = Conversions / Clicks = 200 / 5000 = 4%',
      },
      {
        term: 'CTR',
        definition: 'Click-Through Rate. Percentage of impressions that result in clicks.',
        example: 'CTR = Clicks / Impressions = 5000 / 100000 = 5%',
      },
      {
        term: 'CPM',
        definition: 'Cost Per Mille (thousand impressions). Spend divided by impressions, multiplied by 1000.',
        example: 'CPM = (Spend / Impressions) × 1000 = ($10,000 / 100,000) × 1000 = $100',
      },
      {
        term: 'Frequency',
        definition: 'Average number of times each user sees your ad. High frequency can indicate ad fatigue.',
      },
      {
        term: 'Creative Fatigue',
        definition: 'Decline in performance as audiences see the same creative repeatedly.',
        values: [
          { value: 'HEALTHY (<0.45)', description: 'Creative performing well' },
          { value: 'WATCH (0.45-0.65)', description: 'Monitor for declining performance' },
          { value: 'REFRESH (>0.65)', description: 'Creative needs refresh or replacement' },
        ],
      },
    ],
  },
  {
    id: 'pacing',
    title: 'Pacing & Forecasting',
    icon: SignalIcon,
    color: '#A78BFA',
    description: 'Budget tracking, spend pacing, and performance forecasting.',
    terms: [
      {
        term: 'Pacing',
        definition: 'Comparison of actual spend/performance vs. target for the period. Expressed as percentage.',
        example: 'If target is $30k/month and you\'ve spent $20k by day 20, pacing is 100% (on track).',
      },
      {
        term: 'Target Period',
        definition: 'Time frame for pacing targets.',
        values: [
          { value: 'MONTHLY', description: 'Calendar month targets' },
          { value: 'QUARTERLY', description: 'Quarter targets (Q1-Q4)' },
          { value: 'YEARLY', description: 'Annual targets' },
          { value: 'CUSTOM', description: 'Custom date range' },
        ],
      },
      {
        term: 'Pacing Alerts',
        definition: 'Notifications when spend or performance deviates from targets.',
        values: [
          { value: 'UNDERPACING_SPEND', description: 'Behind on spend target' },
          { value: 'OVERPACING_SPEND', description: 'Ahead of spend target' },
          { value: 'ROAS_BELOW_TARGET', description: 'ROAS falling short' },
          { value: 'BUDGET_EXHAUSTION', description: 'Budget running out early' },
        ],
      },
      {
        term: 'Scaling Actions',
        definition: 'Recommended actions based on campaign performance score.',
        values: [
          { value: 'SCALE', description: 'Increase budget - strong performance (score >0.25)' },
          { value: 'WATCH', description: 'Monitor closely - moderate performance' },
          { value: 'FIX', description: 'Troubleshoot issues - poor performance (score <-0.25)' },
          { value: 'PAUSE', description: 'Pause campaign - critical issues' },
        ],
      },
    ],
  },
  {
    id: 'crm',
    title: 'CRM Integration',
    icon: CurrencyDollarIcon,
    color: '#00D4FF',
    description: 'Customer relationship management sync and pipeline attribution.',
    terms: [
      {
        term: 'Writeback',
        definition: 'Syncing Stratum AI data (ad performance, attribution) back to CRM records.',
      },
      {
        term: 'Identity Matching',
        definition: 'Linking CRM contacts to ad platform audiences using email/phone matching.',
      },
      {
        term: 'Pipeline ROAS',
        definition: 'Return on ad spend calculated using CRM pipeline value instead of just revenue.',
      },
      {
        term: 'Deal Stages',
        definition: 'CRM pipeline stages for tracking sales progression.',
        values: [
          { value: 'LEAD', description: 'New lead entered' },
          { value: 'MQL', description: 'Marketing Qualified Lead' },
          { value: 'SQL', description: 'Sales Qualified Lead' },
          { value: 'OPPORTUNITY', description: 'Active sales opportunity' },
          { value: 'PROPOSAL', description: 'Proposal sent' },
          { value: 'WON/LOST', description: 'Deal closed' },
        ],
      },
      {
        term: 'Attribution Model',
        definition: 'Method for assigning conversion credit to marketing touchpoints.',
        values: [
          { value: 'LAST_TOUCH', description: 'Last touchpoint gets 100% credit' },
          { value: 'FIRST_TOUCH', description: 'First touchpoint gets 100% credit' },
          { value: 'LINEAR', description: 'Equal credit to all touchpoints' },
          { value: 'POSITION_BASED', description: '40% first, 40% last, 20% middle' },
          { value: 'TIME_DECAY', description: 'More credit to recent touchpoints' },
          { value: 'DATA_DRIVEN', description: 'ML-based credit allocation' },
        ],
      },
    ],
  },
  {
    id: 'experiments',
    title: 'A/B Testing & Experiments',
    icon: BeakerIcon,
    color: '#FF6B6B',
    description: 'Controlled experiments for testing campaign variations.',
    terms: [
      {
        term: 'Experiment Status',
        definition: 'Current state of an A/B test or experiment.',
        values: [
          { value: 'DRAFT', description: 'Experiment configured but not started' },
          { value: 'RUNNING', description: 'Experiment actively collecting data' },
          { value: 'PAUSED', description: 'Temporarily stopped' },
          { value: 'COMPLETED', description: 'Finished, results available' },
          { value: 'CANCELLED', description: 'Terminated without results' },
        ],
      },
      {
        term: 'Statistical Significance',
        definition: 'Confidence level that results are not due to random chance. Typically 95% threshold.',
      },
      {
        term: 'Control/Variant',
        definition: 'Control is the baseline (original), Variant is the test version being compared.',
      },
    ],
  },
  {
    id: 'system',
    title: 'System & Configuration',
    icon: Cog6ToothIcon,
    color: '#94A3B8',
    description: 'System status, configuration values, and operational parameters.',
    terms: [
      {
        term: 'Service Status',
        definition: 'Operational state of platform services.',
        values: [
          { value: 'operational', description: 'Service running normally' },
          { value: 'degraded', description: 'Reduced performance or partial outage' },
          { value: 'outage', description: 'Service unavailable' },
          { value: 'maintenance', description: 'Scheduled maintenance window' },
        ],
      },
      {
        term: 'Alert Severity',
        definition: 'Priority level for system and performance alerts.',
        values: [
          { value: 'INFO', description: 'Informational, no action needed' },
          { value: 'LOW', description: 'Minor issue, low priority' },
          { value: 'MEDIUM', description: 'Moderate issue, should address' },
          { value: 'HIGH', description: 'Significant issue, address soon' },
          { value: 'CRITICAL', description: 'Critical, immediate action required' },
        ],
      },
      {
        term: 'Data Freshness',
        definition: 'How recently data was last updated. Stale data (>48 hours) may impact accuracy.',
      },
      {
        term: 'Webhook',
        definition: 'HTTP callback that sends real-time notifications when events occur.',
        values: [
          { value: 'campaign.updated', description: 'Campaign settings changed' },
          { value: 'alert.triggered', description: 'Performance alert fired' },
          { value: 'trust_gate.block', description: 'Automation blocked by trust gate' },
          { value: 'sync.completed', description: 'Data sync finished' },
        ],
      },
    ],
  },
  {
    id: 'platforms',
    title: 'Ad Platforms',
    icon: CpuChipIcon,
    color: '#00FF88',
    description: 'Supported advertising platforms and their specific terminology.',
    terms: [
      {
        term: 'Supported Platforms',
        definition: 'Ad networks integrated with Stratum AI.',
        values: [
          { value: 'META', description: 'Facebook, Instagram, Messenger, WhatsApp' },
          { value: 'GOOGLE', description: 'Google Ads, YouTube, Display Network' },
          { value: 'TIKTOK', description: 'TikTok Ads Manager' },
          { value: 'SNAPCHAT', description: 'Snapchat Ads' },
        ],
      },
      {
        term: 'Entity Hierarchy',
        definition: 'Structural levels within ad platforms.',
        values: [
          { value: 'ACCOUNT', description: 'Top-level ad account' },
          { value: 'CAMPAIGN', description: 'Campaign containing ad sets/groups' },
          { value: 'ADSET/ADGROUP', description: 'Targeting and budget groups' },
          { value: 'CREATIVE/AD', description: 'Individual ad creative' },
        ],
      },
      {
        term: 'Conversion Window',
        definition: 'Time period after click/view during which conversions are attributed.',
        values: [
          { value: 'Meta', description: '1-day view, 7-day click typical' },
          { value: 'Google', description: '30-day click window' },
          { value: 'TikTok', description: '7-day click, 1-day view' },
          { value: 'Snapchat', description: '28-day click window' },
        ],
      },
      {
        term: 'Custom Audience',
        definition: 'Platform audience created from your customer data (email, phone lists).',
      },
      {
        term: 'Lookalike/Similar Audience',
        definition: 'Platform-generated audience of users similar to your custom audience.',
      },
    ],
  },
];

export default function GlossaryPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const filteredCategories = glossaryData.map((category) => ({
    ...category,
    terms: category.terms.filter(
      (term) =>
        term.term.toLowerCase().includes(searchQuery.toLowerCase()) ||
        term.definition.toLowerCase().includes(searchQuery.toLowerCase())
    ),
  })).filter((category) => category.terms.length > 0);

  const totalTerms = glossaryData.reduce((acc, cat) => acc + cat.terms.length, 0);

  return (
    <PageLayout>
      <div className="min-h-screen">
        {/* Hero Section */}
        <section className="relative py-20 overflow-hidden">
          <div className="max-w-5xl mx-auto px-6 lg:px-8 text-center">
            <div
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-6"
              style={{
                background: 'rgba(139, 92, 246, 0.1)',
                border: '1px solid rgba(139, 92, 246, 0.2)',
              }}
            >
              <BookOpenIcon className="w-4 h-4 text-[#8B5CF6]" />
              <span className="text-sm font-medium text-[#8B5CF6]">Glossary</span>
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Platform{' '}
              <span
                style={{
                  background: 'linear-gradient(135deg, #8B5CF6 0%, #00D4FF 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                Terminology
              </span>
            </h1>

            <p className="text-lg text-gray-400 mb-8">
              Complete reference of {totalTerms}+ terms, metrics, and values used across Stratum AI.
            </p>

            {/* Search */}
            <div className="max-w-xl mx-auto">
              <div
                className="relative"
                style={{
                  background: 'rgba(10, 10, 15, 0.6)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '12px',
                }}
              >
                <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search terms..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 bg-transparent text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#8B5CF6]/50 rounded-xl"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Category Navigation */}
        <section className="py-4 sticky top-16 z-10" style={{ background: 'rgba(0, 0, 0, 0.8)', backdropFilter: 'blur(12px)' }}>
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
              <button
                onClick={() => setActiveCategory(null)}
                className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all ${
                  activeCategory === null
                    ? 'bg-[#8B5CF6] text-white'
                    : 'bg-white/5 text-gray-400 hover:text-white'
                }`}
              >
                All Categories
              </button>
              {glossaryData.map((category) => (
                <button
                  key={category.id}
                  onClick={() => setActiveCategory(category.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all flex items-center gap-2 ${
                    activeCategory === category.id
                      ? 'text-white'
                      : 'bg-white/5 text-gray-400 hover:text-white'
                  }`}
                  style={activeCategory === category.id ? { background: category.color } : {}}
                >
                  <category.icon className="w-4 h-4" />
                  {category.title}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Glossary Content */}
        <section className="py-12">
          <div className="max-w-5xl mx-auto px-6 lg:px-8">
            <div className="space-y-12">
              {(activeCategory ? filteredCategories.filter((c) => c.id === activeCategory) : filteredCategories).map(
                (category) => (
                  <div key={category.id} id={category.id}>
                    {/* Category Header */}
                    <div className="flex items-center gap-4 mb-6">
                      <div
                        className="w-12 h-12 rounded-xl flex items-center justify-center"
                        style={{
                          background: `${category.color}15`,
                          border: `1px solid ${category.color}30`,
                        }}
                      >
                        <category.icon className="w-6 h-6" style={{ color: category.color }} />
                      </div>
                      <div>
                        <h2 className="text-xl font-bold text-white">{category.title}</h2>
                        <p className="text-sm text-gray-400">{category.description}</p>
                      </div>
                    </div>

                    {/* Terms */}
                    <div className="space-y-4">
                      {category.terms.map((term, index) => (
                        <div
                          key={index}
                          className="p-5 rounded-xl"
                          style={{
                            background: 'rgba(10, 10, 15, 0.6)',
                            border: '1px solid rgba(255, 255, 255, 0.06)',
                          }}
                        >
                          <h3 className="text-lg font-semibold text-white mb-2">{term.term}</h3>
                          <p className="text-gray-400 mb-3">{term.definition}</p>

                          {term.values && (
                            <div className="space-y-2 mt-4">
                              <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                Values
                              </span>
                              <div className="grid gap-2">
                                {term.values.map((value, vIndex) => (
                                  <div
                                    key={vIndex}
                                    className="flex items-start gap-3 p-3 rounded-lg"
                                    style={{ background: 'rgba(255, 255, 255, 0.03)' }}
                                  >
                                    <code
                                      className="px-2 py-1 rounded text-sm font-mono flex-shrink-0"
                                      style={{
                                        background: `${category.color}15`,
                                        color: category.color,
                                      }}
                                    >
                                      {value.value}
                                    </code>
                                    <span className="text-sm text-gray-400">{value.description}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {term.example && (
                            <div className="mt-4 p-3 rounded-lg" style={{ background: 'rgba(139, 92, 246, 0.1)' }}>
                              <span className="text-xs font-medium text-[#8B5CF6] uppercase tracking-wide">
                                Example
                              </span>
                              <p className="text-sm text-gray-300 mt-1">{term.example}</p>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )
              )}

              {filteredCategories.length === 0 && (
                <div className="text-center py-12">
                  <p className="text-gray-400">No terms found matching "{searchQuery}"</p>
                </div>
              )}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-16">
          <div className="max-w-3xl mx-auto px-6 lg:px-8 text-center">
            <div
              className="p-8 rounded-2xl"
              style={{
                background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(0, 212, 255, 0.05) 100%)',
                border: '1px solid rgba(139, 92, 246, 0.2)',
              }}
            >
              <h3 className="text-xl font-bold text-white mb-2">Can't find what you're looking for?</h3>
              <p className="text-gray-400 mb-6">
                Check our documentation or reach out to our support team.
              </p>
              <div className="flex gap-4 justify-center">
                <a
                  href="/docs"
                  className="px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200"
                  style={{
                    background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                  }}
                >
                  View Docs
                </a>
                <a
                  href="/contact"
                  className="px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200"
                  style={{
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }}
                >
                  Contact Support
                </a>
              </div>
            </div>
          </div>
        </section>
      </div>
    </PageLayout>
  );
}
