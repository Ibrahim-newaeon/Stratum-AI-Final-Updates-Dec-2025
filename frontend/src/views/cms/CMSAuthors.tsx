/**
 * CMS Authors Management
 * Manage blog post authors with profile details
 */

import { useState } from 'react';
import {
  PlusIcon,
  UserCircleIcon,
  PencilSquareIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import {
  CMSAuthor,
  AuthorCreate,
  AuthorUpdate,
  useAdminAuthors,
  useCreateAuthor,
  useUpdateAuthor,
  useDeleteAuthor,
} from '@/api/cms';

export default function CMSAuthors() {
  const { data, isLoading } = useAdminAuthors();
  const createMutation = useCreateAuthor();
  const updateMutation = useUpdateAuthor();
  const deleteMutation = useDeleteAuthor();

  const [showEditor, setShowEditor] = useState(false);
  const [editingAuthor, setEditingAuthor] = useState<CMSAuthor | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [formData, setFormData] = useState<AuthorCreate>({
    name: '',
    slug: '',
    email: '',
    bio: '',
    avatar_url: '',
    job_title: '',
    company: '',
    twitter_handle: '',
    linkedin_url: '',
    website_url: '',
    is_active: true,
  });

  const authors = data?.authors || [];

  const openEditor = (author?: CMSAuthor) => {
    if (author) {
      setEditingAuthor(author);
      setFormData({
        name: author.name,
        slug: author.slug,
        email: author.email || '',
        bio: author.bio || '',
        avatar_url: author.avatar_url || '',
        job_title: author.job_title || '',
        company: author.company || '',
        twitter_handle: author.twitter_handle || '',
        linkedin_url: author.linkedin_url || '',
        github_handle: author.github_handle || '',
        website_url: author.website_url || '',
        is_active: author.is_active,
      });
    } else {
      setEditingAuthor(null);
      setFormData({
        name: '',
        slug: '',
        email: '',
        bio: '',
        avatar_url: '',
        job_title: '',
        company: '',
        twitter_handle: '',
        linkedin_url: '',
        website_url: '',
        is_active: true,
      });
    }
    setShowEditor(true);
  };

  const handleSave = () => {
    if (editingAuthor) {
      updateMutation.mutate(
        { id: editingAuthor.id, data: formData as AuthorUpdate },
        { onSuccess: () => setShowEditor(false) }
      );
    } else {
      createMutation.mutate(formData, {
        onSuccess: () => setShowEditor(false),
      });
    }
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, {
      onSuccess: () => setDeleteConfirm(null),
    });
  };

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '')
      .replace(/[-\s]+/g, '-');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Authors</h1>
          <p className="text-white/60 mt-1">
            {authors.length} author{authors.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => openEditor()}
          className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          New Author
        </button>
      </div>

      {/* Authors Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
        </div>
      ) : authors.length === 0 ? (
        <div className="rounded-2xl bg-white/5 border border-white/10 text-center py-20">
          <UserCircleIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
          <p className="text-white/60 mb-4">No authors yet</p>
          <button
            onClick={() => openEditor()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            Add your first author
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {authors.map((author) => (
            <div
              key={author.id}
              className="rounded-2xl bg-white/5 border border-white/10 p-6 hover:border-white/20 transition-all group"
            >
              <div className="flex items-start gap-4">
                {author.avatar_url ? (
                  <img
                    src={author.avatar_url}
                    alt={author.name}
                    className="w-14 h-14 rounded-full object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="w-14 h-14 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center text-white text-xl font-bold flex-shrink-0">
                    {author.name.charAt(0)}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h3 className="text-white font-semibold truncate">{author.name}</h3>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => openEditor(author)}
                        className="p-1 text-white/40 hover:text-white"
                      >
                        <PencilSquareIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(author.id)}
                        className="p-1 text-white/40 hover:text-red-400"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  {author.job_title && (
                    <p className="text-sm text-white/50">
                      {author.job_title}
                      {author.company && ` at ${author.company}`}
                    </p>
                  )}
                  {author.bio && (
                    <p className="text-sm text-white/40 mt-2 line-clamp-2">{author.bio}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/5 text-xs text-white/40">
                <span>{author.email || 'No email'}</span>
                <span
                  className={`px-2 py-0.5 rounded-full ${author.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}
                >
                  {author.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Editor Modal */}
      {showEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-neutral-900 border border-white/10 rounded-xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-white/10 sticky top-0 bg-neutral-900 z-10">
              <h2 className="text-lg font-semibold text-white">
                {editingAuthor ? 'Edit Author' : 'New Author'}
              </h2>
              <button
                onClick={() => setShowEditor(false)}
                className="p-2 text-white/40 hover:text-white"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    setFormData((f) => ({
                      ...f,
                      name,
                      slug: f.slug || generateSlug(name),
                    }));
                  }}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="Author name"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Slug</label>
                <input
                  type="text"
                  value={formData.slug}
                  onChange={(e) => setFormData((f) => ({ ...f, slug: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="author-slug"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData((f) => ({ ...f, email: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="author@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Bio</label>
                <textarea
                  value={formData.bio}
                  onChange={(e) => setFormData((f) => ({ ...f, bio: e.target.value }))}
                  rows={3}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none"
                  placeholder="Short bio..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">
                  Avatar URL
                </label>
                <input
                  type="url"
                  value={formData.avatar_url}
                  onChange={(e) => setFormData((f) => ({ ...f, avatar_url: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="https://..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">
                    Job Title
                  </label>
                  <input
                    type="text"
                    value={formData.job_title}
                    onChange={(e) => setFormData((f) => ({ ...f, job_title: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="Content Writer"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">
                    Company
                  </label>
                  <input
                    type="text"
                    value={formData.company}
                    onChange={(e) => setFormData((f) => ({ ...f, company: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="Stratum AI"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Twitter</label>
                  <input
                    type="text"
                    value={formData.twitter_handle}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, twitter_handle: e.target.value }))
                    }
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="@handle"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">GitHub</label>
                  <input
                    type="text"
                    value={formData.github_handle}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, github_handle: e.target.value }))
                    }
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="username"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">
                  LinkedIn URL
                </label>
                <input
                  type="url"
                  value={formData.linkedin_url}
                  onChange={(e) => setFormData((f) => ({ ...f, linkedin_url: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="https://linkedin.com/in/..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Website</label>
                <input
                  type="url"
                  value={formData.website_url}
                  onChange={(e) => setFormData((f) => ({ ...f, website_url: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="https://..."
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData((f) => ({ ...f, is_active: e.target.checked }))}
                  className="w-4 h-4 rounded bg-white/5 border-white/20 text-purple-600 focus:ring-purple-500"
                />
                <span className="text-sm text-white/70">Active author</span>
              </label>
            </div>

            <div className="flex justify-end gap-3 p-4 border-t border-white/10 sticky bottom-0 bg-neutral-900">
              <button
                onClick={() => setShowEditor(false)}
                className="px-4 py-2 text-white/60 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={
                  !formData.name || createMutation.isPending || updateMutation.isPending
                }
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? 'Saving...'
                  : editingAuthor
                    ? 'Update'
                    : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-neutral-900 border border-white/10 rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-2">Delete Author</h3>
            <p className="text-white/60 mb-6">
              Posts by this author will become unassigned.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-white/60 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium disabled:opacity-50"
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
