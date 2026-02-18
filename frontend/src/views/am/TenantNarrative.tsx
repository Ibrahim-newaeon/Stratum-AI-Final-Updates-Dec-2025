/**
 * Tenant Narrative (Account Manager Client Story View)
 *
 * Detailed view of a specific tenant for client communication
 * Shows "what changed", timeline, blocked actions, and fix playbook
 */

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { usePriceMetrics } from '@/hooks/usePriceMetrics'
import {
  TrustStatusHeader,
  EmqScoreCard,
  EmqTimeline,
  EmqFixPlaybookPanel,
  KpiStrip,
  type TimelineEvent,
  type PlaybookItem,
  type AutopilotMode,
  type Kpi,
} from '@/components/shared'
import {
  useTenant,
  useEmqScore,
  useAutopilotState,
  useEmqPlaybook,
  useEmqIncidents,
} from '@/api/hooks'
import {
  ArrowLeftIcon,
  DocumentArrowDownIcon,
  EnvelopeIcon,
  PhoneIcon,
  CalendarIcon,
  ShieldCheckIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  XCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'

interface BlockedAction {
  id: string
  type: 'opportunity' | 'risk' | 'fix'
  title: string
  reason: string
  estimatedImpact: string
  blockedAt: Date
}

interface RecoveryMetric {
  label: string
  value: number
  unit: string
  trend: number
  isPositive: boolean
}

const COST_KPI_IDS = ['spend', 'revenue', 'roas', 'cpa']

export default function TenantNarrative() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const { showPriceMetrics } = usePriceMetrics()
  const tid = parseInt(tenantId || '1', 10)

  const [activeTab, setActiveTab] = useState<'summary' | 'timeline' | 'blocked' | 'playbook'>('summary')

  // Date range
  const dateRange = {
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  }

  // Fetch data
  const { data: tenantData } = useTenant(tid)
  const { data: emqData } = useEmqScore(tid)
  const { data: autopilotData } = useAutopilotState(tid)
  const { data: playbookData } = useEmqPlaybook(tid)
  const { data: incidentsData } = useEmqIncidents(tid, dateRange.start, dateRange.end)

  const emqScore = emqData?.score ?? 65
  const autopilotMode: AutopilotMode = autopilotData?.mode ?? 'cuts_only'
  const budgetAtRisk = autopilotData?.budgetAtRisk ?? 12000

  // Sample tenant details
  const tenant = {
    id: tenantId,
    name: tenantData?.name ?? 'Fashion Forward',
    industry: (tenantData as any)?.industry ?? 'Retail',
    plan: 'Pro',
    primaryContact: {
      name: 'Jennifer Smith',
      email: 'jennifer@fashionforward.com',
      phone: '+1 (555) 123-4567',
    },
    lastContact: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    renewalDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
  }

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
  ]

  const recoveryMetrics: RecoveryMetric[] = [
    { label: 'EMQ Recovery', value: 8, unit: 'pts', trend: 12, isPositive: true },
    { label: 'ROAS Impact', value: -15, unit: '%', trend: -15, isPositive: false },
    { label: 'MTTR', value: 18, unit: 'hrs', trend: -25, isPositive: true },
    { label: 'Blocked Actions', value: 5, unit: '', trend: 0, isPositive: false },
  ]

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
  ]

  const playbook: PlaybookItem[] = (playbookData as unknown as PlaybookItem[] | undefined) ?? ([
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
      actionUrl: undefined,
    },
    {
      id: '2',
      title: 'Resolve Meta pixel data loss',
      description: '8% event loss detected on purchase events.',
      priority: 'high',
      owner: undefined,
      estimatedImpact: 6,
      estimatedTime: '1 hour',
      platform: 'Meta',
      status: 'pending',
      actionUrl: undefined,
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
      actionUrl: undefined,
    },
  ] as PlaybookItem[])

  const timeline: TimelineEvent[] = (incidentsData?.map((i) => ({
    id: i.id,
    type: i.type,
    title: i.title,
    description: i.description ?? undefined,
    timestamp: new Date(i.timestamp),
    platform: i.platform ?? undefined,
    severity: i.severity,
    recoveryHours: i.recoveryHours ?? undefined,
    emqImpact: i.emqImpact ?? undefined,
  })) as unknown as TimelineEvent[] | undefined) ?? ([
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
      type: 'update',
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
      type: 'update',
      title: '3 scaling actions blocked',
      description: 'Protected $12,000 budget at risk',
      timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000),
      severity: 'low',
    },
  ] as TimelineEvent[])

  const tabs = [
    { id: 'summary' as const, label: 'Client Summary' },
    { id: 'timeline' as const, label: 'What Changed' },
    { id: 'blocked' as const, label: 'What We Blocked' },
    { id: 'playbook' as const, label: 'Fix Playbook' },
  ]

  const handleExportPDF = () => {
    console.log('Exporting client-safe narrative PDF...')
  }

  const handleScheduleCall = () => {
    console.log('Opening calendar...')
  }

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
              {tenant.primaryContact.name.split(' ').map(n => n[0]).join('')}
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
              {Math.floor((Date.now() - tenant.lastContact.getTime()) / (24 * 60 * 60 * 1000))} days ago
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
      <div className={cn(
        'grid grid-cols-2 gap-4',
        showPriceMetrics ? 'md:grid-cols-4' : 'md:grid-cols-3'
      )}>
        {recoveryMetrics.filter(m => showPriceMetrics || m.label !== 'ROAS Impact').map((metric) => (
          <div key={metric.label} className="p-4 rounded-xl bg-surface-secondary border border-white/10">
            <div className="text-text-muted text-sm mb-1">{metric.label}</div>
            <div className="flex items-center gap-2">
              <span className={cn(
                'text-2xl font-bold',
                metric.isPositive ? 'text-success' : 'text-danger'
              )}>
                {metric.value >= 0 ? (metric.value > 0 ? '+' : '') : ''}{metric.value}{metric.unit}
              </span>
              {metric.trend !== 0 && (
                <span className={cn(
                  'flex items-center text-xs',
                  metric.isPositive ? 'text-success' : 'text-danger'
                )}>
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
      <KpiStrip kpis={showPriceMetrics ? kpis : kpis.filter(k => !COST_KPI_IDS.includes(k.id))} emqScore={emqScore} />

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
                          Blocked {Math.floor((Date.now() - action.blockedAt.getTime()) / (60 * 60 * 1000))}h ago
                        </span>
                      </div>
                    </div>
                  </div>
                  <span className={cn(
                    'px-2 py-1 rounded text-xs',
                    action.type === 'opportunity' && 'bg-success/10 text-success',
                    action.type === 'risk' && 'bg-warning/10 text-warning',
                    action.type === 'fix' && 'bg-stratum-500/10 text-stratum-400'
                  )}>
                    {action.type}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="p-4 rounded-xl bg-surface-tertiary border border-white/5 text-center">
            <p className="text-text-muted">
              These actions will automatically resume once EMQ recovers above 75 and autopilot returns to normal mode.
            </p>
          </div>
        </div>
      )}

      {activeTab === 'playbook' && (
        <div data-tour="fix-playbook">
          <EmqFixPlaybookPanel
            items={playbook}
            onItemClick={(item) => console.log('Clicked:', item)}
            onAssign={(item) => console.log('Assign:', item)}
            maxItems={10}
          />
        </div>
      )}
    </div>
  )
}
