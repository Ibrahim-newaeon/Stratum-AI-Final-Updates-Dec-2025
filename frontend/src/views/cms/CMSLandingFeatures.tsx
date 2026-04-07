/**
 * CMS Landing Features Editor
 * Manage feature layers and items for the landing page
 */

import { useState } from 'react';
import {
  PlusIcon,
  SparklesIcon,
  PencilSquareIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import {
  useFeatureLayers,
  FeatureItem,
  useCreatePost,
  useUpdatePost,
  useDeletePost,
} from '@/api/cms';

export default function CMSLandingFeatures() {
  const { data: layers, isLoading } = useFeatureLayers();
  const createMutation = useCreatePost();
  const updateMutation = useUpdatePost();
  const deleteMutation = useDeletePost();

  const [showEditor, setShowEditor] = useState(false);
  const [editingFeature, setEditingFeature] = useState<FeatureItem | null>(null);
  const [, setEditingLayerId] = useState<string>('');
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    iconName: 'ChartBarIcon',
    layerId: '',
    layerName: '',
    displayOrder: 0,
  });

  const openEditor = (feature?: FeatureItem, layerId?: string) => {
    if (feature) {
      setEditingFeature(feature);
      setEditingLayerId(layerId || '');
      setFormData({
        title: feature.title,
        description: feature.description,
        iconName: feature.iconName,
        layerId: layerId || '',
        layerName: '',
        displayOrder: feature.displayOrder,
      });
    } else {
      setEditingFeature(null);
      setEditingLayerId('');
      setFormData({
        title: '',
        description: '',
        iconName: 'ChartBarIcon',
        layerId: '',
        layerName: '',
        displayOrder: 0,
      });
    }
    setShowEditor(true);
  };

  const handleSave = () => {
    const postData = {
      title: formData.title,
      excerpt: formData.description,
      status: 'published' as const,
      content_type: 'blog_post' as const,
      meta_title: JSON.stringify({
        layerId: formData.layerId || 'default',
        layerName: formData.layerName,
        featureIcon: formData.iconName,
        displayOrder: formData.displayOrder,
      }),
    };

    if (editingFeature) {
      updateMutation.mutate(
        { id: editingFeature.id, data: postData },
        { onSuccess: () => setShowEditor(false) }
      );
    } else {
      createMutation.mutate(postData, {
        onSuccess: () => setShowEditor(false),
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Landing Features</h1>
          <p className="text-white/60 mt-1">Manage feature sections on the landing page</p>
        </div>
        <button
          onClick={() => openEditor()}
          className="flex items-center gap-2 px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          Add Feature
        </button>
      </div>

      {/* Feature Layers */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
        </div>
      ) : !layers || layers.length === 0 ? (
        <div className="rounded-2xl bg-white/5 border border-white/10 text-center py-20">
          <SparklesIcon className="w-12 h-12 text-white/20 mx-auto mb-4" />
          <p className="text-white/60 mb-2">No feature layers configured</p>
          <p className="text-white/40 text-sm mb-6">
            Create feature posts with the &quot;landing-features&quot; category to populate this section.
          </p>
          <button
            onClick={() => openEditor()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            Add first feature
          </button>
        </div>
      ) : (
        <div className="space-y-8">
          {layers.map((layer) => (
            <div key={layer.id} className="rounded-2xl bg-white/5 border border-white/10 overflow-hidden">
              {/* Layer Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-lg ${layer.bgColor} flex items-center justify-center`}>
                    <SparklesIcon className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold">{layer.name}</h3>
                    <p className="text-sm text-white/50">{layer.description}</p>
                  </div>
                </div>
                <span className="text-xs text-white/40">
                  {layer.features.length} feature{layer.features.length !== 1 ? 's' : ''}
                </span>
              </div>

              {/* Features in Layer */}
              <div className="divide-y divide-white/5">
                {layer.features.map((feature) => (
                  <div
                    key={feature.id}
                    className="flex items-center justify-between px-6 py-3 hover:bg-white/5 transition-colors group"
                  >
                    <div className="min-w-0">
                      <p className="text-white font-medium truncate">{feature.title}</p>
                      <p className="text-sm text-white/40 truncate">{feature.description}</p>
                    </div>
                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={() => openEditor(feature, layer.id)}
                        className="p-1.5 text-white/40 hover:text-white"
                      >
                        <PencilSquareIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => deleteMutation.mutate(feature.id)}
                        className="p-1.5 text-white/40 hover:text-red-400"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Add Feature to Layer */}
              <button
                onClick={() => {
                  setFormData((f) => ({ ...f, layerId: layer.id, layerName: layer.name }));
                  openEditor();
                }}
                className="flex items-center gap-2 w-full px-6 py-3 text-sm text-white/40 hover:text-white hover:bg-white/5 transition-colors"
              >
                <PlusIcon className="w-4 h-4" />
                Add feature to this layer
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Editor Modal */}
      {showEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-neutral-900 border border-white/10 rounded-xl w-full max-w-lg">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h2 className="text-lg font-semibold text-white">
                {editingFeature ? 'Edit Feature' : 'Add Feature'}
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
                <label className="block text-sm font-medium text-white/70 mb-1.5">Title *</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData((f) => ({ ...f, title: e.target.value }))}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                  placeholder="Feature title"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData((f) => ({ ...f, description: e.target.value }))}
                  rows={3}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none"
                  placeholder="Feature description..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white/70 mb-1.5">Layer</label>
                  <input
                    type="text"
                    value={formData.layerId}
                    onChange={(e) => setFormData((f) => ({ ...f, layerId: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50"
                    placeholder="Layer ID"
                  />
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
                disabled={!formData.title || createMutation.isPending || updateMutation.isPending}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium disabled:opacity-50"
              >
                {createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
