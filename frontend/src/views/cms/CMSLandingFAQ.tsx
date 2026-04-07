/**
 * CMS Landing FAQ Editor
 * Manage FAQ items for the landing page
 */

import { useState } from 'react';
import {
  PlusIcon,
  QuestionMarkCircleIcon,
  PencilSquareIcon,
  TrashIcon,
  XMarkIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline';
import {
  FAQItem,
  useAllFAQItems,
  useCreatePost,
  useUpdatePost,
  useDeletePost,
} from '@/api/cms';

const FAQ_CATEGORIES = [
  { value: 'general', label: 'General' },
  { value: 'pricing', label: 'Pricing' },
  { value: 'features', label: 'Features' },
  { value: 'trust-engine', label: 'Trust Engine' },
  { value: 'integrations', label: 'Integrations' },
  { value: 'data', label: 'Data & Privacy' },
  { value: 'support', label: 'Support' },
];

export default function CMSLandingFAQ() {
  const { data: faqItems, isLoading } = useAllFAQItems();
  const createMutation = useCreatePost();
  const updateMutation = useUpdatePost();
  const deleteMutation = useDeletePost();

  const [showEditor, setShowEditor] = useState(false);
  const [editingFAQ, setEditingFAQ] = useState<FAQItem | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    question: '',
    answer: '',
    category: 'general',
    displayOrder: 0,
  });

  const items = faqItems || [];

  // Group by category
  const grouped = FAQ_CATEGORIES.map((cat) => ({
    ...cat,
    items: items.filter((item) => item.category === cat.value),
  })).filter((group) => group.items.length > 0);

  const openEditor = (faq?: FAQItem) => {
    if (faq) {
      setEditingFAQ(faq);
      setFormData({
        question: faq.question,
        answer: faq.answer,
        category: faq.category,
        displayOrder: faq.displayOrder,
      });
    } else {
      setEditingFAQ(null);
      setFormData({
        question: '',
        answer: '',
        category: 'general',
        displayOrder: items.length,
      });
    }
    setShowEditor(true);
  };

  const handleSave = () => {
    const postData = {
      title: formData.question,
      content: formData.answer,
      excerpt: formData.answer.substring(0, 200),
      status: 'published' as const,
      content_type: 'blog_post' as const,
      meta_title: JSON.stringify({
        faqCategory: formData.category,
        displayOrder: formData.displayOrder,
      }),
    };

    if (editingFAQ) {
      updateMutation.mutate(
        { id: editingFAQ.id, data: postData },
        { onSuccess: () => setShowEditor(false) }
      );
    } else {
      createMutation.mutate(postData, {
        onSuccess: () => setShowEditor(false),
      });
    }
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id, {
      onSuccess: () => setDeleteConfirm(null),
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Landing FAQ</h1>
          <p className="text-white/60 mt-1">{items.length} FAQ item{items.length !== 1 ? 's' : ''}</p>
        </div>
        <button
          onClick={() => openEditor()}
          className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          Add FAQ
        </button>
      </div>

      {/* FAQ List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl bg-white/5 border border-white/10 text-center py-20">
          <QuestionMarkCircleIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
          <p className="text-white/60 mb-4">No FAQ items yet</p>
          <button
            onClick={() => openEditor()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            Add first FAQ
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {grouped.map((group) => (
            <div key={group.value}>
              <h2 className="text-sm font-medium text-white/50 uppercase tracking-wider mb-3">
                {group.label} ({group.items.length})
              </h2>
              <div className="rounded-2xl bg-white/5 border border-white/10 divide-y divide-white/5 overflow-hidden">
                {group.items.map((faq) => (
                  <div key={faq.id} className="group">
                    <div className="flex items-center justify-between px-6 py-4">
                      <button
                        onClick={() => setExpandedId(expandedId === faq.id ? null : faq.id)}
                        className="flex items-center gap-3 flex-1 text-left min-w-0"
                      >
                        <ChevronDownIcon
                          className={`w-4 h-4 text-white/40 transition-transform flex-shrink-0 ${expandedId === faq.id ? 'rotate-180' : ''}`}
                        />
                        <span className="text-white font-medium truncate">{faq.question}</span>
                      </button>
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => openEditor(faq)}
                          className="p-1.5 text-white/40 hover:text-white"
                        >
                          <PencilSquareIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(faq.id)}
                          className="p-1.5 text-white/40 hover:text-red-400"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    {expandedId === faq.id && (
                      <div className="px-6 pb-4 pl-13">
                        <div className="ml-7 text-white/60 text-sm whitespace-pre-wrap">
                          {faq.answer}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Uncategorized */}
          {items.filter((i) => !FAQ_CATEGORIES.some((c) => c.value === i.category)).length > 0 && (
            <div>
              <h2 className="text-sm font-medium text-white/50 uppercase tracking-wider mb-3">
                Uncategorized
              </h2>
              <div className="rounded-2xl bg-white/5 border border-white/10 divide-y divide-white/5 overflow-hidden">
                {items
                  .filter((i) => !FAQ_CATEGORIES.some((c) => c.value === i.category))
                  .map((faq) => (
                    <div key={faq.id} className="flex items-center justify-between px-6 py-4 group">
                      <span className="text-white font-medium truncate">{faq.question}</span>
                      <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => openEditor(faq)}
                          className="p-1.5 text-white/40 hover:text-white"
                        >
                          <PencilSquareIcon className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(faq.id)}
                          className="p-1.5 text-white/40 hover:text-red-400"
                        >
                          <TrashIcon className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Editor Modal */}
      {showEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-neutral-900 border border-white/10 rounded-xl w-full max-w-lg">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h2 className="text-lg font-semibold text-white">
                {editingFAQ ? 'Edit FAQ' : 'Add FAQ'}
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
                <label className="block text-sm font-medium text-white/70 mb-1.5">
                  Question *
                </label>
                <input
                  type="text"
                  value={formData.question}
                  onChange={(e) => setFormData((f) => ({ ...f, question: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="What is...?"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Answer *</label>
                <textarea
                  value={formData.answer}
                  onChange={(e) => setFormData((f) => ({ ...f, answer: e.target.value }))}
                  rows={5}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none"
                  placeholder="The answer is..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">
                    Category
                  </label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData((f) => ({ ...f, category: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
                  >
                    {FAQ_CATEGORIES.map((cat) => (
                      <option key={cat.value} value={cat.value} className="bg-neutral-900">
                        {cat.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Order</label>
                  <input
                    type="number"
                    value={formData.displayOrder}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, displayOrder: Number(e.target.value) }))
                    }
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 p-4 border-t border-white/10">
              <button
                onClick={() => setShowEditor(false)}
                className="px-4 py-2 text-white/60 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={
                  !formData.question ||
                  !formData.answer ||
                  createMutation.isPending ||
                  updateMutation.isPending
                }
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-neutral-900 border border-white/10 rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-white mb-2">Delete FAQ</h3>
            <p className="text-white/60 mb-6">Remove this FAQ item from the landing page?</p>
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
