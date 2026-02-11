import { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Bell,
  CheckCircle2,
  ChevronRight,
  Clock,
  Copy,
  DollarSign,
  Edit,
  Loader2,
  MessageCircle,
  Pause,
  Play,
  Plus,
  Search,
  Settings,
  Tag,
  Trash2,
  X,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useRules, useToggleRule, useCreateRule, useUpdateRule, useDeleteRule } from '@/api/hooks';
import { useToast } from '@/components/ui/use-toast';

type RuleStatus = 'active' | 'paused' | 'draft';
type RuleAction =
  | 'apply_label'
  | 'send_alert'
  | 'pause_campaign'
  | 'adjust_budget'
  | 'notify_slack'
  | 'notify_whatsapp';

interface Rule {
  id: number;
  name: string;
  description: string;
  status: RuleStatus;
  condition: {
    field: string;
    operator: string;
    value: string;
  };
  action: {
    type: RuleAction;
    config: Record<string, any>;
  };
  appliesTo: string[];
  triggerCount: number;
  lastTriggered: string | null;
  cooldownHours: number;
  createdAt: string;
}

const mockRules: Rule[] = [
  {
    id: 1,
    name: 'WhatsApp Alert for Budget Overspend',
    description: 'Send WhatsApp notification when campaign spends over 80% of budget',
    status: 'active',
    condition: { field: 'spend', operator: 'greater_than', value: '800' },
    action: {
      type: 'notify_whatsapp',
      config: { contact_ids: [1, 2], template_name: 'rule_alert' },
    },
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
];

const operators = [
  { value: 'equals', label: '=' },
  { value: 'not_equals', label: '≠' },
  { value: 'greater_than', label: '>' },
  { value: 'less_than', label: '<' },
  { value: 'greater_than_or_equal', label: '≥' },
  { value: 'less_than_or_equal', label: '≤' },
];

const fields = [
  'roas',
  'ctr',
  'cpc',
  'cpa',
  'spend',
  'impressions',
  'clicks',
  'conversions',
  'fatigue_score',
];

export function Rules() {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { toast } = useToast();

  // Modal state
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<Rule | null>(null);
  const [ruleForm, setRuleForm] = useState({
    name: '',
    description: '',
    conditionField: 'roas',
    conditionOperator: 'less_than',
    conditionValue: '',
    actionType: 'send_alert' as RuleAction,
    cooldownHours: 24,
  });

  // Fetch rules from API
  const { data: rulesData, isLoading } = useRules();
  const toggleRule = useToggleRule();
  const createRule = useCreateRule();
  const updateRule = useUpdateRule();
  const deleteRule = useDeleteRule();

  const resetForm = useCallback(() => {
    setRuleForm({
      name: '',
      description: '',
      conditionField: 'roas',
      conditionOperator: 'less_than',
      conditionValue: '',
      actionType: 'send_alert',
      cooldownHours: 24,
    });
    setEditingRule(null);
  }, []);

  const openCreateModal = useCallback(() => {
    resetForm();
    setShowCreateModal(true);
  }, [resetForm]);

  const openEditModal = useCallback((rule: Rule) => {
    setEditingRule(rule);
    setRuleForm({
      name: rule.name,
      description: rule.description,
      conditionField: rule.condition.field,
      conditionOperator: rule.condition.operator,
      conditionValue: rule.condition.value,
      actionType: rule.action.type,
      cooldownHours: rule.cooldownHours,
    });
    setShowCreateModal(true);
  }, []);

  const handleDuplicate = useCallback(async (rule: Rule) => {
    try {
      await createRule.mutateAsync({
        name: `${rule.name} (Copy)`,
        description: rule.description,
        conditions: [{ field: rule.condition.field, operator: rule.condition.operator as any, value: rule.condition.value }],
        actions: [{ type: rule.action.type as any, config: rule.action.config }],
        trigger: 'metric_threshold',
        status: 'draft',
      } as any);
      toast({ title: 'Rule duplicated', description: `"${rule.name}" has been duplicated as a draft.` });
    } catch {
      toast({ title: 'Error', description: 'Failed to duplicate rule.', variant: 'destructive' });
    }
  }, [createRule, toast]);

  const handleSaveRule = useCallback(async () => {
    if (!ruleForm.name.trim() || !ruleForm.conditionValue.trim()) return;

    const payload = {
      name: ruleForm.name,
      description: ruleForm.description,
      conditions: [{
        field: ruleForm.conditionField,
        operator: ruleForm.conditionOperator as any,
        value: ruleForm.conditionValue,
      }],
      actions: [{
        type: ruleForm.actionType as any,
        config: {},
      }],
      trigger: 'metric_threshold' as const,
      cooldown_hours: ruleForm.cooldownHours,
    };

    try {
      if (editingRule) {
        await updateRule.mutateAsync({ id: editingRule.id.toString(), data: payload as any });
        toast({ title: 'Rule updated', description: `"${ruleForm.name}" has been updated.` });
      } else {
        await createRule.mutateAsync(payload as any);
        toast({ title: 'Rule created', description: `"${ruleForm.name}" has been created.` });
      }
      setShowCreateModal(false);
      resetForm();
    } catch {
      toast({ title: 'Error', description: `Failed to ${editingRule ? 'update' : 'create'} rule.`, variant: 'destructive' });
    }
  }, [ruleForm, editingRule, createRule, updateRule, toast, resetForm]);

  const handleDeleteRule = useCallback(async (rule: Rule) => {
    try {
      await deleteRule.mutateAsync(rule.id.toString());
      toast({ title: 'Rule deleted', description: `"${rule.name}" has been deleted.` });
      setShowDeleteConfirm(null);
    } catch {
      toast({ title: 'Error', description: 'Failed to delete rule.', variant: 'destructive' });
    }
  }, [deleteRule, toast]);

  // Transform API data or fall back to mock
  const rules = useMemo((): Rule[] => {
    if (rulesData?.items && rulesData.items.length > 0) {
      return rulesData.items.map((r: any) => ({
        id: Number(r.id) || 0,
        name: r.name || '',
        description: r.description || '',
        status: r.status || r.is_active ? 'active' : 'paused',
        condition: r.condition ||
          r.conditions?.[0] || { field: 'roas', operator: 'less_than', value: '2.0' },
        action: r.action || r.actions?.[0] || { type: 'send_alert', config: {} },
        appliesTo: r.applies_to || r.campaigns || [],
        triggerCount: r.trigger_count || r.triggerCount || 0,
        lastTriggered: r.last_triggered || r.lastTriggered || null,
        cooldownHours: r.cooldown_hours || r.cooldownHours || 24,
        createdAt: r.created_at || r.createdAt || new Date().toISOString(),
      }));
    }
    return mockRules;
  }, [rulesData]);

  // Handle toggle rule status
  const handleToggleRule = async (ruleId: number, _currentStatus: RuleStatus) => {
    await toggleRule.mutateAsync(ruleId.toString());
  };

  const filteredRules = rules.filter((rule) => {
    if (searchQuery && !rule.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (statusFilter !== 'all' && rule.status !== statusFilter) {
      return false;
    }
    return true;
  });

  const getStatusBadge = (status: RuleStatus) => {
    const config = {
      active: { color: 'bg-green-500/10 text-green-500', icon: CheckCircle2, label: 'Active' },
      paused: { color: 'bg-amber-500/10 text-amber-500', icon: Pause, label: 'Paused' },
      draft: { color: 'bg-gray-500/10 text-gray-500', icon: Edit, label: 'Draft' },
    };
    const { color, icon: Icon, label } = config[status];
    return (
      <span
        className={cn(
          'px-2 py-1 rounded-full text-xs font-medium inline-flex items-center gap-1',
          color
        )}
      >
        <Icon className="w-3 h-3" />
        {label}
      </span>
    );
  };

  const getActionIcon = (action: RuleAction) => {
    switch (action) {
      case 'apply_label':
        return <Tag className="w-4 h-4 text-blue-500" />;
      case 'send_alert':
        return <Bell className="w-4 h-4 text-amber-500" />;
      case 'pause_campaign':
        return <Pause className="w-4 h-4 text-red-500" />;
      case 'adjust_budget':
        return <DollarSign className="w-4 h-4 text-green-500" />;
      case 'notify_slack':
        return <Settings className="w-4 h-4 text-purple-500" />;
      case 'notify_whatsapp':
        return <MessageCircle className="w-4 h-4 text-green-600" />;
    }
  };

  const getActionLabel = (action: RuleAction) => {
    const labels = {
      apply_label: 'Apply Label',
      send_alert: 'Send Alert',
      pause_campaign: 'Pause Campaign',
      adjust_budget: 'Adjust Budget',
      notify_slack: 'Notify Slack',
      notify_whatsapp: 'Notify WhatsApp',
    };
    return labels[action];
  };

  const getOperatorLabel = (operator: string) => {
    return operators.find((op) => op.value === operator)?.label || operator;
  };

  const formatLastTriggered = (date: string | null) => {
    if (!date) return 'Never';
    const d = new Date(date);
    const now = new Date();
    const diffHours = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60));

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffHours < 48) return 'Yesterday';
    return d.toLocaleDateString();
  };

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
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>{t('rules.createRule')}</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="metric-card info p-4">
          <p className="text-sm text-muted-foreground mb-1">{t('rules.totalRules')}</p>
          <p className="text-2xl font-bold">{isLoading ? '...' : rules.length}</p>
        </div>
        <div className="metric-card success p-4">
          <p className="text-sm text-muted-foreground mb-1">{t('rules.activeRules')}</p>
          <p className="text-2xl font-bold text-green-500">
            {isLoading ? '...' : rules.filter((r) => r.status === 'active').length}
          </p>
        </div>
        <div className="metric-card active p-4">
          <p className="text-sm text-muted-foreground mb-1">{t('rules.triggersToday')}</p>
          <p className="text-2xl font-bold text-primary">23</p>
        </div>
        <div className="metric-card premium p-4">
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
                    {toggleRule.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Pause className="w-4 h-4" />
                    )}
                  </button>
                ) : (
                  <button
                    onClick={() => handleToggleRule(rule.id, rule.status)}
                    disabled={toggleRule.isPending}
                    className="p-2 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
                    title="Activate"
                  >
                    {toggleRule.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </button>
                )}
                <button
                  onClick={() => openEditModal(rule)}
                  className="p-2 rounded-lg hover:bg-muted transition-colors"
                  title="Edit"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDuplicate(rule)}
                  disabled={createRule.isPending}
                  className="p-2 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
                  title="Duplicate"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setShowDeleteConfirm(rule)}
                  className="p-2 rounded-lg hover:bg-muted hover:text-red-500 transition-colors"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Rule Logic Display */}
            <div className="flex flex-wrap items-center gap-2 mb-4 p-3 rounded-lg bg-muted/50">
              <span className="text-sm font-medium text-primary">IF</span>
              <span className="px-2 py-1 rounded bg-background text-sm font-mono">
                {rule.condition.field}
              </span>
              <span className="text-sm font-bold">{getOperatorLabel(rule.condition.operator)}</span>
              <span className="px-2 py-1 rounded bg-background text-sm font-mono">
                {rule.condition.value}
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
            onClick={openCreateModal}
            className="mt-4 text-primary hover:underline"
          >
            {t('rules.createFirst')}
          </button>
        </div>
      )}

      {/* Create/Edit Rule Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-xl p-6 w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">
                {editingRule ? 'Edit Rule' : t('rules.createRule')}
              </h2>
              <button
                onClick={() => { setShowCreateModal(false); resetForm(); }}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-1 block">{t('rules.ruleName')}</label>
                <input
                  type="text"
                  value={ruleForm.name}
                  onChange={(e) => setRuleForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="e.g., Pause Low Performers"
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-1 block">{t('rules.description')}</label>
                <textarea
                  value={ruleForm.description}
                  onChange={(e) => setRuleForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                  rows={2}
                  placeholder="Describe what this rule does..."
                />
              </div>

              <div className="p-4 rounded-lg bg-muted/50">
                <p className="text-sm font-medium mb-3">{t('rules.condition')}</p>
                <div className="flex gap-2">
                  <select
                    value={ruleForm.conditionField}
                    onChange={(e) => setRuleForm(f => ({ ...f, conditionField: e.target.value }))}
                    className="flex-1 px-3 py-2 rounded-lg border bg-background"
                  >
                    {fields.map((field) => (
                      <option key={field} value={field}>
                        {field.toUpperCase()}
                      </option>
                    ))}
                  </select>
                  <select
                    value={ruleForm.conditionOperator}
                    onChange={(e) => setRuleForm(f => ({ ...f, conditionOperator: e.target.value }))}
                    className="w-24 px-3 py-2 rounded-lg border bg-background"
                  >
                    {operators.map((op) => (
                      <option key={op.value} value={op.value}>
                        {op.label}
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={ruleForm.conditionValue}
                    onChange={(e) => setRuleForm(f => ({ ...f, conditionValue: e.target.value }))}
                    className="w-32 px-3 py-2 rounded-lg border bg-background"
                    placeholder="Value"
                  />
                </div>
              </div>

              <div className="p-4 rounded-lg bg-muted/50">
                <p className="text-sm font-medium mb-3">{t('rules.action')}</p>
                <select
                  value={ruleForm.actionType}
                  onChange={(e) => setRuleForm(f => ({ ...f, actionType: e.target.value as RuleAction }))}
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

              <div>
                <label className="text-sm font-medium mb-1 block">Cooldown (hours)</label>
                <input
                  type="number"
                  value={ruleForm.cooldownHours}
                  onChange={(e) => setRuleForm(f => ({ ...f, cooldownHours: parseInt(e.target.value) || 1 }))}
                  className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                  min={1}
                  max={168}
                />
                <p className="text-xs text-muted-foreground mt-1">Minimum time between rule triggers</p>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => { setShowCreateModal(false); resetForm(); }}
                className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleSaveRule}
                disabled={createRule.isPending || updateRule.isPending || !ruleForm.name.trim() || !ruleForm.conditionValue.trim()}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {(createRule.isPending || updateRule.isPending) && <Loader2 className="w-4 h-4 animate-spin" />}
                {editingRule ? 'Update Rule' : t('rules.createRule')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-xl p-6 w-full max-w-md mx-4">
            <h2 className="text-lg font-bold mb-2">Delete Rule</h2>
            <p className="text-muted-foreground mb-4">
              Are you sure you want to delete &quot;{showDeleteConfirm.name}&quot;? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteRule(showDeleteConfirm)}
                disabled={deleteRule.isPending}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {deleteRule.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Rules;
