/**
 * CDP Computed Trait Builder Component
 * UI for creating and managing computed traits
 */

import { useState } from 'react';
import { Activity, Calculator, Clock, Hash, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  CDPComputedTrait,
  ComputedTraitCreate,
  useComputedTraits,
  useCreateComputedTrait,
  useDeleteComputedTrait,
} from '@/api/cdp';

const TRAIT_TYPES = [
  { value: 'count', label: 'Count', icon: Hash, description: 'Count of events' },
  { value: 'sum', label: 'Sum', icon: Calculator, description: 'Sum of property values' },
  { value: 'average', label: 'Average', icon: Activity, description: 'Average of values' },
  { value: 'min', label: 'Minimum', icon: Activity, description: 'Minimum value' },
  { value: 'max', label: 'Maximum', icon: Activity, description: 'Maximum value' },
  { value: 'first', label: 'First', icon: Clock, description: 'First occurrence' },
  { value: 'last', label: 'Last', icon: Clock, description: 'Most recent occurrence' },
  { value: 'unique_count', label: 'Unique Count', icon: Hash, description: 'Count unique values' },
  { value: 'exists', label: 'Exists', icon: Activity, description: 'Boolean if exists' },
];

const OUTPUT_TYPES = [
  { value: 'number', label: 'Number' },
  { value: 'string', label: 'Text' },
  { value: 'boolean', label: 'Boolean' },
  { value: 'date', label: 'Date' },
];

interface TraitFormData {
  name: string;
  display_name: string;
  description: string;
  trait_type: string;
  output_type: string;
  event_name: string;
  property: string;
  time_window_days: number | null;
  default_value: string;
}

const initialFormData: TraitFormData = {
  name: '',
  display_name: '',
  description: '',
  trait_type: 'count',
  output_type: 'number',
  event_name: '',
  property: '',
  time_window_days: null,
  default_value: '',
};

