/**
 * Blog Page — landing-themed (ink + ember).
 * Company blog and articles - fetches from CMS API.
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { MktHero, MktCard } from '@/components/landing/marketing';
import { SEO } from '@/components/common/SEO';
import { CalendarIcon, ClockIcon, NewspaperIcon, UserIcon } from '@heroicons/react/24/outline';
import { useCategories, usePosts } from '@/api/cms';

export default function Blog() {
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);
  const [searchQuery] = useState('');

  const { data: postsData, isLoading: postsLoading } = usePosts({
    category_slug: selectedCategory,
    search: searchQuery || undefined,
    page_size: 12,
  });

  const { data: categoriesData } = useCategories();

  const posts = postsData?.posts || [];
  const categories = categoriesData?.categories || [];

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <PageLayout>
      <SEO
        title="Blog"
        description="Marketing intelligence insights, product updates, and best practices from the Stratum AI team."
        url="https://stratum-ai.com/blog"
      />

      <MktHero
        badge="Blog"
        badgeIcon={NewspaperIcon}
        title="Insights &"
        highlight="resources"
        subtitle="Latest news, guides, and insights from the Stratum AI team."
      />

      {/* Categories */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex flex-wrap gap-3 justify-center">
            <button
              onClick={() => setSelectedCategory(undefined)}
              className={`px-4 py-2 rounded-full text-meta uppercase font-medium border transition-colors ${
                !selectedCategory
                  ? 'bg-secondary/10 border-secondary/20 text-secondary'
                  : 'bg-card border-border text-muted-foreground hover:border-secondary/30'
              }`}
            >
              All
            </button>
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.slug)}
                className={`px-4 py-2 rounded-full text-meta uppercase font-medium border transition-colors ${
                  selectedCategory === category.slug
                    ? 'bg-secondary/10 border-secondary/20 text-secondary'
                    : 'bg-card border-border text-muted-foreground hover:border-secondary/30'
                }`}
              >
                {category.name}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Posts Grid */}
      <section className="pb-24 lg:pb-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          {postsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <MktCard key={i} className="p-6 animate-pulse">
                  <div className="h-4 bg-foreground/10 rounded w-1/4 mb-4" />
                  <div className="h-6 bg-foreground/10 rounded w-3/4 mb-3" />
                  <div className="h-4 bg-foreground/10 rounded w-full mb-2" />
                  <div className="h-4 bg-foreground/10 rounded w-2/3" />
                </MktCard>
              ))}
            </div>
          ) : posts.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-body text-muted-foreground">No posts found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {posts.map((post, i) => (
                <Link key={post.id} to={`/blog/${post.slug}`} className="block group">
                  <MktCard className="p-6 h-full" delay={(i % 3) * 0.05}>
                    {post.featured_image_url && (
                      <div className="mb-4 rounded-xl overflow-hidden">
                        <img
                          src={post.featured_image_url}
                          alt={post.title}
                          className="w-full h-40 object-cover"
                          loading="lazy"
                          decoding="async"
                        />
                      </div>
                    )}
                    <div className="flex items-center gap-2 mb-4">
                      {post.category && (
                        <span className="text-meta uppercase px-2 py-1 rounded bg-secondary/10 text-secondary">
                          {post.category.name}
                        </span>
                      )}
                      {post.reading_time_minutes && (
                        <span className="text-meta uppercase text-muted-foreground flex items-center gap-1">
                          <ClockIcon className="w-3 h-3" />
                          {post.reading_time_minutes} min read
                        </span>
                      )}
                    </div>
                    <h2 className="text-h3 text-foreground font-semibold mb-3 group-hover:text-secondary transition-colors">
                      {post.title}
                    </h2>
                    {post.excerpt && (
                      <p className="text-body text-muted-foreground mb-4">{post.excerpt}</p>
                    )}
                    <div className="flex items-center gap-4 text-meta uppercase text-muted-foreground">
                      {post.author && (
                        <span className="flex items-center gap-1">
                          <UserIcon className="w-3 h-3" />
                          {post.author.name}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <CalendarIcon className="w-3 h-3" />
                        {formatDate(post.published_at || '')}
                      </span>
                    </div>
                  </MktCard>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
