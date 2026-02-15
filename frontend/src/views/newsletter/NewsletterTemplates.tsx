/**
 * Newsletter Email Templates Library
 *
 * Browse, create, edit, and delete email templates.
 * Templates can be applied when creating new campaigns.
 */

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  DocumentDuplicateIcon,
  EnvelopeIcon,
  InboxIcon,
} from '@heroicons/react/24/outline';
import {
  useTemplates,
  useCreateTemplate,
  useUpdateTemplate,
  useDeleteTemplate,
} from '@/api/newsletter';
import type {
  NewsletterTemplate,
  TemplateCategory,
  TemplateCreate,
  TemplateUpdate,
} from '@/api/newsletter';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CATEGORIES: { value: TemplateCategory | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'promotional', label: 'Promotional' },
  { value: 'transactional', label: 'Transactional' },
  { value: 'update', label: 'Update' },
  { value: 'announcement', label: 'Announcement' },
];

const categoryColors: Record<TemplateCategory, { text: string; bg: string }> = {
  promotional: { text: 'text-purple-400', bg: 'bg-purple-500/10' },
  transactional: { text: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  update: { text: 'text-amber-400', bg: 'bg-amber-500/10' },
  announcement: { text: 'text-pink-400', bg: 'bg-pink-500/10' },
};

const INPUT_CLS =
  'bg-white/5 border border-white/[0.08] rounded-xl px-4 py-2.5 text-white placeholder:text-white/30 focus:border-[#00c7be] focus:outline-none w-full';

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function NewsletterTemplates() {
  const navigate = useNavigate();
  const { data: templates = [], isLoading } = useTemplates();
  const deleteMutation = useDeleteTemplate();

  const [activeCategory, setActiveCategory] = useState<TemplateCategory | 'all'>('all');
  const [modalState, setModalState] = useState<
    | { mode: 'closed' }
    | { mode: 'create' }
    | { mode: 'edit'; template: NewsletterTemplate }
  >({ mode: 'closed' });
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const filtered = useMemo(() => {
    if (activeCategory === 'all') return templates;
    return templates.filter((t) => t.category === activeCategory);
  }, [templates, activeCategory]);

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this template? This cannot be undone.')) {
      return;
    }
    setDeletingId(id);
    try {
      await deleteMutation.mutateAsync(id);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* ---------------------------------------------------------------- */}
      {/* Header                                                           */}
      {/* ---------------------------------------------------------------- */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <h2 className="text-xl font-semibold text-[rgba(245,245,247,0.92)]">Email Templates</h2>
        <button
          onClick={() => setModalState({ mode: 'create' })}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#00c7be] hover:bg-[#00b3ab] text-white font-medium rounded-xl transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          Create Template
        </button>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Category Filter Tabs                                             */}
      {/* ---------------------------------------------------------------- */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setActiveCategory(cat.value)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              activeCategory === cat.value
                ? 'bg-[rgba(0,199,190,0.15)] text-[#00c7be]'
                : 'text-white/60 hover:text-white/80'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* Loading State                                                    */}
      {/* ---------------------------------------------------------------- */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="bg-white/5 border border-white/[0.08] rounded-2xl overflow-hidden animate-pulse"
            >
              <div className="h-40 bg-white/[0.03]" />
              <div className="p-4 space-y-3">
                <div className="h-4 bg-white/[0.06] rounded w-3/4" />
                <div className="h-3 bg-white/[0.04] rounded w-1/2" />
                <div className="flex gap-2">
                  <div className="h-5 bg-white/[0.04] rounded-full w-20" />
                  <div className="h-5 bg-white/[0.04] rounded-full w-16" />
                </div>
                <div className="h-8 bg-white/[0.04] rounded-lg w-full mt-2" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Empty State                                                      */}
      {/* ---------------------------------------------------------------- */}
      {!isLoading && filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
            <InboxIcon className="w-8 h-8 text-white/30" />
          </div>
          <h3 className="text-lg font-medium text-[rgba(245,245,247,0.92)] mb-1">
            No templates yet
          </h3>
          <p className="text-[rgba(245,245,247,0.6)] text-sm max-w-sm mb-6">
            Create your first email template to speed up campaign creation. Templates let you reuse
            designs and content across campaigns.
          </p>
          <button
            onClick={() => setModalState({ mode: 'create' })}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#00c7be] hover:bg-[#00b3ab] text-white font-medium rounded-xl transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            Create Template
          </button>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Template Grid                                                    */}
      {/* ---------------------------------------------------------------- */}
      {!isLoading && filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <AnimatePresence mode="popLayout">
            {filtered.map((template) => {
              const catStyle = categoryColors[template.category];
              return (
                <motion.div
                  key={template.id}
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="bg-white/5 border border-white/[0.08] rounded-2xl overflow-hidden hover:border-white/[0.15] transition-colors group"
                >
                  {/* Preview Area */}
                  <div className="relative h-40 bg-white/[0.02] overflow-hidden">
                    {template.content_html ? (
                      <div
                        className="origin-top-left pointer-events-none opacity-80 p-2"
                        style={{ transform: 'scale(0.45)', width: '222%', height: '222%' }}
                      >
                        <div
                          dangerouslySetInnerHTML={{ __html: template.content_html }}
                          className="bg-white text-black rounded"
                        />
                      </div>
                    ) : (
                      <div className="flex items-center justify-center h-full">
                        <EnvelopeIcon className="w-10 h-10 text-white/10" />
                      </div>
                    )}
                    {/* Overlay gradient for readability */}
                    <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-[rgba(11,18,21,0.9)] to-transparent" />
                  </div>

                  {/* Info Section */}
                  <div className="p-4 space-y-2">
                    <h3 className="font-semibold text-[rgba(245,245,247,0.92)] truncate">
                      {template.name}
                    </h3>
                    {template.subject && (
                      <p className="text-sm text-[rgba(245,245,247,0.6)] truncate">
                        {template.subject}
                      </p>
                    )}
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${catStyle.bg} ${catStyle.text}`}
                      >
                        {template.category}
                      </span>
                      {!template.is_active && (
                        <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400">
                          Inactive
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[rgba(245,245,247,0.4)]">
                      Updated {new Date(template.updated_at).toLocaleDateString()}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="px-4 pb-4 flex items-center gap-2">
                    <button
                      onClick={() =>
                        navigate(
                          `/dashboard/newsletter/campaigns/new?template=${template.id}`
                        )
                      }
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-[rgba(0,199,190,0.12)] text-[#00c7be] rounded-lg text-sm font-medium hover:bg-[rgba(0,199,190,0.2)] transition-colors"
                    >
                      <DocumentDuplicateIcon className="w-4 h-4" />
                      Use Template
                    </button>
                    <button
                      onClick={() => setModalState({ mode: 'edit', template })}
                      className="p-2 text-[rgba(245,245,247,0.6)] hover:bg-white/5 rounded-lg transition-colors"
                      title="Edit template"
                    >
                      <PencilIcon className="w-4 h-4" />
                    </button>
                    <button
                      disabled={deletingId === template.id}
                      onClick={() => handleDelete(template.id)}
                      className="p-2 text-[rgba(245,245,247,0.6)] hover:bg-red-500/10 hover:text-red-400 rounded-lg transition-colors disabled:opacity-40"
                      title="Delete template"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Create / Edit Modal                                              */}
      {/* ---------------------------------------------------------------- */}
      <AnimatePresence>
        {modalState.mode !== 'closed' && (
          <TemplateModal
            mode={modalState.mode}
            template={modalState.mode === 'edit' ? modalState.template : undefined}
            onClose={() => setModalState({ mode: 'closed' })}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create / Edit Modal
// ---------------------------------------------------------------------------

interface TemplateModalProps {
  mode: 'create' | 'edit';
  template?: NewsletterTemplate;
  onClose: () => void;
}

function TemplateModal({ mode, template, onClose }: TemplateModalProps) {
  const createMutation = useCreateTemplate();
  const updateMutation = useUpdateTemplate();

  const [form, setForm] = useState<{
    name: string;
    subject: string;
    preheader_text: string;
    content_html: string;
    category: TemplateCategory;
    is_active: boolean;
  }>({
    name: template?.name ?? '',
    subject: template?.subject ?? '',
    preheader_text: template?.preheader_text ?? '',
    content_html: template?.content_html ?? '',
    category: template?.category ?? 'promotional',
    is_active: template?.is_active ?? true,
  });

  const [saving, setSaving] = useState(false);

  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (mode === 'create') {
        const payload: TemplateCreate = {
          name: form.name,
          subject: form.subject || undefined,
          preheader_text: form.preheader_text || undefined,
          content_html: form.content_html || undefined,
          category: form.category,
        };
        await createMutation.mutateAsync(payload);
      } else if (template) {
        const payload: TemplateUpdate = {
          name: form.name,
          subject: form.subject || undefined,
          preheader_text: form.preheader_text || undefined,
          content_html: form.content_html || undefined,
          category: form.category,
          is_active: form.is_active,
        };
        await updateMutation.mutateAsync({ id: template.id, data: payload });
      }
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm overflow-y-auto"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-2xl bg-[#0b1215]/95 backdrop-blur-xl border border-white/[0.08] rounded-2xl p-6 my-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold text-[rgba(245,245,247,0.92)]">
            {mode === 'create' ? 'Create Template' : 'Edit Template'}
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors"
          >
            <XMarkIcon className="w-5 h-5 text-[rgba(245,245,247,0.6)]" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-[rgba(245,245,247,0.6)] mb-1.5">
              Template Name
            </label>
            <input
              type="text"
              required
              placeholder="e.g., Monthly Product Update"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              className={INPUT_CLS}
            />
          </div>

          {/* Subject */}
          <div>
            <label className="block text-sm font-medium text-[rgba(245,245,247,0.6)] mb-1.5">
              Subject Line
            </label>
            <input
              type="text"
              placeholder="Email subject"
              value={form.subject}
              onChange={(e) => set('subject', e.target.value)}
              className={INPUT_CLS}
            />
          </div>

          {/* Preheader */}
          <div>
            <label className="block text-sm font-medium text-[rgba(245,245,247,0.6)] mb-1.5">
              Preheader Text
            </label>
            <input
              type="text"
              placeholder="Preview text shown in inbox"
              value={form.preheader_text}
              onChange={(e) => set('preheader_text', e.target.value)}
              className={INPUT_CLS}
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-[rgba(245,245,247,0.6)] mb-1.5">
              Category
            </label>
            <select
              value={form.category}
              onChange={(e) => set('category', e.target.value as TemplateCategory)}
              className={INPUT_CLS}
            >
              <option value="promotional">Promotional</option>
              <option value="transactional">Transactional</option>
              <option value="update">Update</option>
              <option value="announcement">Announcement</option>
            </select>
          </div>

          {/* Active toggle (edit only) */}
          {mode === 'edit' && (
            <label className="flex items-center gap-3 cursor-pointer">
              <div
                className={`relative w-10 h-6 rounded-full transition-colors ${
                  form.is_active ? 'bg-[#00c7be]' : 'bg-white/10'
                }`}
                onClick={() => set('is_active', !form.is_active)}
              >
                <div
                  className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                    form.is_active ? 'translate-x-4' : ''
                  }`}
                />
              </div>
              <span className="text-sm text-[rgba(245,245,247,0.6)]">Active</span>
            </label>
          )}

          {/* HTML Content */}
          <div>
            <label className="block text-sm font-medium text-[rgba(245,245,247,0.6)] mb-1.5">
              HTML Content
            </label>
            <textarea
              rows={10}
              placeholder="<html>&#10;  <body>&#10;    <h1>Hello!</h1>&#10;  </body>&#10;</html>"
              value={form.content_html}
              onChange={(e) => set('content_html', e.target.value)}
              className={`${INPUT_CLS} resize-y font-mono text-sm`}
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 bg-white/5 border border-white/[0.08] rounded-xl text-[rgba(245,245,247,0.6)] hover:bg-white/[0.08] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || !form.name.trim()}
              className="flex-1 px-4 py-2.5 bg-[#00c7be] hover:bg-[#00b3ab] text-white font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving
                ? 'Saving...'
                : mode === 'create'
                  ? 'Create Template'
                  : 'Save Changes'}
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}