export function ComputedTraitBuilder() {
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<TraitFormData>(initialFormData);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data: traitsData, isLoading, refetch } = useComputedTraits({ active_only: false });
  const createMutation = useCreateComputedTrait();
  const deleteMutation = useDeleteComputedTrait();

  const traits = traitsData?.traits || [];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const traitCreate: ComputedTraitCreate = {
      name: formData.name.toLowerCase().replace(/\s+/g, '_'),
      display_name: formData.display_name,
      description: formData.description || undefined,
      trait_type: formData.trait_type,
      output_type: formData.output_type,
      source_config: {
        event_name: formData.event_name || undefined,
        property: formData.property || undefined,
        time_window_days: formData.time_window_days || undefined,
      },
      default_value: formData.default_value || undefined,
    };

    try {
      await createMutation.mutateAsync(traitCreate);
      setFormData(initialFormData);
      setShowForm(false);
    } catch (error) {
      console.error('Failed to create trait:', error);
    }
  };

  const handleDelete = async (traitId: string) => {
    setDeletingId(traitId);
    try {
      await deleteMutation.mutateAsync(traitId);
    } catch (error) {
      console.error('Failed to delete trait:', error);
    } finally {
      setDeletingId(null);
    }
  };

  const getTraitTypeInfo = (type: string) => {
    return TRAIT_TYPES.find((t) => t.value === type) || TRAIT_TYPES[0];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Computed Traits</h2>
          <p className="text-muted-foreground">
            Define derived values calculated from profile events
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="px-3 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            New Trait
          </button>
        </div>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="p-6 rounded-xl border bg-card">
          <h3 className="text-lg font-semibold mb-4">Create Computed Trait</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Display Name</label>
                <input
                  type="text"
                  value={formData.display_name}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      display_name: e.target.value,
                      name: e.target.value.toLowerCase().replace(/\s+/g, '_'),
                    })
                  }
                  placeholder="e.g., Total Purchases"
                  className="w-full px-3 py-2 rounded-lg border bg-background"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Internal Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., total_purchases"
                  className="w-full px-3 py-2 rounded-lg border bg-background font-mono text-sm"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Optional description"
                className="w-full px-3 py-2 rounded-lg border bg-background"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Trait Type</label>
                <select
                  value={formData.trait_type}
                  onChange={(e) => setFormData({ ...formData, trait_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border bg-background"
                >
                  {TRAIT_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label} - {type.description}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Output Type</label>
                <select
                  value={formData.output_type}
                  onChange={(e) => setFormData({ ...formData, output_type: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border bg-background"
                >
                  {OUTPUT_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-muted/50 space-y-4">
              <h4 className="font-medium">Source Configuration</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Event Name</label>
                  <input
                    type="text"
                    value={formData.event_name}
                    onChange={(e) => setFormData({ ...formData, event_name: e.target.value })}
                    placeholder="e.g., Purchase, PageView"
                    className="w-full px-3 py-2 rounded-lg border bg-background"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Property (for aggregations)
                  </label>
                  <input
                    type="text"
                    value={formData.property}
                    onChange={(e) => setFormData({ ...formData, property: e.target.value })}
                    placeholder="e.g., total, price"
                    className="w-full px-3 py-2 rounded-lg border bg-background"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Time Window (days)</label>
                  <input
                    type="number"
                    value={formData.time_window_days || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        time_window_days: e.target.value ? parseInt(e.target.value) : null,
                      })
                    }
                    placeholder="Leave empty for all time"
                    className="w-full px-3 py-2 rounded-lg border bg-background"
                    min={1}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Default Value</label>
                  <input
                    type="text"
                    value={formData.default_value}
                    onChange={(e) => setFormData({ ...formData, default_value: e.target.value })}
                    placeholder="Value when no data"
                    className="w-full px-3 py-2 rounded-lg border bg-background"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setFormData(initialFormData);
                }}
                className="px-4 py-2 rounded-lg border hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating...' : 'Create Trait'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Traits List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : traits.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Calculator className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No computed traits defined yet.</p>
          <p className="text-sm">Create your first trait to start enriching profiles.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {traits.map((trait: CDPComputedTrait) => {
            const typeInfo = getTraitTypeInfo(trait.trait_type);
            const TypeIcon = typeInfo.icon;

            return (
              <div
                key={trait.id}
                className="p-4 rounded-xl border bg-card hover:border-primary/50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <TypeIcon className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-semibold">{trait.display_name}</h3>
                      <p className="text-sm text-muted-foreground font-mono">{trait.name}</p>
                      {trait.description && (
                        <p className="text-sm text-muted-foreground mt-1">{trait.description}</p>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(trait.id)}
                    disabled={deletingId === trait.id}
                    className="p-2 rounded-lg hover:bg-destructive/10 hover:text-destructive transition-colors"
                  >
                    {deletingId === trait.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
                    {typeInfo.label}
                  </span>
                  <span className="px-2 py-1 rounded-full text-xs bg-muted">
                    Output: {trait.output_type}
                  </span>
                  {trait.source_config?.event_name && (
                    <span className="px-2 py-1 rounded-full text-xs bg-muted">
                      Event: {trait.source_config.event_name}
                    </span>
                  )}
                  {trait.source_config?.time_window_days && (
                    <span className="px-2 py-1 rounded-full text-xs bg-muted">
                      Window: {trait.source_config.time_window_days}d
                    </span>
                  )}
                  <span
                    className={cn(
                      'px-2 py-1 rounded-full text-xs',
                      trait.is_active
                        ? 'bg-green-500/10 text-green-600'
                        : 'bg-muted text-muted-foreground'
                    )}
                  >
                    {trait.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                {trait.last_computed_at && (
                  <p className="text-xs text-muted-foreground mt-3">
                    Last computed: {new Date(trait.last_computed_at).toLocaleString()}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
