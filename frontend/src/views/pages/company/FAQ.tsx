/**
 * FAQ Page - Battle Card Style
 * Interactive FAQ with category filtering and expandable cards
 * Supports CMS integration with fallback to hardcoded content
 */

import { useState } from 'react';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  BoltIcon,
  ChartBarIcon,
  CogIcon,
  CurrencyDollarIcon,
  MagnifyingGlassIcon,
  QuestionMarkCircleIcon,
  ShieldCheckIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import { pageSEO, SEO } from '@/components/common/SEO';
import { type FAQItem as CMSFAQItem, useAllFAQItems } from '@/api/cms';

interface FAQItem {
  id: string;
  question: string;
  answer: string;
  category: string;
}

const categories = [
  { id: 'all', name: 'All Questions', icon: QuestionMarkCircleIcon, color: 'text-white' },
  { id: 'pricing', name: 'Pricing & Plans', icon: CurrencyDollarIcon, color: 'text-green-400' },
  { id: 'features', name: 'Features', icon: BoltIcon, color: 'text-purple-400' },
  { id: 'trust-engine', name: 'Trust Engine', icon: ShieldCheckIcon, color: 'text-cyan-400' },
  { id: 'integrations', name: 'Integrations', icon: CogIcon, color: 'text-orange-400' },
  { id: 'data', name: 'Data & Privacy', icon: ChartBarIcon, color: 'text-blue-400' },
  { id: 'support', name: 'Support', icon: UserGroupIcon, color: 'text-pink-400' },
];

// Fallback FAQ data when CMS content is not available
const fallbackFaqs: FAQItem[] = [
  // Pricing & Plans
  {
    id: '1',
    question: 'What pricing plans does Stratum AI offer?',
    answer:
      'We offer three tiers: Starter ($499/mo) for growing teams, Professional ($1,499/mo) for scaling businesses with advanced automation, and custom Enterprise plans for large organizations. Each tier includes a 14-day free trial with full feature access.',
    category: 'pricing',
  },
  {
    id: '2',
    question: 'Is there a free trial available?',
    answer:
      'Yes! We offer a 14-day free trial on all plans with full feature access. No credit card required to start. You can also use our Interactive Demo Mode to explore the platform with sample data before signing up.',
    category: 'pricing',
  },
  {
    id: '3',
    question: 'Can I change my plan later?',
    answer:
      'Absolutely. You can upgrade or downgrade your plan at any time. Upgrades take effect immediately with prorated billing. Downgrades take effect at the start of your next billing cycle.',
    category: 'pricing',
  },
  // Features
  {
    id: '4',
    question: 'What is the Trust-Gated Autopilot?',
    answer:
      'Trust-Gated Autopilot is our core innovation. It automatically executes optimizations ONLY when signal health passes safety thresholds (70+ score). This prevents costly mistakes from bad data while maximizing automation when conditions are right.',
    category: 'features',
  },
  {
    id: '5',
    question: 'Which ad platforms do you support?',
    answer:
      'We support Meta (Facebook/Instagram), Google Ads, TikTok Ads, and Snapchat Ads. Our platform connects via OAuth for campaign management and CAPI for server-side conversion tracking.',
    category: 'features',
  },
  {
    id: '6',
    question: 'What is the CDP and how does it work?',
    answer:
      'Our Customer Data Platform (CDP) unifies customer profiles across all touchpoints. It includes identity resolution, behavioral segmentation, RFM analysis, and one-click audience sync to all major ad platforms.',
    category: 'features',
  },
  // Trust Engine
  {
    id: '7',
    question: 'How does Signal Health scoring work?',
    answer:
      'Signal Health is a 0-100 score measuring data reliability. It factors in data freshness, completeness, consistency, and anomaly detection. Scores above 70 are "Healthy" (green), 40-70 are "Degraded" (yellow), and below 40 are "Unhealthy" (red).',
    category: 'trust-engine',
  },
  {
    id: '8',
    question: 'What happens when Signal Health drops?',
    answer:
      'When Signal Health drops below thresholds, the Trust Gate automatically blocks automated actions and alerts your team. This prevents optimizations based on unreliable data. You can still take manual actions with an override.',
    category: 'trust-engine',
  },
  {
    id: '9',
    question: 'Can I customize Trust Gate thresholds?',
    answer:
      'Yes, on Growth plans and above. You can set custom thresholds per campaign, automation rule, or globally. Enterprise plans include advanced configuration with time-based rules and multi-signal gates.',
    category: 'trust-engine',
  },
  // Integrations
  {
    id: '10',
    question: 'How do I connect my ad accounts?',
    answer:
      'Go to Tenant Settings → Connect Platforms. Click "Connect" on any platform to start the OAuth flow. You\'ll be redirected to the platform to grant permissions, then automatically returned to Stratum AI.',
    category: 'integrations',
  },
  {
    id: '11',
    question: 'What is CAPI and do I need it?',
    answer:
      'CAPI (Conversions API) sends conversion events server-side directly to ad platforms. This bypasses browser limitations like ad blockers and iOS privacy restrictions. It improves match rates from ~42% to 70-90%, significantly boosting ROAS.',
    category: 'integrations',
  },
  {
    id: '12',
    question: 'Do you integrate with Slack?',
    answer:
      'Yes! Our Slack integration sends real-time Trust Gate alerts, daily performance summaries, and anomaly notifications to your chosen channels. Configure it in Settings → Integrations.',
    category: 'integrations',
  },
  // Data & Privacy
  {
    id: '13',
    question: 'How do you handle my data?',
    answer:
      'We follow strict data security practices: SOC 2 Type II compliant, AES-256 encryption at rest, TLS 1.3 in transit. We never sell your data or use it for anything other than providing our service to you.',
    category: 'data',
  },
  {
    id: '14',
    question: 'Are you GDPR and CCPA compliant?',
    answer:
      "Yes. We're fully GDPR and CCPA compliant. Our CDP includes built-in consent management, data subject request handling, and automatic PII hashing for platform syncs. DPA available for all customers.",
    category: 'data',
  },
  {
    id: '15',
    question: 'Where is my data stored?',
    answer:
      'Data is stored in AWS data centers. US customers use us-east-1, EU customers use eu-west-1. Enterprise plans can specify custom regions. All data is encrypted and backed up with 99.9% SLA.',
    category: 'data',
  },
  // Support
  {
    id: '16',
    question: 'What support options are available?',
    answer:
      'Starter: Email support (48h response). Growth: Priority email + chat (24h response). Scale: Dedicated CSM + phone support (4h response). Enterprise: 24/7 support + SLA guarantees.',
    category: 'support',
  },
  {
    id: '17',
    question: 'Do you offer onboarding assistance?',
    answer:
      'Yes! All plans include self-service onboarding with interactive guides. Growth and above get a 1-hour kickoff call. Scale and Enterprise receive full white-glove onboarding with dedicated implementation support.',
    category: 'support',
  },
  {
    id: '18',
    question: 'How can I contact the team?',
    answer:
      'Email us at support@stratum.ai for support, sales@stratum.ai for sales inquiries, or use the in-app chat. Enterprise customers have direct Slack channels with our team.',
    category: 'support',
  },
];

