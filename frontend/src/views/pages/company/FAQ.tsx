/**
 * FAQ Page - Battle Card Style
 * Interactive FAQ with category filtering and expandable cards
 */

import { useState } from 'react';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  QuestionMarkCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  MagnifyingGlassIcon,
  CurrencyDollarIcon,
  CogIcon,
  ShieldCheckIcon,
  ChartBarIcon,
  UserGroupIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

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

const faqs: FAQItem[] = [
  // Pricing & Plans
  {
    id: '1',
    question: 'What pricing plans does Stratum AI offer?',
    answer: 'We offer four tiers: Starter ($299/mo) for small teams, Growth ($799/mo) for scaling businesses, Scale ($1,999/mo) for enterprises, and custom Enterprise plans. Each tier includes increasing levels of ad spend capacity, signals, and features.',
    category: 'pricing',
  },
  {
    id: '2',
    question: 'Is there a free trial available?',
    answer: 'Yes! We offer a 14-day free trial on all plans with full feature access. No credit card required to start. You can also use our Interactive Demo Mode to explore the platform with sample data before signing up.',
    category: 'pricing',
  },
  {
    id: '3',
    question: 'Can I change my plan later?',
    answer: 'Absolutely. You can upgrade or downgrade your plan at any time. Upgrades take effect immediately with prorated billing. Downgrades take effect at the start of your next billing cycle.',
    category: 'pricing',
  },
  // Features
  {
    id: '4',
    question: 'What is the Trust-Gated Autopilot?',
    answer: 'Trust-Gated Autopilot is our core innovation. It automatically executes optimizations ONLY when signal health passes safety thresholds (70+ score). This prevents costly mistakes from bad data while maximizing automation when conditions are right.',
    category: 'features',
  },
  {
    id: '5',
    question: 'Which ad platforms do you support?',
    answer: 'We support Meta (Facebook/Instagram), Google Ads, TikTok Ads, and Snapchat Ads. Our platform connects via OAuth for campaign management and CAPI for server-side conversion tracking.',
    category: 'features',
  },
  {
    id: '6',
    question: 'What is the CDP and how does it work?',
    answer: 'Our Customer Data Platform (CDP) unifies customer profiles across all touchpoints. It includes identity resolution, behavioral segmentation, RFM analysis, and one-click audience sync to all major ad platforms.',
    category: 'features',
  },
  // Trust Engine
  {
    id: '7',
    question: 'How does Signal Health scoring work?',
    answer: 'Signal Health is a 0-100 score measuring data reliability. It factors in data freshness, completeness, consistency, and anomaly detection. Scores above 70 are "Healthy" (green), 40-70 are "Degraded" (yellow), and below 40 are "Unhealthy" (red).',
    category: 'trust-engine',
  },
  {
    id: '8',
    question: 'What happens when Signal Health drops?',
    answer: 'When Signal Health drops below thresholds, the Trust Gate automatically blocks automated actions and alerts your team. This prevents optimizations based on unreliable data. You can still take manual actions with an override.',
    category: 'trust-engine',
  },
  {
    id: '9',
    question: 'Can I customize Trust Gate thresholds?',
    answer: 'Yes, on Growth plans and above. You can set custom thresholds per campaign, automation rule, or globally. Enterprise plans include advanced configuration with time-based rules and multi-signal gates.',
    category: 'trust-engine',
  },
  // Integrations
  {
    id: '10',
    question: 'How do I connect my ad accounts?',
    answer: 'Go to Tenant Settings → Connect Platforms. Click "Connect" on any platform to start the OAuth flow. You\'ll be redirected to the platform to grant permissions, then automatically returned to Stratum AI.',
    category: 'integrations',
  },
  {
    id: '11',
    question: 'What is CAPI and do I need it?',
    answer: 'CAPI (Conversions API) sends conversion events server-side directly to ad platforms. This bypasses browser limitations like ad blockers and iOS privacy restrictions. It improves match rates from ~42% to 70-90%, significantly boosting ROAS.',
    category: 'integrations',
  },
  {
    id: '12',
    question: 'Do you integrate with Slack?',
    answer: 'Yes! Our Slack integration sends real-time Trust Gate alerts, daily performance summaries, and anomaly notifications to your chosen channels. Configure it in Settings → Integrations.',
    category: 'integrations',
  },
  // Data & Privacy
  {
    id: '13',
    question: 'How do you handle my data?',
    answer: 'We follow strict data security practices: SOC 2 Type II compliant, AES-256 encryption at rest, TLS 1.3 in transit. We never sell your data or use it for anything other than providing our service to you.',
    category: 'data',
  },
  {
    id: '14',
    question: 'Are you GDPR and CCPA compliant?',
    answer: 'Yes. We\'re fully GDPR and CCPA compliant. Our CDP includes built-in consent management, data subject request handling, and automatic PII hashing for platform syncs. DPA available for all customers.',
    category: 'data',
  },
  {
    id: '15',
    question: 'Where is my data stored?',
    answer: 'Data is stored in AWS data centers. US customers use us-east-1, EU customers use eu-west-1. Enterprise plans can specify custom regions. All data is encrypted and backed up with 99.9% SLA.',
    category: 'data',
  },
  // Support
  {
    id: '16',
    question: 'What support options are available?',
    answer: 'Starter: Email support (48h response). Growth: Priority email + chat (24h response). Scale: Dedicated CSM + phone support (4h response). Enterprise: 24/7 support + SLA guarantees.',
    category: 'support',
  },
  {
    id: '17',
    question: 'Do you offer onboarding assistance?',
    answer: 'Yes! All plans include self-service onboarding with interactive guides. Growth and above get a 1-hour kickoff call. Scale and Enterprise receive full white-glove onboarding with dedicated implementation support.',
    category: 'support',
  },
  {
    id: '18',
    question: 'How can I contact the team?',
    answer: 'Email us at support@stratum.ai for support, sales@stratum.ai for sales inquiries, or use the in-app chat. Enterprise customers have direct Slack channels with our team.',
    category: 'support',
  },
];

