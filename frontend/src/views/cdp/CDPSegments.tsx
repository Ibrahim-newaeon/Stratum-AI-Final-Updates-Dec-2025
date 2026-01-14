/**
 * CDP Segments - Segment builder and manager
 */

import { useState } from 'react'
import {
  PlusIcon,
  MagnifyingGlassIcon,
  TagIcon,
  UserGroupIcon,
  ClockIcon,
  PlayIcon,
  PauseIcon,
  TrashIcon,
  PencilIcon,
  XMarkIcon,
  CheckIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import {
  useSegments,
  useCreateSegment,
  useUpdateSegment,
  useDeleteSegment,
  useComputeSegment,
  usePreviewSegment,
  type CDPSegment,
  type SegmentCreate,
  type SegmentRules,
  type SegmentCondition,
  type SegmentStatus,
} from '@/api/cdp'

// Status Badge
function StatusBadge({ status }: { status: SegmentStatus }) {
  const config = {
    draft: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
    computing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    stale: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
    archived: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  }

  return (
    <span className={cn('px-2 py-1 rounded-full text-xs font-medium capitalize', config[status])}>
      {status}
    </span>
  )
}

// Condition Builder Row
function ConditionRow({
  condition,
  onChange,
  onRemove,
  isLast,
}: {
  condition: SegmentCondition
  onChange: (condition: SegmentCondition) => void
  onRemove: () => void
  isLast: boolean
}) {
  const fieldOptions = [
    { value: 'lifecycle_stage', label: 'Lifecycle Stage' },
    { value: 'total_events', label: 'Total Events' },
    { value: 'total_revenue', label: 'Total Revenue' },
    { value: 'total_purchases', label: 'Total Purchases' },
    { value: 'first_seen_at', label: 'First Seen' },
    { value: 'last_seen_at', label: 'Last Seen' },
    { value: 'has_email', label: 'Has Email' },
    { value: 'has_phone', label: 'Has Phone' },
  ]

  const operatorOptions: Record<string, Array<{ value: string; label: string }>> = {
    lifecycle_stage: [
      { value: 'eq', label: 'equals' },
      { value: 'neq', label: 'not equals' },
      { value: 'in', label: 'is one of' },
    ],
    total_events: [
      { value: 'gt', label: 'greater than' },
      { value: 'gte', label: 'greater or equal' },
      { value: 'lt', label: 'less than' },
      { value: 'lte', label: 'less or equal' },
      { value: 'eq', label: 'equals' },
    ],
    total_revenue: [
      { value: 'gt', label: 'greater than' },
      { value: 'gte', label: 'greater or equal' },
      { value: 'lt', label: 'less than' },
      { value: 'lte', label: 'less or equal' },
    ],
    total_purchases: [
      { value: 'gt', label: 'greater than' },
      { value: 'gte', label: 'greater or equal' },
      { value: 'eq', label: 'equals' },
    ],
    first_seen_at: [
      { value: 'after', label: 'after' },
      { value: 'before', label: 'before' },
      { value: 'within_days', label: 'within last N days' },
    ],
    last_seen_at: [
      { value: 'after', label: 'after' },
      { value: 'before', label: 'before' },
      { value: 'within_days', label: 'within last N days' },
    ],
    has_email: [{ value: 'eq', label: 'is' }],
    has_phone: [{ value: 'eq', label: 'is' }],
  }

  const operators = operatorOptions[condition.field] || operatorOptions.total_events

  return (
    <div className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
      <select
        value={condition.field}
        onChange={(e) => onChange({ ...condition, field: e.target.value, value: '' })}
        className="px-3 py-2 border rounded-lg bg-background text-sm"
      >
        {fieldOptions.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      <select
        value={condition.operator}
        onChange={(e) => onChange({ ...condition, operator: e.target.value })}
        className="px-3 py-2 border rounded-lg bg-background text-sm"
      >
        {operators.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {condition.field === 'lifecycle_stage' ? (
        <select
          value={String(condition.value)}
          onChange={(e) => onChange({ ...condition, value: e.target.value })}
          className="flex-1 px-3 py-2 border rounded-lg bg-background text-sm"
        >
          <option value="">Select stage...</option>
          <option value="anonymous">Anonymous</option>
          <option value="known">Known</option>
          <option value="customer">Customer</option>
          <option value="churned">Churned</option>
        </select>
      ) : condition.field === 'has_email' || condition.field === 'has_phone' ? (
        <select
          value={String(condition.value)}
          onChange={(e) => onChange({ ...condition, value: e.target.value === 'true' })}
          className="flex-1 px-3 py-2 border rounded-lg bg-background text-sm"
        >
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      ) : (
        <input
          type={condition.field.includes('_at') && !condition.operator.includes('days') ? 'date' : 'number'}
          value={String(condition.value || '')}
          onChange={(e) => onChange({ ...condition, value: e.target.value })}
          placeholder="Enter value..."
          className="flex-1 px-3 py-2 border rounded-lg bg-background text-sm"
        />
      )}

      <button
        onClick={onRemove}
        disabled={isLast}
        className="p-2 hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
      >
        <TrashIcon className="h-4 w-4" />
      </button>
    </div>
  )
}

// Segment Builder Modal
function SegmentBuilderModal({
  segment,
  onClose,
  onSave,
}: {
  segment?: CDPSegment
  onClose: () => void
  onSave: (data: SegmentCreate) => void
}) {
  const [name, setName] = useState(segment?.name || '')
  const [description, setDescription] = useState(segment?.description || '')
  const [logic, setLogic] = useState<'and' | 'or'>('and')
  const [conditions, setConditions] = useState<SegmentCondition[]>(
    (segment?.rules as SegmentRules)?.conditions || [
      { field: 'lifecycle_stage', operator: 'eq', value: '' },
    ]
  )
  const [autoRefresh, setAutoRefresh] = useState(segment?.auto_refresh ?? true)
  const [refreshInterval, setRefreshInterval] = useState(segment?.refresh_interval_hours || 24)

  const previewMutation = usePreviewSegment()

  const handlePreview = async () => {
    try {
      await previewMutation.mutateAsync({
        rules: { logic, conditions },
        limit: 10,
      })
    } catch (error) {
      console.error('Preview failed:', error)
    }
  }

  const handleSave = () => {
    if (!name.trim()) return
    onSave({
      name: name.trim(),
      description: description.trim() || undefined,
      rules: { logic, conditions },
      auto_refresh: autoRefresh,
      refresh_interval_hours: refreshInterval,
    })
  }

  const addCondition = () => {
    setConditions([...conditions, { field: 'total_events', operator: 'gt', value: 0 }])
  }

  const updateCondition = (index: number, condition: SegmentCondition) => {
    const updated = [...conditions]
    updated[index] = condition
    setConditions(updated)
  }

  const removeCondition = (index: number) => {
    if (conditions.length > 1) {
      setConditions(conditions.filter((_, i) => i !== index))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-card rounded-xl border shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            {segment ? 'Edit Segment' : 'Create Segment'}
          </h3>
          <button onClick={onClose} className="p-2 hover:bg-muted rounded-lg">
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(90vh-150px)] space-y-6">
          {/* Name & Description */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Segment Name *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., High-Value Customers"
                className="w-full px-3 py-2 border rounded-lg bg-background"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this segment includes..."
                rows={2}
                className="w-full px-3 py-2 border rounded-lg bg-background resize-none"
              />
            </div>
          </div>

          {/* Logic Toggle */}
          <div>
            <label className="block text-sm font-medium mb-2">Match profiles where:</label>
            <div className="flex gap-2">
              <button
                onClick={() => setLogic('and')}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  logic === 'and'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                )}
              >
                ALL conditions match (AND)
              </button>
              <button
                onClick={() => setLogic('or')}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  logic === 'or'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                )}
              >
                ANY condition matches (OR)
              </button>
            </div>
          </div>

          {/* Conditions */}
          <div className="space-y-3">
            <label className="block text-sm font-medium">Conditions</label>
            {conditions.map((condition, index) => (
              <ConditionRow
                key={index}
                condition={condition}
                onChange={(c) => updateCondition(index, c)}
                onRemove={() => removeCondition(index)}
                isLast={conditions.length === 1}
              />
            ))}
            <button
              onClick={addCondition}
              className="flex items-center gap-2 px-4 py-2 border border-dashed rounded-lg text-sm text-muted-foreground hover:text-foreground hover:border-primary transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Add Condition
            </button>
          </div>

          {/* Auto-Refresh Settings */}
          <div className="space-y-3">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300"
              />
              <span className="text-sm font-medium">Auto-refresh segment</span>
            </label>
            {autoRefresh && (
              <div className="ml-6">
                <label className="block text-sm text-muted-foreground mb-1">
                  Refresh every
                </label>
                <select
                  value={refreshInterval}
                  onChange={(e) => setRefreshInterval(Number(e.target.value))}
                  className="px-3 py-2 border rounded-lg bg-background text-sm"
                >
                  <option value={1}>1 hour</option>
                  <option value={6}>6 hours</option>
                  <option value={12}>12 hours</option>
                  <option value={24}>24 hours</option>
                  <option value={168}>Weekly</option>
                </select>
              </div>
            )}
          </div>

          {/* Preview */}
          <div className="pt-4 border-t">
            <button
              onClick={handlePreview}
              disabled={previewMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 border rounded-lg text-sm hover:bg-muted transition-colors disabled:opacity-50"
            >
              <UserGroupIcon className="h-4 w-4" />
              {previewMutation.isPending ? 'Loading...' : 'Preview Segment'}
            </button>
            {previewMutation.data && (
              <div className="mt-3 p-3 bg-muted/50 rounded-lg">
                <p className="text-sm font-medium">
                  Estimated: {previewMutation.data.estimated_count.toLocaleString()} profiles
                </p>
                {previewMutation.data.sample_profiles.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Sample: {previewMutation.data.sample_profiles.map((p) => p.id.slice(0, 8)).join(', ')}...
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium hover:bg-muted rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <CheckIcon className="h-4 w-4 inline-block mr-1" />
            {segment ? 'Update' : 'Create'} Segment
          </button>
        </div>
      </div>
    </div>
  )
}

// Segment Card
function SegmentCard({
  segment,
  onEdit,
  onCompute,
  onDelete,
}: {
  segment: CDPSegment
  onEdit: () => void
  onCompute: () => void
  onDelete: () => void
}) {
  return (
    <div className="bg-card rounded-xl border p-4 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <TagIcon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">{segment.name}</h3>
            <p className="text-sm text-muted-foreground">{segment.slug}</p>
          </div>
        </div>
        <StatusBadge status={segment.status} />
      </div>

      {segment.description && (
        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
          {segment.description}
        </p>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs text-muted-foreground">Profiles</p>
          <p className="font-semibold">{segment.profile_count.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Last Computed</p>
          <p className="text-sm">
            {segment.last_computed_at
              ? new Date(segment.last_computed_at).toLocaleDateString()
              : 'Never'}
          </p>
        </div>
      </div>

      {segment.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-4">
          {segment.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 bg-muted rounded text-xs"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t">
        <div className="flex items-center gap-1">
          {segment.auto_refresh && (
            <span className="flex items-center gap-1 text-xs text-muted-foreground">
              <ArrowPathIcon className="h-3 w-3" />
              Every {segment.refresh_interval_hours}h
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onCompute}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Recompute"
          >
            <PlayIcon className="h-4 w-4" />
          </button>
          <button
            onClick={onEdit}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Edit"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors text-red-500"
            title="Delete"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default function CDPSegments() {
  const [search, setSearch] = useState('')
  const [showBuilder, setShowBuilder] = useState(false)
  const [editingSegment, setEditingSegment] = useState<CDPSegment | undefined>()
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data, isLoading, refetch } = useSegments()
  const createMutation = useCreateSegment()
  const updateMutation = useUpdateSegment()
  const deleteMutation = useDeleteSegment()
  const computeMutation = useComputeSegment()

  const filteredSegments = data?.segments.filter((s) =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.description?.toLowerCase().includes(search.toLowerCase())
  ) || []

  const handleCreate = async (segmentData: SegmentCreate) => {
    try {
      await createMutation.mutateAsync(segmentData)
      setShowBuilder(false)
      refetch()
    } catch (error) {
      console.error('Create failed:', error)
    }
  }

  const handleUpdate = async (segmentData: SegmentCreate) => {
    if (!editingSegment) return
    try {
      await updateMutation.mutateAsync({
        segmentId: editingSegment.id,
        ...segmentData,
      })
      setEditingSegment(undefined)
      refetch()
    } catch (error) {
      console.error('Update failed:', error)
    }
  }

  const handleDelete = async (segmentId: string) => {
    try {
      await deleteMutation.mutateAsync(segmentId)
      setDeleteConfirm(null)
      refetch()
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }

  const handleCompute = async (segmentId: string) => {
    try {
      await computeMutation.mutateAsync(segmentId)
      refetch()
    } catch (error) {
      console.error('Compute failed:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Segments</h1>
          <p className="text-muted-foreground mt-1">
            {data?.total || 0} segments
          </p>
        </div>
        <button
          onClick={() => setShowBuilder(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
        >
          <PlusIcon className="h-4 w-4" />
          Create Segment
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search segments..."
          className="w-full pl-10 pr-4 py-2 border rounded-lg bg-background focus:ring-2 focus:ring-primary focus:outline-none"
        />
      </div>

      {/* Segments Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card rounded-xl border p-4 animate-pulse">
              <div className="h-10 w-10 bg-muted rounded-lg mb-3" />
              <div className="h-5 w-32 bg-muted rounded mb-2" />
              <div className="h-4 w-full bg-muted rounded" />
            </div>
          ))}
        </div>
      ) : filteredSegments.length === 0 ? (
        <div className="text-center py-12 bg-card rounded-xl border">
          <TagIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="font-semibold mb-2">No segments found</h3>
          <p className="text-muted-foreground text-sm mb-4">
            {search ? 'Try a different search term' : 'Create your first segment to get started'}
          </p>
          {!search && (
            <button
              onClick={() => setShowBuilder(true)}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90"
            >
              Create Segment
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSegments.map((segment) => (
            <SegmentCard
              key={segment.id}
              segment={segment}
              onEdit={() => setEditingSegment(segment)}
              onCompute={() => handleCompute(segment.id)}
              onDelete={() => setDeleteConfirm(segment.id)}
            />
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {(showBuilder || editingSegment) && (
        <SegmentBuilderModal
          segment={editingSegment}
          onClose={() => {
            setShowBuilder(false)
            setEditingSegment(undefined)
          }}
          onSave={editingSegment ? handleUpdate : handleCreate}
        />
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-card rounded-xl border p-6 max-w-md mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="h-10 w-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
              </div>
              <div>
                <h3 className="font-semibold">Delete Segment</h3>
                <p className="text-sm text-muted-foreground">This action cannot be undone</p>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-sm font-medium hover:bg-muted rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-red-500 text-white rounded-lg text-sm font-medium hover:bg-red-600 disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
