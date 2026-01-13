/**
 * CDP Segment Builder Component
 * Visual interface for creating and managing customer segments with rule-based conditions
 */

import { useState } from 'react'
import {
  Users,
  Plus,
  Trash2,
  Save,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Layers,
  Eye,
  Search,
  Calendar,
  Hash,
  Type,
  ToggleLeft,
  Clock,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  useSegments,
  useCreateSegment,
  useUpdateSegment,
  useDeleteSegment,
  useComputeSegment,
  usePreviewSegment,
  CDPSegment,
  SegmentRules,
  SegmentCondition,
} from '@/api/cdp'

// Condition operators by field type
const OPERATORS = {
  string: [
    { value: 'equals', label: 'equals' },
    { value: 'not_equals', label: 'not equals' },
    { value: 'contains', label: 'contains' },
    { value: 'not_contains', label: 'does not contain' },
    { value: 'starts_with', label: 'starts with' },
    { value: 'ends_with', label: 'ends with' },
    { value: 'is_null', label: 'is empty' },
    { value: 'is_not_null', label: 'is not empty' },
  ],
  number: [
    { value: 'equals', label: 'equals' },
    { value: 'not_equals', label: 'not equals' },
    { value: 'greater_than', label: 'greater than' },
    { value: 'less_than', label: 'less than' },
    { value: 'gte', label: 'greater or equal' },
    { value: 'lte', label: 'less or equal' },
    { value: 'between', label: 'between' },
  ],
  date: [
    { value: 'within_last', label: 'within last N days' },
    { value: 'not_within_last', label: 'not within last N days' },
    { value: 'equals', label: 'on date' },
    { value: 'greater_than', label: 'after' },
    { value: 'less_than', label: 'before' },
  ],
  boolean: [
    { value: 'equals', label: 'is' },
  ],
  list: [
    { value: 'in', label: 'is one of' },
    { value: 'not_in', label: 'is not one of' },
  ],
}

// Available fields for conditions
const AVAILABLE_FIELDS = [
  { name: 'lifecycle_stage', label: 'Lifecycle Stage', type: 'list', options: ['anonymous', 'known', 'customer', 'churned'] },
  { name: 'total_events', label: 'Total Events', type: 'number' },
  { name: 'total_revenue', label: 'Total Revenue', type: 'number' },
  { name: 'first_seen_at', label: 'First Seen', type: 'date' },
  { name: 'last_seen_at', label: 'Last Seen', type: 'date' },
  { name: 'is_customer', label: 'Is Customer', type: 'boolean' },
  { name: 'profile_data.country', label: 'Country', type: 'string' },
  { name: 'profile_data.city', label: 'City', type: 'string' },
  { name: 'profile_data.source', label: 'Source', type: 'string' },
  { name: 'computed_traits.ltv', label: 'Lifetime Value', type: 'number' },
  { name: 'computed_traits.rfm.rfm_segment', label: 'RFM Segment', type: 'list', options: ['champions', 'loyal_customers', 'potential_loyalists', 'new_customers', 'promising', 'need_attention', 'about_to_sleep', 'at_risk', 'cannot_lose', 'hibernating', 'lost'] },
]

interface ConditionBuilderProps {
  condition: SegmentCondition
  onChange: (condition: SegmentCondition) => void
  onRemove: () => void
}

