/**
 * CMS Landing Pricing Editor
 * Manage pricing tiers for the landing page
 */

import { useState } from 'react';
import {
  PlusIcon,
  CurrencyDollarIcon,
  PencilSquareIcon,
  TrashIcon,
  XMarkIcon,
  CheckIcon,
} from '@heroicons/react/24/outline';
import {
  PricingTier,
  usePricingTiers,
  useCreatePost,
  useUpdatePost,
  useDeletePost,
} from '@/api/cms';

export default function CMSLandingPricing() {
  const { data: tiers, isLoading } = usePricingTiers();
  const createMutation = useCreatePost();
  const updateMutation = useUpdatePost();
  const deleteMutation = useDeletePost();

  const [showEditor, setShowEditor] = useState(false);
  const [editingTier, setEditingTier] = useState<PricingTier | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '$0',
    period: '/month',
    adSpend: '',
    features: '' as string, // newline-separated
    cta: 'Get Started',
    ctaLink: '/signup',
    highlighted: false,
    badge: '',
    displayOrder: 0,
  });

  const pricingTiers = tiers || [];

  const openEditor = (tier?: PricingTier) => {
    if (tier) {
      setEditingTier(tier);
      setFormData({
        name: tier.name,
        description: tier.description,
        price: tier.price,
        period: tier.period,
        adSpend: tier.adSpend,
        features: tier.features.join('\n'),
        cta: tier.cta,
        ctaLink: tier.ctaLink,
        highlighted: tier.highlighted,
        badge: tier.badge || '',
        displayOrder: tier.displayOrder,
      });
    } else {
      setEditingTier(null);
      setFormData({
        name: '',
        description: '',
        price: '$0',
        period: '/month',
        adSpend: '',
        features: '',
        cta: 'Get Started',
        ctaLink: '/signup',
        highlighted: false,
        badge: '',
        displayOrder: pricingTiers.length,
      });
    }
    setShowEditor(true);
  };

  const handleSave = () => {
    const features = formData.features
      .split('\n')
      .map((f) => f.trim())
      .filter(Boolean);

    const postData = {
      title: formData.name,
      excerpt: formData.description,
      status: 'published' as const,
      content_type: 'blog_post' as const,
      meta_title: JSON.stringify({
        price: formData.price,
        period: formData.period,
        adSpend: formData.adSpend,
        features,
        cta: formData.cta,
        ctaLink: formData.ctaLink,
        highlighted: formData.highlighted,
        badge: formData.badge || undefined,
        displayOrder: formData.displayOrder,
      }),
    };

    if (editingTier) {
      updateMutation.mutate(
        { id: editingTier.id, data: postData },
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
          <h1 className="text-2xl font-bold text-white">Landing Pricing</h1>
          <p className="text-white/60 mt-1">Manage pricing tiers on the landing page</p>
        </div>
        <button
          onClick={() => openEditor()}
          className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          Add Tier
        </button>
      </div>

      {/* Pricing Tiers Preview */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
        </div>
      ) : pricingTiers.length === 0 ? (
        <div className="rounded-2xl bg-white/5 border border-white/10 text-center py-20">
          <CurrencyDollarIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
          <p className="text-white/60 mb-4">No pricing tiers configured</p>
          <button
            onClick={() => openEditor()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            Add first tier
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {pricingTiers.map((tier) => (
            <div
              key={tier.id}
              className={`relative rounded-2xl border p-6 transition-all group ${
                tier.highlighted
                  ? 'bg-purple-500/10 border-purple-500/30'
                  : 'bg-white/5 border-white/10 hover:border-white/20'
              }`}
            >
              {/* Badge */}
              {tier.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 bg-purple-600 text-white text-xs font-medium rounded-full">
                    {tier.badge}
                  </span>
                </div>
              )}

              {/* Edit/Delete */}
              <div className="absolute top-4 right-4 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => openEditor(tier)}
                  className="p-1.5 text-white/40 hover:text-white"
                >
                  <PencilSquareIcon className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setDeleteConfirm(tier.id)}
                  className="p-1.5 text-white/40 hover:text-red-400"
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              </div>

              {/* Tier Info */}
              <h3 className="text-xl font-bold text-white mb-1">{tier.name}</h3>
              <p className="text-sm text-white/50 mb-4">{tier.description}</p>

              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-3xl font-bold text-white">{tier.price}</span>
                <span className="text-white/50">{tier.period}</span>
              </div>
              {tier.adSpend && (
                <p className="text-xs text-white/40 mb-4">{tier.adSpend}</p>
              )}

              {/* Features */}
              <ul className="space-y-2 mb-6">
                {tier.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-white/70">
                    <CheckIcon className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>

              {/* CTA Preview */}
              <div
                className={`w-full py-2.5 text-center rounded-lg text-sm font-medium ${
                  tier.highlighted
                    ? 'bg-purple-600 text-white'
                    : 'bg-white/10 text-white/80'
                }`}
              >
                {tier.cta}
              </div>

              {tier.highlighted && (
                <div className="absolute -top-0.5 left-0 right-0 h-1 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-t-2xl" />
              )}
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
                {editingTier ? 'Edit Pricing Tier' : 'Add Pricing Tier'}
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
                  Tier Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData((f) => ({ ...f, name: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="e.g., Starter, Growth, Enterprise"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">
                  Description
                </label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData((f) => ({ ...f, description: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="For growing businesses"
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Price</label>
                  <input
                    type="text"
                    value={formData.price}
                    onChange={(e) => setFormData((f) => ({ ...f, price: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="$99"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Period</label>
                  <input
                    type="text"
                    value={formData.period}
                    onChange={(e) => setFormData((f) => ({ ...f, period: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="/month"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">
                    Ad Spend
                  </label>
                  <input
                    type="text"
                    value={formData.adSpend}
                    onChange={(e) => setFormData((f) => ({ ...f, adSpend: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="Up to $50k"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">
                  Features (one per line)
                </label>
                <textarea
                  value={formData.features}
                  onChange={(e) => setFormData((f) => ({ ...f, features: e.target.value }))}
                  rows={6}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none font-mono text-sm"
                  placeholder={"Trust Engine\nSignal Monitoring\nAutomation Rules\nAPI Access"}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">
                    CTA Text
                  </label>
                  <input
                    type="text"
                    value={formData.cta}
                    onChange={(e) => setFormData((f) => ({ ...f, cta: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="Get Started"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">
                    CTA Link
                  </label>
                  <input
                    type="text"
                    value={formData.ctaLink}
                    onChange={(e) => setFormData((f) => ({ ...f, ctaLink: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="/signup"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Badge</label>
                <input
                  type="text"
                  value={formData.badge}
                  onChange={(e) => setFormData((f) => ({ ...f, badge: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="Most Popular"
                />
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.highlighted}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, highlighted: e.target.checked }))
                    }
                    className="w-4 h-4 rounded bg-white/5 border-white/20 text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-sm text-white/70">Highlighted tier</span>
                </label>
                <div className="flex items-center gap-2">
                  <label className="text-sm text-white/70">Order:</label>
                  <input
                    type="number"
                    value={formData.displayOrder}
                    onChange={(e) =>
                      setFormData((f) => ({ ...f, displayOrder: Number(e.target.value) }))
                    }
                    className="w-20 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-purple-500/50"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 p-4 border-t border-white/10 sticky bottom-0 bg-neutral-900">
              <button
                onClick={() => setShowEditor(false)}
                className="px-4 py-2 text-white/60 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!formData.name || createMutation.isPending || updateMutation.isPending}
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
            <h3 className="text-lg font-semibold text-white mb-2">Delete Pricing Tier</h3>
            <p className="text-white/60 mb-6">Remove this tier from the landing page?</p>
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
