import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Search,
  Plus,
  Play,
  Pause,
  Edit,
  Copy,
  ChevronRight,
  Bell,
  Tag,
  DollarSign,
  Settings,
  MessageCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePriceMetrics } from '@/hooks/usePriceMetrics'
import { useRules, useToggleRule, useDuplicateRule, useUpdateRule } from '@/api/hooks'
import { PageHeader } from '@/components/primitives/PageHeader'
import { StatRow, type StatRowItem } from '@/components/primitives/StatRow'
import { StatusPill } from '@/components/primitives/StatusPill'
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable'
import { statusVariant, statusLabel } from '@/lib/statusVariant'

type RuleStatus = 'active' | 'paused' | 'draft'
type RuleAction = 'apply_label' | 'send_alert' | 'pause_campaign' | 'adjust_budget' | 'notify_slack' | 'notify_whatsapp'

interface Rule {
  id: number
  name: string
  description: string
  status: RuleStatus
  condition: {
    field: string
    operator: string
    value: string
  }
  action: {
    type: RuleAction
    config: Record<string, unknown>
  }
  appliesTo: string[]
  triggerCount: number
  lastTriggered: string | null
  cooldownHours: number
  createdAt: string
}

const operators = [
  { value: 'equals', label: '=' },
  { value: 'not_equals', label: '≠' },
  { value: 'greater_than', label: '>' },
  { value: 'less_than', label: '<' },
  { value: 'greater_than_or_equal', label: '≥' },
  { value: 'less_than_or_equal', label: '≤' },
]

const fields = ['roas', 'ctr', 'cpc', 'cpa', 'spend', 'impressions', 'clicks', 'conversions', 'fatigue_score']

const COST_RELATED_FIELDS = ['spend', 'roas', 'cpc', 'cpa', 'budget', 'revenue', 'cost', 'profit', 'margin']

