/**
 * Tenant Overview (Head of Marketing View)
 *
 * Primary goal: Trust, control, decisions, reporting
 * Shows EMQ + Confidence + Autopilot Mode + Budget at Risk
 */

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  TrustStatusHeader,
  EmqScoreCard,
  EmqFixPlaybookPanel,
  EmqTimeline,
  KpiStrip,
  ActionsPanel,
  type PlaybookItem,
  type TimelineEvent,
  type Action,
  type Kpi,
} from '@/components/shared'
import {
  useEmqScore,
  useAutopilotState,
  useEmqPlaybook,
  useEmqIncidents,
} from '@/api/hooks'
import { useTenantOverview, useTenantRecommendations } from '@/api/hooks'
import { DocumentArrowDownIcon, CalendarIcon } from '@heroicons/react/24/outline'

export default function TenantOverview() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const tid = parseInt(tenantId || '1', 10)

  // Date range state
  const [dateRange] = useState({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  })

  // Fetch data
  const { data: emqData, isLoading: emqLoading } = useEmqScore(tid)
  const { data: autopilotData } = useAutopilotState(tid)
  const { data: playbookData } = useEmqPlaybook(tid)
  const { data: incidentsData } = useEmqIncidents(tid, dateRange.start, dateRange.end)
  const { data: overviewData } = useTenantOverview(tid.toString())
  const { data: recommendationsData } = useTenantRecommendations(tid.toString())

  // Transform data for components
  const emqScore = emqData?.score ?? 85
  const autopilotMode = autopilotData?.mode ?? 'normal'
  const budgetAtRisk = autopilotData?.budgetAtRisk ?? 0

  const kpis: Kpi[] = [
    {
      id: 'spend',
      label: 'Spend',
      value: overviewData?.kpis.totalSpend ?? 45000,
      format: 'currency',
      previousValue: 42000,
      confidence: emqScore,
    },
    {
      id: 'revenue',
      label: 'Revenue',
      value: overviewData?.kpis.totalRevenue ?? 180000,
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
  ]

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
  ]

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
  ]

  const actions: Action[] = recommendationsData?.map((r) => ({
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
    createdAt: new Date(r.createdAt),
  })) as Action[] ?? [
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
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Overview</h1>
          <p className="text-text-muted">Trust & Performance Dashboard</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors">
            <CalendarIcon className="w-4 h-4" />
            Last 30 days
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-stratum text-white font-medium hover:shadow-glow transition-all">
            <DocumentArrowDownIcon className="w-4 h-4" />
            Export Report
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
          onViewDetails={() => {}}
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
          <EmqScoreCard
            score={emqScore}
            previousScore={emqData?.previousScore ?? 82}
            showDrivers
          />

          {/* Fix Playbook */}
          <div data-tour="fix-playbook">
            <EmqFixPlaybookPanel
              items={playbook}
              onItemClick={(item) => console.log('Clicked:', item)}
              onAssign={(item) => console.log('Assign:', item)}
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
            onApply={(action) => console.log('Apply:', action)}
            onDismiss={(action) => console.log('Dismiss:', action)}
            onQueue={(action) => console.log('Queue:', action)}
            maxActions={5}
          />

          {/* Incident Timeline */}
          <EmqTimeline events={timeline} maxEvents={5} />
        </div>
      </div>
    </div>
  )
}
