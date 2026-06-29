/**
 * Dynamic documentation article page — landing-themed (ink + ember).
 * Serves every `/docs/*` route from the content registry.
 */

import { useEffect } from 'react';
import { Link, useParams } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { SEO } from '@/components/common/SEO';
import { usePublicPage } from '@/api/cms';
import { sanitizeHtml } from '@/lib/sanitize';
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import { docsNav, getDocArticle, docArticleOrder, docArticles } from './registry';
import type { DocBlock } from './types';

function calloutClasses(tone: 'info' | 'warning' | 'success' | undefined): string {
  switch (tone) {
    case 'warning':
      return 'bg-warning/10 border-warning/30 text-warning';
    case 'success':
      return 'bg-success/10 border-success/30 text-success';
    default:
      return 'bg-accent/10 border-accent/30 text-accent';
  }
}

function Block({ block }: { block: DocBlock }) {
  switch (block.type) {
    case 'heading':
      return (
        <h2 className="text-h2 text-foreground font-semibold mt-10 mb-4 scroll-mt-28">
          {block.text}
        </h2>
      );
    case 'subheading':
      return <h3 className="text-h3 text-foreground font-semibold mt-7 mb-2">{block.text}</h3>;
    case 'paragraph':
      return <p className="text-body text-muted-foreground leading-relaxed mb-4">{block.text}</p>;
    case 'list':
      return block.ordered ? (
        <ol className="list-decimal pl-6 space-y-2 mb-4 text-body text-muted-foreground">
          {block.items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ol>
      ) : (
        <ul className="list-disc pl-6 space-y-2 mb-4 text-body text-muted-foreground">
          {block.items.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      );
    case 'code':
      return (
        <div className="mb-5 rounded-xl border border-border bg-card overflow-hidden">
          {block.language ? (
            <div className="px-4 py-2 border-b border-border text-micro uppercase tracking-wide text-muted-foreground font-mono">
              {block.language}
            </div>
          ) : null}
          <pre className="p-4 overflow-x-auto">
            <code className="font-mono text-meta text-foreground whitespace-pre">{block.code}</code>
          </pre>
        </div>
      );
    case 'callout':
      return (
        <div className={`mb-5 flex gap-3 rounded-xl border p-4 ${calloutClasses(block.tone)}`}>
          {block.tone === 'warning' ? (
            <ExclamationTriangleIcon className="w-5 h-5 flex-shrink-0 mt-0.5" />
          ) : (
            <InformationCircleIcon className="w-5 h-5 flex-shrink-0 mt-0.5" />
          )}
          <div>
            {block.title ? <p className="font-semibold mb-1">{block.title}</p> : null}
            <p className="text-body text-foreground/90 leading-relaxed">{block.text}</p>
          </div>
        </div>
      );
    default:
      return null;
  }
}

function DocNotFound({ slug }: { slug: string }) {
  return (
    <PageLayout>
      <SEO title="Documentation Not Found" description="That documentation page could not be found." noIndex />
      <section className="py-24 lg:py-32">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <p className="text-meta uppercase text-secondary mb-3">Documentation</p>
          <h1 className="text-display-xs md:text-display-sm text-foreground mb-4">
            We couldn&apos;t find <span className="text-gradient-primary">that page</span>
          </h1>
          <p className="text-body text-muted-foreground mb-2">
            There&apos;s no documentation article at
          </p>
          <p className="font-mono text-meta text-foreground/80 mb-8 break-all">/docs/{slug}</p>
          <Link
            to="/docs"
            className="inline-flex items-center gap-2 px-7 py-3.5 rounded-full bg-stratum-500 text-primary-foreground font-semibold text-body hover:brightness-110 hover:shadow-glow transition-all duration-200"
          >
            <ArrowLeftIcon className="w-5 h-5" />
            Back to docs
          </Link>
        </div>
      </section>
    </PageLayout>
  );
}

export default function DocArticlePage() {
  const params = useParams();
  const slug = (params['*'] ?? '').replace(/^\/+|\/+$/g, '');
  const article = getDocArticle(slug);
  // CMS override: a published page with slug `docs-<slug-with-dashes>` wins over
  // the built-in article, mirroring the fallback pattern used across the
  // marketing site. `usePublicPage` returns null when absent, so the code
  // content remains the default.
  const cmsSlug = slug ? `docs-${slug.replace(/\//g, '-')}` : '';
  const { data: cmsPage } = usePublicPage(cmsSlug);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [slug]);

  if (!article && !cmsPage) {
    return <DocNotFound slug={slug} />;
  }

  const title = article?.title ?? cmsPage?.title ?? 'Documentation';
  const category = article?.category ?? 'Docs';
  const description = article?.description ?? cmsPage?.meta_description ?? '';
  const readTime = article?.readTime;
  const cmsHtml = cmsPage?.content;
  const orderSlug = article?.slug ?? slug;

  const idx = docArticleOrder.indexOf(orderSlug);
  const prevSlug = idx > 0 ? docArticleOrder[idx - 1] : undefined;
  const nextSlug = idx >= 0 && idx < docArticleOrder.length - 1 ? docArticleOrder[idx + 1] : undefined;
  const prev = prevSlug ? docArticles[prevSlug] : undefined;
  const next = nextSlug ? docArticles[nextSlug] : undefined;

  return (
    <PageLayout>
      <SEO
        title={`${title} — Docs`}
        description={description}
        url={`https://stratumai.app/docs/${orderSlug}`}
      />

      <div className="max-w-7xl mx-auto px-6 lg:px-8 pt-12 pb-24">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-meta text-muted-foreground mb-8" aria-label="Breadcrumb">
          <Link to="/docs" className="hover:text-secondary transition-colors">
            Docs
          </Link>
          <span aria-hidden="true">/</span>
          <span className="text-foreground/70">{category}</span>
        </nav>

        <div className="grid lg:grid-cols-[16rem_1fr] gap-10 lg:gap-14">
          {/* Sidebar */}
          <aside className="hidden lg:block">
            <div className="sticky top-28 space-y-7">
              {docsNav.map((cat) => (
                <div key={cat.title}>
                  <p className="text-meta uppercase text-muted-foreground mb-2">{cat.title}</p>
                  <ul className="space-y-1.5 border-l border-border">
                    {cat.links.map((link) => {
                      const active = link.href === `/docs/${orderSlug}`;
                      return (
                        <li key={link.href}>
                          <Link
                            to={link.href}
                            className={`-ml-px block border-l pl-3 py-0.5 text-body transition-colors ${
                              active
                                ? 'border-secondary text-secondary font-medium'
                                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-foreground/30'
                            }`}
                          >
                            {link.name}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </div>
          </aside>

          {/* Article */}
          <article className="min-w-0 max-w-3xl">
            <p className="text-meta uppercase text-secondary mb-3">{category}</p>
            <h1 className="text-display-xs md:text-display-sm text-foreground mb-4">{title}</h1>
            {description ? (
              <p className="text-body text-muted-foreground leading-relaxed mb-3">{description}</p>
            ) : null}
            <div className="flex items-center gap-2 text-meta text-muted-foreground mb-10 pb-8 border-b border-border">
              {readTime ? (
                <>
                  <ClockIcon className="w-4 h-4" />
                  <span>{readTime} read</span>
                </>
              ) : (
                <span>Documentation</span>
              )}
            </div>

            {cmsHtml ? (
              <div
                className="text-body text-muted-foreground leading-relaxed [&_h2]:text-h2 [&_h2]:text-foreground [&_h2]:font-semibold [&_h2]:mt-10 [&_h2]:mb-4 [&_h3]:text-h3 [&_h3]:text-foreground [&_h3]:font-semibold [&_h3]:mt-7 [&_h3]:mb-2 [&_p]:mb-4 [&_strong]:text-foreground [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:mb-4 [&_ul]:space-y-2 [&_ol]:list-decimal [&_ol]:pl-6 [&_ol]:mb-4 [&_ol]:space-y-2 [&_a]:text-secondary [&_a:hover]:underline [&_code]:font-mono [&_code]:text-foreground [&_pre]:bg-card [&_pre]:border [&_pre]:border-border [&_pre]:rounded-xl [&_pre]:p-4 [&_pre]:overflow-x-auto [&_pre]:mb-5 [&_blockquote]:bg-secondary/5 [&_blockquote]:rounded-lg [&_blockquote]:px-4 [&_blockquote]:py-2 [&_blockquote]:my-5"
                dangerouslySetInnerHTML={{ __html: sanitizeHtml(cmsHtml) }}
              />
            ) : article ? (
              <div>
                {article.blocks.map((block, i) => (
                  <Block key={i} block={block} />
                ))}
              </div>
            ) : null}

            {/* Prev / next */}
            <div className="mt-14 pt-8 border-t border-border grid sm:grid-cols-2 gap-4">
              {prev ? (
                <Link
                  to={`/docs/${prev.slug}`}
                  className="group rounded-2xl bg-card border border-border p-5 hover:border-secondary/30 transition-colors"
                >
                  <span className="flex items-center gap-1.5 text-meta text-muted-foreground mb-1">
                    <ArrowLeftIcon className="w-3.5 h-3.5" /> Previous
                  </span>
                  <span className="text-body text-foreground font-medium group-hover:text-secondary transition-colors">
                    {prev.title}
                  </span>
                </Link>
              ) : (
                <span />
              )}
              {next ? (
                <Link
                  to={`/docs/${next.slug}`}
                  className="group rounded-2xl bg-card border border-border p-5 hover:border-secondary/30 transition-colors text-right"
                >
                  <span className="flex items-center justify-end gap-1.5 text-meta text-muted-foreground mb-1">
                    Next <ArrowRightIcon className="w-3.5 h-3.5" />
                  </span>
                  <span className="text-body text-foreground font-medium group-hover:text-secondary transition-colors">
                    {next.title}
                  </span>
                </Link>
              ) : (
                <span />
              )}
            </div>
          </article>
        </div>
      </div>

      <CTA />
    </PageLayout>
  );
}
