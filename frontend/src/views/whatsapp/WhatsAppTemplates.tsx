/**
 * WhatsApp Templates Manager
 * Create, manage, and submit message templates to Meta for approval
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PlusIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  PencilIcon,
  TrashIcon,
  EyeIcon,
  PaperAirplaneIcon,
  XMarkIcon,
  PhotoIcon,
  VideoCameraIcon,
  DocumentIcon,
  ChatBubbleLeftIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

interface Template {
  id: number;
  name: string;
  language: string;
  category: 'MARKETING' | 'UTILITY' | 'AUTHENTICATION';
  header_type: string | null;
  header_content: string | null;
  body_text: string;
  footer_text: string | null;
  buttons: { type: string; text: string; url?: string; phone?: string }[];
  status: 'pending' | 'approved' | 'rejected';
  rejection_reason: string | null;
  usage_count: number;
  created_at: string;
}


const statusConfig = {
  approved: {
    label: 'Approved',
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    icon: CheckCircleIcon,
  },
  pending: { label: 'Pending', color: 'text-yellow-400', bg: 'bg-yellow-500/10', icon: ClockIcon },
  rejected: { label: 'Rejected', color: 'text-red-400', bg: 'bg-red-500/10', icon: XCircleIcon },
};

const categoryConfig = {
  MARKETING: { label: 'Marketing', color: 'text-purple-400', bg: 'bg-purple-500/10' },
  UTILITY: { label: 'Utility', color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  AUTHENTICATION: { label: 'Authentication', color: 'text-orange-400', bg: 'bg-orange-500/10' },
};

export default function WhatsAppTemplates() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState<Template | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const filteredTemplates = templates.filter((t) => {
    const matchesCategory = categoryFilter === 'all' || t.category === categoryFilter;
    const matchesStatus = statusFilter === 'all' || t.status === statusFilter;
    return matchesCategory && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">Message Templates</h2>
          <p className="text-gray-400 text-sm">
            {templates.filter((t) => t.status === 'approved').length} approved •{' '}
            {templates.filter((t) => t.status === 'pending').length} pending approval
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#25D366] to-[#128C7E] rounded-xl hover:opacity-90 transition-opacity"
        >
          <PlusIcon className="w-4 h-4" />
          Create Template
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="flex gap-2">
          <span className="text-sm text-gray-400 self-center">Category:</span>
          {['all', 'MARKETING', 'UTILITY', 'AUTHENTICATION'].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm transition-colors',
                categoryFilter === cat
                  ? 'bg-[#25D366] text-white'
                  : 'bg-[rgba(255,_255,_255,_0.05)] text-gray-400 hover:text-white'
              )}
            >
              {cat === 'all' ? 'All' : categoryConfig[cat as keyof typeof categoryConfig]?.label}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <span className="text-sm text-gray-400 self-center">Status:</span>
          {['all', 'approved', 'pending', 'rejected'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm transition-colors',
                statusFilter === status
                  ? 'bg-[#25D366] text-white'
                  : 'bg-[rgba(255,_255,_255,_0.05)] text-gray-400 hover:text-white'
              )}
            >
              {status === 'all' ? 'All' : statusConfig[status as keyof typeof statusConfig]?.label}
            </button>
          ))}
        </div>
      </div>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTemplates.map((template) => {
          const status = statusConfig[template.status];
          const category = categoryConfig[template.category];
          const StatusIcon = status.icon;

          return (
            <motion.div
              key={template.id}
              layout
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-[rgba(255,_255,_255,_0.05)] rounded-2xl border border-white/5 p-5 hover:border-white/10 transition-colors"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold mb-1">{template.name}</h3>
                  <div className="flex gap-2">
                    <span
                      className={cn('px-2 py-0.5 rounded text-xs', category.bg, category.color)}
                    >
                      {category.label}
                    </span>
                    <span
                      className={cn(
                        'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs',
                        status.bg,
                        status.color
                      )}
                    >
                      <StatusIcon className="w-3 h-3" />
                      {status.label}
                    </span>
                  </div>
                </div>
                <span className="text-xs text-gray-500">{template.language.toUpperCase()}</span>
              </div>

              {/* Preview */}
              <div className="bg-[#075e54] rounded-xl p-3 mb-4 text-sm">
                {template.header_type === 'TEXT' && (
                  <div className="font-bold text-white mb-1">{template.header_content}</div>
                )}
                {template.header_type === 'IMAGE' && (
                  <div className="flex items-center gap-2 text-gray-300 mb-2">
                    <PhotoIcon className="w-4 h-4" /> Image Header
                  </div>
                )}
                <div className="text-gray-100 whitespace-pre-wrap">
                  {template.body_text.replace(/\{\{(\d+)\}\}/g, (_, n) => `[Variable ${n}]`)}
                </div>
                {template.footer_text && (
                  <div className="text-gray-400 text-xs mt-2">{template.footer_text}</div>
                )}
                {template.buttons.length > 0 && (
                  <div className="flex gap-2 mt-3 pt-2 border-t border-white/10">
                    {template.buttons.map((btn, i) => (
                      <span key={i} className="text-cyan-400 text-xs">
                        {btn.text}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Stats */}
              <div className="flex items-center justify-between text-sm mb-4">
                <span className="text-gray-400">
                  Used {template.usage_count.toLocaleString()} times
                </span>
                <span className="text-gray-500">
                  {new Date(template.created_at).toLocaleDateString()}
                </span>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  onClick={() => setShowPreviewModal(template)}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-[#1a1a24] rounded-lg hover:bg-[#22222e] transition-colors text-sm"
                >
                  <EyeIcon className="w-4 h-4" />
                  Preview
                </button>
                {template.status === 'approved' && (
                  <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-[#25D366]/20 text-[#25D366] rounded-lg hover:bg-[#25D366]/30 transition-colors text-sm">
                    <PaperAirplaneIcon className="w-4 h-4" />
                    Use
                  </button>
                )}
                <button className="p-2 text-gray-400 hover:bg-white/5 rounded-lg transition-colors">
                  <PencilIcon className="w-4 h-4" />
                </button>
                <button className="p-2 text-gray-400 hover:bg-red-500/10 hover:text-red-400 rounded-lg transition-colors">
                  <TrashIcon className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Create Template Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <CreateTemplateModal
            onClose={() => setShowCreateModal(false)}
            onCreate={(template) => {
              setTemplates((prev) => [{ ...template, id: prev.length + 1 }, ...prev]);
              setShowCreateModal(false);
            }}
          />
        )}
      </AnimatePresence>

      {/* Preview Modal */}
      <AnimatePresence>
        {showPreviewModal && (
          <TemplatePreviewModal
            template={showPreviewModal}
            onClose={() => setShowPreviewModal(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// Create Template Modal
function CreateTemplateModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (template: Omit<Template, 'id'>) => void;
}) {
  const [formData, setFormData] = useState({
    name: '',
    language: 'en',
    category: 'UTILITY' as Template['category'],
    header_type: '' as string,
    header_content: '',
    body_text: '',
    footer_text: '',
    buttons: [] as Template['buttons'],
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onCreate({
      ...formData,
      header_type: formData.header_type || null,
      header_content: formData.header_content || null,
      footer_text: formData.footer_text || null,
      status: 'pending',
      rejection_reason: null,
      usage_count: 0,
      created_at: new Date().toISOString(),
    });
  };

  const addButton = (type: string) => {
    if (formData.buttons.length >= 3) return;
    setFormData((prev) => ({
      ...prev,
      buttons: [...prev.buttons, { type, text: '', url: '', phone: '' }],
    }));
  };

  const updateButton = (index: number, updates: Partial<Template['buttons'][0]>) => {
    setFormData((prev) => ({
      ...prev,
      buttons: prev.buttons.map((btn, i) => (i === index ? { ...btn, ...updates } : btn)),
    }));
  };

  const removeButton = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      buttons: prev.buttons.filter((_, i) => i !== index),
    }));
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
        className="w-full max-w-2xl bg-[rgba(255,_255,_255,_0.05)] rounded-2xl border border-white/10 p-6 my-8"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold">Create Message Template</h3>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">Template Name</label>
              <input
                type="text"
                required
                placeholder="e.g., order_confirmation"
                pattern="[a-z0-9_]+"
                value={formData.name}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    name: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '_'),
                  })
                }
                className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
              />
              <span className="text-xs text-gray-500">Lowercase, underscores only</span>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">Category</label>
              <select
                required
                value={formData.category}
                onChange={(e) =>
                  setFormData({ ...formData, category: e.target.value as Template['category'] })
                }
                className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
              >
                <option value="UTILITY">Utility - Transactional</option>
                <option value="MARKETING">Marketing - Promotional</option>
                <option value="AUTHENTICATION">Authentication - OTP</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Language</label>
            <select
              value={formData.language}
              onChange={(e) => setFormData({ ...formData, language: e.target.value })}
              className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
            >
              <option value="en">English</option>
              <option value="ar">Arabic</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
            </select>
          </div>

          {/* Header */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Header (Optional)
            </label>
            <div className="flex gap-2 mb-2">
              {[
                { value: '', label: 'None', icon: XMarkIcon },
                { value: 'TEXT', label: 'Text', icon: ChatBubbleLeftIcon },
                { value: 'IMAGE', label: 'Image', icon: PhotoIcon },
                { value: 'VIDEO', label: 'Video', icon: VideoCameraIcon },
                { value: 'DOCUMENT', label: 'Document', icon: DocumentIcon },
              ].map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() =>
                    setFormData({ ...formData, header_type: opt.value, header_content: '' })
                  }
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm transition-colors',
                    formData.header_type === opt.value
                      ? 'bg-[#25D366] text-white'
                      : 'bg-[#1a1a24] text-gray-400 hover:text-white'
                  )}
                >
                  <opt.icon className="w-4 h-4" />
                  {opt.label}
                </button>
              ))}
            </div>
            {formData.header_type === 'TEXT' && (
              <input
                type="text"
                placeholder="Header text (max 60 chars)"
                maxLength={60}
                value={formData.header_content}
                onChange={(e) => setFormData({ ...formData, header_content: e.target.value })}
                className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
              />
            )}
            {['IMAGE', 'VIDEO', 'DOCUMENT'].includes(formData.header_type) && (
              <input
                type="url"
                placeholder="Media URL for preview"
                value={formData.header_content}
                onChange={(e) => setFormData({ ...formData, header_content: e.target.value })}
                className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
              />
            )}
          </div>

          {/* Body */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Body Text</label>
            <textarea
              required
              rows={4}
              maxLength={1024}
              placeholder="Hi {{1}}, your order #{{2}} has been confirmed..."
              value={formData.body_text}
              onChange={(e) => setFormData({ ...formData, body_text: e.target.value })}
              className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none resize-none"
            />
            <span className="text-xs text-gray-500">
              Use {'{{1}}'}, {'{{2}}'} for variables. {formData.body_text.length}/1024
            </span>
          </div>

          {/* Footer */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Footer (Optional)
            </label>
            <input
              type="text"
              maxLength={60}
              placeholder="e.g., Reply STOP to unsubscribe"
              value={formData.footer_text}
              onChange={(e) => setFormData({ ...formData, footer_text: e.target.value })}
              className="w-full px-4 py-3 bg-[#0b1215] border border-white/10 rounded-xl focus:border-[#25D366]/50 focus:outline-none"
            />
          </div>

          {/* Buttons */}
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Buttons (Optional, max 3)
            </label>
            <div className="space-y-2 mb-2">
              {formData.buttons.map((btn, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <input
                    type="text"
                    placeholder="Button text"
                    maxLength={25}
                    value={btn.text}
                    onChange={(e) => updateButton(i, { text: e.target.value })}
                    className="flex-1 px-3 py-2 bg-[#0b1215] border border-white/10 rounded-lg text-sm"
                  />
                  {btn.type === 'URL' && (
                    <input
                      type="url"
                      placeholder="URL"
                      value={btn.url}
                      onChange={(e) => updateButton(i, { url: e.target.value })}
                      className="flex-1 px-3 py-2 bg-[#0b1215] border border-white/10 rounded-lg text-sm"
                    />
                  )}
                  {btn.type === 'PHONE_NUMBER' && (
                    <input
                      type="tel"
                      placeholder="Phone"
                      value={btn.phone}
                      onChange={(e) => updateButton(i, { phone: e.target.value })}
                      className="flex-1 px-3 py-2 bg-[#0b1215] border border-white/10 rounded-lg text-sm"
                    />
                  )}
                  <span className="text-xs text-gray-500 w-16">{btn.type}</span>
                  <button
                    type="button"
                    onClick={() => removeButton(i)}
                    className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg"
                  >
                    <XMarkIcon className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
            {formData.buttons.length < 3 && (
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => addButton('QUICK_REPLY')}
                  className="px-3 py-1.5 bg-[#1a1a24] rounded-lg text-sm hover:bg-[#22222e]"
                >
                  + Quick Reply
                </button>
                <button
                  type="button"
                  onClick={() => addButton('URL')}
                  className="px-3 py-1.5 bg-[#1a1a24] rounded-lg text-sm hover:bg-[#22222e]"
                >
                  + URL Button
                </button>
                <button
                  type="button"
                  onClick={() => addButton('PHONE_NUMBER')}
                  className="px-3 py-1.5 bg-[#1a1a24] rounded-lg text-sm hover:bg-[#22222e]"
                >
                  + Call Button
                </button>
              </div>
            )}
          </div>

          {/* Submit */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 bg-[#1a1a24] border border-white/10 rounded-xl hover:bg-[#22222e] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-3 bg-gradient-to-r from-[#25D366] to-[#128C7E] rounded-xl hover:opacity-90 transition-opacity font-medium"
            >
              Create & Submit to Meta
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}

// Template Preview Modal
function TemplatePreviewModal({ template, onClose }: { template: Template; onClose: () => void }) {
  const [sampleValues, setSampleValues] = useState<string[]>(['John', '12345', '2-3']);

  const getPreviewText = (text: string) => {
    return text.replace(/\{\{(\d+)\}\}/g, (_, n) => {
      const idx = parseInt(n) - 1;
      return sampleValues[idx] || `[${n}]`;
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-lg bg-[rgba(255,_255,_255,_0.05)] rounded-2xl border border-white/10 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold">Template Preview</h3>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* WhatsApp Style Preview */}
        <div
          className="bg-[#0b141a] rounded-2xl p-4 mb-6"
          style={{
            backgroundImage:
              'url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFklEQVR42mNkYPhfz0AEYBxVOGoFAC6pBAt7z0yRAAAAAElFTkSuQmCC")',
          }}
        >
          <div className="bg-[#005c4b] rounded-lg p-3 max-w-[280px] ml-auto">
            {template.header_type === 'TEXT' && (
              <div className="font-bold text-white mb-2">
                {getPreviewText(template.header_content || '')}
              </div>
            )}
            {template.header_type === 'IMAGE' && (
              <div className="bg-[#1a3a34] rounded-lg h-32 flex items-center justify-center mb-2">
                <PhotoIcon className="w-8 h-8 text-gray-400" />
              </div>
            )}
            <div className="text-white text-sm whitespace-pre-wrap">
              {getPreviewText(template.body_text)}
            </div>
            {template.footer_text && (
              <div className="text-gray-400 text-xs mt-2">{template.footer_text}</div>
            )}
            <div className="text-right text-xs text-gray-400 mt-1">
              {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
          {template.buttons.length > 0 && (
            <div className="bg-[#005c4b] rounded-lg mt-1 max-w-[280px] ml-auto divide-y divide-white/10">
              {template.buttons.map((btn, i) => (
                <div key={i} className="text-center py-2 text-[#53bdeb] text-sm">
                  {btn.text}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sample Values Editor */}
        <div className="space-y-3">
          <h4 className="font-medium text-sm text-gray-400">Sample Variable Values</h4>
          {[1, 2, 3].map((num) => (
            <div key={num} className="flex items-center gap-3">
              <span className="text-sm text-gray-500 w-16">{`{{${num}}}`}</span>
              <input
                type="text"
                value={sampleValues[num - 1] || ''}
                onChange={(e) => {
                  const newValues = [...sampleValues];
                  newValues[num - 1] = e.target.value;
                  setSampleValues(newValues);
                }}
                placeholder={`Value for variable ${num}`}
                className="flex-1 px-3 py-2 bg-[#0b1215] border border-white/10 rounded-lg text-sm"
              />
            </div>
          ))}
        </div>

        <button
          onClick={onClose}
          className="w-full mt-6 px-4 py-3 bg-[#1a1a24] border border-white/10 rounded-xl hover:bg-[#22222e] transition-colors"
        >
          Close
        </button>
      </motion.div>
    </motion.div>
  );
}
