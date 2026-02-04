/**
 * CMS Dashboard
 * Main overview page for the Content Management System
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowTrendingUpIcon,
  DocumentTextIcon,
  EnvelopeIcon,
  EyeIcon,
  PencilSquareIcon,
  PlusIcon,
  RectangleStackIcon,
  TagIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';
import { useAdminAuthors, useAdminContacts, useCategories, usePosts } from '@/api/cms';

interface StatCard {
  name: string;
  value: number;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  href: string;
  color: string;
  change?: number;
}

export default function CMSDashboard() {
  const { data: posts, isLoading: postsLoading } = usePosts();
  const { data: categories, isLoading: categoriesLoading } = useCategories();
  const { data: authors, isLoading: authorsLoading } = useAdminAuthors();
  const { data: contacts, isLoading: contactsLoading } = useAdminContacts();

  const isLoading = postsLoading || categoriesLoading || authorsLoading || contactsLoading;

  // Count published vs draft posts
  const publishedPosts = posts?.filter((p) => p.status === 'published').length || 0;
  const draftPosts = posts?.filter((p) => p.status === 'draft').length || 0;

  // Count unread contact submissions
  const unreadContacts = contacts?.filter((c) => !c.read).length || 0;

  const stats: StatCard[] = [
    {
      name: 'Total Posts',
      value: posts?.length || 0,
      icon: DocumentTextIcon,
      href: '/cms/posts',
      color: 'from-purple-500 to-purple-600',
    },
    {
      name: 'Categories',
      value: categories?.length || 0,
      icon: TagIcon,
      href: '/cms/categories',
      color: 'from-cyan-500 to-cyan-600',
    },
    {
      name: 'Authors',
      value: authors?.length || 0,
      icon: UserCircleIcon,
      href: '/cms/authors',
      color: 'from-orange-500 to-orange-600',
    },
    {
      name: 'Contact Messages',
      value: contacts?.length || 0,
      icon: EnvelopeIcon,
      href: '/cms/contacts',
      color: 'from-green-500 to-green-600',
    },
  ];

  const quickActions = [
    { name: 'New Post', href: '/cms/posts/new', icon: PlusIcon },
    { name: 'New Category', href: '/cms/categories/new', icon: TagIcon },
    { name: 'View Blog', href: '/blog', icon: EyeIcon, external: true },
    { name: 'Edit Features', href: '/cms/landing/features', icon: PencilSquareIcon },
  ];

  // Get recent posts for activity feed
  const recentPosts = posts?.slice(0, 5) || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">CMS Dashboard</h1>
        <p className="text-white/60 mt-2">
          Manage your website content, blog posts, and landing page sections.
        </p>
      </div>

      {/* Stats Grid */}
      <div
        className={`grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 ${isLoading ? 'opacity-50' : ''}`}
      >
        {stats.map((stat) => (
          <Link
            key={stat.name}
            to={stat.href}
            className="group relative overflow-hidden rounded-2xl bg-white/5 border border-white/10 p-6 hover:border-white/20 transition-all"
          >
            {/* Gradient accent */}
            <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${stat.color}`} />

            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-white/60">{stat.name}</p>
                <p className="text-3xl font-bold text-white mt-2">{stat.value}</p>
              </div>
              <div className={`p-3 rounded-xl bg-gradient-to-br ${stat.color} bg-opacity-20`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>

            {/* Hover indicator */}
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          </Link>
        ))}
      </div>

      {/* Content Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Post Status */}
        <div className="rounded-2xl bg-white/5 border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Content Status</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="text-white/80">Published Posts</span>
              </div>
              <span className="text-white font-medium">{publishedPosts}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-yellow-500" />
                <span className="text-white/80">Draft Posts</span>
              </div>
              <span className="text-white font-medium">{draftPosts}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-orange-500" />
                <span className="text-white/80">Unread Messages</span>
              </div>
              <span className="text-white font-medium">{unreadContacts}</span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-6">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-white/60">Published vs Draft</span>
              <span className="text-white/60">
                {posts?.length ? Math.round((publishedPosts / posts.length) * 100) : 0}% published
              </span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-green-500 to-green-600 transition-all"
                style={{
                  width: posts?.length ? `${(publishedPosts / posts.length) * 100}%` : '0%',
                }}
              />
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="rounded-2xl bg-white/5 border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-4">
            {quickActions.map((action) => (
              <Link
                key={action.name}
                to={action.href}
                target={action.external ? '_blank' : undefined}
                className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all"
              >
                <action.icon className="w-5 h-5 text-purple-400" />
                <span className="text-white font-medium">{action.name}</span>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="rounded-2xl bg-white/5 border border-white/10 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">Recent Posts</h2>
          <Link
            to="/cms/posts"
            className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
          >
            View all
          </Link>
        </div>

        {recentPosts.length > 0 ? (
          <div className="space-y-4">
            {recentPosts.map((post) => (
              <div
                key={post.id}
                className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10"
              >
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500/20 to-cyan-500/20 flex items-center justify-center flex-shrink-0">
                    <DocumentTextIcon className="w-5 h-5 text-purple-400" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white font-medium truncate">{post.title}</p>
                    <p className="text-sm text-white/50">
                      {post.author?.name || 'Unknown'} &middot;{' '}
                      {new Date(post.updatedAt || post.createdAt).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                      post.status === 'published'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-yellow-500/20 text-yellow-400'
                    }`}
                  >
                    {post.status}
                  </span>
                  <Link
                    to={`/cms/posts/${post.id}`}
                    className="text-white/40 hover:text-white transition-colors"
                  >
                    <PencilSquareIcon className="w-5 h-5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <DocumentTextIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
            <p className="text-white/60">No posts yet</p>
            <Link
              to="/cms/posts/new"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-lg bg-purple-500 text-white hover:bg-purple-600 transition-colors"
            >
              <PlusIcon className="w-4 h-4" />
              Create your first post
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
