/**
 * Resources Hub Page — landing-themed (ink + ember).
 */

import { Link } from 'react-router-dom';
import { usePageContent, type ResourcesPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import {
  MktHero,
  MktSectionHeader,
  MktCard,
} from '@/components/landing/marketing';
import {
  AcademicCapIcon,
  ArrowDownTrayIcon,
  ArrowRightIcon,
  BookOpenIcon,
  CalendarIcon,
  DocumentTextIcon,
  NewspaperIcon,
  PlayIcon,
  PresentationChartBarIcon,
} from '@heroicons/react/24/outline';

const resourceCategories = [
  {
    title: 'Documentation',
    description: 'Technical guides and API references',
    icon: BookOpenIcon,
    href: '/docs',
    cta: 'Browse Docs',
  },
  {
    title: 'Case Studies',
    description: 'Success stories from our customers',
    icon: PresentationChartBarIcon,
    href: '/case-studies',
    cta: 'Read Stories',
  },
  {
    title: 'Blog',
    description: 'Latest news and industry insights',
    icon: NewspaperIcon,
    href: '/blog',
    cta: 'Read Blog',
  },
  {
    title: 'Changelog',
    description: 'Product updates and release notes',
    icon: DocumentTextIcon,
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
  },
  {
    title: 'CDP Implementation Playbook',
    description: 'Step-by-step guide to implementing your Customer Data Platform.',
    type: 'Playbook',
    readTime: '25 min',
  },
  {
    title: 'Signal Health Optimization',
    description: 'Best practices for maintaining healthy signal scores.',
    type: 'Guide',
    readTime: '12 min',
  },
  {
    title: 'Multi-Platform Audience Sync Setup',
    description: 'Configure audience sync across Meta, Google, TikTok, and Snapchat.',
    type: 'Tutorial',
    readTime: '10 min',
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
      <MktHero
        badge="Resources"
        badgeIcon={AcademicCapIcon}
        title="Learn, grow, and"
        highlight="succeed"
        subtitle="Everything you need to master trust-gated automation and transform your marketing performance."
      />

      {/* Category Cards */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {resourceCategories.map((cat, i) => (
              <MktCard
                key={cat.title}
                delay={(i % 4) * 0.05}
                className="group p-6 hover:-translate-y-1"
              >
                <Link to={cat.href} className="block">
                  <div className="w-12 h-12 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center mb-4">
                    <cat.icon className="w-6 h-6 text-secondary" />
                  </div>
                  <h3 className="text-h3 text-foreground font-semibold mb-1">{cat.title}</h3>
                  <p className="text-body text-muted-foreground mb-4">{cat.description}</p>
                  <div className="flex items-center gap-2 text-body font-medium text-secondary group-hover:gap-3 transition-all">
                    <span>{cat.cta}</span>
                    <ArrowRightIcon className="w-4 h-4" />
                  </div>
                </Link>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      {/* Guides & Tutorials */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="Learn"
            title="Guides &"
            highlight="tutorials"
          />
          <div className="grid md:grid-cols-2 gap-6">
            {guides.map((guide, i) => (
              <MktCard key={guide.title} delay={(i % 2) * 0.05} className="group p-6">
                <Link to="#" className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center flex-shrink-0">
                    <BookOpenIcon className="w-6 h-6 text-secondary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-micro uppercase font-medium px-2 py-0.5 rounded-full bg-secondary/10 text-secondary">
                        {guide.type}
                      </span>
                      {guide.readTime ? (
                        <span className="text-micro uppercase text-muted-foreground">
                          {guide.readTime} read
                        </span>
                      ) : null}
                    </div>
                    <h3 className="text-h3 text-foreground font-semibold group-hover:text-secondary transition-colors">
                      {guide.title}
                    </h3>
                    <p className="mt-1 text-body text-muted-foreground">{guide.description}</p>
                  </div>
                </Link>
              </MktCard>
            ))}
          </div>
          <div className="mt-8 text-center">
            <Link
              to="/docs"
              className="inline-flex items-center gap-2 text-body font-medium text-secondary hover:gap-3 transition-all"
            >
              <span>View All</span>
              <ArrowRightIcon className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* Webinars */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="Watch" title="Webinars" />
          <div className="grid md:grid-cols-3 gap-6">
            {webinars.map((webinar, i) => (
              <MktCard
                key={webinar.title}
                delay={(i % 3) * 0.05}
                className={`p-6 flex flex-col ${
                  webinar.isUpcoming ? 'border-secondary/40' : ''
                }`}
              >
                {webinar.isUpcoming && (
                  <span className="inline-flex items-center gap-1 self-start text-micro uppercase font-medium px-2 py-1 rounded-full bg-success/15 text-success mb-3">
                    <CalendarIcon className="w-3 h-3" />
                    Upcoming
                  </span>
                )}
                <h3 className="text-h3 text-foreground font-semibold mb-2">{webinar.title}</h3>
                <p className="text-body text-muted-foreground mb-3">
                  {webinar.date} • {webinar.time}
                </p>
                <p className="text-meta uppercase text-muted-foreground mb-4">
                  Speakers: {webinar.speakers.join(', ')}
                </p>
                <button
                  className="mt-auto inline-flex items-center gap-2 self-start text-body font-medium text-secondary hover:gap-3 transition-all"
                  type="button"
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
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      {/* Whitepapers */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="Download"
            title="Whitepapers &"
            highlight="reports"
          />
          <div className="grid md:grid-cols-3 gap-6">
            {whitepapers.map((paper, i) => (
              <MktCard key={paper.title} delay={(i % 3) * 0.05} className="p-6 flex flex-col">
                <div className="w-12 h-12 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center mb-4">
                  <DocumentTextIcon className="w-6 h-6 text-secondary" />
                </div>
                <h3 className="text-h3 text-foreground font-semibold mb-2">{paper.title}</h3>
                <p className="text-body text-muted-foreground mb-4">{paper.description}</p>
                <div className="mt-auto flex items-center justify-between">
                  <span className="text-micro uppercase text-muted-foreground">
                    {paper.pages} pages
                    {paper.downloads ? ` • ${paper.downloads} downloads` : ''}
                  </span>
                  <button
                    className="inline-flex items-center gap-1 text-body font-medium text-secondary hover:gap-2 transition-all"
                    type="button"
                  >
                    <ArrowDownTrayIcon className="w-4 h-4" />
                    Download
                  </button>
                </div>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
