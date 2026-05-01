/**
 * Resources Hub Page
 * StratumAI Dark Enterprise Theme
 */

import { Link } from 'react-router-dom';
import { usePageContent, type ResourcesPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  AcademicCapIcon,
  ArrowDownTrayIcon,
  ArrowRightIcon,
  BookOpenIcon,
  CalendarIcon,
  DocumentTextIcon,
  MicrophoneIcon,
  NewspaperIcon,
  PlayIcon,
  PresentationChartBarIcon,
} from '@heroicons/react/24/outline';

const resourceCategories = [
  {
    title: 'Documentation',
    description: 'Technical guides and API references',
    icon: BookOpenIcon,
    color: 'var(--landing-accent-warm)',
    href: '/docs',
    cta: 'Browse Docs',
  },
  {
    title: 'Case Studies',
    description: 'Success stories from our customers',
    icon: PresentationChartBarIcon,
    color: 'var(--landing-accent-sky)',
    href: '/case-studies',
    cta: 'Read Stories',
  },
  {
    title: 'Blog',
    description: 'Latest news and industry insights',
    icon: NewspaperIcon,
    color: 'var(--landing-accent-teal)',
    href: '/blog',
    cta: 'Read Blog',
  },
  {
    title: 'Changelog',
    description: 'Product updates and release notes',
    icon: DocumentTextIcon,
    color: 'var(--landing-accent-amber)',
    href: '/changelog',
    cta: 'View Updates',
  },
];

const fallbackGuides = [
  {
    title: 'Complete Guide to Trust-Gated Automation',
    description: 'Learn how to set up and optimize trust gates for maximum performance.',
    type: 'Guide',
    readTime: '15 min',
    color: 'var(--landing-accent-warm)',
  },
  {
    title: 'CDP Implementation Playbook',
    description: 'Step-by-step guide to implementing your Customer Data Platform.',
    type: 'Playbook',
    readTime: '25 min',
    color: 'var(--landing-accent-sky)',
  },
  {
    title: 'Signal Health Optimization',
    description: 'Best practices for maintaining healthy signal scores.',
    type: 'Guide',
    readTime: '12 min',
    color: 'var(--landing-accent-teal)',
  },
  {
    title: 'Multi-Platform Audience Sync Setup',
    description: 'Configure audience sync across Meta, Google, TikTok, and Snapchat.',
    type: 'Tutorial',
    readTime: '10 min',
    color: 'var(--landing-accent-red)',
  },
];

const fallbackWebinars = [
  {
    title: 'Mastering Trust-Gated Automation in 2026',
    date: 'February 15, 2026',
    time: '11:00 AM EST',
    speakers: ['Sarah Chen, VP of Growth', 'Mike Rodriguez, Product Lead'],
    isUpcoming: true,
  },
  {
    title: 'CDP Best Practices for E-Commerce',
    date: 'January 28, 2026',
    time: 'On-Demand',
    speakers: ['Lisa Park, CDO', 'James Liu, Head of Growth'],
    isUpcoming: false,
  },
  {
    title: 'Predictive Analytics for Marketing Teams',
    date: 'January 10, 2026',
    time: 'On-Demand',
    speakers: ['Dr. Alex Kim, ML Engineer'],
    isUpcoming: false,
  },
];

const fallbackWhitepapers = [
  {
    title: 'The State of Marketing Automation 2026',
    description: 'Industry report on automation trends and best practices.',
    pages: 42,
    downloads: '5.2K',
  },
  {
    title: 'Signal Health: A New Framework for Ad Optimization',
    description: 'Technical whitepaper on our signal health methodology.',
    pages: 28,
    downloads: '3.8K',
  },
  {
    title: 'Privacy-First Customer Data Strategies',
    description: 'How to build effective CDP strategies in a privacy-focused world.',
    pages: 35,
    downloads: '4.1K',
  },
];

