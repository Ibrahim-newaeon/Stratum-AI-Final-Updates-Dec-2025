/**
 * Blog Page
 * Company blog and articles
 */

import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import { NewspaperIcon, CalendarIcon, UserIcon } from '@heroicons/react/24/outline';

const posts = [
  {
    title: 'Introducing Trust-Gated Autopilot: The Future of Marketing Automation',
    excerpt:
      'Learn how our new Trust-Gated Autopilot feature ensures automations only execute when your data is healthy.',
    author: 'Sarah Chen',
    date: 'Jan 15, 2026',
    category: 'Product',
    readTime: '5 min read',
  },
  {
    title: 'How Signal Health Monitoring Saved One Company $2M in Ad Spend',
    excerpt:
      'A case study on how real-time signal health monitoring prevented a major data quality issue from impacting campaign performance.',
    author: 'Marcus Rodriguez',
    date: 'Jan 10, 2026',
    category: 'Case Study',
    readTime: '8 min read',
  },
  {
    title: 'The Complete Guide to CDP Implementation in 2026',
    excerpt:
      'Everything you need to know about implementing a Customer Data Platform, from planning to activation.',
    author: 'Emily Watson',
    date: 'Jan 5, 2026',
    category: 'Guide',
    readTime: '12 min read',
  },
  {
    title: 'Multi-Platform Audience Sync: Best Practices for Match Rate Optimization',
    excerpt:
      'Tips and strategies for maximizing your audience match rates across Meta, Google, TikTok, and Snapchat.',
    author: 'David Kim',
    date: 'Dec 28, 2025',
    category: 'Tutorial',
    readTime: '7 min read',
  },
  {
    title: 'Understanding RFM Analysis for E-commerce Growth',
    excerpt:
      'How to use Recency, Frequency, and Monetary analysis to segment customers and drive revenue growth.',
    author: 'Lisa Thompson',
    date: 'Dec 20, 2025',
    category: 'Guide',
    readTime: '10 min read',
  },
  {
    title: 'The Rise of Privacy-First Marketing: What You Need to Know',
    excerpt:
      'Navigating the cookieless future with first-party data strategies and privacy-compliant audience targeting.',
    author: 'James Park',
    date: 'Dec 15, 2025',
    category: 'Industry',
    readTime: '6 min read',
  },
];

const categories = ['All', 'Product', 'Case Study', 'Guide', 'Tutorial', 'Industry'];

export default function Blog() {
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
            {categories.map((category) => (
              <button
                key={category}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                style={{
                  background: category === 'All' ? '#f97316' : 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                  color: '#ffffff',
                }}
              >
                {category}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Posts Grid */}
      <section className="py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {posts.map((post) => (
              <article
                key={post.title}
                className="p-6 rounded-2xl transition-all hover:scale-[1.02] cursor-pointer group"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <div className="flex items-center gap-2 mb-4">
                  <span
                    className="text-xs px-2 py-1 rounded"
                    style={{
                      background: 'rgba(168, 85, 247, 0.1)',
                      color: '#a855f7',
                    }}
                  >
                    {post.category}
                  </span>
                  <span className="text-xs" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                    {post.readTime}
                  </span>
                </div>
                <h2 className="text-lg font-semibold text-white mb-3 group-hover:text-orange-500 transition-colors">
                  {post.title}
                </h2>
                <p className="text-sm mb-4" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  {post.excerpt}
                </p>
                <div
                  className="flex items-center gap-4 text-xs"
                  style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                >
                  <span className="flex items-center gap-1">
                    <UserIcon className="w-3 h-3" />
                    {post.author}
                  </span>
                  <span className="flex items-center gap-1">
                    <CalendarIcon className="w-3 h-3" />
                    {post.date}
                  </span>
                </div>
              </article>
            ))}
          </div>
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
