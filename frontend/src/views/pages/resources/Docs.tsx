/**
 * Documentation Portal Page — landing-themed (ink + ember).
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { usePublicPage } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { MktHero, MktSectionHeader, MktCard } from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';
import { sanitizeHtml } from '@/lib/sanitize';
import { BookOpenIcon, MagnifyingGlassIcon, ArrowRightIcon } from '@heroicons/react/24/outline';
import { docsNav as docCategories } from './docs/registry';

const popularArticles = [
  { title: 'Setting up your first Trust Gate', views: '12.5K', time: '5 min' },
  { title: 'Understanding Signal Health scores', views: '10.2K', time: '8 min' },
  { title: 'Connecting Meta Ads API', views: '9.8K', time: '4 min' },
  { title: 'Building dynamic segments in CDP', views: '8.4K', time: '6 min' },
  { title: 'Configuring Autopilot rules', views: '7.9K', time: '7 min' },
];

export default function DocsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const { data: page } = usePublicPage('docs');
  const hasCMSContent = !!(page?.content && page.content.length > 0);

  const seoTitle = page?.meta_title || pageSEO.docs.title;
  const seoDescription = page?.meta_description || pageSEO.docs.description;

  return (
    <PageLayout>
      <SEO {...pageSEO.docs} title={seoTitle} description={seoDescription} url="https://stratum-ai.com/docs" />

      <MktHero
        badge="Documentation"
        badgeIcon={BookOpenIcon}
        title="Learn how to build with"
        highlight="Stratum AI"
        subtitle="Comprehensive guides, API references, and tutorials to help you integrate and maximize the power of trust-gated automation."
      >
        <div
          className="mt-10 relative max-w-xl mx-auto animate-enter"
          style={{ animationDelay: '0.35s' }}
        >
          <MagnifyingGlassIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search documentation..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 pr-4 py-4 rounded-xl bg-card border border-border text-foreground placeholder:text-muted-foreground transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>
      </MktHero>

      {/* Content */}
      {hasCMSContent ? (
        <section className="pb-24">
          <div className="max-w-4xl mx-auto px-6">
            <MktCard className="p-8 md:p-10">
              <div
                className="space-y-4 text-body text-muted-foreground [&_h2]:text-h2 [&_h2]:text-foreground [&_h2]:font-semibold [&_h2]:mt-6 [&_h2]:mb-3 [&_h3]:text-h3 [&_h3]:text-foreground [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-6 [&_a]:text-secondary"
                dangerouslySetInnerHTML={{ __html: sanitizeHtml(page!.content!) }}
              />
            </MktCard>
          </div>
        </section>
      ) : (
        <>
          {/* Documentation Categories */}
          <section className="pb-12">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
              <MktSectionHeader
                eyebrow="Browse the docs"
                title="Find your"
                highlight="answers"
                subtitle="Guides, references, and tutorials organized by topic — from first setup to advanced automation."
              />
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {docCategories.map((category, i) => (
                  <MktCard key={category.title} delay={(i % 3) * 0.05} className="p-6">
                    <div className="w-12 h-12 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center mb-4">
                      <category.icon className="w-6 h-6 text-secondary" />
                    </div>

                    <h3 className="text-h3 text-foreground font-semibold mb-2">{category.title}</h3>
                    <p className="text-body text-muted-foreground mb-4">{category.description}</p>

                    <ul className="space-y-2">
                      {category.links.map((link) => (
                        <li key={link.name}>
                          <Link
                            to={link.href}
                            className="flex items-center gap-2 text-body text-muted-foreground hover:text-secondary transition-colors group/link"
                          >
                            <ArrowRightIcon className="w-3 h-3 opacity-0 -translate-x-2 group-hover/link:opacity-100 group-hover/link:translate-x-0 transition-transform" />
                            <span>{link.name}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </MktCard>
                ))}
              </div>
            </div>
          </section>

          {/* Popular Articles */}
          <section className="py-24 lg:py-28">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
              <h2 className="text-h1 text-foreground font-semibold mb-8">Popular Articles</h2>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {popularArticles.map((article, index) => (
                  <Link key={article.title} to="#" className="group">
                    <MktCard className="flex items-center gap-4 p-4">
                      <span className="text-h2 font-semibold text-muted-foreground/50">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                      <div className="flex-1">
                        <h4 className="text-foreground font-medium group-hover:text-secondary transition-colors">
                          {article.title}
                        </h4>
                        <div className="flex items-center gap-3 mt-1 text-micro text-muted-foreground">
                          <span>{article.views} views</span>
                          <span>{article.time} read</span>
                        </div>
                      </div>
                    </MktCard>
                  </Link>
                ))}
              </div>
            </div>
          </section>

          <CTA />
        </>
      )}
    </PageLayout>
  );
}
