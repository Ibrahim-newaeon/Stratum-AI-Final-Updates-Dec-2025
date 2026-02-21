import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Search,
  Plus,
  MoreHorizontal,
  Play,
  Pause,
  Edit,
  Copy,
  Zap,
  Clock,
  CheckCircle2,
  ChevronRight,
  Bell,
  Tag,
  DollarSign,
  Settings,
  MessageCircle,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { usePriceMetrics } from '@/hooks/usePriceMetrics'
import { useRules, useToggleRule, useDuplicateRule, useUpdateRule } from '@/api/hooks'

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
    config: Record<string, any>
  }
  appliesTo: string[]
  triggerCount: number
  lastTriggered: string | null
  cooldownHours: number
  createdAt: string
}

const mockRules: Rule[] = [
  {
    id: 1,
    name: 'WhatsApp Alert for Budget Overspend',
    description: 'Send WhatsApp notification when campaign spends over 80% of budget',
    status: 'active',
    condition: { field: 'spend', operator: 'greater_than', value: '800' },
    action: { type: 'notify_whatsapp', config: { contact_ids: [1, 2], template_name: 'rule_alert' } },
    appliesTo: ['Summer Sale 2024', 'Brand Awareness Q4'],
    triggerCount: 7,
    lastTriggered: '2024-12-06T08:00:00Z',
    cooldownHours: 12,
    createdAt: '2024-12-01',
  },
  {
    id: 2,
    name: 'Pause Low ROAS Campaigns',
    description: 'Automatically pause campaigns when ROAS drops below 2.0',
    status: 'active',
    condition: { field: 'roas', operator: 'less_than', value: '2.0' },
    action: { type: 'pause_campaign', config: {} },
    appliesTo: ['All Campaigns'],
    triggerCount: 12,
    lastTriggered: '2024-11-28T14:30:00Z',
    cooldownHours: 24,
    createdAt: '2024-06-15',
  },
  {
    id: 3,
    name: 'Alert on High Spend',
    description: 'Send alert when daily spend exceeds $500',
    status: 'active',
    condition: { field: 'spend', operator: 'greater_than', value: '500' },
    action: { type: 'send_alert', config: { email: 'marketing@company.com' } },
    appliesTo: ['Summer Sale 2024', 'Brand Awareness Q4'],
    triggerCount: 45,
    lastTriggered: '2024-11-29T09:15:00Z',
    cooldownHours: 4,
    createdAt: '2024-07-20',
  },
  {
    id: 4,
    name: 'Label High Performers',
    description: 'Apply "star" label to campaigns with ROAS above 4.0',
    status: 'active',
    condition: { field: 'roas', operator: 'greater_than', value: '4.0' },
    action: { type: 'apply_label', config: { label: 'star-performer' } },
    appliesTo: ['All Campaigns'],
    triggerCount: 8,
    lastTriggered: '2024-11-27T16:45:00Z',
    cooldownHours: 12,
    createdAt: '2024-08-10',
  },
  {
    id: 5,
    name: 'Budget Boost for Winners',
    description: 'Increase budget by 20% when CTR exceeds 3%',
    status: 'paused',
    condition: { field: 'ctr', operator: 'greater_than', value: '3.0' },
    action: { type: 'adjust_budget', config: { adjustment_percent: 20 } },
    appliesTo: ['Product Launch - Widget Pro'],
    triggerCount: 3,
    lastTriggered: '2024-11-25T11:00:00Z',
    cooldownHours: 48,
    createdAt: '2024-09-05',
  },
  {
    id: 6,
    name: 'Slack Alert for Fatigue',
    description: 'Notify Slack when creative fatigue score exceeds 70%',
    status: 'draft',
    condition: { field: 'fatigue_score', operator: 'greater_than', value: '70' },
    action: { type: 'notify_slack', config: { channel: '#marketing-alerts' } },
    appliesTo: [],
    triggerCount: 0,
    lastTriggered: null,
    cooldownHours: 24,
    createdAt: '2024-11-28',
  },
]

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
  const { data: rulesData, isLoading } = useRules()
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
    return mockRules
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

  const getStatusBadge = (status: RuleStatus) => {
    const config = {
      active: { color: 'bg-green-500/10 text-green-500', icon: CheckCircle2, label: 'Active' },
      paused: { color: 'bg-amber-500/10 text-amber-500', icon: Pause, label: 'Paused' },
      draft: { color: 'bg-gray-500/10 text-gray-500', icon: Edit, label: 'Draft' },
    }
    const { color, icon: Icon, label } = config[status]
    return (
      <span className={cn('px-2 py-1 rounded-full text-xs font-medium inline-flex items-center gap-1', color)}>
        <Icon className="w-3 h-3" />
        {label}
      </span>
    )
  }

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

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="w-7 h-7 text-primary" />
            {t('rules.title')}
          </h1>
          <p className="text-muted-foreground">{t('rules.subtitle')}</p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>{t('rules.createRule')}</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <p className="text-sm text-muted-foreground mb-1">{t('rules.totalRules')}</p>
          <p className="text-2xl font-bold">{isLoading ? '...' : rules.length}</p>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <p className="text-sm text-muted-foreground mb-1">{t('rules.activeRules')}</p>
          <p className="text-2xl font-bold text-green-500">
            {isLoading ? '...' : rules.filter((r) => r.status === 'active').length}
          </p>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <p className="text-sm text-muted-foreground mb-1">{t('rules.triggersToday')}</p>
          <p className="text-2xl font-bold text-primary">23</p>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <p className="text-sm text-muted-foreground mb-1">{t('rules.actionsExecuted')}</p>
          <p className="text-2xl font-bold">
            {isLoading ? '...' : rules.reduce((acc, r) => acc + r.triggerCount, 0)}
          </p>
        </div>
      </div>

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

      {/* Rules List */}
      <div className="space-y-4">
        {filteredRules.map((rule) => (
          <div
            key={rule.id}
            className="rounded-xl border bg-card p-5 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start gap-4">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Zap className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold">{rule.name}</h3>
                    {getStatusBadge(rule.status)}
                  </div>
                  <p className="text-sm text-muted-foreground">{rule.description}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {rule.status === 'active' ? (
                  <button
                    onClick={() => handleToggleRule(rule.id, rule.status)}
                    disabled={toggleRule.isPending}
                    className="p-2 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
                    title="Pause"
                  >
                    {toggleRule.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Pause className="w-4 h-4" />}
                  </button>
                ) : (
                  <button
                    onClick={() => handleToggleRule(rule.id, rule.status)}
                    disabled={toggleRule.isPending}
                    className="p-2 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
                    title="Activate"
                  >
                    {toggleRule.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  </button>
                )}
                <button
                  onClick={() => handleEditRule(rule)}
                  className="p-2 rounded-lg hover:bg-muted transition-colors"
                  title="Edit"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDuplicateRule(rule.id)}
                  disabled={duplicateRule.isPending}
                  className="p-2 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
                  title="Duplicate"
                >
                  {duplicateRule.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Copy className="w-4 h-4" />}
                </button>
                <button className="p-2 rounded-lg hover:bg-muted transition-colors">
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Rule Logic Display */}
            <div className="flex flex-wrap items-center gap-2 mb-4 p-3 rounded-lg bg-muted/50">
              <span className="text-sm font-medium text-primary">IF</span>
              <span className="px-2 py-1 rounded bg-background text-sm font-mono">
                {rule.condition.field}
              </span>
              <span className="text-sm font-bold">
                {getOperatorLabel(rule.condition.operator)}
              </span>
              <span className="px-2 py-1 rounded bg-background text-sm font-mono">
                {!showPriceMetrics && COST_RELATED_FIELDS.includes(rule.condition.field)
                  ? '***'
                  : rule.condition.value}
              </span>
              <ChevronRight className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium text-primary">THEN</span>
              <div className="flex items-center gap-1 px-2 py-1 rounded bg-background">
                {getActionIcon(rule.action.type)}
                <span className="text-sm">{getActionLabel(rule.action.type)}</span>
              </div>
            </div>

            {/* Rule Metadata */}
            <div className="flex flex-wrap items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">{t('rules.appliesTo')}:</span>
                <span className="font-medium">
                  {rule.appliesTo.length > 0 ? rule.appliesTo.join(', ') : 'Not configured'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">{t('rules.cooldown')}:</span>
                <span className="font-medium">{rule.cooldownHours}h</span>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">{t('rules.triggered')}:</span>
                <span className="font-medium">{rule.triggerCount} times</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">{t('rules.lastTriggered')}:</span>
                <span className="font-medium">{formatLastTriggered(rule.lastTriggered)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredRules.length === 0 && (
        <div className="text-center py-12">
          <Zap className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">{t('rules.noRules')}</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 text-primary hover:underline"
          >
            {t('rules.createFirst')}
          </button>
        </div>
      )}

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