export default function FAQ() {
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

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

  const getCategoryColor = (categoryId: string) => {
    const category = categories.find((c) => c.id === categoryId);
    return category?.color || 'text-white';
  };

  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(168, 85, 247, 0.1)',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              color: '#a855f7',
            }}
          >
            <QuestionMarkCircleIcon className="w-4 h-4" />
            Help Center
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Frequently Asked</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Questions
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto mb-8"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            Everything you need to know about Stratum AI. Can&apos;t find what you&apos;re looking for?{' '}
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
              className="w-full pl-12 pr-4 py-4 rounded-2xl text-white placeholder-white/40 outline-none transition-all focus:ring-2 focus:ring-purple-500/50"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
              }}
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
              return (
                <button
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={cn(
                    'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all',
                    isSelected
                      ? 'bg-white/10 text-white border border-white/20'
                      : 'text-white/60 hover:text-white hover:bg-white/5'
                  )}
                >
                  <Icon className={cn('w-4 h-4', isSelected ? category.color : '')} />
                  {category.name}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* FAQ Battle Cards */}
      <section className="py-12 px-6">
        <div className="max-w-4xl mx-auto">
          <div className="space-y-4">
            {filteredFaqs.length === 0 ? (
              <div className="text-center py-12">
                <QuestionMarkCircleIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
                <p className="text-white/60">No questions found matching your search.</p>
              </div>
            ) : (
              filteredFaqs.map((faq) => {
                const Icon = getCategoryIcon(faq.category);
                const isExpanded = expandedId === faq.id;

                return (
                  <div
                    key={faq.id}
                    className={cn(
                      'rounded-2xl transition-all cursor-pointer overflow-hidden',
                      isExpanded
                        ? 'bg-white/[0.08] border border-white/20 shadow-lg'
                        : 'bg-white/[0.04] border border-white/10 hover:bg-white/[0.06] hover:border-white/15'
                    )}
                    onClick={() => setExpandedId(isExpanded ? null : faq.id)}
                  >
                    {/* Card Header */}
                    <div className="p-6 flex items-start gap-4">
                      <div
                        className={cn(
                          'flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center',
                          isExpanded ? 'bg-purple-500/20' : 'bg-white/10'
                        )}
                      >
                        <Icon className={cn('w-5 h-5', getCategoryColor(faq.category))} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-4">
                          <h3 className="text-lg font-semibold text-white pr-4">{faq.question}</h3>
                          <div
                            className={cn(
                              'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors',
                              isExpanded ? 'bg-purple-500/20' : 'bg-white/10'
                            )}
                          >
                            {isExpanded ? (
                              <ChevronUpIcon className="w-4 h-4 text-purple-400" />
                            ) : (
                              <ChevronDownIcon className="w-4 h-4 text-white/60" />
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          <span
                            className={cn(
                              'text-xs px-2 py-0.5 rounded-full',
                              'bg-white/10 text-white/60'
                            )}
                          >
                            {categories.find((c) => c.id === faq.category)?.name}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Expanded Answer */}
                    {isExpanded && (
                      <div className="px-6 pb-6 pt-0">
                        <div className="ml-14 pl-4 border-l-2 border-purple-500/30">
                          <p className="text-white/70 leading-relaxed">{faq.answer}</p>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </section>

      {/* Contact CTA */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="p-8 rounded-3xl"
            style={{
              background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
              Still have questions?
            </h2>
            <p className="text-white/60 mb-6 max-w-xl mx-auto">
              Our team is here to help. Reach out and we&apos;ll get back to you as soon as possible.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/contact"
                className="px-6 py-3 rounded-xl font-semibold text-white transition-all hover:opacity-90"
                style={{
                  background: '#f97316',
                  boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
                }}
              >
                Contact Support
              </a>
              <a
                href="mailto:sales@stratum.ai"
                className="px-6 py-3 rounded-xl font-semibold text-white transition-all hover:bg-white/10"
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                }}
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