export function Rules() {
  const { t } = useTranslation()
  const { showPriceMetrics } = usePriceMetrics()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [showCreateModal, setShowCreateModal] = useState(false)

  const [editingRule, setEditingRule] = useState<Rule | null>(null)

  // Fetch rules from API
  const { data: rulesData, isLoading, error, refetch } = useRules()
  const toggleRule = useToggleRule()
  const duplicateRule = useDuplicateRule()
  const updateRule = useUpdateRule()

  // Handle duplicate rule
  const handleDuplicateRule = async (ruleId: number) => {
    try {
      await duplicateRule.mutateAsync(ruleId.toString())
    } catch {
      // silently handled – query invalidation refreshes list
    }
  }

  // Handle edit rule (open modal pre-filled)
  const handleEditRule = (rule: Rule) => {
    setEditingRule(rule)
    setShowCreateModal(true)
  }

  // Transform API data or fall back to mock
  const rules = useMemo((): Rule[] => {
    if (rulesData?.items && rulesData.items.length > 0) {
      return (rulesData.items as unknown as Array<Record<string, unknown>>).map((r) => ({
        id: Number(r.id) || 0,
        name: String(r.name || ''),
        description: String(r.description || ''),
        status: (r.status || r.is_active ? 'active' : 'paused') as Rule['status'],
        condition: (r.condition || (r.conditions as unknown as unknown[])?.[0] || { field: 'roas', operator: 'less_than', value: '2.0' }) as Rule['condition'],
        action: (r.action || (r.actions as unknown as unknown[])?.[0] || { type: 'send_alert', config: {} }) as Rule['action'],
        appliesTo: (r.applies_to || r.campaigns || []) as string[],
        triggerCount: Number(r.trigger_count || r.triggerCount) || 0,
        lastTriggered: (r.last_triggered || r.lastTriggered || null) as string | null,
        cooldownHours: Number(r.cooldown_hours || r.cooldownHours) || 24,
        createdAt: String(r.created_at || r.createdAt || new Date().toISOString()),
      }))
    }
    return []
  }, [rulesData])

  // Handle toggle rule status
  const handleToggleRule = async (ruleId: number, _currentStatus: RuleStatus) => {
    await toggleRule.mutateAsync(ruleId.toString())
  }

  const filteredRules = rules.filter((rule) => {
    if (searchQuery && !rule.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    if (statusFilter !== 'all' && rule.status !== statusFilter) {
      return false
    }
    return true
  })

  // "Triggers today" was the literal 23, rendered as a live metric whatever the
  // data said. Derived from last_triggered now: a number that can be wrong is
  // better than one that is decorative.
  const stats = useMemo((): StatRowItem[] => {
    const today = new Date().toDateString()
    const triggeredToday = rules.filter(
      (r) => r.lastTriggered && new Date(r.lastTriggered).toDateString() === today,
    ).length
    return [
      { label: 'Rules', value: String(rules.length) },
      { label: 'Active', value: String(rules.filter((r) => r.status === 'active').length) },
      { label: 'Triggered today', value: String(triggeredToday) },
      { label: 'Total triggers', value: String(rules.reduce((acc, r) => acc + r.triggerCount, 0)) },
    ]
  }, [rules])

  // getStatusBadge lived here — the third independent status badge in this
  // codebase, with its own greens and ambers. Replaced by StatusPill via the
  // shared statusVariant/statusLabel mapping.

  const getActionIcon = (action: RuleAction) => {
    switch (action) {
      case 'apply_label':
        return <Tag className="w-4 h-4 text-blue-500" />
      case 'send_alert':
        return <Bell className="w-4 h-4 text-amber-500" />
      case 'pause_campaign':
        return <Pause className="w-4 h-4 text-red-500" />
      case 'adjust_budget':
        return <DollarSign className="w-4 h-4 text-green-500" />
      case 'notify_slack':
        return <Settings className="w-4 h-4 text-purple-500" />
      case 'notify_whatsapp':
        return <MessageCircle className="w-4 h-4 text-green-600" />
    }
  }

  const getActionLabel = (action: RuleAction) => {
    const labels = {
      apply_label: 'Apply Label',
      send_alert: 'Send Alert',
      pause_campaign: 'Pause Campaign',
      adjust_budget: 'Adjust Budget',
      notify_slack: 'Notify Slack',
      notify_whatsapp: 'Notify WhatsApp',
    }
    return labels[action]
  }

  const getOperatorLabel = (operator: string) => {
    return operators.find((op) => op.value === operator)?.label || operator
  }

  const formatLastTriggered = (date: string | null) => {
    if (!date) return 'Never'
    const d = new Date(date)
    const now = new Date()
    const diffHours = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60))

    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffHours < 48) return 'Yesterday'
    return d.toLocaleDateString()
  }

  const columns: DataTableColumn<Rule>[] = [
    {
      id: 'name',
      header: 'Rule',
      sortable: true,
      sortAccessor: (r) => r.name,
      cell: (r) => (
        <div className="min-w-0">
          <div className="truncate font-medium text-foreground">{r.name}</div>
          {r.description ? (
            <div className="truncate text-xs text-muted-foreground">{r.description}</div>
          ) : null}
        </div>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: (r) => (
        <StatusPill size="sm" variant={statusVariant(r.status)}>
          {statusLabel(r.status)}
        </StatusPill>
      ),
    },
    {
      id: 'logic',
      header: 'Logic',
      hideOnMobile: true,
      // The rule reads as a sentence in mono: IF <field> <op> <value> THEN <action>.
      cell: (r) => (
        <span className="flex flex-wrap items-center gap-1.5 font-mono text-xs text-muted-foreground">
          <span className="text-primary">IF</span>
          <span className="text-foreground">{r.condition.field}</span>
          <span>{getOperatorLabel(r.condition.operator)}</span>
          <span className="text-foreground">
            {!showPriceMetrics && COST_RELATED_FIELDS.includes(r.condition.field)
              ? '***'
              : r.condition.value}
          </span>
          <ChevronRight className="h-3 w-3" />
          <span className="text-primary">THEN</span>
          <span className="inline-flex items-center gap-1 text-foreground">
            {getActionIcon(r.action.type)}
            {getActionLabel(r.action.type)}
          </span>
        </span>
      ),
    },
    {
      id: 'triggers',
      header: 'Triggers',
      sortable: true,
      sortAccessor: (r) => r.triggerCount,
      headerClassName: 'text-right',
      cellClassName: 'text-right font-mono tabular-nums',
      cell: (r) => String(r.triggerCount),
    },
    {
      id: 'last',
      header: 'Last fired',
      hideOnMobile: true,
      headerClassName: 'text-right',
      cellClassName: 'text-right font-mono text-xs',
      cell: (r) => formatLastTriggered(r.lastTriggered),
    },
    {
      id: 'actions',
      header: '',
      className: 'w-32',
      cellClassName: 'text-right',
      // Hidden until hover, always reachable by keyboard via focus-within.
      cell: (r) => (
        <div className="flex justify-end gap-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover/row:opacity-100">
          <button
            type="button"
            onClick={() => handleToggleRule(r.id, r.status)}
            disabled={toggleRule.isPending}
            aria-label={r.status === 'active' ? `Pause ${r.name}` : `Activate ${r.name}`}
            className="rounded-full p-2 hover:bg-muted disabled:opacity-50"
          >
            {r.status === 'active' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
          <button
            type="button"
            onClick={() => handleEditRule(r)}
            aria-label={`Edit ${r.name}`}
            className="rounded-full p-2 hover:bg-muted"
          >
            <Edit className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => handleDuplicateRule(r.id)}
            disabled={duplicateRule.isPending}
            aria-label={`Duplicate ${r.name}`}
            className="rounded-full p-2 hover:bg-muted disabled:opacity-50"
          >
            <Copy className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="px-8 py-6">
      <PageHeader
        title={t('rules.title')}
        context={
          rules.length
            ? `${rules.filter((r) => r.status === 'active').length} active · ${rules.filter((r) => r.status === 'paused').length} paused`
            : t('rules.subtitle')
        }
        actions={
          <>
            <button
              type="button"
              onClick={() => refetch()}
              disabled={isLoading}
              aria-label="Refresh rules"
              className="rounded-full border border-border p-2 hover:bg-muted"
            >
              <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
            </button>
            <button
              type="button"
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-4 w-4" />
              <span>{t('rules.createRule')}</span>
            </button>
          </>
        }
      />

      <StatRow items={stats} />

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={t('rules.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
        >
          <option value="all">{t('rules.allStatuses')}</option>
          <option value="active">{t('rules.active')}</option>
          <option value="paused">{t('rules.paused')}</option>
          <option value="draft">{t('rules.draft')}</option>
        </select>
      </div>

      <DataTable
        data={filteredRules}
        columns={columns}
        rowKey={(r) => r.id}
        loading={isLoading}
        ariaLabel="Automation rules"
        className="mt-4"
        emptyMessage="No automation rules yet. Create one to act on signal changes."
        // An empty list and a failed fetch must never look identical.
        error={error ? "Could not load rules. Retry, or check the connection." : undefined}
      />

      {/* Create / Edit Rule Modal */}
      {showCreateModal && (
        <RuleModal
          rule={editingRule}
          fields={fields}
          operators={operators}
          onClose={() => { setShowCreateModal(false); setEditingRule(null) }}
          onSave={async (data) => {
            if (editingRule) {
              await updateRule.mutateAsync({ id: editingRule.id.toString(), data })
            }
            setShowCreateModal(false)
            setEditingRule(null)
          }}
          isSaving={updateRule.isPending}
          t={t}
        />
      )}
    </div>
  )
}

// =============================================================================
// Rule Create/Edit Modal
// =============================================================================

interface RuleModalProps {
  rule: Rule | null
  fields: string[]
  operators: { value: string; label: string }[]
  onClose: () => void
  onSave: (data: Record<string, unknown>) => Promise<void>
  isSaving: boolean
  t: (key: string) => string
}

function RuleModal({ rule, fields: fieldsList, operators: operatorsList, onClose, onSave, isSaving, t }: RuleModalProps) {
  const isEditing = !!rule
  const [name, setName] = useState(rule?.name || '')
  const [description, setDescription] = useState(rule?.description || '')
  const [conditionField, setConditionField] = useState(rule?.condition?.field || fieldsList[0])
  const [conditionOperator, setConditionOperator] = useState(rule?.condition?.operator || operatorsList[0].value)
  const [conditionValue, setConditionValue] = useState(rule?.condition?.value || '')
  const [actionType, setActionType] = useState(rule?.action?.type || 'send_alert')

  const handleSubmit = async () => {
    const data: Record<string, unknown> = {
      name,
      description,
      condition_field: conditionField,
      condition_operator: conditionOperator,
      condition_value: conditionValue,
      action_type: actionType,
    }
    await onSave(data)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background rounded-xl p-6 w-full max-w-2xl mx-4">
        <h2 className="text-xl font-bold mb-4">
          {isEditing ? 'Edit Rule' : t('rules.createRule')}
        </h2>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">{t('rules.ruleName')}</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
              placeholder="e.g., Pause Low Performers"
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-1 block">{t('rules.description')}</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
              rows={2}
              placeholder="Describe what this rule does..."
            />
          </div>

          <div className="p-4 rounded-lg bg-muted/50">
            <p className="text-sm font-medium mb-3">{t('rules.condition')}</p>
            <div className="flex gap-2">
              <select
                value={conditionField}
                onChange={(e) => setConditionField(e.target.value)}
                className="flex-1 px-3 py-2 rounded-lg border bg-background"
              >
                {fieldsList.map((field) => (
                  <option key={field} value={field}>
                    {field.toUpperCase()}
                  </option>
                ))}
              </select>
              <select
                value={conditionOperator}
                onChange={(e) => setConditionOperator(e.target.value)}
                className="w-24 px-3 py-2 rounded-lg border bg-background"
              >
                {operatorsList.map((op) => (
                  <option key={op.value} value={op.value}>
                    {op.label}
                  </option>
                ))}
              </select>
              <input
                type="text"
                value={conditionValue}
                onChange={(e) => setConditionValue(e.target.value)}
                className="w-32 px-3 py-2 rounded-lg border bg-background"
                placeholder="Value"
              />
            </div>
          </div>

          <div className="p-4 rounded-lg bg-muted/50">
            <p className="text-sm font-medium mb-3">{t('rules.action')}</p>
            <select
              value={actionType}
              onChange={(e) => setActionType(e.target.value as RuleAction)}
              className="w-full px-3 py-2 rounded-lg border bg-background"
            >
              <option value="apply_label">Apply Label</option>
              <option value="send_alert">Send Alert</option>
              <option value="pause_campaign">Pause Campaign</option>
              <option value="adjust_budget">Adjust Budget</option>
              <option value="notify_slack">Notify Slack</option>
              <option value="notify_whatsapp">Notify WhatsApp</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSaving || !name.trim()}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
            ) : null}
            {isEditing ? 'Save Changes' : t('rules.createRule')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default Rules
