/**
 * BlogPost Page — landing-themed (ink + ember).
 * Individual blog post page - fetches from CMS API.
 */

import { Link, useParams } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { MktCard } from '@/components/landing/marketing';
import { sanitizeHtml } from '@/lib/sanitize';
import {
  ArrowLeftIcon,
  CalendarIcon,
  ClockIcon,
  TagIcon,
  UserIcon,
} from '@heroicons/react/24/outline';
import { usePost } from '@/api/cms';

export default function BlogPost() {
  const { slug } = useParams<{ slug: string }>();
  const { data: post, isLoading, error } = usePost(slug || '');

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <PageLayout>
        <section className="py-20">
          <div className="max-w-3xl mx-auto px-6 lg:px-8">
            <div className="animate-pulse">
              <div className="h-8 bg-foreground/10 rounded w-3/4 mb-4" />
              <div className="h-4 bg-foreground/10 rounded w-1/2 mb-8" />
              <div className="space-y-4">
                {[...Array(8)].map((_, i) => (
                  <div key={i} className="h-4 bg-foreground/10 rounded w-full" />
                ))}
              </div>
            </div>
          </div>
        </section>
      </PageLayout>
    );
  }

  if (error || !post) {
    return (
      <PageLayout>
        <section className="py-20">
          <div className="max-w-3xl mx-auto px-6 lg:px-8 text-center">
            <h1 className="text-display-sm text-foreground mb-4">Post Not Found</h1>
            <p className="text-body text-muted-foreground mb-8">
              The blog post you&apos;re looking for doesn&apos;t exist or has been removed.
            </p>
            <Link
              to="/blog"
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-full bg-stratum-500 text-primary-foreground font-semibold text-body hover:brightness-110 hover:shadow-glow transition-all duration-200"
            >
              <ArrowLeftIcon className="w-5 h-5" />
              Back to Blog
            </Link>
          </div>
        </section>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      {/* Back Link */}
      <div className="py-6">
        <div className="max-w-3xl mx-auto px-6 lg:px-8">
          <Link
            to="/blog"
            className="inline-flex items-center gap-2 text-meta uppercase text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            Back to Blog
          </Link>
        </div>
      </div>

      {/* Article Header */}
      <article className="pb-24 lg:pb-28">
        <div className="max-w-3xl mx-auto px-6 lg:px-8">
          {/* Category and Reading Time */}
          <div className="flex items-center gap-4 mb-6">
            {post.category && (
              <span className="text-meta uppercase px-3 py-1 rounded-full bg-secondary/10 text-secondary">
                {post.category.name}
              </span>
            )}
            {post.reading_time_minutes && (
              <span className="text-meta uppercase text-muted-foreground flex items-center gap-1">
                <ClockIcon className="w-4 h-4" />
                {post.reading_time_minutes} min read
              </span>
            )}
          </div>

          {/* Title */}
          <h1 className="text-display-sm text-foreground mb-6">{post.title}</h1>

          {/* Excerpt */}
          {post.excerpt && (
            <p className="text-body text-muted-foreground mb-8">{post.excerpt}</p>
          )}

          {/* Meta Info */}
          <div className="flex flex-wrap items-center gap-6 pb-8 border-b border-border text-meta uppercase text-muted-foreground">
            {post.author && (
              <div className="flex items-center gap-3">
                {post.author.avatar_url ? (
                  <img
                    src={post.author.avatar_url}
                    alt={post.author.name}
                    className="w-10 h-10 rounded-full object-cover"
                    loading="lazy"
                    decoding="async"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-secondary/10 border border-secondary/20 flex items-center justify-center">
                    <UserIcon className="w-5 h-5 text-secondary" />
                  </div>
                )}
                <div>
                  <p className="text-foreground font-medium normal-case">{post.author.name}</p>
                  {post.author.job_title && (
                    <p className="text-meta uppercase text-muted-foreground">
                      {post.author.job_title}
                    </p>
                  )}
                </div>
              </div>
            )}
            <span className="flex items-center gap-2">
              <CalendarIcon className="w-5 h-5" />
              {formatDate(post.published_at || '')}
            </span>
          </div>

          {/* Featured Image */}
          {post.featured_image_url && (
            <div className="my-8 rounded-2xl overflow-hidden">
              <img
                src={post.featured_image_url}
                alt={post.title}
                className="w-full h-auto"
                loading="lazy"
              />
            </div>
          )}

          {/* Content */}
          <div
            className="mt-8 max-w-none text-body text-muted-foreground leading-relaxed space-y-4 [&_h2]:text-h2 [&_h2]:text-foreground [&_h2]:font-semibold [&_h2]:mt-8 [&_h2]:mb-3 [&_h3]:text-h3 [&_h3]:text-foreground [&_h3]:font-semibold [&_h3]:mt-6 [&_h3]:mb-2 [&_p]:text-body [&_p]:text-muted-foreground [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:space-y-2 [&_ol]:list-decimal [&_ol]:pl-6 [&_ol]:space-y-2 [&_a]:text-secondary [&_a:hover]:underline [&_strong]:text-foreground [&_strong]:font-semibold [&_blockquote]:border-l-2 [&_blockquote]:border-secondary [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground [&_blockquote]:italic [&_code]:font-mono [&_code]:text-foreground [&_img]:rounded-xl"
            dangerouslySetInnerHTML={{ __html: sanitizeHtml(post.content || '') }}
          />

          {/* Tags */}
          {post.tags && post.tags.length > 0 && (
            <div className="mt-12 pt-8 border-t border-border">
              <div className="flex items-center gap-3 flex-wrap">
                <TagIcon className="w-5 h-5 text-muted-foreground" />
                {post.tags.map((tag) => (
                  <span
                    key={tag.id}
                    className="px-3 py-1 rounded-full text-meta uppercase bg-card border border-border text-muted-foreground"
                  >
                    {tag.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Author Bio */}
          {post.author && post.author.bio && (
            <MktCard className="mt-12 p-8">
              <div className="flex items-start gap-4">
                {post.author.avatar_url ? (
                  <img
                    src={post.author.avatar_url}
                    alt={post.author.name}
                    className="w-16 h-16 rounded-full object-cover"
                    loading="lazy"
                    decoding="async"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-full bg-secondary/10 border border-secondary/20 flex items-center justify-center">
                    <UserIcon className="w-8 h-8 text-secondary" />
                  </div>
                )}
                <div>
                  <h3 className="text-h3 text-foreground font-semibold mb-1">
                    About {post.author.name}
                  </h3>
                  {post.author.job_title && (
                    <p className="text-meta uppercase text-muted-foreground mb-2">
                      {post.author.job_title}
                    </p>
                  )}
                  <p className="text-body text-muted-foreground">{post.author.bio}</p>
                </div>
              </div>
            </MktCard>
          )}
        </div>
      </article>

      <CTA />
    </PageLayout>
  );
}
