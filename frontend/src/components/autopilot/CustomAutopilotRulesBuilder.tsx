/**
 * Custom Autopilot Rules Builder - Enterprise Feature
 *
 * Advanced rule builder allowing Enterprise users to create
 * complex automation rules with multi-condition logic,
 * trust-gated execution, and advanced actions.
 */

import { useState } from 'react';
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Copy,
  DollarSign,
  Info,
  Loader2,
  MessageCircle,
  Pause,
  Play,
  Plus,
  Save,
  Settings,
  Shield,
  Tag,
  Target,
  Trash2,
  TrendingDown,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Types
interface RuleCondition {
  id: string;
  field: string;
  operator: string;
  value: string;
  valueType: 'number' | 'percentage' | 'currency';
}

interface ConditionGroup {
  id: string;
  logic: 'AND' | 'OR';
  conditions: RuleCondition[];
}

interface RuleAction {
  id: string;
  type: string;
  config: Record<string, any>;
  priority: number;
}

interface RuleSchedule {
  enabled: boolean;
  frequency: 'hourly' | 'daily' | 'weekly' | 'custom';
  daysOfWeek?: number[];
  hoursOfDay?: number[];
  timezone: string;
}

interface TrustGateConfig {
  enabled: boolean;
  minSignalHealth: number;
  requireApproval: boolean;
  dryRunFirst: boolean;
}

interface CustomRule {
  id?: string;
  name: string;
  description: string;
  status: 'active' | 'paused' | 'draft';
  conditionGroups: ConditionGroup[];
  conditionLogic: 'AND' | 'OR';
  actions: RuleAction[];
  targeting: {
    platforms: string[];
    campaignTypes: string[];
    specificCampaigns: string[];
  };
  schedule: RuleSchedule;
  trustGate: TrustGateConfig;
  cooldownHours: number;
  maxExecutionsPerDay: number;
  createdAt?: string;
  lastModifiedAt?: string;
}

// Available fields for conditions
const CONDITION_FIELDS = [
  { value: 'roas', label: 'ROAS', category: 'Performance', valueType: 'number' as const },
  { value: 'cpa', label: 'CPA', category: 'Performance', valueType: 'currency' as const },
  { value: 'cpc', label: 'CPC', category: 'Performance', valueType: 'currency' as const },
  { value: 'cpm', label: 'CPM', category: 'Performance', valueType: 'currency' as const },
  { value: 'ctr', label: 'CTR', category: 'Performance', valueType: 'percentage' as const },
  {
    value: 'conversion_rate',
    label: 'Conversion Rate',
    category: 'Performance',
    valueType: 'percentage' as const,
  },
  { value: 'spend', label: 'Spend', category: 'Budget', valueType: 'currency' as const },
  {
    value: 'spend_pct',
    label: 'Budget Spent %',
    category: 'Budget',
    valueType: 'percentage' as const,
  },
  {
    value: 'daily_budget',
    label: 'Daily Budget',
    category: 'Budget',
    valueType: 'currency' as const,
  },
  { value: 'impressions', label: 'Impressions', category: 'Volume', valueType: 'number' as const },
  { value: 'clicks', label: 'Clicks', category: 'Volume', valueType: 'number' as const },
  { value: 'conversions', label: 'Conversions', category: 'Volume', valueType: 'number' as const },
  { value: 'frequency', label: 'Frequency', category: 'Delivery', valueType: 'number' as const },
  { value: 'reach', label: 'Reach', category: 'Delivery', valueType: 'number' as const },
  {
    value: 'fatigue_score',
    label: 'Creative Fatigue Score',
    category: 'Health',
    valueType: 'percentage' as const,
  },
  {
    value: 'signal_health',
    label: 'Signal Health Score',
    category: 'Health',
    valueType: 'number' as const,
  },
  { value: 'days_running', label: 'Days Running', category: 'Time', valueType: 'number' as const },
  {
    value: 'hours_since_change',
    label: 'Hours Since Last Change',
    category: 'Time',
    valueType: 'number' as const,
  },
];

