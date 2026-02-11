/**
 * Tenant Narrative (Account Manager Client Story View)
 *
 * Detailed view of a specific tenant for client communication
 * Shows "what changed", timeline, blocked actions, and fix playbook
 */

import { useCallback, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';
import {
  type AutopilotMode,
  EmqFixPlaybookPanel,
  EmqScoreCard,
  EmqTimeline,
  type Kpi,
  KpiStrip,
  type PlaybookItem,
  type TimelineEvent,
  TrustStatusHeader,
} from '@/components/shared';
import {
  useAutopilotState,
  useEmqIncidents,
  useEmqPlaybook,
  useEmqScore,
  useTenant,
} from '@/api/hooks';
import {
  ArrowLeftIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  CalendarIcon,
  ClockIcon,
  DocumentArrowDownIcon,
  EnvelopeIcon,
  PhoneIcon,
  ShieldCheckIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

interface BlockedAction {
  id: string;
  type: 'opportunity' | 'risk' | 'fix';
  title: string;
  reason: string;
  estimatedImpact: string;
  blockedAt: Date;
}

interface RecoveryMetric {
  label: string;
  value: number;
  unit: string;
  trend: number;
  isPositive: boolean;
}

export default function TenantNarrative() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const tid = parseInt(tenantId || '1', 10);
  const { toast } = useToast();
  const [selectedPlaybookItem, setSelectedPlaybookItem] = useState<PlaybookItem | null>(null);

  const [activeTab, setActiveTab] = useState<'summary' | 'timeline' | 'blocked' | 'playbook'>(
    'summary'
  );

  // Date range
  const dateRange = {
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  };

  // Fetch data
  const { data: tenantData } = useTenant(Number(tenantId) || 0);
  const { data: emqData } = useEmqScore(tid);
  const { data: autopilotData } = useAutopilotState(tid);
  const { data: playbookData } = useEmqPlaybook(tid);
  const { data: incidentsData } = useEmqIncidents(tid, dateRange.start, dateRange.end);

  const emqScore = emqData?.score ?? 65;
  const autopilotMode: AutopilotMode = autopilotData?.mode ?? 'cuts_only';
  const budgetAtRisk = autopilotData?.budgetAtRisk ?? 12000;

  // Sample tenant details
  const tenant = {
    id: tenantId,
    name: tenantData?.name ?? 'Fashion Forward',
    industry: (tenantData as { industry?: string } | undefined)?.industry ?? 'Retail',
    plan: 'Pro',
    primaryContact: {
      name: 'Jennifer Smith',
      email: 'jennifer@fashionforward.com',
      phone: '+1 (555) 123-4567',
    },
    lastContact: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    renewalDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
  };

  const kpis: Kpi[] = [
    {
      id: 'spend',
      label: 'Monthly Spend',
      value: 120000,
      format: 'currency',
      previousValue: 115000,
      confidence: emqScore,
    },
    {
      id: 'revenue',
      label: 'Revenue',
      value: 336000,
      format: 'currency',
      previousValue: 380000,
      confidence: emqScore,
    },
    {
      id: 'roas',
      label: 'ROAS',
      value: 2.8,
      format: 'multiplier',
      previousValue: 3.3,
      confidence: emqScore,
    },
    {
      id: 'cpa',
      label: 'CPA',
      value: 42,
      format: 'currency',
      previousValue: 35,
      trendIsPositive: false,
      confidence: emqScore,
    },
  ];

  const recoveryMetrics: RecoveryMetric[] = [
    { label: 'EMQ Recovery', value: 8, unit: 'pts', trend: 12, isPositive: true },
    { label: 'ROAS Impact', value: -15, unit: '%', trend: -15, isPositive: false },
    { label: 'MTTR', value: 18, unit: 'hrs', trend: -25, isPositive: true },
    { label: 'Blocked Actions', value: 5, unit: '', trend: 0, isPositive: false },
  ];

  const blockedActions: BlockedAction[] = [
    {
      id: '1',
      type: 'opportunity',
      title: 'Scale Summer Sale campaign by 25%',
      reason: 'EMQ below threshold - data quality uncertain',
      estimatedImpact: '+$18,000 revenue',
      blockedAt: new Date(Date.now() - 18 * 60 * 60 * 1000),
    },
    {
      id: '2',
      type: 'opportunity',
      title: 'Activate new lookalike audience',
      reason: 'Autopilot in cuts_only mode',
      estimatedImpact: '+45% reach',
      blockedAt: new Date(Date.now() - 12 * 60 * 60 * 1000),
    },
    {
      id: '3',
      type: 'opportunity',
      title: 'Launch TikTok retargeting campaign',
      reason: 'Platform signal degraded',
      estimatedImpact: '+$8,500 revenue',
      blockedAt: new Date(Date.now() - 6 * 60 * 60 * 1000),
    },
  ];

  const playbook: PlaybookItem[] = playbookData ?? [
    {
      id: '1',
      title: 'Fix TikTok conversion tracking',
      description: 'TikTok reporting 22% lower conversions than GA4. Primary driver of EMQ drop.',
      priority: 'critical',
      owner: 'Data Team',
      estimatedImpact: 12,
      estimatedTime: '2 hours',
      platform: 'TikTok',
      status: 'in_progress',
      actionUrl: null,
    },
    {
      id: '2',
      title: 'Resolve Meta pixel data loss',
      description: '8% event loss detected on purchase events.',
      priority: 'high',
      owner: null,
      estimatedImpact: 6,
      estimatedTime: '1 hour',
      platform: 'Meta',
      status: 'pending',
      actionUrl: null,
    },
    {
      id: '3',
      title: 'Validate Snapchat API connection',
      description: 'Intermittent 504 errors causing freshness issues.',
      priority: 'medium',
      owner: 'Engineering',
      estimatedImpact: 4,
      estimatedTime: '30 min',
      platform: 'Snapchat',
      status: 'pending',
      actionUrl: null,
    },
  ];

  const timeline: TimelineEvent[] = incidentsData?.map((i) => ({
    id: i.id,
    type: i.type,
    title: i.title,
    description: i.description ?? undefined,
    timestamp: new Date(i.timestamp),
    platform: i.platform ?? undefined,
    severity: i.severity,
    recoveryHours: i.recoveryHours ?? undefined,
    emqImpact: i.emqImpact ?? undefined,
  })) ?? [
    {
      id: '1',
      type: 'incident_opened',
      title: 'TikTok conversion tracking degraded',
      description: '22% variance from GA4 detected',
      timestamp: new Date(Date.now() - 18 * 60 * 60 * 1000),
      platform: 'TikTok',
      severity: 'high',
      emqImpact: 12,
    },
    {
      id: '2',
      type: 'mode_change',
      title: 'Autopilot mode → cuts_only',
      description: 'Automatic protection triggered',
      timestamp: new Date(Date.now() - 16 * 60 * 60 * 1000),
      severity: 'medium',
    },
    {
      id: '3',
      type: 'incident_opened',
      title: 'Meta pixel data loss detected',
      description: '8% purchase events missing',
      timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000),
      platform: 'Meta',
      severity: 'medium',
      emqImpact: 6,
    },
    {
      id: '4',
      type: 'action_blocked',
      title: '3 scaling actions blocked',
      description: 'Protected $12,000 budget at risk',
      timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000),
      severity: 'low',
    },
  ];

  const tabs = [
    { id: 'summary' as const, label: 'Client Summary' },
    { id: 'timeline' as const, label: 'What Changed' },
    { id: 'blocked' as const, label: 'What We Blocked' },
    { id: 'playbook' as const, label: 'Fix Playbook' },
  ];

  const handleExportPDF = useCallback(() => {
    const lines: string[] = [];
    lines.push('CLIENT NARRATIVE REPORT');
    lines.push(`Generated: ${new Date().toLocaleDateString()}`);
    lines.push('');
    lines.push(`Client: ${tenant.name}`);
    lines.push(`Industry: ${tenant.industry}`);
    lines.push(`Plan: ${tenant.plan}`);
    lines.push(`Primary Contact: ${tenant.primaryContact.name} (${tenant.primaryContact.email})`);
    lines.push('');

    lines.push('--- TRUST STATUS ---');
    lines.push(`EMQ Score: ${emqScore}/100`);
    lines.push(`Autopilot Mode: ${autopilotMode}`);
    lines.push(`Budget at Risk: $${budgetAtRisk.toLocaleString()}`);
    lines.push('');

    lines.push('--- KEY PERFORMANCE INDICATORS ---');
    kpis.forEach((kpi) => {
      const val = typeof kpi.value === 'number' ? kpi.value : parseFloat(kpi.value) || 0;
      const prev = kpi.previousValue ?? 0;
      const change = prev ? (((val - prev) / prev) * 100).toFixed(1) : 'N/A';
      const prefix = kpi.format === 'currency' ? '$' : '';
      const suffix = kpi.format === 'multiplier' ? 'x' : '';
      lines.push(`${kpi.label}: ${prefix}${val.toLocaleString()}${suffix} (${change}% vs prior)`);
    });
    lines.push('');

    lines.push('--- RECOVERY METRICS ---');
    recoveryMetrics.forEach((m) => {
      lines.push(`${m.label}: ${m.value >= 0 ? '+' : ''}${m.value}${m.unit}`);
    });
    lines.push('');

    lines.push('--- BLOCKED ACTIONS ---');
    blockedActions.forEach((a) => {
      lines.push(`[${a.type.toUpperCase()}] ${a.title}`);
      lines.push(`  Reason: ${a.reason}`);
      lines.push(`  Estimated Impact: ${a.estimatedImpact}`);
    });
    lines.push('');

    lines.push('--- FIX PLAYBOOK ---');
    playbook.forEach((item) => {
      lines.push(`[${item.priority.toUpperCase()}] ${item.title} - ${item.status}`);
      lines.push(`  ${item.description}`);
      lines.push(`  Owner: ${item.owner || 'Unassigned'} | Est. Impact: +${item.estimatedImpact} EMQ pts | Time: ${item.estimatedTime}`);
    });

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `narrative-${tenant.name.replace(/\s+/g, '-').toLowerCase()}-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [tenant, emqScore, autopilotMode, budgetAtRisk, kpis, recoveryMetrics, blockedActions, playbook]);

  const handleScheduleCall = useCallback(() => {
    const subject = encodeURIComponent(`Stratum AI - ${tenant.name} Account Review`);
    const body = encodeURIComponent(
      `Hi ${tenant.primaryContact.name},\n\nI'd like to schedule a call to review your account performance.\n\nKey topics:\n- EMQ Score: ${emqScore}/100\n- ${blockedActions.length} blocked actions to discuss\n- Recovery playbook status\n\nPlease let me know your availability.\n\nBest regards`
    );
    window.open(`mailto:${tenant.primaryContact.email}?subject=${subject}&body=${body}`, '_blank');
  }, [tenant, emqScore, blockedActions.length]);

  return (
    <div data-tour="tenant-narrative" className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard/am/portfolio"
            className="p-2 rounded-lg bg-surface-secondary border border-white/10 text-text-muted hover:text-white transition-colors"
          >
            <ArrowLeftIcon className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white">{tenant.name}</h1>
              <span className="px-2 py-1 rounded-full text-xs bg-stratum-500/10 text-stratum-400">
                {tenant.plan}
              </span>
            </div>
            <p className="text-text-muted">{tenant.industry}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleScheduleCall}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors"
          >
            <CalendarIcon className="w-4 h-4" />
            Schedule Call
          </button>
          <button
            data-tour="export-pdf"
            onClick={handleExportPDF}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-stratum text-white font-medium hover:shadow-glow transition-all"
          >
            <DocumentArrowDownIcon className="w-4 h-4" />
            Export PDF
          </button>
        </div>
      </div>

      {/* Contact Info */}
      <div className="flex items-center gap-6 p-4 rounded-xl bg-surface-secondary border border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-stratum-500/20 flex items-center justify-center">
            <span className="text-stratum-400 font-semibold">
              {tenant.primaryContact.name
                .split(' ')
                .map((n) => n[0])
                .join('')}
            </span>
          </div>
          <div>
            <div className="text-white font-medium">{tenant.primaryContact.name}</div>
            <div className="text-sm text-text-muted">Primary Contact</div>
          </div>
        </div>
        <div className="flex items-center gap-2 text-text-muted">
          <EnvelopeIcon className="w-4 h-4" />
          <span>{tenant.primaryContact.email}</span>
        </div>
        <div className="flex items-center gap-2 text-text-muted">
          <PhoneIcon className="w-4 h-4" />
          <span>{tenant.primaryContact.phone}</span>
        </div>
        <div className="ml-auto flex items-center gap-4 text-sm">
          <div>
            <span className="text-text-muted">Last Contact:</span>
            <span className="text-white ml-2">
              {Math.floor((Date.now() - tenant.lastContact.getTime()) / (24 * 60 * 60 * 1000))} days
              ago
            </span>
          </div>
          <div>
            <span className="text-text-muted">Renewal:</span>
            <span className="text-warning ml-2">
              {Math.floor((tenant.renewalDate.getTime() - Date.now()) / (24 * 60 * 60 * 1000))} days
            </span>
          </div>
        </div>
      </div>

      {/* Trust Status */}
      <TrustStatusHeader
        emqScore={emqScore}
        autopilotMode={autopilotMode}
        budgetAtRisk={budgetAtRisk}
        svi={35}
        onViewDetails={() => setActiveTab('timeline')}
      />

      {/* Recovery Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {recoveryMetrics.map((metric) => (
          <div
            key={metric.label}
            className="p-4 rounded-xl bg-surface-secondary border border-white/10"
          >
            <div className="text-text-muted text-sm mb-1">{metric.label}</div>
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'text-2xl font-bold',
                  metric.isPositive ? 'text-success' : 'text-danger'
                )}
              >
                {metric.value >= 0 ? (metric.value > 0 ? '+' : '') : ''}
                {metric.value}
                {metric.unit}
              </span>
              {metric.trend !== 0 && (
                <span
                  className={cn(
                    'flex items-center text-xs',
                    metric.isPositive ? 'text-success' : 'text-danger'
                  )}
                >
                  {metric.isPositive ? (
                    <ArrowTrendingUpIcon className="w-3 h-3" />
                  ) : (
                    <ArrowTrendingDownIcon className="w-3 h-3" />
                  )}
                  {Math.abs(metric.trend)}%
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* KPI Strip */}
      <KpiStrip kpis={kpis} emqScore={emqScore} />

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-white/10 pb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'px-4 py-2 rounded-lg transition-colors',
              activeTab === tab.id
                ? 'bg-stratum-500/10 text-stratum-400'
                : 'text-text-muted hover:text-white hover:bg-white/5'
            )}
          >
            {tab.label}
            {tab.id === 'blocked' && blockedActions.length > 0 && (
              <span className="ml-2 px-2 py-0.5 rounded-full bg-warning/20 text-warning text-xs">
                {blockedActions.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'summary' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <EmqScoreCard
              score={emqScore}
              previousScore={emqData?.previousScore ?? 78}
              showDrivers
            />
          </div>
          <div>
            <EmqTimeline events={timeline} maxEvents={6} />
          </div>
        </div>
      )}

      {activeTab === 'timeline' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">What Changed (Last 30 Days)</h2>
          </div>
          <EmqTimeline events={timeline} maxEvents={20} />
        </div>
      )}

      {activeTab === 'blocked' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white">What We Blocked</h2>
              <p className="text-sm text-text-muted">
                Actions blocked to protect performance during signal degradation
              </p>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-success/10 border border-success/20">
              <ShieldCheckIcon className="w-5 h-5 text-success" />
              <span className="text-success font-medium">${budgetAtRisk.toLocaleString()}</span>
              <span className="text-success/80">protected</span>
            </div>
          </div>

          <div className="space-y-3">
            {blockedActions.map((action) => (
              <div
                key={action.id}
                className="p-4 rounded-xl bg-surface-secondary border border-white/10"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-warning/10">
                      <XCircleIcon className="w-5 h-5 text-warning" />
                    </div>
                    <div>
                      <h3 className="font-medium text-white">{action.title}</h3>
                      <p className="text-sm text-text-muted mt-1">{action.reason}</p>
                      <div className="flex items-center gap-4 mt-2 text-sm">
                        <span className="text-success">{action.estimatedImpact} missed</span>
                        <span className="flex items-center gap-1 text-text-muted">
                          <ClockIcon className="w-3 h-3" />
                          Blocked{' '}
                          {Math.floor((Date.now() - action.blockedAt.getTime()) / (60 * 60 * 1000))}
                          h ago
                        </span>
                      </div>
                    </div>
                  </div>
                  <span
                    className={cn(
                      'px-2 py-1 rounded text-xs',
                      action.type === 'opportunity' && 'bg-success/10 text-success',
                      action.type === 'risk' && 'bg-warning/10 text-warning',
                      action.type === 'fix' && 'bg-stratum-500/10 text-stratum-400'
                    )}
                  >
                    {action.type}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 rounded-xl bg-surface-tertiary border border-white/5 text-center">
            <p className="text-text-muted">
              These actions will automatically resume once EMQ recovers above 75 and autopilot
              returns to normal mode.
            </p>
          </div>
        </div>
      )}

      {activeTab === 'playbook' && (
        <div data-tour="fix-playbook" className="space-y-4">
          <EmqFixPlaybookPanel
            items={playbook}
            onItemClick={(item) => setSelectedPlaybookItem(item)}
            onAssign={(item) => {
              toast({
                title: 'Assignment requested',
                description: `"${item.title}" has been flagged for assignment. The ${item.owner || 'team'} will be notified.`,
              });
            }}
            maxItems={10}
          />

          {/* Playbook Item Detail Panel */}
          {selectedPlaybookItem && (
            <div className="p-5 rounded-xl bg-surface-secondary border border-white/10">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold text-white">{selectedPlaybookItem.title}</h3>
                <button
                  onClick={() => setSelectedPlaybookItem(null)}
                  className="text-text-muted hover:text-white transition-colors text-sm"
                >
                  Close
                </button>
              </div>
              <p className="text-text-secondary mb-4">{selectedPlaybookItem.description}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-text-muted">Priority</span>
                  <p className={cn(
                    'font-medium capitalize',
                    selectedPlaybookItem.priority === 'critical' && 'text-danger',
                    selectedPlaybookItem.priority === 'high' && 'text-warning',
                    selectedPlaybookItem.priority === 'medium' && 'text-stratum-400',
                  )}>
                    {selectedPlaybookItem.priority}
                  </p>
                </div>
                <div>
                  <span className="text-text-muted">Owner</span>
                  <p className="text-white font-medium">{selectedPlaybookItem.owner || 'Unassigned'}</p>
                </div>
                <div>
                  <span className="text-text-muted">Est. Impact</span>
                  <p className="text-success font-medium">+{selectedPlaybookItem.estimatedImpact} EMQ pts</p>
                </div>
                <div>
                  <span className="text-text-muted">Est. Time</span>
                  <p className="text-white font-medium">{selectedPlaybookItem.estimatedTime}</p>
                </div>
              </div>
              {selectedPlaybookItem.platform && (
                <div className="mt-3 text-sm">
                  <span className="text-text-muted">Platform: </span>
                  <span className="text-white">{selectedPlaybookItem.platform}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
