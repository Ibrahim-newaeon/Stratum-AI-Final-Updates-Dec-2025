/**
 * CMS Pages Management
 * Manage static pages (About, Terms, Privacy, etc.)
 */

import { useState } from 'react';
import {
  PlusIcon,
  RectangleStackIcon,
  PencilSquareIcon,
  TrashIcon,
  XMarkIcon,
  GlobeAltIcon,
} from '@heroicons/react/24/outline';
import {
  CMSPage,
  PageCreate,
  PageUpdate,
  PageStatus,
  useAdminPages,
  useCreatePage,
  useUpdatePage,
  useDeletePage,
} from '@/api/cms';

const PAGE_STATUS_STYLES: Record<PageStatus, { label: string; color: string; bg: string }> = {
  draft: { label: 'Draft', color: 'text-gray-400', bg: 'bg-gray-500/20' },
  in_review: { label: 'In Review', color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  approved: { label: 'Approved', color: 'text-green-400', bg: 'bg-green-500/20' },
  published: { label: 'Published', color: 'text-emerald-400', bg: 'bg-emerald-500/20' },
  archived: { label: 'Archived', color: 'text-gray-500', bg: 'bg-gray-600/20' },
};

const TEMPLATES = [
  { value: 'default', label: 'Default' },
  { value: 'full-width', label: 'Full Width' },
  { value: 'sidebar', label: 'With Sidebar' },
  { value: 'landing', label: 'Landing Page' },
];

export default function CMSPages() {
  const { data, isLoading } = useAdminPages();
  const createMutation = useCreatePage();
  const updateMutation = useUpdatePage();
  const deleteMutation = useDeletePage();

  const [showEditor, setShowEditor] = useState(false);
  const [editingPage, setEditingPage] = useState<CMSPage | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [formData, setFormData] = useState<PageCreate>({
    title: '',
    slug: '',
    content: '',
    status: 'draft',
    template: 'default',
    show_in_navigation: false,
    navigation_order: 0,
  });

  const pages = data?.pages || [];

  const openEditor = (page?: CMSPage) => {
    if (page) {
      setEditingPage(page);
      setFormData({
        title: page.title,
        slug: page.slug,
        content: page.content || '',
        status: page.status,
        meta_title: page.meta_title || '',
        meta_description: page.meta_description || '',
        template: page.template,
        show_in_navigation: page.show_in_navigation,
        navigation_label: page.navigation_label || '',
        navigation_order: page.navigation_order,
      });
    } else {
      setEditingPage(null);
      setFormData({
        title: '',
        slug: '',
        content: '',
        status: 'draft',
        template: 'default',
        show_in_navigation: false,
        navigation_order: 0,
      });
    }
    setShowEditor(true);
  };

  const handleSave = () => {
    if (editingPage) {
      updateMutation.mutate(
        { id: editingPage.id, data: formData as PageUpdate },
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

  const generateSlug = (title: string) => {
    return title
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
          <h1 className="text-2xl font-bold text-white">Pages</h1>
          <p className="text-white/60 mt-1">Manage static website pages</p>
        </div>
        <button
          onClick={() => openEditor()}
          className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          New Page
        </button>
      </div>

      {/* Pages List */}
      <div className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
          </div>
        ) : pages.length === 0 ? (
          <div className="text-center py-20">
            <RectangleStackIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
            <p className="text-white/60 mb-4">No pages yet</p>
            <button
              onClick={() => openEditor()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
            >
              <PlusIcon className="w-4 h-4" />
              Create your first page
            </button>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {pages.map((page) => {
              const statusStyle = PAGE_STATUS_STYLES[page.status];
              return (
                <div
                  key={page.id}
                  className="flex items-center justify-between px-6 py-4 hover:bg-white/5 transition-colors"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500/20 to-purple-500/20 flex items-center justify-center flex-shrink-0">
                      <RectangleStackIcon className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-white font-medium truncate">{page.title}</p>
                      <div className="flex items-center gap-2 text-xs text-white/40">
                        <span>/{page.slug}</span>
                        <span>&middot;</span>
                        <span>{page.template}</span>
                        {page.show_in_navigation && (
                          <>
                            <span>&middot;</span>
                            <GlobeAltIcon className="w-3 h-3 inline" />
                            <span>In Nav</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-medium ${statusStyle.bg} ${statusStyle.color}`}
                    >
                      {statusStyle.label}
                    </span>
                    <button
                      onClick={() => openEditor(page)}
                      className="p-1.5 text-white/40 hover:text-white transition-colors"
                    >
                      <PencilSquareIcon className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(page.id)}
                      className="p-1.5 text-white/40 hover:text-red-400 transition-colors"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Page Editor Modal */}
      {showEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-neutral-900 border border-white/10 rounded-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h2 className="text-lg font-semibold text-white">
                {editingPage ? 'Edit Page' : 'Create New Page'}
              </h2>
              <button
                onClick={() => setShowEditor(false)}
                className="p-2 text-white/40 hover:text-white"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => {
                    const title = e.target.value;
                    setFormData((f) => ({
                      ...f,
                      title,
                      slug: f.slug || generateSlug(title),
                    }));
                  }}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="Page title"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Slug</label>
                <input
                  type="text"
                  value={formData.slug}
                  onChange={(e) => setFormData((f) => ({ ...f, slug: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="page-url-slug"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Content</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData((f) => ({ ...f, content: e.target.value }))}
                  rows={8}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none"
                  placeholder="HTML content for the page..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, status: e.target.value as PageStatus }))
                    }
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {Object.entries(PAGE_STATUS_STYLES).map(([val, { label }]) => (
                      <option key={val} value={val} className="bg-neutral-900">
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Template</label>
                  <select
                    value={formData.template}
                    onChange={(e) => setFormData((f) => ({ ...f, template: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {TEMPLATES.map((t) => (
                      <option key={t.value} value={t.value} className="bg-neutral-900">
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">
                  Meta Title
                </label>
                <input
                  type="text"
                  value={formData.meta_title || ''}
                  onChange={(e) => setFormData((f) => ({ ...f, meta_title: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="SEO title"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">
                  Meta Description
                </label>
                <textarea
                  value={formData.meta_description || ''}
                  onChange={(e) =>
                    setFormData((f) => ({ ...f, meta_description: e.target.value }))
                  }
                  rows={2}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none"
                  placeholder="SEO description"
                />
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.show_in_navigation}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, show_in_navigation: e.target.checked }))
                    }
                    className="w-4 h-4 rounded bg-white/5 border-white/20 text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-sm text-white/70">Show in navigation</span>
                </label>
                {formData.show_in_navigation && (
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-white/70">Order:</label>
                    <input
                      type="number"
                      value={formData.navigation_order || 0}
                      onChange={(e) =>
                        setFormData((f) => ({ ...f, navigation_order: Number(e.target.value) }))
                      }
                      className="w-20 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-purple-500/50"
                    />
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-3 p-4 border-t border-white/10">
              <button
                onClick={() => setShowEditor(false)}
                className="px-4 py-2 text-white/60 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={
                  !formData.title || createMutation.isPending || updateMutation.isPending
                }
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending
                  ? 'Saving...'
                  : editingPage
                    ? 'Update Page'
                    : 'Create Page'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-neutral-900 border border-white/10 rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-2">Delete Page</h3>
            <p className="text-white/60 mb-6">
              Are you sure? This action cannot be undone.
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
