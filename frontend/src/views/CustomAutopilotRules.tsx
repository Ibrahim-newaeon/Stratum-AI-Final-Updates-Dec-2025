/**
 * Custom Autopilot Rules View - Enterprise Feature
 *
 * Page for managing custom autopilot automation rules.
 * Enterprise tier only.
 */

import { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Copy,
  Edit,
  Filter,
  Loader2,
  MoreHorizontal,
  Pause,
  Play,
  Plus,
  Search,
  Shield,
  Trash2,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { CustomAutopilotRulesBuilder } from '@/components/autopilot/CustomAutopilotRulesBuilder';

// Mock data for existing rules
const mockRules = [
  {
    id: '1',
    name: 'Scale High ROAS Campaigns',
    description: 'Automatically increase budget by 20% when ROAS exceeds 4x for 3 consecutive days',
    status: 'active' as const,
    conditionGroups: [
      {
        id: '1',
        logic: 'AND' as const,
        conditions: [
          { id: '1', field: 'roas', operator: 'gt', value: '4.0', valueType: 'number' as const },
          {
            id: '2',
            field: 'days_running',
            operator: 'gte',
            value: '3',
            valueType: 'number' as const,
          },
        ],
      },
    ],
    conditionLogic: 'AND' as const,
    actions: [
      {
        id: '1',
        type: 'scale_budget',
        config: { direction: 'increase', amount: '20' },
        priority: 1,
      },
    ],
    targeting: { platforms: ['meta', 'google'], campaignTypes: [], specificCampaigns: [] },
    schedule: { enabled: false, frequency: 'hourly' as const, timezone: 'UTC' },
    trustGate: { enabled: true, minSignalHealth: 70, requireApproval: false, dryRunFirst: true },
    cooldownHours: 48,
    maxExecutionsPerDay: 5,
    triggerCount: 23,
    lastTriggered: '2024-12-10T14:30:00Z',
    createdAt: '2024-11-01',
  },
  {
    id: '2',
    name: 'Pause Underperformers',
    description: 'Pause campaigns with CPA > $50 and less than 10 conversions after 7 days',
    status: 'active' as const,
    conditionGroups: [
      {
        id: '1',
        logic: 'AND' as const,
        conditions: [
          { id: '1', field: 'cpa', operator: 'gt', value: '50', valueType: 'currency' as const },
          {
            id: '2',
            field: 'conversions',
            operator: 'lt',
            value: '10',
            valueType: 'number' as const,
          },
          {
            id: '3',
            field: 'days_running',
            operator: 'gte',
            value: '7',
            valueType: 'number' as const,
          },
        ],
      },
    ],
    conditionLogic: 'AND' as const,
    actions: [{ id: '1', type: 'pause_campaign', config: {}, priority: 1 }],
    targeting: { platforms: [], campaignTypes: ['prospecting'], specificCampaigns: [] },
    schedule: { enabled: false, frequency: 'hourly' as const, timezone: 'UTC' },
    trustGate: { enabled: true, minSignalHealth: 70, requireApproval: true, dryRunFirst: false },
    cooldownHours: 24,
    maxExecutionsPerDay: 10,
    triggerCount: 8,
    lastTriggered: '2024-12-08T09:15:00Z',
    createdAt: '2024-10-15',
  },
  {
    id: '3',
    name: 'Creative Fatigue Alert',
    description: 'Send Slack notification when creative fatigue score exceeds 70%',
    status: 'paused' as const,
    conditionGroups: [
      {
        id: '1',
        logic: 'AND' as const,
        conditions: [
          {
            id: '1',
            field: 'fatigue_score',
            operator: 'gt',
            value: '70',
            valueType: 'percentage' as const,
          },
        ],
      },
    ],
    conditionLogic: 'AND' as const,
    actions: [
      { id: '1', type: 'notify_slack', config: { channel: '#creative-alerts' }, priority: 1 },
    ],
    targeting: { platforms: ['meta'], campaignTypes: [], specificCampaigns: [] },
    schedule: { enabled: true, frequency: 'daily' as const, timezone: 'America/New_York' },
    trustGate: { enabled: false, minSignalHealth: 0, requireApproval: false, dryRunFirst: false },
    cooldownHours: 24,
    maxExecutionsPerDay: 3,
    triggerCount: 15,
    lastTriggered: '2024-12-05T10:00:00Z',
    createdAt: '2024-09-20',
  },
];

export default function CustomAutopilotRules() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [showBuilder, setShowBuilder] = useState(false);
  const [editingRule, setEditingRule] = useState<(typeof mockRules)[0] | null>(null);
  const [rules, setRules] = useState(mockRules);
  const [isSaving, setIsSaving] = useState(false);

  const filteredRules = rules.filter((rule) => {
    if (searchQuery && !rule.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (statusFilter !== 'all' && rule.status !== statusFilter) {
      return false;
    }
    return true;
  });

  const handleSaveRule = async (rule: any) => {
    setIsSaving(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));

    if (editingRule) {
      setRules((prev) =>
        prev.map((r) => (r.id === editingRule.id ? { ...rule, id: editingRule.id } : r))
      );
    } else {
      setRules((prev) => [
        ...prev,
        { ...rule, id: crypto.randomUUID(), triggerCount: 0, lastTriggered: null },
      ]);
    }

    setIsSaving(false);
    setShowBuilder(false);
    setEditingRule(null);
  };

  const handleToggleRule = (ruleId: string) => {
    setRules((prev) =>
      prev.map((r) =>
        r.id === ruleId ? { ...r, status: r.status === 'active' ? 'paused' : 'active' } : r
      )
    );
  };

  const handleDeleteRule = (ruleId: string) => {
    if (confirm('Are you sure you want to delete this rule?')) {
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
    }
  };

  const handleDuplicateRule = (rule: (typeof mockRules)[0]) => {
    setRules((prev) => [
      ...prev,
      {
        ...rule,
        id: crypto.randomUUID(),
        name: `${rule.name} (Copy)`,
        status: 'draft',
        triggerCount: 0,
        lastTriggered: null,
        createdAt: new Date().toISOString().split('T')[0],
      },
    ]);
  };

  const getStatusBadge = (status: string) => {
    const config = {
      active: { color: 'bg-green-500/10 text-green-500', icon: CheckCircle2, label: 'Active' },
      paused: { color: 'bg-amber-500/10 text-amber-500', icon: Pause, label: 'Paused' },
      draft: { color: 'bg-gray-500/10 text-gray-500', icon: Edit, label: 'Draft' },
    };
    const { color, icon: Icon, label } = config[status as keyof typeof config] || config.draft;
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

  if (showBuilder || editingRule) {
    return (
      <div className="p-6">
        <CustomAutopilotRulesBuilder
          rule={editingRule || undefined}
          onSave={handleSaveRule}
          onCancel={() => {
            setShowBuilder(false);
            setEditingRule(null);
          }}
          isLoading={isSaving}
        />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Zap className="w-7 h-7 text-primary" />
              Custom Autopilot Rules
            </h1>
            <span className="px-2 py-0.5 rounded-full bg-gradient-to-r from-purple-500/20 to-primary/20 text-primary text-xs font-medium">
              Enterprise
            </span>
          </div>
          <p className="text-muted-foreground">
            Create advanced automation rules with multi-condition logic and trust-gated execution
          </p>
        </div>

        <button
          onClick={() => setShowBuilder(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Create Rule</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <p className="text-sm text-muted-foreground mb-1">Total Rules</p>
          <p className="text-2xl font-bold">{rules.length}</p>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <p className="text-sm text-muted-foreground mb-1">Active</p>
          <p className="text-2xl font-bold text-green-500">
            {rules.filter((r) => r.status === 'active').length}
          </p>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <p className="text-sm text-muted-foreground mb-1">Paused</p>
          <p className="text-2xl font-bold text-amber-500">
            {rules.filter((r) => r.status === 'paused').length}
          </p>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <p className="text-sm text-muted-foreground mb-1">Executions (7d)</p>
          <p className="text-2xl font-bold text-primary">
            {rules.reduce((acc, r) => acc + r.triggerCount, 0)}
          </p>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <p className="text-sm text-muted-foreground mb-1">Trust-Gated</p>
          <p className="text-2xl font-bold">{rules.filter((r) => r.trustGate.enabled).length}</p>
        </div>
      </div>

      {/* Info Banner */}
      <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
        <div className="flex items-start gap-3">
          <Shield className="w-5 h-5 text-primary mt-0.5" />
          <div>
            <h4 className="font-medium">Trust-Gated Automation</h4>
            <p className="text-sm text-muted-foreground mt-1">
              Custom rules respect Stratum's Trust Gate. Actions are only executed when signal
              health meets your configured threshold, protecting against automation during data
              quality issues.
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search rules..."
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
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="draft">Draft</option>
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
                    {rule.trustGate.enabled && (
                      <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-500 text-xs font-medium inline-flex items-center gap-1">
                        <Shield className="w-3 h-3" />
                        Trust-Gated
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{rule.description}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {rule.status === 'active' ? (
                  <button
                    onClick={() => handleToggleRule(rule.id)}
                    className="p-2 rounded-lg hover:bg-muted transition-colors"
                    title="Pause"
                  >
                    <Pause className="w-4 h-4" />
                  </button>
                ) : (
                  <button
                    onClick={() => handleToggleRule(rule.id)}
                    className="p-2 rounded-lg hover:bg-muted transition-colors"
                    title="Activate"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => setEditingRule(rule)}
                  className="p-2 rounded-lg hover:bg-muted transition-colors"
                  title="Edit"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDuplicateRule(rule)}
                  className="p-2 rounded-lg hover:bg-muted transition-colors"
                  title="Duplicate"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDeleteRule(rule.id)}
                  className="p-2 rounded-lg hover:bg-destructive/10 hover:text-destructive transition-colors"
                  title="Delete"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Conditions Summary */}
            <div className="mb-4 p-3 rounded-lg bg-muted/50">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="font-medium text-primary">IF</span>
                {rule.conditionGroups.map((group, gIdx) => (
                  <span key={group.id} className="flex items-center gap-2">
                    {gIdx > 0 && (
                      <span className="text-primary font-medium">{rule.conditionLogic}</span>
                    )}
                    <span className="text-muted-foreground">(</span>
                    {group.conditions.map((cond, cIdx) => (
                      <span key={cond.id} className="flex items-center gap-1">
                        {cIdx > 0 && <span className="text-xs text-primary">{group.logic}</span>}
                        <code className="px-1.5 py-0.5 rounded bg-background text-xs">
                          {cond.field}
                        </code>
                        <span className="font-mono text-xs">
                          {cond.operator === 'gt'
                            ? '>'
                            : cond.operator === 'lt'
                              ? '<'
                              : cond.operator}
                        </span>
                        <code className="px-1.5 py-0.5 rounded bg-background text-xs">
                          {cond.valueType === 'currency'
                            ? `$${cond.value}`
                            : cond.valueType === 'percentage'
                              ? `${cond.value}%`
                              : cond.value}
                        </code>
                      </span>
                    ))}
                    <span className="text-muted-foreground">)</span>
                  </span>
                ))}
                <span className="font-medium text-primary">THEN</span>
                {rule.actions.map((action) => (
                  <code
                    key={action.id}
                    className="px-1.5 py-0.5 rounded bg-primary/10 text-primary text-xs"
                  >
                    {action.type.replace('_', ' ')}
                    {action.config.amount &&
                      ` ${action.config.direction === 'decrease' ? '-' : '+'}${action.config.amount}%`}
                  </code>
                ))}
              </div>
            </div>

            {/* Metadata */}
            <div className="flex flex-wrap items-center gap-6 text-sm">
              {rule.targeting.platforms.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Platforms:</span>
                  <span className="font-medium">{rule.targeting.platforms.join(', ')}</span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">Cooldown:</span>
                <span className="font-medium">{rule.cooldownHours}h</span>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-muted-foreground" />
                <span className="text-muted-foreground">Triggered:</span>
                <span className="font-medium">{rule.triggerCount} times</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Last:</span>
                <span className="font-medium">{formatLastTriggered(rule.lastTriggered)}</span>
              </div>
              {rule.trustGate.enabled && (
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-blue-500" />
                  <span className="text-muted-foreground">Min Health:</span>
                  <span className="font-medium">{rule.trustGate.minSignalHealth}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {filteredRules.length === 0 && (
        <div className="text-center py-12">
          <Zap className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No rules found</p>
          <button
            onClick={() => setShowBuilder(true)}
            className="mt-4 text-primary hover:underline"
          >
            Create your first custom rule
          </button>
        </div>
      )}
    </div>
  );
}