// Convert CMS FAQ items to local format
function convertCMSFaqs(cmsItems: CMSFAQItem[]): FAQItem[] {
  return cmsItems.map((item) => ({
    id: item.id,
    question: item.question,
    answer: item.answer,
    category: item.category,
  }));
}

export default function FAQ() {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch from CMS with fallback
  const { data: cmsFaqs, isLoading } = useAllFAQItems();

  // Use CMS data if available and has content, otherwise use fallback
  const faqs = cmsFaqs && cmsFaqs.length > 0 ? convertCMSFaqs(cmsFaqs) : fallbackFaqs;

  const filteredFaqs = faqs.filter((faq) => {
    const matchesCategory = selectedCategory === 'all' || faq.category === selectedCategory;
    const matchesSearch =
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const getCategoryIcon = (categoryId: string) => {
    const category = categories.find((c) => c.id === categoryId);
    return category?.icon || QuestionMarkCircleIcon;
  };

  return (
    <PageLayout>
      <SEO {...pageSEO.faq} url="https://stratum-ai.com/faq" />
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400 text-sm mb-6">
            <QuestionMarkCircleIcon className="w-4 h-4" />
            Help Center
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6">
            <span className="text-white">Frequently Asked</span>
            <br />
            <span className="bg-gradient-stratum bg-clip-text text-transparent">Questions</span>
          </h1>
          <p className="text-lg md:text-xl text-white/70 max-w-2xl mx-auto mb-8">
            Everything you need to know about Stratum AI. Can&apos;t find what you&apos;re looking
            for?{' '}
            <a href="/contact" className="text-orange-500 hover:underline">
              Contact our team
            </a>
          </p>

          {/* Search */}
          <div className="max-w-xl mx-auto relative">
            <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
            <input
              type="text"
              placeholder="Search questions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-4 rounded-2xl bg-white/5 border border-white/10 text-white placeholder-white/40 outline-none transition-all focus:ring-2 focus:ring-purple-500/50"
            />
          </div>
        </div>
      </section>

      {/* Category Filter */}
      <section className="px-6 pb-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-wrap justify-center gap-3">
            {categories.map((category) => {
              const Icon = category.icon;
              const isSelected = selectedCategory === category.id;
              const colorMap: Record<string, string> = {
                'text-green-400': '#34c759',
                'text-purple-400': '#a855f7',
                'text-cyan-400': '#06b6d4',
                'text-orange-400': '#f97316',
                'text-blue-400': '#3b82f6',
                'text-pink-400': '#ec4899',
                'text-white': '#ffffff',
              };
              const accentColor = colorMap[category.color] || '#a855f7';

              return (
                <button
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    isSelected ? 'text-white' : 'text-white/60 hover:text-white'
                  }`}
                  style={{
                    background: isSelected ? `${accentColor}20` : 'rgba(255, 255, 255, 0.04)',
                    border: `1px solid ${isSelected ? `${accentColor}40` : 'rgba(255, 255, 255, 0.08)'}`,
                  }}
                >
                  <Icon
                    className="w-4 h-4"
                    style={{ color: isSelected ? accentColor : undefined }}
                  />
                  {category.name}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* FAQ Cards Grid - Battle Card Style */}
      <section className="py-12 px-6">
        <div className="max-w-7xl mx-auto">
          {filteredFaqs.length === 0 ? (
            <div className="text-center py-12">
              <QuestionMarkCircleIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
              <p className="text-white/60">No questions found matching your search.</p>
            </div>
          ) : (
            <div
              className={`grid md:grid-cols-2 lg:grid-cols-3 gap-5 ${isLoading ? 'opacity-50' : ''}`}
            >
              {filteredFaqs.map((faq) => {
                const Icon = getCategoryIcon(faq.category);
                const categoryData = categories.find((c) => c.id === faq.category);
                const colorMap: Record<string, string> = {
                  'text-green-400': '#34c759',
                  'text-purple-400': '#a855f7',
                  'text-cyan-400': '#06b6d4',
                  'text-orange-400': '#f97316',
                  'text-blue-400': '#3b82f6',
                  'text-pink-400': '#ec4899',
                  'text-white': '#ffffff',
                };
                const accentColor = colorMap[categoryData?.color || 'text-purple-400'] || '#a855f7';

                return (
                  <div
                    key={faq.id}
                    className="group p-6 rounded-2xl transition-all duration-300 hover:scale-[1.02]"
                    style={{
                      background: `linear-gradient(135deg, ${accentColor}08 0%, transparent 100%)`,
                      border: `1px solid ${accentColor}20`,
                    }}
                  >
                    {/* Icon */}
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center mb-4 transition-all duration-300 group-hover:scale-110"
                      style={{
                        background: `${accentColor}15`,
                        border: `1px solid ${accentColor}30`,
                      }}
                    >
                      <Icon className="w-6 h-6" style={{ color: accentColor }} />
                    </div>

                    {/* Category Tag */}
                    <div className="mb-3">
                      <span
                        className="text-xs font-medium px-2 py-1 rounded-full"
                        style={{
                          background: `${accentColor}15`,
                          color: accentColor,
                        }}
                      >
                        {categoryData?.name}
                      </span>
                    </div>

                    {/* Question */}
                    <h3 className="text-lg font-semibold text-white mb-3 leading-snug">
                      {faq.question}
                    </h3>

                    {/* Answer */}
                    <p className="text-sm text-white/60 leading-relaxed">{faq.answer}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* Contact CTA */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="p-8 rounded-3xl bg-gradient-to-br from-purple-500/10 to-cyan-500/10 border border-white/10">
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
              Still have questions?
            </h2>
            <p className="text-white/60 mb-6 max-w-xl mx-auto">
              Our team is here to help. Reach out and we&apos;ll get back to you as soon as
              possible.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/contact"
                className="px-6 py-3 rounded-xl font-semibold text-white bg-orange-500 hover:bg-orange-600 transition-colors shadow-lg shadow-orange-500/40"
              >
                Contact Support
              </a>
              <a
                href="mailto:sales@stratum.ai"
                className="px-6 py-3 rounded-xl font-semibold text-white bg-white/5 border border-white/10 hover:bg-white/10 transition-colors"
              >
                Email Us
              </a>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
