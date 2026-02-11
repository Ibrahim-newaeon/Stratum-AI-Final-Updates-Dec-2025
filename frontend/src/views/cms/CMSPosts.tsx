/**
 * CMS Posts Management
 * List, filter, search, and manage blog posts with workflow actions
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  DocumentTextIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import {
  AdminPostFilters,
  CMSPost,
  PostStatus,
  useAdminPosts,
  useDeletePost,
  usePublishPost,
  useUnpublishPost,
  useArchivePost,
  useSubmitForReview,
  WORKFLOW_STATUS_CONFIG,
} from '@/api/cms';

const STATUS_FILTERS: { value: PostStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'in_review', label: 'In Review' },
  { value: 'changes_requested', label: 'Changes Requested' },
  { value: 'approved', label: 'Approved' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'published', label: 'Published' },
  { value: 'unpublished', label: 'Unpublished' },
  { value: 'archived', label: 'Archived' },
  { value: 'rejected', label: 'Rejected' },
];

export default function CMSPosts() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<AdminPostFilters>({
    page: 1,
    page_size: 20,
  });
  const [search, setSearch] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const { data, isLoading } = useAdminPosts({
    ...filters,
    search: search || undefined,
  });
  const deleteMutation = useDeletePost();
  const publishMutation = usePublishPost();
  const unpublishMutation = useUnpublishPost();
  const archiveMutation = useArchivePost();
  const submitForReviewMutation = useSubmitForReview();

  const posts = data?.posts || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / (filters.page_size || 20));

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, {
      onSuccess: () => setDeleteConfirm(null),
    });
  };

  const getQuickAction = (post: CMSPost) => {
    switch (post.status) {
      case 'draft':
        return {
          label: 'Submit for Review',
          action: () => submitForReviewMutation.mutate({ postId: post.id }),
        };
      case 'approved':
        return {
          label: 'Publish',
          action: () => publishMutation.mutate(post.id),
        };
      case 'published':
        return {
          label: 'Unpublish',
          action: () => unpublishMutation.mutate(post.id),
        };
      case 'unpublished':
        return {
          label: 'Archive',
          action: () => archiveMutation.mutate(post.id),
        };
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Posts</h1>
          <p className="text-white/60 mt-1">
            {total} post{total !== 1 ? 's' : ''} total
          </p>
        </div>
        <Link
          to="/cms/posts/new"
          className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          New Post
        </Link>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setFilters((f) => ({ ...f, page: 1 }));
            }}
            placeholder="Search posts..."
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-purple-500/50"
          />
        </div>

        {/* Status Filter */}
        <div className="relative">
          <FunnelIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/40" />
          <select
            value={filters.status_filter || ''}
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                status_filter: (e.target.value as PostStatus) || undefined,
                page: 1,
              }))
            }
            className="pl-9 pr-8 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white appearance-none focus:outline-none focus:border-purple-500/50"
          >
            {STATUS_FILTERS.map((s) => (
              <option key={s.value} value={s.value} className="bg-neutral-900">
                {s.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Posts Table */}
      <div className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
          </div>
        ) : posts.length === 0 ? (
          <div className="text-center py-20">
            <DocumentTextIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
            <p className="text-white/60 mb-4">No posts found</p>
            <Link
              to="/cms/posts/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <PlusIcon className="w-4 h-4" />
              Create your first post
            </Link>
          </div>
        ) : (
          <>
            {/* Table Header */}
            <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-3 border-b border-white/10 text-xs font-medium text-white/50 uppercase tracking-wider">
              <div className="col-span-5">Title</div>
              <div className="col-span-2">Status</div>
              <div className="col-span-2">Author</div>
              <div className="col-span-1">Views</div>
              <div className="col-span-2 text-right">Actions</div>
            </div>

            {/* Posts List */}
            <div className="divide-y divide-white/5">
              {posts.map((post) => {
                const statusConfig = WORKFLOW_STATUS_CONFIG[post.status];
                const quickAction = getQuickAction(post);

                return (
                  <div
                    key={post.id}
                    className="grid grid-cols-1 md:grid-cols-12 gap-4 px-6 py-4 hover:bg-white/5 transition-colors items-center"
                  >
                    {/* Title */}
                    <div className="col-span-5 flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500/20 to-cyan-500/20 flex items-center justify-center flex-shrink-0">
                        <DocumentTextIcon className="w-5 h-5 text-purple-400" />
                      </div>
                      <div className="min-w-0">
                        <Link
                          to={`/cms/posts/${post.id}`}
                          className="text-white font-medium hover:text-purple-400 transition-colors truncate block"
                        >
                          {post.title}
                        </Link>
                        <p className="text-xs text-white/40 truncate">
                          /{post.slug} &middot; {post.content_type.replace('_', ' ')}
                          {post.is_featured && ' \u2022 Featured'}
                        </p>
                      </div>
                    </div>

                    {/* Status */}
                    <div className="col-span-2">
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusConfig.bgColor} ${statusConfig.color}`}
                      >
                        {statusConfig.label}
                      </span>
                    </div>

                    {/* Author */}
                    <div className="col-span-2 text-sm text-white/60 truncate">
                      {post.author?.name || 'Unassigned'}
                    </div>

                    {/* Views */}
                    <div className="col-span-1 text-sm text-white/60">
                      {post.view_count.toLocaleString()}
                    </div>

                    {/* Actions */}
                    <div className="col-span-2 flex items-center justify-end gap-2">
                      {quickAction && (
                        <button
                          onClick={quickAction.action}
                          className="px-3 py-1.5 text-xs font-medium bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-colors"
                        >
                          {quickAction.label}
                        </button>
                      )}
                      <button
                        onClick={() => navigate(`/cms/posts/${post.id}`)}
                        className="p-1.5 text-white/40 hover:text-white transition-colors"
                        title="Edit"
                      >
                        <PencilSquareIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(post.id)}
                        className="p-1.5 text-white/40 hover:text-red-400 transition-colors"
                        title="Delete"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-white/50">
            Page {filters.page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) - 1 }))}
              disabled={filters.page === 1}
              className="px-3 py-1.5 text-sm bg-white/5 border border-white/10 rounded-lg text-white/60 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setFilters((f) => ({ ...f, page: (f.page || 1) + 1 }))}
              disabled={filters.page === totalPages}
              className="px-3 py-1.5 text-sm bg-white/5 border border-white/10 rounded-lg text-white/60 hover:bg-white/10 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-neutral-900 border border-white/10 rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-2">Delete Post</h3>
            <p className="text-white/60 mb-6">
              Are you sure you want to delete this post? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-white/60 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
