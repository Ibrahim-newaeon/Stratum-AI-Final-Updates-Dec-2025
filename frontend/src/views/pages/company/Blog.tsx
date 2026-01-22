/**
 * Blog Page
 * Company blog and articles - fetches from CMS API
 */

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import { NewspaperIcon, CalendarIcon, UserIcon, ClockIcon } from '@heroicons/react/24/outline';
import { usePosts, useCategories } from '@/api/cms';

export default function Blog() {
  const [selectedCategory, setSelectedCategory] = useState<string | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: postsData, isLoading: postsLoading } = usePosts({
    category: selectedCategory,
    search: searchQuery || undefined,
    limit: 12,
  });

  const { data: categoriesData } = useCategories();

  const posts = postsData?.items || [];
  const categories = categoriesData || [];

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(59, 130, 246, 0.1)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              color: '#3b82f6',
            }}
          >
            <NewspaperIcon className="w-4 h-4" />
            Blog
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Insights &</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Resources
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            Latest news, guides, and insights from the Stratum AI team.
          </p>
        </div>
      </section>

      {/* Categories */}
      <section className="py-6 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-wrap gap-3 justify-center">
            <button
              onClick={() => setSelectedCategory(undefined)}
              className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
              style={{
                background: !selectedCategory ? '#f97316' : 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(255, 255, 255, 0.12)',
                color: '#ffffff',
              }}
            >
              All
            </button>
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.slug)}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                style={{
                  background:
                    selectedCategory === category.slug ? '#f97316' : 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#ffffff',
                }}
              >
                {category.name}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Posts Grid */}
      <section className="py-12 px-6">
        <div className="max-w-7xl mx-auto">
          {postsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(6)].map((_, i) => (
                <div
                  key={i}
                  className="p-6 rounded-2xl animate-pulse"
                  style={{
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                  }}
                >
                  <div className="h-4 bg-white/10 rounded w-1/4 mb-4" />
                  <div className="h-6 bg-white/10 rounded w-3/4 mb-3" />
                  <div className="h-4 bg-white/10 rounded w-full mb-2" />
                  <div className="h-4 bg-white/10 rounded w-2/3" />
                </div>
              ))}
            </div>
          ) : posts.length === 0 ? (
            <div className="text-center py-12">
              <p style={{ color: 'rgba(255, 255, 255, 0.6)' }}>No posts found.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {posts.map((post) => (
                <Link
                  key={post.id}
                  to={`/blog/${post.slug}`}
                  className="block"
                >
                  <article
                    className="p-6 rounded-2xl transition-all hover:scale-[1.02] cursor-pointer group h-full"
                    style={{
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                    }}
                  >
                    {post.featured_image_url && (
                      <div className="mb-4 rounded-lg overflow-hidden">
                        <img
                          src={post.featured_image_url}
                          alt={post.title}
                          className="w-full h-40 object-cover"
                        />
                      </div>
                    )}
                    <div className="flex items-center gap-2 mb-4">
                      {post.category && (
                        <span
                          className="text-xs px-2 py-1 rounded"
                          style={{
                            background: 'rgba(168, 85, 247, 0.1)',
                            color: '#a855f7',
                          }}
                        >
                          {post.category.name}
                        </span>
                      )}
                      {post.reading_time_minutes && (
                        <span
                          className="text-xs flex items-center gap-1"
                          style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                        >
                          <ClockIcon className="w-3 h-3" />
                          {post.reading_time_minutes} min read
                        </span>
                      )}
                    </div>
                    <h2 className="text-lg font-semibold text-white mb-3 group-hover:text-orange-500 transition-colors">
                      {post.title}
                    </h2>
                    {post.excerpt && (
                      <p className="text-sm mb-4" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                        {post.excerpt}
                      </p>
                    )}
                    <div
                      className="flex items-center gap-4 text-xs"
                      style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                    >
                      {post.author && (
                        <span className="flex items-center gap-1">
                          <UserIcon className="w-3 h-3" />
                          {post.author.name}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <CalendarIcon className="w-3 h-3" />
                        {formatDate(post.published_at || post.created_at)}
                      </span>
                    </div>
                  </article>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Newsletter CTA */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="p-12 rounded-3xl"
            style={{
              background:
                'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">Subscribe to Our Newsletter</h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              Get the latest insights and updates delivered to your inbox.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-4 py-3 rounded-xl text-white placeholder-white/40 outline-none"
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                }}
              />
              <button
                className="px-6 py-3 rounded-xl font-semibold text-white transition-all hover:opacity-90"
                style={{
                  background: '#f97316',
                  boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
                }}
              >
                Subscribe
              </button>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
