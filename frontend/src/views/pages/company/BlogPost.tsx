/**
 * BlogPost Page
 * Individual blog post page - fetches from CMS API
 */

import { Link, useParams } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
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
        <div className="py-20 px-6">
          <div className="max-w-4xl mx-auto">
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
        </div>
      </PageLayout>
    );
  }

  if (error || !post) {
    return (
      <PageLayout>
        <div className="py-20 px-6">
          <div className="max-w-4xl mx-auto text-center">
            <h1 className="text-4xl font-bold text-white mb-4">Post Not Found</h1>
            <p className="text-lg mb-8" style={{ color: 'var(--landing-text)' }}>
              The blog post you're looking for doesn't exist or has been removed.
            </p>
            <Link
              to="/blog"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-full font-semibold text-white transition-opacity hover:opacity-90"
              style={{
                background: 'var(--landing-accent-coral)',
                boxShadow: '0 4px 20px rgba(255, 77, 77, 0.3)',
              }}
            >
              <ArrowLeftIcon className="w-5 h-5" />
              Back to Blog
            </Link>
          </div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      {/* Back Link */}
      <div className="py-6 px-6">
        <div className="max-w-4xl mx-auto">
          <Link
            to="/blog"
            className="inline-flex items-center gap-2 text-sm transition-colors hover:text-white"
            style={{ color: 'var(--landing-text)' }}
          >
            <ArrowLeftIcon className="w-4 h-4" />
            Back to Blog
          </Link>
        </div>
      </div>

      {/* Article Header */}
      <article className="py-8 px-6">
        <div className="max-w-4xl mx-auto">
          {/* Category and Reading Time */}
          <div className="flex items-center gap-4 mb-6">
            {post.category && (
              <span
                className="text-sm px-3 py-1 rounded-full"
                style={{
                  background: 'rgba(255, 179, 71, 0.1)',
                  color: 'var(--landing-accent-warm)',
                }}
              >
                {post.category.name}
              </span>
            )}
            {post.reading_time_minutes && (
              <span
                className="text-sm flex items-center gap-1"
                style={{ color: 'var(--landing-text-dim)' }}
              >
                <ClockIcon className="w-4 h-4" />
                {post.reading_time_minutes} min read
              </span>
            )}
          </div>

          {/* Title */}
          <h1
            className="text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-6"
            style={{ fontFamily: "Geist, system-ui, sans-serif" }}
          >
            {post.title}
          </h1>

          {/* Excerpt */}
          {post.excerpt && (
            <p className="text-lg md:text-xl mb-8" style={{ color: 'var(--landing-text)' }}>
              {post.excerpt}
            </p>
          )}

          {/* Meta Info */}
          <div
            className="flex flex-wrap items-center gap-6 pb-8 border-b"
            style={{
              borderColor: 'var(--landing-border)',
              color: 'rgba(139, 141, 158, 0.7)',
            }}
          >
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
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center"
                    style={{ background: 'rgba(255, 77, 77, 0.2)' }}
                  >
                    <UserIcon className="w-5 h-5 text-purple-400" />
                  </div>
                )}
                <div>
                  <p className="text-white font-medium">{post.author.name}</p>
                  {post.author.job_title && (
                    <p className="text-sm" style={{ color: 'var(--landing-text-dim)' }}>
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
              <img src={post.featured_image_url} alt={post.title} className="w-full h-auto"  loading="lazy" />
            </div>
          )}

          {/* Content */}
          <div
            className="prose prose-invert prose-lg max-w-none"
            style={{
              color: 'var(--landing-text-white-mid)',
            }}
            dangerouslySetInnerHTML={{ __html: sanitizeHtml(post.content || '') }}
          />

          {/* Tags */}
          {post.tags && post.tags.length > 0 && (
            <div
              className="mt-12 pt-8 border-t"
              style={{ borderColor: 'var(--landing-border)' }}
            >
              <div className="flex items-center gap-3 flex-wrap">
                <TagIcon className="w-5 h-5" style={{ color: 'var(--landing-text-dim)' }} />
                {post.tags.map((tag) => (
                  <span
                    key={tag.id}
                    className="px-3 py-1 rounded-full text-sm"
                    style={{
                      background: 'var(--landing-surface-glass)',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      color: '#8B8D9E',
                    }}
                  >
                    {tag.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Author Bio */}
          {post.author && post.author.bio && (
            <div
              className="mt-12 p-8 rounded-2xl"
              style={{
                background: 'var(--landing-card)',
                border: '1px solid var(--landing-border)',
              }}
            >
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
                  <div
                    className="w-16 h-16 rounded-full flex items-center justify-center"
                    style={{ background: 'rgba(255, 77, 77, 0.2)' }}
                  >
                    <UserIcon className="w-8 h-8 text-purple-400" />
                  </div>
                )}
                <div>
                  <h3 className="text-lg font-semibold text-white mb-1">
                    About {post.author.name}
                  </h3>
                  {post.author.job_title && (
                    <p className="text-sm mb-2" style={{ color: 'var(--landing-text-dim)' }}>
                      {post.author.job_title}
                    </p>
                  )}
                  <p style={{ color: 'var(--landing-text)' }}>{post.author.bio}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </article>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="p-12 rounded-3xl"
            style={{
              background: 'var(--landing-card)',
              border: '1px solid var(--landing-border)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">Ready to Get Started?</h2>
            <p className="text-lg mb-8" style={{ color: 'var(--landing-text)' }}>
              See how Stratum AI can help you optimize your marketing performance.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                to="/signup"
                className="px-6 py-3 rounded-full font-semibold text-white transition-opacity hover:opacity-90"
                style={{
                  background: 'var(--landing-accent-coral)',
                  boxShadow: '0 4px 20px rgba(255, 77, 77, 0.3)',
                }}
              >
                Start Free Trial
              </Link>
              <Link
                to="/contact"
                className="px-6 py-3 rounded-xl font-semibold transition-colors hover:bg-foreground/10"
                style={{
                  background: 'var(--landing-surface-glass)',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  color: '#ffffff',
                }}
              >
                Contact Sales
              </Link>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
