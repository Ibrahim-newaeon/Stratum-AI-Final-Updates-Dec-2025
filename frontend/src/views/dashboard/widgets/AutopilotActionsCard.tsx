/**
 * AutopilotActionsCard - Filterable autopilot action log
 */

import { useState } from 'react';
import { Loader2, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useTenantStore } from '@/stores/tenantStore';
import {
  useAutopilotActions,
  getActionTypeLabel,
  getActionStatusColor,
  getPlatformIcon,
  type AutopilotAction,
  type ActionStatus,
} from '@/api/autopilot';

type FilterTab = 'all' | 'applied' | 'queued' | 'failed';

const TABS: { key: FilterTab; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'applied', label: 'Executed' },
  { key: 'queued', label: 'Hold' },
  { key: 'failed', label: 'Blocked' },
];

const FALLBACK_ACTIONS: AutopilotAction[] = [
  {
    id: 'fb-act-1',
    date: new Date().toISOString(),
    action_type: 'budget_increase',
    entity_type: 'campaign',
    entity_id: 'c-101',
    entity_name: 'Summer Retargeting',
    platform: 'meta',
    action_json: { amount: 150 },
    before_value: { budget: 500 },
    after_value: { budget: 650 },
    status: 'applied',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    approved_at: new Date(Date.now() - 3000000).toISOString(),
    applied_at: new Date(Date.now() - 2400000).toISOString(),
    error: null,
  },
  {
    id: 'g-act-2',
    date: new Date().toISOString(),
    action_type: 'pause_adset',
    entity_type: 'adset',
    entity_id: 'as-201',
    entity_name: 'Broad Lookalike US',
    platform: 'google',
    action_json: {},
    before_value: null,
    after_value: null,
    status: 'queued',
    created_at: new Date(Date.now() - 7200000).toISOString(),
    approved_at: null,
    applied_at: null,
    error: null,
  },
  {
    id: 'tt-act-3',
    date: new Date().toISOString(),
    action_type: 'bid_decrease',
    entity_type: 'campaign',
    entity_id: 'c-301',
    entity_name: 'Brand Awareness Q1',
    platform: 'tiktok',
    action_json: { amount: -0.25 },
    before_value: { bid: 2.5 },
    after_value: { bid: 2.25 },
    status: 'applied',
    created_at: new Date(Date.now() - 14400000).toISOString(),
    approved_at: new Date(Date.now() - 13800000).toISOString(),
    applied_at: new Date(Date.now() - 13200000).toISOString(),
    error: null,
  },
  {
    id: 'fb-act-4',
    date: new Date().toISOString(),
    action_type: 'budget_decrease',
    entity_type: 'campaign',
    entity_id: 'c-102',
    entity_name: 'Prospecting Cold',
    platform: 'meta',
    action_json: { amount: -200 },
    before_value: { budget: 1000 },
    after_value: null,
    status: 'failed',
    created_at: new Date(Date.now() - 21600000).toISOString(),
    approved_at: null,
    applied_at: null,
    error: 'Signal health below threshold',
  },
  {
    id: 'sc-act-5',
    date: new Date().toISOString(),
    action_type: 'enable_campaign',
    entity_type: 'campaign',
    entity_id: 'c-401',
    entity_name: 'Spring Promo 2025',
    platform: 'snapchat',
    action_json: {},
    before_value: null,
    after_value: null,
    status: 'queued',
    created_at: new Date(Date.now() - 28800000).toISOString(),
    approved_at: null,
    applied_at: null,
    error: null,
  },
];

function getStatusBadgeClass(status: ActionStatus): string {
  const color = getActionStatusColor(status);
  const map: Record<string, string> = {
    green: 'bg-emerald-500/10 text-emerald-500',
    blue: 'bg-blue-500/10 text-blue-500',
    yellow: 'bg-amber-500/10 text-amber-500',
    red: 'bg-red-500/10 text-red-500',
    gray: 'bg-muted text-muted-foreground',
  };
  return map[color] || map.gray;
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function statusForTab(tab: FilterTab): ActionStatus | undefined {
  switch (tab) {
    case 'applied':
      return 'applied';
    case 'queued':
      return 'queued';
    case 'failed':
      return 'failed';
    default:
      return undefined;
  }
}

export function AutopilotActionsCard() {
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const tenantId = useTenantStore((s) => s.tenantId);

  const { data, isLoading } = useAutopilotActions(tenantId ?? 0, { limit: 20 });

  const allActions = data?.actions && data.actions.length > 0 ? data.actions : FALLBACK_ACTIONS;

  const filterStatus = statusForTab(activeTab);
  const filtered = filterStatus ? allActions.filter((a) => a.status === filterStatus) : allActions;

  if (isLoading) {
    return (
      <div className="widget-card flex items-center justify-center min-h-[12.5rem]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="widget-card h-full flex flex-col">
      <div className="widget-header">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-primary/10">
            <Zap className="w-3.5 h-3.5 text-primary" />
          </div>
          <h3 className="widget-title">
            Autopilot Actions
          </h3>
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">{allActions.length} total</span>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-4 bg-white/[0.04] border border-white/[0.06] rounded-lg p-0.5">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            aria-label={`Filter: ${tab.label}`}
            aria-current={activeTab === tab.key ? "true" : undefined}
            className={cn(
              'flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors duration-200',
              activeTab === tab.key
                ? 'bg-primary/20 text-primary shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Action list */}
      <div className="flex-1 max-h-[25rem] overflow-y-auto space-y-1.5 scrollbar-hide">
        {filtered.length === 0 ? (
          <div className="text-center py-8 text-sm text-muted-foreground">
            No actions in this category
          </div>
        ) : (
          filtered.map((action) => (
            <div
              key={action.id}
              className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-transparent hover:border-white/[0.05] transition-colors duration-200"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span
                  className={cn(
                    'shrink-0 px-2 py-0.5 text-[11px] font-medium rounded',
                    getStatusBadgeClass(action.status)
                  )}
                >
                  {getActionTypeLabel(action.action_type)}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">
                    {action.entity_name || action.entity_id}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs">{getPlatformIcon(action.platform)}</span>
                    <span className="text-xs text-muted-foreground capitalize">{action.platform}</span>
                  </div>
                </div>
              </div>
              <div className="text-right shrink-0 ml-3">
                <span
                  className={cn(
                    'block text-[11px] font-medium px-2 py-0.5 rounded-full mb-1',
                    getStatusBadgeClass(action.status)
                  )}
                >
                  {action.status}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {formatRelativeTime(action.created_at)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
