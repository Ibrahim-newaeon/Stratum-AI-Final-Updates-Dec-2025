/**
 * Documentation Portal Page
 * 2026 Theme - Electric Neon / OLED-Optimized
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  AcademicCapIcon,
  ArrowRightIcon,
  BookOpenIcon,
  CloudIcon,
  CodeBracketIcon,
  CpuChipIcon,
  MagnifyingGlassIcon,
  PlayIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

const docCategories = [
  {
    title: 'Getting Started',
    description: 'Quick start guides to get you up and running',
    icon: PlayIcon,
    color: '#00FF88',
    links: [
      { name: 'Quick Start Guide', href: '/docs/quickstart' },
      { name: 'Installation', href: '/docs/installation' },
      { name: 'Authentication', href: '/docs/auth' },
      { name: 'First Campaign', href: '/docs/first-campaign' },
    ],
  },
  {
    title: 'API Reference',
    description: 'Complete API documentation with examples',
    icon: CodeBracketIcon,
    color: '#8B5CF6',
    links: [
      { name: 'REST API', href: '/api-docs' },
      { name: 'Webhooks', href: '/docs/webhooks' },
      { name: 'SDKs', href: '/docs/sdks' },
      { name: 'Rate Limits', href: '/docs/rate-limits' },
    ],
  },
  {
    title: 'Trust Engine',
    description: 'Learn about our trust-gated automation',
    icon: ShieldCheckIcon,
    color: '#00D4FF',
    links: [
      { name: 'Signal Health', href: '/docs/signal-health' },
      { name: 'Trust Gates', href: '/docs/trust-gates' },
      { name: 'Autopilot Rules', href: '/docs/autopilot' },
      { name: 'Thresholds', href: '/docs/thresholds' },
    ],
  },
  {
    title: 'CDP',
    description: 'Customer Data Platform documentation',
    icon: CpuChipIcon,
    color: '#FF6B6B',
    links: [
      { name: 'Profiles', href: '/docs/cdp/profiles' },
      { name: 'Segments', href: '/docs/cdp/segments' },
      { name: 'Identity Resolution', href: '/docs/cdp/identity' },
      { name: 'Audience Sync', href: '/docs/cdp/audience-sync' },
    ],
  },
  {
    title: 'Integrations',
    description: 'Connect with ad platforms and tools',
    icon: CloudIcon,
    color: '#FFB800',
    links: [
      { name: 'Meta Ads', href: '/docs/integrations/meta' },
      { name: 'Google Ads', href: '/docs/integrations/google' },
      { name: 'TikTok Ads', href: '/docs/integrations/tiktok' },
      { name: 'CRM Systems', href: '/docs/integrations/crm' },
    ],
  },
  {
    title: 'Tutorials',
    description: 'Step-by-step guides and best practices',
    icon: AcademicCapIcon,
    color: '#A78BFA',
    links: [
      { name: 'Video Tutorials', href: '/docs/tutorials/videos' },
      { name: 'Use Cases', href: '/docs/tutorials/use-cases' },
      { name: 'Best Practices', href: '/docs/tutorials/best-practices' },
      { name: 'Troubleshooting', href: '/docs/tutorials/troubleshooting' },
    ],
  },
];

const popularArticles = [
  { title: 'Setting up your first Trust Gate', views: '12.5K', time: '5 min' },
  { title: 'Understanding Signal Health scores', views: '10.2K', time: '8 min' },
  { title: 'Connecting Meta Ads API', views: '9.8K', time: '4 min' },
  { title: 'Building dynamic segments in CDP', views: '8.4K', time: '6 min' },
  { title: 'Configuring Autopilot rules', views: '7.9K', time: '7 min' },
];

export default function DocsPage() {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <PageLayout>
      <div className="min-h-screen">
        {/* Hero Section */}
        <section className="relative py-20 overflow-hidden">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto">
              <div
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-6"
                style={{
                  background: 'rgba(139, 92, 246, 0.1)',
                  border: '1px solid rgba(139, 92, 246, 0.2)',
                }}
              >
                <BookOpenIcon className="w-4 h-4 text-[#8B5CF6]" />
                <span className="text-sm font-medium text-[#8B5CF6]">Documentation</span>
              </div>

              <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
                Learn how to build with{' '}
                <span
                  style={{
                    background: 'linear-gradient(135deg, #8B5CF6 0%, #00D4FF 50%, #FF6B6B 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                  }}
                >
                  Stratum AI
                </span>
              </h1>

              <p className="text-lg text-gray-400 mb-8">
                Comprehensive guides, API references, and tutorials to help you integrate and
                maximize the power of trust-gated automation.
              </p>

              {/* Search Bar */}
              <div className="relative max-w-xl mx-auto">
                <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search documentation..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 rounded-xl text-white placeholder-gray-500 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-[#8B5CF6]/50"
                  style={{
                    background: 'rgba(10, 10, 15, 0.8)',
                    border: '1px solid rgba(139, 92, 246, 0.2)',
                  }}
                />
              </div>
            </div>
          </div>
        </section>

        {/* Documentation Categories */}
        <section className="py-16">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {docCategories.map((category) => (
                <div
                  key={category.title}
                  className="group p-6 rounded-2xl transition-all duration-300 hover:-translate-y-1"
                  style={{
                    background: 'rgba(10, 10, 15, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                    style={{
                      background: `${category.color}15`,
                      border: `1px solid ${category.color}30`,
                    }}
                  >
                    <category.icon className="w-6 h-6" style={{ color: category.color }} />
                  </div>

                  <h3 className="text-xl font-semibold text-white mb-2">{category.title}</h3>
                  <p className="text-gray-400 text-sm mb-4">{category.description}</p>

                  <ul className="space-y-2">
                    {category.links.map((link) => (
                      <li key={link.name}>
                        <Link
                          to={link.href}
                          className="flex items-center gap-2 text-sm text-gray-300 hover:text-white transition-colors group/link"
                        >
                          <ArrowRightIcon className="w-3 h-3 opacity-0 -translate-x-2 group-hover/link:opacity-100 group-hover/link:translate-x-0 transition-all" />
                          <span>{link.name}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Popular Articles */}
        <section className="py-16">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <h2 className="text-2xl font-bold text-white mb-8">Popular Articles</h2>

            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {popularArticles.map((article, index) => (
                <Link
                  key={article.title}
                  to="#"
                  className="flex items-center gap-4 p-4 rounded-xl transition-all duration-200 hover:bg-white/5 group"
                  style={{
                    background: 'rgba(10, 10, 15, 0.4)',
                    border: '1px solid rgba(255, 255, 255, 0.04)',
                  }}
                >
                  <span className="text-2xl font-bold text-gray-600">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <div className="flex-1">
                    <h4 className="text-white font-medium group-hover:text-[#8B5CF6] transition-colors">
                      {article.title}
                    </h4>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{article.views} views</span>
                      <span>{article.time} read</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16">
          <div className="max-w-4xl mx-auto px-6 lg:px-8">
            <div
              className="rounded-2xl p-8 md:p-12 text-center"
              style={{
                background:
                  'linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(0, 212, 255, 0.05) 100%)',
                border: '1px solid rgba(139, 92, 246, 0.2)',
              }}
            >
              <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
                Can't find what you're looking for?
              </h2>
              <p className="text-gray-400 mb-8">
                Our support team is here to help you with any questions.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/contact"
                  className="px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200"
                  style={{
                    background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                    boxShadow: '0 4px 20px rgba(139, 92, 246, 0.3)',
                  }}
                >
                  Contact Support
                </Link>
                <Link
                  to="/faq"
                  className="px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200"
                  style={{
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }}
                >
                  View FAQ
                </Link>
              </div>
            </div>
          </div>
        </section>
      </div>
    </PageLayout>
  );
}