const OPERATORS = [
  { value: 'gt', label: '>', description: 'Greater than' },
  { value: 'gte', label: '>=', description: 'Greater than or equal' },
  { value: 'lt', label: '<', description: 'Less than' },
  { value: 'lte', label: '<=', description: 'Less than or equal' },
  { value: 'eq', label: '=', description: 'Equal to' },
  { value: 'neq', label: '!=', description: 'Not equal to' },
  { value: 'between', label: 'Between', description: 'Between two values' },
  { value: 'change_gt', label: 'Changed by >', description: 'Changed by more than' },
  { value: 'change_lt', label: 'Changed by <', description: 'Changed by less than' },
];

const ACTION_TYPES = [
  { value: 'adjust_budget', label: 'Adjust Budget', icon: DollarSign, category: 'Budget' },
  { value: 'scale_budget', label: 'Scale Budget %', icon: TrendingUp, category: 'Budget' },
  { value: 'set_budget', label: 'Set Budget To', icon: Target, category: 'Budget' },
  { value: 'adjust_bid', label: 'Adjust Bid', icon: TrendingUp, category: 'Bidding' },
  { value: 'pause_campaign', label: 'Pause Campaign', icon: Pause, category: 'Status' },
  { value: 'pause_adset', label: 'Pause Ad Set', icon: Pause, category: 'Status' },
  { value: 'pause_ad', label: 'Pause Ad', icon: Pause, category: 'Status' },
  { value: 'enable_campaign', label: 'Enable Campaign', icon: Play, category: 'Status' },
  { value: 'apply_label', label: 'Apply Label', icon: Tag, category: 'Organization' },
  { value: 'send_alert', label: 'Send Alert', icon: Bell, category: 'Notification' },
  { value: 'notify_slack', label: 'Notify Slack', icon: MessageCircle, category: 'Notification' },
  {
    value: 'notify_whatsapp',
    label: 'Notify WhatsApp',
    icon: MessageCircle,
    category: 'Notification',
  },
];

const PLATFORMS = [
  { value: 'meta', label: 'Meta (Facebook/Instagram)' },
  { value: 'google', label: 'Google Ads' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'snapchat', label: 'Snapchat' },
];

const CAMPAIGN_TYPES = [
  { value: 'prospecting', label: 'Prospecting' },
  { value: 'retargeting', label: 'Retargeting' },
  { value: 'brand', label: 'Brand Awareness' },
  { value: 'conversion', label: 'Conversion' },
  { value: 'engagement', label: 'Engagement' },
];

interface Props {
  rule?: CustomRule;
  onSave: (rule: CustomRule) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export function CustomAutopilotRulesBuilder({ rule, onSave, onCancel, isLoading }: Props) {
  const [formData, setFormData] = useState<CustomRule>(
    rule || {
      name: '',
      description: '',
      status: 'draft',
      conditionGroups: [
        {
          id: crypto.randomUUID(),
          logic: 'AND',
          conditions: [
            {
              id: crypto.randomUUID(),
              field: 'roas',
              operator: 'lt',
              value: '2.0',
              valueType: 'number',
            },
          ],
        },
      ],
      conditionLogic: 'AND',
      actions: [{ id: crypto.randomUUID(), type: 'pause_campaign', config: {}, priority: 1 }],
      targeting: {
        platforms: [],
        campaignTypes: [],
        specificCampaigns: [],
      },
      schedule: {
        enabled: false,
        frequency: 'hourly',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      },
      trustGate: {
        enabled: true,
        minSignalHealth: 70,
        requireApproval: false,
        dryRunFirst: true,
      },
      cooldownHours: 24,
      maxExecutionsPerDay: 10,
    }
  );

  const [activeTab, setActiveTab] = useState<
    'conditions' | 'actions' | 'targeting' | 'schedule' | 'safety'
  >('conditions');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set([formData.conditionGroups[0]?.id])
  );

  // Condition Group Management
  const addConditionGroup = () => {
    setFormData((prev) => ({
      ...prev,
      conditionGroups: [
        ...prev.conditionGroups,
        {
          id: crypto.randomUUID(),
          logic: 'AND',
          conditions: [
            {
              id: crypto.randomUUID(),
              field: 'roas',
              operator: 'lt',
              value: '',
              valueType: 'number',
            },
          ],
        },
      ],
    }));
  };