function ConditionBuilder({ condition, onChange, onRemove }: ConditionBuilderProps) {
  const field = AVAILABLE_FIELDS.find(f => f.name === condition.field)
  const fieldType = field?.type || 'string'
  const operators = OPERATORS[fieldType as keyof typeof OPERATORS] || OPERATORS.string

  const getFieldIcon = () => {
    switch (fieldType) {
      case 'number': return <Hash className="w-4 h-4" />
      case 'date': return <Calendar className="w-4 h-4" />
      case 'boolean': return <ToggleLeft className="w-4 h-4" />
      default: return <Type className="w-4 h-4" />
    }
  }

  return (
    <div className="flex items-center gap-2 p-3 bg-muted/30 rounded-lg border">
      <div className="flex items-center gap-2 text-muted-foreground">
        {getFieldIcon()}
      </div>

      {/* Field selector */}
      <select
        value={condition.field}
        onChange={(e) => onChange({ ...condition, field: e.target.value })}
        className="px-3 py-1.5 rounded-md border bg-background text-sm min-w-[160px]"
      >
        <option value="">Select field...</option>
        {AVAILABLE_FIELDS.map(f => (
          <option key={f.name} value={f.name}>{f.label}</option>
        ))}
      </select>

      {/* Operator selector */}
      <select
        value={condition.operator}
        onChange={(e) => onChange({ ...condition, operator: e.target.value })}
        className="px-3 py-1.5 rounded-md border bg-background text-sm min-w-[140px]"
      >
        {operators.map(op => (
          <option key={op.value} value={op.value}>{op.label}</option>
        ))}
      </select>

      {/* Value input */}
      {!['is_null', 'is_not_null'].includes(condition.operator) && (
        <>
          {field?.options ? (
            <select
              value={condition.value as string}
              onChange={(e) => onChange({ ...condition, value: e.target.value })}
              className="px-3 py-1.5 rounded-md border bg-background text-sm min-w-[140px]"
            >
              <option value="">Select value...</option>
              {field.options.map(opt => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          ) : fieldType === 'boolean' ? (
            <select
              value={String(condition.value)}
              onChange={(e) => onChange({ ...condition, value: e.target.value === 'true' })}
              className="px-3 py-1.5 rounded-md border bg-background text-sm"
            >
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          ) : (
            <input
              type={fieldType === 'number' ? 'number' : 'text'}
              value={condition.value as string}
              onChange={(e) => onChange({
                ...condition,
                value: fieldType === 'number' ? Number(e.target.value) : e.target.value
              })}
              placeholder="Enter value..."
              className="px-3 py-1.5 rounded-md border bg-background text-sm min-w-[140px]"
            />
          )}
        </>
      )}

      {/* Remove button */}
      <button
        onClick={onRemove}
        className="p-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  )
}

interface RuleGroupBuilderProps {
  group: SegmentRules
  onChange: (group: SegmentRules) => void
  onRemove?: () => void
  depth?: number
}

function RuleGroupBuilder({ group, onChange, onRemove, depth = 0 }: RuleGroupBuilderProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  const addCondition = () => {
    onChange({
      ...group,
      conditions: [
        ...(group.conditions || []),
        { field: '', operator: 'equals', value: '' }
      ]
    })
  }

  const updateCondition = (index: number, condition: SegmentCondition) => {
    const newConditions = [...(group.conditions || [])]
    newConditions[index] = condition
    onChange({ ...group, conditions: newConditions })
  }

  const removeCondition = (index: number) => {
    onChange({
      ...group,
      conditions: (group.conditions || []).filter((_: SegmentCondition, i: number) => i !== index)
    })
  }

  const addGroup = () => {
    onChange({
      ...group,
      groups: [
        ...(group.groups || []),
        { logic: 'and', conditions: [], groups: [] }
      ]
    })
  }

  const updateGroup = (index: number, subGroup: SegmentRules) => {
    const newGroups = [...(group.groups || [])]
    newGroups[index] = subGroup
    onChange({ ...group, groups: newGroups })
  }

  const removeGroup = (index: number) => {
    onChange({
      ...group,
      groups: (group.groups || []).filter((_: SegmentRules, i: number) => i !== index)
    })
  }

  return (
    <div className={cn(
      'rounded-lg border',
      depth === 0 ? 'bg-card p-4' : 'bg-muted/20 p-3 ml-4'
    )}>
      {/* Group header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-muted rounded"
          >
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
          <Layers className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">Match</span>
          <select
            value={group.logic}
            onChange={(e) => onChange({ ...group, logic: e.target.value as 'and' | 'or' })}
            className="px-2 py-1 rounded border bg-background text-sm font-medium"
          >
            <option value="and">ALL</option>
            <option value="or">ANY</option>
          </select>
          <span className="text-sm text-muted-foreground">of the following conditions</span>
        </div>

        {onRemove && (
          <button
            onClick={onRemove}
            className="p-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-500 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {isExpanded && (
        <div className="space-y-3">
          {/* Conditions */}
          {(group.conditions || []).map((condition, index) => (
            <ConditionBuilder
              key={index}
              condition={condition}
              onChange={(c) => updateCondition(index, c)}
              onRemove={() => removeCondition(index)}
            />
          ))}

          {/* Nested groups */}
          {(group.groups || []).map((subGroup, index) => (
            <RuleGroupBuilder
              key={index}
              group={subGroup}
              onChange={(g) => updateGroup(index, g)}
              onRemove={() => removeGroup(index)}
              depth={depth + 1}
            />
          ))}

          {/* Add buttons */}
          <div className="flex items-center gap-2 pt-2">
            <button
              onClick={addCondition}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary/10 text-primary hover:bg-primary/20 text-sm font-medium transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Condition
            </button>
            {depth < 2 && (
              <button
                onClick={addGroup}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border hover:bg-muted text-sm font-medium transition-colors"
              >
                <Layers className="w-4 h-4" />
                Add Group
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

interface SegmentFormProps {
  segment?: CDPSegment
  onSave: () => void
  onCancel: () => void
}

function SegmentForm({ segment, onSave, onCancel }: SegmentFormProps) {
  const [name, setName] = useState(segment?.name || '')
  const [description, setDescription] = useState(segment?.description || '')
  const [segmentType, setSegmentType] = useState<'dynamic' | 'static'>(
    segment?.segment_type === 'static' ? 'static' : 'dynamic'
  )
  const [rules, setRules] = useState<SegmentRules>(
    (segment?.rules as unknown as SegmentRules) || { logic: 'and', conditions: [], groups: [] }
  )
  const [autoRefresh, setAutoRefresh] = useState(segment?.auto_refresh ?? true)
  const [refreshInterval, setRefreshInterval] = useState(segment?.refresh_interval_hours || 24)

  const createMutation = useCreateSegment()
  const updateMutation = useUpdateSegment()
  const previewMutation = usePreviewSegment()

  const [previewCount, setPreviewCount] = useState<number | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  const handlePreview = async () => {
    setPreviewLoading(true)
    try {
      const result = await previewMutation.mutateAsync({ rules })
      setPreviewCount(result.estimated_count)
    } catch (error) {
      console.error('Preview failed:', error)
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleSubmit = async () => {
    const data = {
      name,
      description,
      segment_type: segmentType,
      rules,
      auto_refresh: autoRefresh,
      refresh_interval_hours: refreshInterval,
    }

    try {
      if (segment) {
        await updateMutation.mutateAsync({ segmentId: segment.id, update: data })
      } else {
        await createMutation.mutateAsync(data)
      }
      onSave()
    } catch (error) {
      console.error('Save failed:', error)
    }
  }

  const isLoading = createMutation.isPending || updateMutation.isPending

  return (
    <div className="space-y-6">
      {/* Basic info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1.5">Segment Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., High-Value Customers"
            className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1.5">Type</label>
          <select
            value={segmentType}
            onChange={(e) => setSegmentType(e.target.value as 'dynamic' | 'static')}
            className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
          >
            <option value="dynamic">Dynamic (auto-updates)</option>
            <option value="static">Static (manual members)</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-1.5">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe this segment..."
          rows={2}
          className="w-full px-3 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20 resize-none"
        />
      </div>

      {/* Rules builder */}
      {segmentType === 'dynamic' && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <label className="block text-sm font-medium">Segment Rules</label>
            <button
              onClick={handlePreview}
              disabled={previewLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary/10 text-primary hover:bg-primary/20 text-sm font-medium transition-colors"
            >
              {previewLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Eye className="w-4 h-4" />
              )}
              Preview
            </button>
          </div>
          <RuleGroupBuilder
            group={rules}
            onChange={setRules}
          />
          {previewCount !== null && (
            <div className="mt-3 p-3 rounded-lg bg-primary/5 border border-primary/20 flex items-center gap-2">
              <Users className="w-5 h-5 text-primary" />
              <span className="text-sm">
                Estimated <strong>{previewCount.toLocaleString()}</strong> profiles match these rules
              </span>
            </div>
          )}
        </div>
      )}

      {/* Auto-refresh settings */}
      {segmentType === 'dynamic' && (
        <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/30 border">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="autoRefresh"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300"
            />
            <label htmlFor="autoRefresh" className="text-sm font-medium">
              Auto-refresh segment
            </label>
          </div>
          {autoRefresh && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">every</span>
              <select
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(Number(e.target.value))}
                className="px-2 py-1 rounded border bg-background text-sm"
              >
                <option value={1}>1 hour</option>
                <option value={6}>6 hours</option>
                <option value={12}>12 hours</option>
                <option value={24}>24 hours</option>
                <option value={48}>48 hours</option>
              </select>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-4 border-t">
        <button
          onClick={onCancel}
          className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!name || isLoading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {segment ? 'Update Segment' : 'Create Segment'}
        </button>
      </div>
    </div>
  )
}

export function SegmentBuilder() {
  const [showForm, setShowForm] = useState(false)
  const [selectedSegment, setSelectedSegment] = useState<CDPSegment | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  const { data: segmentsData, isLoading, refetch } = useSegments()
  const deleteMutation = useDeleteSegment()
  const computeMutation = useComputeSegment()

  const segments = segmentsData?.segments || []
  const filteredSegments = segments.filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleEdit = (segment: CDPSegment) => {
    setSelectedSegment(segment)
    setShowForm(true)
  }

  const handleDelete = async (segmentId: string) => {
    if (confirm('Are you sure you want to delete this segment?')) {
      await deleteMutation.mutateAsync(segmentId)
      refetch()
    }
  }

  const handleCompute = async (segmentId: string) => {
    await computeMutation.mutateAsync(segmentId)
    refetch()
  }

  const handleFormSave = () => {
    setShowForm(false)
    setSelectedSegment(null)
    refetch()
  }

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      active: 'bg-green-500/10 text-green-500',
      computing: 'bg-blue-500/10 text-blue-500',
      stale: 'bg-amber-500/10 text-amber-500',
      draft: 'bg-gray-500/10 text-gray-500',
    }
    return (
      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', styles[status] || styles.draft)}>
        {status}
      </span>
    )
  }

  if (showForm) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setShowForm(false); setSelectedSegment(null) }}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <ChevronDown className="w-5 h-5 rotate-90" />
          </button>
          <h2 className="text-xl font-semibold">
            {selectedSegment ? 'Edit Segment' : 'Create Segment'}
          </h2>
        </div>
        <SegmentForm
          segment={selectedSegment || undefined}
          onSave={handleFormSave}
          onCancel={() => { setShowForm(false); setSelectedSegment(null) }}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Users className="w-6 h-6 text-primary" />
            Segment Builder
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Create and manage customer segments based on behavior and attributes
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Segment
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search segments..."
          className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {/* Segments list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : filteredSegments.length === 0 ? (
        <div className="text-center py-12 bg-card border rounded-xl">
          <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="font-semibold mb-2">No segments yet</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Create your first segment to start grouping customers
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Segment
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSegments.map((segment) => (
            <div
              key={segment.id}
              className="p-4 rounded-xl border bg-card hover:shadow-md transition-all"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold">{segment.name}</h3>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {segment.description || 'No description'}
                  </p>
                </div>
                {getStatusBadge(segment.status)}
              </div>

              <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
                <div className="flex items-center gap-1">
                  <Users className="w-4 h-4" />
                  <span>{segment.profile_count?.toLocaleString() || 0}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  <span>{segment.segment_type}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-3 border-t">
                <button
                  onClick={() => handleEdit(segment)}
                  className="flex-1 px-3 py-1.5 rounded-md bg-muted hover:bg-muted/80 text-sm font-medium transition-colors"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleCompute(segment.id)}
                  disabled={computeMutation.isPending}
                  className="px-3 py-1.5 rounded-md bg-primary/10 text-primary hover:bg-primary/20 text-sm font-medium transition-colors"
                >
                  <RefreshCw className={cn('w-4 h-4', computeMutation.isPending && 'animate-spin')} />
                </button>
                <button
                  onClick={() => handleDelete(segment.id)}
                  className="px-3 py-1.5 rounded-md hover:bg-red-500/10 text-muted-foreground hover:text-red-500 text-sm font-medium transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SegmentBuilder