export default function ResourcesPage() {
  const { content } = usePageContent<ResourcesPageContent>('resources');

  // Use CMS data if available, otherwise fallback
  const guides = content?.guides?.length
    ? content.guides.map((g) => ({
        title: g.title,
        description: g.description,
        type: g.tag,
        readTime: '',
        color: 'var(--landing-accent-warm)',
      }))
    : fallbackGuides;

  const webinars = content?.webinars?.length
    ? content.webinars.map((w) => ({
        title: w.title,
        date: w.date,
        time: w.status === 'upcoming' ? 'TBD' : 'On-Demand',
        speakers: [] as string[],
        isUpcoming: w.status === 'upcoming',
      }))
    : fallbackWebinars;

  const whitepapers = content?.whitepapers?.length
    ? content.whitepapers.map((wp) => ({
        title: wp.title,
        description: wp.description,
        pages: wp.pages,
        downloads: '',
      }))
    : fallbackWhitepapers;

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
                  background: 'rgba(255, 107, 107, 0.1)',
                  border: '1px solid rgba(255, 107, 107, 0.2)',
                }}
              >
                <AcademicCapIcon className="w-4 h-4 text-[#FF6B6B]" />
                <span className="text-sm font-medium text-[#FF6B6B]">Resources</span>
              </div>

              <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
                Learn, Grow, and{' '}
                <span
                  style={{ color: 'var(--landing-accent-coral)' }}
                >
                  Succeed
                </span>
              </h1>

              <p className="text-lg" style={{ color: 'var(--landing-text)' }}>
                Everything you need to master trust-gated automation and transform your marketing
                performance.
              </p>
            </div>
          </div>
        </section>

        {/* Category Cards */}
        <section className="py-8">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              {resourceCategories.map((cat) => (
                <Link
                  key={cat.title}
                  to={cat.href}
                  className="group p-6 rounded-2xl transition-transform duration-300 hover:-translate-y-1"
                  style={{
                    background: 'var(--landing-card)',
                    border: '1px solid var(--landing-border)',
                  }}
                >
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                    style={{
                      background: `${cat.color}15`,
                      border: `1px solid ${cat.color}30`,
                    }}
                  >
                    <cat.icon className="w-6 h-6" style={{ color: cat.color }} />
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-1">{cat.title}</h3>
                  <p className="text-sm mb-4" style={{ color: 'var(--landing-text)' }}>{cat.description}</p>
                  <div
                    className="flex items-center gap-2 text-sm font-medium group-hover:gap-3 transition-colors"
                    style={{ color: cat.color }}
                  >
                    <span>{cat.cta}</span>
                    <ArrowRightIcon className="w-4 h-4" />
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* Guides & Tutorials */}
        <section className="py-16">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-2xl font-bold text-white">Guides & Tutorials</h2>
              <Link to="/docs" className="text-sm text-secondary hover:underline">
                View All
              </Link>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              {guides.map((guide) => (
                <Link
                  key={guide.title}
                  to="#"
                  className="group flex items-start gap-4 p-5 rounded-xl transition-colors duration-200 hover:bg-foreground/5"
                  style={{
                    background: 'var(--landing-card)',
                    border: '1px solid var(--landing-border)',
                  }}
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{
                      background: `${guide.color}15`,
                      border: `1px solid ${guide.color}30`,
                    }}
                  >
                    <BookOpenIcon className="w-5 h-5" style={{ color: guide.color }} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="text-xs font-medium px-2 py-0.5 rounded"
                        style={{
                          background: `${guide.color}20`,
                          color: guide.color,
                        }}
                      >
                        {guide.type}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--landing-text-dim)' }}>{guide.readTime} read</span>
                    </div>
                    <h4 className="text-white font-medium group-hover:text-[#FF5A1F] transition-colors">
                      {guide.title}
                    </h4>
                    <p className="text-sm mt-1" style={{ color: 'var(--landing-text)' }}>{guide.description}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* Webinars */}
        <section className="py-16">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-2xl font-bold text-white">Webinars</h2>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              {webinars.map((webinar) => (
                <div
                  key={webinar.title}
                  className="p-5 rounded-xl"
                  style={{
                    background: 'var(--landing-card)',
                    border: webinar.isUpcoming
                      ? '1px solid var(--landing-border)'
                      : '1px solid var(--landing-border)',
                  }}
                >
                  {webinar.isUpcoming && (
                    <span
                      className="inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded mb-3"
                      style={{ background: 'rgba(0, 255, 136, 0.2)', color: 'var(--landing-status-green)' }}
                    >
                      <CalendarIcon className="w-3 h-3" />
                      Upcoming
                    </span>
                  )}
                  <h4 className="text-white font-medium mb-2">{webinar.title}</h4>
                  <p className="text-sm mb-3" style={{ color: 'var(--landing-text-dim)' }}>
                    {webinar.date} • {webinar.time}
                  </p>
                  <p className="text-xs mb-4" style={{ color: 'var(--landing-text)' }}>
                    Speakers: {webinar.speakers.join(', ')}
                  </p>
                  <button
                    className="flex items-center gap-2 text-sm font-medium transition-colors"
                    style={{ color: webinar.isUpcoming ? 'var(--landing-accent-warm)' : 'var(--landing-accent-sky)' }}
                  >
                    {webinar.isUpcoming ? (
                      <>
                        <CalendarIcon className="w-4 h-4" />
                        Register Now
                      </>
                    ) : (
                      <>
                        <PlayIcon className="w-4 h-4" />
                        Watch Recording
                      </>
                    )}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Whitepapers */}
        <section className="py-16">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-2xl font-bold text-white">Whitepapers & Reports</h2>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              {whitepapers.map((paper) => (
                <div
                  key={paper.title}
                  className="p-5 rounded-xl"
                  style={{
                    background: 'var(--landing-card)',
                    border: '1px solid var(--landing-border)',
                  }}
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
                    style={{
                      background: 'rgba(255, 107, 107, 0.15)',
                      border: '1px solid rgba(255, 107, 107, 0.3)',
                    }}
                  >
                    <DocumentTextIcon className="w-5 h-5 text-[#FF6B6B]" />
                  </div>
                  <h4 className="text-white font-medium mb-2">{paper.title}</h4>
                  <p className="text-sm mb-3" style={{ color: 'var(--landing-text)' }}>{paper.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs" style={{ color: 'var(--landing-text-dim)' }}>
                      {paper.pages} pages • {paper.downloads} downloads
                    </span>
                    <button className="flex items-center gap-1 text-sm font-medium text-[#FF6B6B]">
                      <ArrowDownTrayIcon className="w-4 h-4" />
                      Download
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Newsletter CTA */}
        <section className="py-16">
          <div className="max-w-3xl mx-auto px-6 lg:px-8">
            <div
              className="p-8 rounded-2xl text-center"
              style={{
                background: 'var(--landing-card)',
                border: '1px solid var(--landing-border)',
              }}
            >
              <MicrophoneIcon className="w-10 h-10 mx-auto mb-4 text-secondary" />
              <h3 className="text-xl font-bold text-white mb-2">Stay in the Loop</h3>
              <p className="mb-6" style={{ color: 'var(--landing-text)' }}>
                Get the latest resources, guides, and product updates delivered to your inbox.
              </p>
              <div className="flex gap-3 max-w-md mx-auto">
                <input
                  type="email"
                  placeholder="Enter your email"
                  className="flex-1 px-4 py-3 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#FF5A1F]/50"
                  style={{
                    background: 'var(--landing-bg)',
                    border: '1px solid var(--landing-border)',
                  }}
                />
                <button
                  className="px-6 py-3 rounded-full font-semibold text-white transition-colors duration-200"
                  style={{
                    background: 'var(--landing-accent-coral)',
                    boxShadow: 'var(--landing-glow-coral)',
                  }}
                >
                  Subscribe
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </PageLayout>
  );
}
