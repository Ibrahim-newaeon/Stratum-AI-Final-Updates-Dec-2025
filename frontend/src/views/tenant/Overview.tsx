/**
 * Tenant Overview (Head of Marketing View)
 *
 * Primary goal: Trust, control, decisions, reporting
 * Shows EMQ + Confidence + Autopilot Mode + Budget at Risk
 */

import { useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  type Action,
  ActionsPanel,
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
  useUpdatePlaybookItem,
} from '@/api/hooks';
import { useTenantOverview, useTenantRecommendations } from '@/api/hooks';
import { useApproveAction, useDismissAction, useQueueAction } from '@/api/autopilot';
import { useToast } from '@/components/ui/use-toast';
import {
  CalendarIcon,
  DocumentArrowDownIcon,
  XMarkIcon,
  UserIcon,
} from '@heroicons/react/24/outline';

export default function TenantOverview() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const tid = parseInt(tenantId || '1', 10);

  // Assignment modal state
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assigningItem, setAssigningItem] = useState<PlaybookItem | null>(null);
  const [assignee, setAssignee] = useState('');
  const [assignNotes, setAssignNotes] = useState('');

  // Export state
  const [isExporting, setIsExporting] = useState(false);

  // Date range state
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });
  const [dateRangeLabel, setDateRangeLabel] = useState('Last 30 days');

  // Mutation hooks for autopilot actions
  const approveAction = useApproveAction(tid);
  const dismissAction = useDismissAction(tid);
  const queueAction = useQueueAction(tid);
  const updatePlaybookItem = useUpdatePlaybookItem(tid);

  // Fetch data
  const { data: emqData } = useEmqScore(tid);
  const { data: autopilotData } = useAutopilotState(tid);
  const { data: playbookData } = useEmqPlaybook(tid);
  const { data: incidentsData } = useEmqIncidents(tid, dateRange.start, dateRange.end);
  const { data: overviewData } = useTenantOverview(tid);
  const { data: recommendationsData } = useTenantRecommendations(tid);

  // Transform data for components
  const emqScore = emqData?.score ?? 85;
  const autopilotMode = autopilotData?.mode ?? 'normal';
  const budgetAtRisk = autopilotData?.budgetAtRisk ?? 0;

  const kpis: Kpi[] = [
    {
      id: 'spend',
      label: 'Spend',
      value: overviewData?.kpis?.total_spend ?? 45000,
      format: 'currency',
      previousValue: 42000,
      confidence: emqScore,
    },
    {
      id: 'revenue',
      label: 'Revenue',
      value: overviewData?.kpis?.total_revenue ?? 180000,
      format: 'currency',
      previousValue: 165000,
      confidence: emqScore,
    },
    {
      id: 'roas',
      label: 'ROAS',
      value: overviewData?.kpis.roas ?? 4.0,
      format: 'multiplier',
      previousValue: 3.9,
      confidence: emqScore,
    },
    {
      id: 'cpa',
      label: 'CPA',
      value: overviewData?.kpis.cpa ?? 25,
      format: 'currency',
      previousValue: 28,
      trendIsPositive: false,
      confidence: emqScore,
    },
  ];

  const playbook: PlaybookItem[] = playbookData ?? [
    {
      id: '1',
      title: 'Fix Meta pixel data loss',
      description: 'Meta is reporting 15% lower conversions than GA4. Verify pixel implementation.',
      priority: 'critical',
      owner: null,
      estimatedImpact: 8,
      estimatedTime: '30 min',
      platform: 'Meta',
      status: 'pending',
      actionUrl: null,
    },
    {
      id: '2',
      title: 'Resolve Google Ads API timeout',
      description: 'Intermittent connection issues causing data freshness delays.',
      priority: 'high',
      owner: 'Data Team',
      estimatedImpact: 5,
      estimatedTime: '1 hour',
      platform: 'Google',
      status: 'in_progress',
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
      title: 'Meta conversion tracking degraded',
      description: 'Conversion attribution showing 20% variance from GA4',
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
      platform: 'Meta',
      severity: 'high',
    },
    {
      id: '2',
      type: 'recovery',
      title: 'Google Ads sync restored',
      description: 'API connection stable after maintenance',
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000),
      platform: 'Google',
      severity: 'medium',
      recoveryHours: 3,
      emqImpact: 5,
    },
  ];

  // Handle both array and object response shapes
  const recommendationsList = Array.isArray(recommendationsData)
    ? recommendationsData
    : (recommendationsData as { recommendations?: unknown[] } | undefined)?.recommendations || [];
  const actions: Action[] = ((
    recommendationsList as {
      id: string;
      priority: string;
      title: string;
      description: string;
      platform?: string;
      expectedImpact: number;
      status: string;
      createdAt?: string;
    }[]
  ).map((r) => ({
    id: r.id,
    type: r.priority === 'high' ? 'opportunity' : 'recommendation',
    title: r.title,
    description: r.description,
    platform: r.platform ?? undefined,
    confidence: 85,
    estimatedImpact: {
      metric: 'ROAS',
      value: r.expectedImpact,
      unit: '%',
    },
    status: r.status === 'approved' ? 'applied' : 'pending',
    priority: r.priority === 'high' ? 1 : 2,
    createdAt: r.createdAt ? new Date(r.createdAt) : new Date(),
  })) as Action[]) ?? [
    {
      id: '1',
      type: 'opportunity',
      title: 'Increase budget on high-performing campaign',
      description: 'Campaign "Summer Sale" has 5.2x ROAS, recommend 20% budget increase.',
      platform: 'Meta',
      confidence: 92,
      estimatedImpact: { metric: 'Revenue', value: 15, unit: '%' },
      status: 'pending',
      priority: 1,
      createdAt: new Date(),
    },
    {
      id: '2',
      type: 'risk',
      title: 'Pause underperforming ad set',
      description: 'Ad set "Broad Targeting" has 0.8x ROAS over last 7 days.',
      platform: 'Meta',
      confidence: 88,
      estimatedImpact: { metric: 'Waste', value: -2500, unit: '$' },
      status: 'pending',
      priority: 2,
      createdAt: new Date(),
    },
  ];

  // Handler: View EMQ details in signal hub
  const handleViewDetails = () => {
    navigate(`/tenant/${tid}/signal-hub`);
  };

  // Handler: Playbook item click - navigate to fix page or show details
  const handlePlaybookItemClick = (item: PlaybookItem) => {
    if (item.actionUrl) {
      navigate(item.actionUrl);
    } else {
      // Navigate to signal-hub with item context
      navigate(`/tenant/${tid}/signal-hub?issue=${item.id}`);
    }
  };

  // Handler: Assign playbook item
  const handlePlaybookAssign = (item: PlaybookItem) => {
    setAssigningItem(item);
    setAssignee(item.owner || '');
    setAssignNotes('');
    setShowAssignModal(true);
  };

  // Handler: Confirm assignment
  const handleConfirmAssign = useCallback(async () => {
    if (!assigningItem || !assignee.trim()) return;
    try {
      await updatePlaybookItem.mutateAsync({
        itemId: assigningItem.id,
        updates: { owner: assignee.trim(), status: 'in_progress' },
      });
      toast({
        title: 'Assigned',
        description: `"${assigningItem.title}" assigned to ${assignee.trim()}.`,
      });
      setShowAssignModal(false);
      setAssigningItem(null);
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to assign item',
        variant: 'destructive',
      });
    }
  }, [assigningItem, assignee, updatePlaybookItem, toast]);

  // Handler: Apply playbook fix
  const handlePlaybookApply = async (item: PlaybookItem) => {
    try {
      await updatePlaybookItem.mutateAsync({
        itemId: item.id,
        updates: { status: 'completed' },
      });
      toast({
        title: 'Fix Applied',
        description: `Successfully applied: ${item.title}. Expected EMQ improvement: +${item.estimatedImpact}`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to apply fix',
        variant: 'destructive',
      });
    }
  };

  // Handler: Apply action
  const handleApplyAction = async (action: Action) => {
    try {
      await approveAction.mutateAsync(action.id);
      toast({
        title: 'Action Applied',
        description: `Successfully applied: ${action.title}`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to apply action',
        variant: 'destructive',
      });
    }
  };

  // Handler: Dismiss action
  const handleDismissAction = async (action: Action) => {
    try {
      await dismissAction.mutateAsync(action.id);
      toast({
        title: 'Action Dismissed',
        description: `Dismissed: ${action.title}`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to dismiss action',
        variant: 'destructive',
      });
    }
  };

  // Handler: Queue action
  const handleQueueAction = async (action: Action) => {
    try {
      await queueAction.mutateAsync({
        action_type: 'budget_increase', // Default type, would be determined by action
        entity_type: 'campaign',
        entity_id: action.id,
        entity_name: action.title,
        platform: action.platform || 'unknown',
        action_json: { description: action.description },
      });
      toast({
        title: 'Action Queued',
        description: `Queued for later: ${action.title}`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to queue action',
        variant: 'destructive',
      });
    }
  };

  // Handler: Date range change
  const handleDateRangeChange = () => {
    // Cycle through common date ranges
    const ranges = [
      { days: 7, label: 'Last 7 days' },
      { days: 14, label: 'Last 14 days' },
      { days: 30, label: 'Last 30 days' },
      { days: 90, label: 'Last 90 days' },
    ];
    const currentIndex = ranges.findIndex((r) => r.label === dateRangeLabel);
    const nextIndex = (currentIndex + 1) % ranges.length;
    const nextRange = ranges[nextIndex];

    const end = new Date();
    const start = new Date(Date.now() - nextRange.days * 24 * 60 * 60 * 1000);

    setDateRange({
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
    });
    setDateRangeLabel(nextRange.label);
  };

  // Handler: Export report
  const handleExportReport = useCallback(() => {
    setIsExporting(true);
    try {
      const reportData = {
        generatedAt: new Date().toISOString(),
        dateRange,
        emqScore,
        autopilotMode,
        budgetAtRisk,
        kpis: kpis.map((k) => ({ label: k.label, value: k.value, confidence: k.confidence })),
        playbook: playbook.map((p) => ({
          title: p.title,
          priority: p.priority,
          owner: p.owner || 'Unassigned',
          status: p.status,
          estimatedImpact: p.estimatedImpact,
          platform: p.platform || '-',
        })),
        actions: actions.map((a) => ({
          title: a.title,
          type: a.type,
          platform: a.platform || '-',
          confidence: a.confidence,
          status: a.status,
          impact: `${a.estimatedImpact.value}${a.estimatedImpact.unit} ${a.estimatedImpact.metric}`,
        })),
      };

      // Build CSV
      const lines: string[] = [];
      lines.push('Stratum AI - Overview Report');
      lines.push(`Generated: ${new Date().toLocaleString()}`);
      lines.push(`Date Range: ${dateRange.start} to ${dateRange.end}`);
      lines.push('');
      lines.push(`EMQ Score: ${emqScore}`);
      lines.push(`Autopilot Mode: ${autopilotMode}`);
      lines.push(`Budget at Risk: $${budgetAtRisk.toLocaleString()}`);
      lines.push('');

      // KPIs
      lines.push('--- KPIs ---');
      lines.push('Metric,Value,Confidence');
      reportData.kpis.forEach((k) => lines.push(`${k.label},${k.value},${k.confidence}%`));
      lines.push('');

      // Playbook
      lines.push('--- Fix Playbook ---');
      lines.push('Title,Priority,Owner,Status,EMQ Impact,Platform');
      reportData.playbook.forEach((p) =>
        lines.push(`"${p.title}",${p.priority},${p.owner},${p.status},+${p.estimatedImpact},${p.platform}`)
      );
      lines.push('');

      // Actions
      lines.push('--- Actions ---');
      lines.push('Title,Type,Platform,Confidence,Status,Impact');
      reportData.actions.forEach((a) =>
        lines.push(`"${a.title}",${a.type},${a.platform},${a.confidence}%,${a.status},${a.impact}`)
      );

      const csvContent = lines.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `stratum-overview-report-${dateRange.start}-to-${dateRange.end}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast({
        title: 'Report Exported',
        description: 'CSV report downloaded successfully.',
      });
    } catch (error) {
      toast({
        title: 'Export Failed',
        description: error instanceof Error ? error.message : 'Could not generate report',
        variant: 'destructive',
      });
    } finally {
      setIsExporting(false);
    }
  }, [dateRange, emqScore, autopilotMode, budgetAtRisk, kpis, playbook, actions, toast]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Overview</h1>
          <p className="text-text-muted">Trust & Performance Dashboard</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleDateRangeChange}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors"
          >
            <CalendarIcon className="w-4 h-4" />
            {dateRangeLabel}
          </button>
          <button
            onClick={handleExportReport}
            disabled={isExporting}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-stratum text-white font-medium hover:shadow-glow transition-all disabled:opacity-50"
          >
            <DocumentArrowDownIcon className="w-4 h-4" />
            {isExporting ? 'Exporting...' : 'Export Report'}
          </button>
        </div>
      </div>

      {/* Trust Status Header - Always visible */}
      <div data-tour="trust-header">
        <TrustStatusHeader
          emqScore={emqScore}
          autopilotMode={autopilotMode}
          budgetAtRisk={budgetAtRisk}
          svi={25}
          onViewDetails={handleViewDetails}
        />
      </div>

      {/* KPI Strip with confidence stamp */}
      <div data-tour="kpi-strip">
        <KpiStrip kpis={kpis} emqScore={emqScore} />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column - EMQ Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* EMQ Score Card */}
          <EmqScoreCard score={emqScore} previousScore={emqData?.previousScore ?? 82} showDrivers />

          {/* Fix Playbook */}
          <div data-tour="fix-playbook">
            <EmqFixPlaybookPanel
              items={playbook}
              onItemClick={handlePlaybookItemClick}
              onAssign={handlePlaybookAssign}
              onApply={handlePlaybookApply}
              maxItems={5}
            />
          </div>
        </div>

        {/* Right column - Actions & Timeline */}
        <div className="space-y-6">
          {/* Actions Panel */}
          <ActionsPanel
            actions={actions}
            autopilotMode={autopilotMode}
            onApply={handleApplyAction}
            onDismiss={handleDismissAction}
            onQueue={handleQueueAction}
            maxActions={5}
          />

          {/* Incident Timeline */}
          <EmqTimeline events={timeline} maxEvents={5} />
        </div>
      </div>

      {/* Assignment Modal */}
      {showAssignModal && assigningItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-neutral-900 border border-white/10 rounded-xl w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h3 className="text-lg font-semibold text-white">Assign Task</h3>
              <button
                onClick={() => setShowAssignModal(false)}
                className="p-2 text-white/40 hover:text-white"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* Item being assigned */}
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <p className="text-white font-medium text-sm">{assigningItem.title}</p>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-white/50">
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                    assigningItem.priority === 'critical' ? 'bg-red-500/20 text-red-400' :
                    assigningItem.priority === 'high' ? 'bg-orange-500/20 text-orange-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {assigningItem.priority}
                  </span>
                  {assigningItem.platform && <span>{assigningItem.platform}</span>}
                  {assigningItem.estimatedTime && <span>{assigningItem.estimatedTime}</span>}
                </div>
              </div>

              {/* Assignee */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">
                  <UserIcon className="w-4 h-4 inline mr-1" />
                  Assign to *
                </label>
                <select
                  value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-purple-500/50"
                >
                  <option value="" className="bg-neutral-900">Select team member...</option>
                  <option value="Data Team" className="bg-neutral-900">Data Team</option>
                  <option value="Engineering" className="bg-neutral-900">Engineering</option>
                  <option value="Marketing Ops" className="bg-neutral-900">Marketing Ops</option>
                  <option value="Platform Lead" className="bg-neutral-900">Platform Lead</option>
                  <option value="Analytics Team" className="bg-neutral-900">Analytics Team</option>
                </select>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1.5">Notes (optional)</label>
                <textarea
                  value={assignNotes}
                  onChange={(e) => setAssignNotes(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/30 focus:outline-none focus:border-purple-500/50 resize-none"
                  placeholder="Additional context or instructions..."
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 p-4 border-t border-white/10">
              <button
                onClick={() => setShowAssignModal(false)}
                className="px-4 py-2 text-white/60 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmAssign}
                disabled={!assignee.trim() || updatePlaybookItem.isPending}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium disabled:opacity-50 transition-colors"
              >
                {updatePlaybookItem.isPending ? 'Assigning...' : 'Assign'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