  const removeConditionGroup = (groupId: string) => {
    if (formData.conditionGroups.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      conditionGroups: prev.conditionGroups.filter((g) => g.id !== groupId),
    }));
  };

  const addCondition = (groupId: string) => {
    setFormData((prev) => ({
      ...prev,
      conditionGroups: prev.conditionGroups.map((g) =>
        g.id === groupId
          ? {
              ...g,
              conditions: [
                ...g.conditions,
                {
                  id: crypto.randomUUID(),
                  field: 'roas',
                  operator: 'lt',
                  value: '',
                  valueType: 'number',
                },
              ],
            }
          : g
      ),
    }));
  };

  const removeCondition = (groupId: string, conditionId: string) => {
    setFormData((prev) => ({
      ...prev,
      conditionGroups: prev.conditionGroups.map((g) =>
        g.id === groupId
          ? { ...g, conditions: g.conditions.filter((c) => c.id !== conditionId) }
          : g
      ),
    }));
  };

  const updateCondition = (
    groupId: string,
    conditionId: string,
    updates: Partial<RuleCondition>
  ) => {
    setFormData((prev) => ({
      ...prev,
      conditionGroups: prev.conditionGroups.map((g) =>
        g.id === groupId
          ? {
              ...g,
              conditions: g.conditions.map((c) =>
                c.id === conditionId ? { ...c, ...updates } : c
              ),
            }
          : g
      ),
    }));
  };

  // Action Management
  const addAction = () => {
    setFormData((prev) => ({
      ...prev,
      actions: [
        ...prev.actions,
        {
          id: crypto.randomUUID(),
          type: 'send_alert',
          config: {},
          priority: prev.actions.length + 1,
        },
      ],
    }));
  };

  const removeAction = (actionId: string) => {
    if (formData.actions.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      actions: prev.actions.filter((a) => a.id !== actionId),
    }));
  };

  const updateAction = (actionId: string, updates: Partial<RuleAction>) => {
    setFormData((prev) => ({
      ...prev,
      actions: prev.actions.map((a) => (a.id === actionId ? { ...a, ...updates } : a)),
    }));
  };

  const handleSubmit = async () => {
    await onSave(formData);
  };

  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  return (
    <div className="bg-card rounded-xl border">
      {/* Header */}
      <div className="p-6 border-b">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Zap className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold">
                {rule ? 'Edit Custom Rule' : 'Create Custom Autopilot Rule'}
              </h2>
              <p className="text-sm text-muted-foreground">
                Enterprise feature for advanced automation
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-1 rounded-full bg-gradient-to-r from-purple-500/20 to-primary/20 text-primary text-xs font-medium">
              Enterprise
            </span>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-1 block">Rule Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="e.g., Scale High Performers"
              className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="Describe what this rule does and when it should trigger..."
              rows={2}
              className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        {[
          { id: 'conditions', label: 'Conditions', icon: Settings },
          { id: 'actions', label: 'Actions', icon: Zap },
          { id: 'targeting', label: 'Targeting', icon: Target },
          { id: 'schedule', label: 'Schedule', icon: Clock },
          { id: 'safety', label: 'Safety & Trust', icon: Shield },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={cn(
              'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors',
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {/* Conditions Tab */}
        {activeTab === 'conditions' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Trigger Conditions</h3>
                <p className="text-sm text-muted-foreground">
                  Define when this rule should trigger
                </p>
              </div>
              <button
                onClick={addConditionGroup}
                className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border hover:bg-muted transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Group
              </button>
            </div>

            {/* Condition Groups */}
            {formData.conditionGroups.map((group, groupIndex) => (
              <div key={group.id} className="rounded-lg border">
                {groupIndex > 0 && (
                  <div className="flex items-center justify-center -mt-3 mb-2">
                    <select
                      value={formData.conditionLogic}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          conditionLogic: e.target.value as 'AND' | 'OR',
                        }))
                      }
                      className="px-3 py-1 text-sm rounded-full bg-primary/10 text-primary font-medium border-0"
                    >
                      <option value="AND">AND</option>
                      <option value="OR">OR</option>
                    </select>
                  </div>
                )}

                {/* Group Header */}
                <div
                  className="flex items-center justify-between p-3 bg-muted/50 cursor-pointer"
                  onClick={() => toggleGroup(group.id)}
                >
                  <div className="flex items-center gap-2">
                    {expandedGroups.has(group.id) ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                    <span className="font-medium">Condition Group {groupIndex + 1}</span>
                    <span className="text-sm text-muted-foreground">
                      ({group.conditions.length} condition{group.conditions.length !== 1 ? 's' : ''}
                      )
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={group.logic}
                      onChange={(e) => {
                        e.stopPropagation();
                        setFormData((prev) => ({
                          ...prev,
                          conditionGroups: prev.conditionGroups.map((g) =>
                            g.id === group.id ? { ...g, logic: e.target.value as 'AND' | 'OR' } : g
                          ),
                        }));
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="px-2 py-1 text-xs rounded border bg-background"
                    >
                      <option value="AND">Match ALL</option>
                      <option value="OR">Match ANY</option>
                    </select>
                    {formData.conditionGroups.length > 1 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeConditionGroup(group.id);
                        }}
                        className="p-1 rounded hover:bg-destructive/10 text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>

                {/* Group Conditions */}
                {expandedGroups.has(group.id) && (
                  <div className="p-4 space-y-3">
                    {group.conditions.map((condition, condIndex) => (
                      <div key={condition.id} className="flex items-center gap-2">
                        {condIndex > 0 && (
                          <span className="text-xs font-medium text-primary px-2">
                            {group.logic}
                          </span>
                        )}
                        <select
                          value={condition.field}
                          onChange={(e) => {
                            const field = CONDITION_FIELDS.find((f) => f.value === e.target.value);
                            updateCondition(group.id, condition.id, {
                              field: e.target.value,
                              valueType: field?.valueType || 'number',
                            });
                          }}
                          className="flex-1 px-3 py-2 rounded-lg border bg-background text-sm"
                        >
                          {Object.entries(
                            CONDITION_FIELDS.reduce(
                              (acc, f) => {
                                acc[f.category] = acc[f.category] || [];
                                acc[f.category].push(f);
                                return acc;
                              },
                              {} as Record<string, typeof CONDITION_FIELDS>
                            )
                          ).map(([category, fields]) => (
                            <optgroup key={category} label={category}>
                              {fields.map((f) => (
                                <option key={f.value} value={f.value}>
                                  {f.label}
                                </option>
                              ))}
                            </optgroup>
                          ))}
                        </select>
                        <select
                          value={condition.operator}
                          onChange={(e) =>
                            updateCondition(group.id, condition.id, { operator: e.target.value })
                          }
                          className="w-28 px-3 py-2 rounded-lg border bg-background text-sm"
                        >
                          {OPERATORS.map((op) => (
                            <option key={op.value} value={op.value}>
                              {op.label}
                            </option>
                          ))}
                        </select>
                        <div className="relative">
                          {condition.valueType === 'currency' && (
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                              $
                            </span>
                          )}
                          <input
                            type="text"
                            value={condition.value}
                            onChange={(e) =>
                              updateCondition(group.id, condition.id, { value: e.target.value })
                            }
                            placeholder="Value"
                            className={cn(
                              'w-28 px-3 py-2 rounded-lg border bg-background text-sm',
                              condition.valueType === 'currency' && 'pl-7'
                            )}
                          />
                          {condition.valueType === 'percentage' && (
                            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                              %
                            </span>
                          )}
                        </div>
                        {group.conditions.length > 1 && (
                          <button
                            onClick={() => removeCondition(group.id, condition.id)}
                            className="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      onClick={() => addCondition(group.id)}
                      className="flex items-center gap-1 text-sm text-primary hover:underline"
                    >
                      <Plus className="w-4 h-4" />
                      Add Condition
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Actions Tab */}
        {activeTab === 'actions' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Actions</h3>
                <p className="text-sm text-muted-foreground">
                  What should happen when conditions are met
                </p>
              </div>
              <button
                onClick={addAction}
                className="flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg border hover:bg-muted transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Action
              </button>
            </div>

            {formData.actions.map((action, index) => {
              const actionType = ACTION_TYPES.find((a) => a.value === action.type);
              const ActionIcon = actionType?.icon || Zap;

              return (
                <div key={action.id} className="rounded-lg border p-4">
                  <div className="flex items-start gap-4">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-medium text-sm">
                      {index + 1}
                    </div>
                    <div className="flex-1 space-y-3">
                      <select
                        value={action.type}
                        onChange={(e) =>
                          updateAction(action.id, { type: e.target.value, config: {} })
                        }
                        className="w-full px-3 py-2 rounded-lg border bg-background text-sm"
                      >
                        {Object.entries(
                          ACTION_TYPES.reduce(
                            (acc, a) => {
                              acc[a.category] = acc[a.category] || [];
                              acc[a.category].push(a);
                              return acc;
                            },
                            {} as Record<string, typeof ACTION_TYPES>
                          )
                        ).map(([category, actions]) => (
                          <optgroup key={category} label={category}>
                            {actions.map((a) => (
                              <option key={a.value} value={a.value}>
                                {a.label}
                              </option>
                            ))}
                          </optgroup>
                        ))}
                      </select>

                      {/* Action Config */}
                      {(action.type === 'adjust_budget' || action.type === 'scale_budget') && (
                        <div className="flex items-center gap-2">
                          <label className="text-sm text-muted-foreground">Adjustment:</label>
                          <select
                            value={action.config.direction || 'increase'}
                            onChange={(e) =>
                              updateAction(action.id, {
                                config: { ...action.config, direction: e.target.value },
                              })
                            }
                            className="px-2 py-1 rounded border bg-background text-sm"
                          >
                            <option value="increase">Increase by</option>
                            <option value="decrease">Decrease by</option>
                          </select>
                          <input
                            type="number"
                            value={action.config.amount || ''}
                            onChange={(e) =>
                              updateAction(action.id, {
                                config: { ...action.config, amount: e.target.value },
                              })
                            }
                            placeholder="10"
                            className="w-20 px-2 py-1 rounded border bg-background text-sm"
                          />
                          <span className="text-sm text-muted-foreground">%</span>
                        </div>
                      )}

                      {action.type === 'set_budget' && (
                        <div className="flex items-center gap-2">
                          <label className="text-sm text-muted-foreground">Set to:</label>
                          <span className="text-muted-foreground">$</span>
                          <input
                            type="number"
                            value={action.config.amount || ''}
                            onChange={(e) =>
                              updateAction(action.id, {
                                config: { ...action.config, amount: e.target.value },
                              })
                            }
                            placeholder="100"
                            className="w-28 px-2 py-1 rounded border bg-background text-sm"
                          />
                        </div>
                      )}

                      {action.type === 'apply_label' && (
                        <div className="flex items-center gap-2">
                          <label className="text-sm text-muted-foreground">Label:</label>
                          <input
                            type="text"
                            value={action.config.label || ''}
                            onChange={(e) =>
                              updateAction(action.id, {
                                config: { ...action.config, label: e.target.value },
                              })
                            }
                            placeholder="e.g., high-performer"
                            className="flex-1 px-2 py-1 rounded border bg-background text-sm"
                          />
                        </div>
                      )}

                      {action.type === 'notify_slack' && (
                        <div className="flex items-center gap-2">
                          <label className="text-sm text-muted-foreground">Channel:</label>
                          <input
                            type="text"
                            value={action.config.channel || ''}
                            onChange={(e) =>
                              updateAction(action.id, {
                                config: { ...action.config, channel: e.target.value },
                              })
                            }
                            placeholder="#marketing-alerts"
                            className="flex-1 px-2 py-1 rounded border bg-background text-sm"
                          />
                        </div>
                      )}
                    </div>

                    {formData.actions.length > 1 && (
                      <button
                        onClick={() => removeAction(action.id)}
                        className="p-1.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Targeting Tab */}
        {activeTab === 'targeting' && (
          <div className="space-y-6">
            <div>
              <h3 className="font-semibold mb-2">Platforms</h3>
              <p className="text-sm text-muted-foreground mb-3">
                Select which ad platforms this rule applies to
              </p>
              <div className="flex flex-wrap gap-2">
                {PLATFORMS.map((platform) => (
                  <button
                    key={platform.value}
                    onClick={() => {
                      setFormData((prev) => ({
                        ...prev,
                        targeting: {
                          ...prev.targeting,
                          platforms: prev.targeting.platforms.includes(platform.value)
                            ? prev.targeting.platforms.filter((p) => p !== platform.value)
                            : [...prev.targeting.platforms, platform.value],
                        },
                      }));
                    }}
                    className={cn(
                      'px-3 py-2 rounded-lg border text-sm transition-colors',
                      formData.targeting.platforms.includes(platform.value)
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'hover:bg-muted'
                    )}
                  >
                    {platform.label}
                  </button>
                ))}
                {formData.targeting.platforms.length === 0 && (
                  <span className="text-sm text-muted-foreground italic">
                    All platforms (no filter)
                  </span>
                )}
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-2">Campaign Types</h3>
              <p className="text-sm text-muted-foreground mb-3">
                Filter by campaign objective/type
              </p>
              <div className="flex flex-wrap gap-2">
                {CAMPAIGN_TYPES.map((type) => (
                  <button
                    key={type.value}
                    onClick={() => {
                      setFormData((prev) => ({
                        ...prev,
                        targeting: {
                          ...prev.targeting,
                          campaignTypes: prev.targeting.campaignTypes.includes(type.value)
                            ? prev.targeting.campaignTypes.filter((t) => t !== type.value)
                            : [...prev.targeting.campaignTypes, type.value],
                        },
                      }));
                    }}
                    className={cn(
                      'px-3 py-2 rounded-lg border text-sm transition-colors',
                      formData.targeting.campaignTypes.includes(type.value)
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'hover:bg-muted'
                    )}
                  >
                    {type.label}
                  </button>
                ))}
                {formData.targeting.campaignTypes.length === 0 && (
                  <span className="text-sm text-muted-foreground italic">
                    All types (no filter)
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Schedule Tab */}
        {activeTab === 'schedule' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Enable Schedule</h3>
                <p className="text-sm text-muted-foreground">
                  Run this rule on a schedule instead of continuously
                </p>
              </div>
              <button
                onClick={() =>
                  setFormData((prev) => ({
                    ...prev,
                    schedule: { ...prev.schedule, enabled: !prev.schedule.enabled },
                  }))
                }
                className={cn(
                  'w-12 h-6 rounded-full transition-colors relative',
                  formData.schedule.enabled ? 'bg-primary' : 'bg-muted'
                )}
              >
                <div
                  className={cn(
                    'absolute w-5 h-5 rounded-full bg-white top-0.5 transition-all',
                    formData.schedule.enabled ? 'left-6' : 'left-0.5'
                  )}
                />
              </button>
            </div>

            {formData.schedule.enabled && (
              <div className="space-y-4 p-4 rounded-lg bg-muted/50">
                <div>
                  <label className="text-sm font-medium mb-1 block">Frequency</label>
                  <select
                    value={formData.schedule.frequency}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        schedule: { ...prev.schedule, frequency: e.target.value as any },
                      }))
                    }
                    className="w-full px-3 py-2 rounded-lg border bg-background text-sm"
                  >
                    <option value="hourly">Every Hour</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>

                <div>
                  <label className="text-sm font-medium mb-1 block">Timezone</label>
                  <select
                    value={formData.schedule.timezone}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        schedule: { ...prev.schedule, timezone: e.target.value },
                      }))
                    }
                    className="w-full px-3 py-2 rounded-lg border bg-background text-sm"
                  >
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">Eastern Time</option>
                    <option value="America/Los_Angeles">Pacific Time</option>
                    <option value="Europe/London">London</option>
                    <option value="Asia/Dubai">Dubai</option>
                  </select>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Cooldown Period</label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={formData.cooldownHours}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        cooldownHours: parseInt(e.target.value) || 0,
                      }))
                    }
                    className="w-20 px-3 py-2 rounded-lg border bg-background text-sm"
                  />
                  <span className="text-sm text-muted-foreground">hours</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Minimum time between rule executions
                </p>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">Max Executions/Day</label>
                <input
                  type="number"
                  value={formData.maxExecutionsPerDay}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      maxExecutionsPerDay: parseInt(e.target.value) || 1,
                    }))
                  }
                  className="w-20 px-3 py-2 rounded-lg border bg-background text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">Limit executions per 24 hours</p>
              </div>
            </div>
          </div>
        )}

        {/* Safety & Trust Tab */}
        {activeTab === 'safety' && (
          <div className="space-y-6">
            <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <div className="flex items-start gap-3">
                <Shield className="w-5 h-5 text-amber-500 mt-0.5" />
                <div>
                  <h4 className="font-medium text-amber-700 dark:text-amber-400">
                    Trust-Gated Execution
                  </h4>
                  <p className="text-sm text-amber-600 dark:text-amber-300 mt-1">
                    Actions are only executed when signal health meets the threshold. This protects
                    against automation during data quality issues.
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold">Enable Trust Gate</h3>
                <p className="text-sm text-muted-foreground">
                  Check signal health before executing actions
                </p>
              </div>
              <button
                onClick={() =>
                  setFormData((prev) => ({
                    ...prev,
                    trustGate: { ...prev.trustGate, enabled: !prev.trustGate.enabled },
                  }))
                }
                className={cn(
                  'w-12 h-6 rounded-full transition-colors relative',
                  formData.trustGate.enabled ? 'bg-primary' : 'bg-muted'
                )}
              >
                <div
                  className={cn(
                    'absolute w-5 h-5 rounded-full bg-white top-0.5 transition-all',
                    formData.trustGate.enabled ? 'left-6' : 'left-0.5'
                  )}
                />
              </button>
            </div>

            {formData.trustGate.enabled && (
              <div className="space-y-4 p-4 rounded-lg bg-muted/50">
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Minimum Signal Health Score: {formData.trustGate.minSignalHealth}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={formData.trustGate.minSignalHealth}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        trustGate: {
                          ...prev.trustGate,
                          minSignalHealth: parseInt(e.target.value),
                        },
                      }))
                    }
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>0 (No check)</span>
                    <span className="text-amber-500">40 (Hold)</span>
                    <span className="text-green-500">70 (Pass)</span>
                    <span>100</span>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium">Require Manual Approval</h4>
                    <p className="text-xs text-muted-foreground">
                      Queue actions for review before execution
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      setFormData((prev) => ({
                        ...prev,
                        trustGate: {
                          ...prev.trustGate,
                          requireApproval: !prev.trustGate.requireApproval,
                        },
                      }))
                    }
                    className={cn(
                      'w-10 h-5 rounded-full transition-colors relative',
                      formData.trustGate.requireApproval ? 'bg-primary' : 'bg-muted'
                    )}
                  >
                    <div
                      className={cn(
                        'absolute w-4 h-4 rounded-full bg-white top-0.5 transition-all',
                        formData.trustGate.requireApproval ? 'left-5' : 'left-0.5'
                      )}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium">Dry Run First</h4>
                    <p className="text-xs text-muted-foreground">
                      Simulate action before first real execution
                    </p>
                  </div>
                  <button
                    onClick={() =>
                      setFormData((prev) => ({
                        ...prev,
                        trustGate: {
                          ...prev.trustGate,
                          dryRunFirst: !prev.trustGate.dryRunFirst,
                        },
                      }))
                    }
                    className={cn(
                      'w-10 h-5 rounded-full transition-colors relative',
                      formData.trustGate.dryRunFirst ? 'bg-primary' : 'bg-muted'
                    )}
                  >
                    <div
                      className={cn(
                        'absolute w-4 h-4 rounded-full bg-white top-0.5 transition-all',
                        formData.trustGate.dryRunFirst ? 'left-5' : 'left-0.5'
                      )}
                    />
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between p-6 border-t bg-muted/30">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Info className="w-4 h-4" />
          <span>Rules are evaluated continuously unless scheduled</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => setFormData((prev) => ({ ...prev, status: 'draft' }))}
            className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            Save as Draft
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || !formData.name}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {rule ? 'Update Rule' : 'Create Rule'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CustomAutopilotRulesBuilder;
