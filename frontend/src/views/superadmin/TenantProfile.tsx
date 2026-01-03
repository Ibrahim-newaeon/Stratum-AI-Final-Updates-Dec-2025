/**
 * Tenant Profile (Super Admin Individual Tenant View)
 *
 * Detailed health profile for a specific tenant
 * Shows EMQ history, incidents, actions, and allows admin controls
 */

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
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
  BuildingOfficeIcon,
  UserGroupIcon,
  CurrencyDollarIcon,
  CalendarIcon,
  Cog6ToothIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  ArrowPathIcon,
  ShieldCheckIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline'

type AdminAction = 'restrict' | 'support' | 'override'

export default function TenantProfile() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const tid = parseInt(tenantId || '1', 10)

  const [activeTab, setActiveTab] = useState<'overview' | 'incidents' | 'actions' | 'settings'>('overview')

  // Date range
  const dateRange = {
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  }

  // Fetch data
  const { data: tenantData } = useTenant(tenantId || '')
  const { data: emqData } = useEmqScore(tid)
  const { data: autopilotData } = useAutopilotState(tid)
  const { data: playbookData } = useEmqPlaybook(tid)
  const { data: incidentsData } = useEmqIncidents(tid, dateRange.start, dateRange.end)

  const emqScore = emqData?.score ?? 72
  const autopilotMode: AutopilotMode = autopilotData?.mode ?? 'limited'
  const budgetAtRisk = autopilotData?.budgetAtRisk ?? 8500

  // Sample tenant details
  const tenant = {
    id: tenantId,
    name: tenantData?.name ?? 'Fashion Forward',
    industry: tenantData?.industry ?? 'Retail',
    plan: tenantData?.plan ?? 'Pro',
    accountManager: 'Sarah Johnson',
    createdAt: new Date('2024-01-15'),
    platforms: ['Meta', 'TikTok', 'Snapchat'],
    users: 8,
    monthlySpend: 120000,
    mrr: 499,
    status: 'active' as const,
    features: {
      autopilot: true,
      campaignBuilder: true,
      competitorIntel: false,
      predictions: true,
    },
    restrictions: [] as string[],
  }

  const kpis: Kpi[] = [
    {
      id: 'spend',
      label: 'Monthly Spend',
      value: tenant.monthlySpend,
      format: 'currency',
      previousValue: 115000,
      confidence: emqScore,
    },
    {
      id: 'mrr',
      label: 'MRR',
      value: tenant.mrr,
      format: 'currency',
      previousValue: 499,
      confidence: 100,
    },
    {
      id: 'users',
      label: 'Active Users',
      value: tenant.users,
      format: 'number',
      previousValue: 7,
      confidence: 100,
    },
    {
      id: 'uptime',
      label: 'Data Uptime',
      value: 99.2,
      format: 'percentage',
      previousValue: 98.5,
      confidence: emqScore,
    },
  ]

  const playbook: PlaybookItem[] = playbookData ?? [
    {
      id: '1',
      title: 'Fix TikTok conversion variance',
      description: 'TikTok reporting 22% lower conversions than GA4',
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
      title: 'Resolve Snapchat API timeout',
      description: 'Intermittent 504 errors causing data freshness issues',
      priority: 'high',
      owner: null,
      estimatedImpact: 8,
      estimatedTime: '1 hour',
      platform: 'Snapchat',
      status: 'pending',
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
      title: 'TikTok conversion tracking degraded',
      description: 'Significant variance detected',
      timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000),
      platform: 'TikTok',
      severity: 'high',
    },
    {
      id: '2',
      type: 'mode_change',
      title: 'Autopilot mode changed to Limited',
      description: 'Due to signal degradation',
      timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000),
      severity: 'medium',
    },
    {
      id: '3',
      type: 'recovery',
      title: 'Meta pixel issue resolved',
      description: 'Data loss recovered',
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000),
      platform: 'Meta',
      severity: 'low',
      recoveryHours: 6,
      emqImpact: 8,
    },
  ]

  const handleAdminAction = (action: AdminAction) => {
    console.log('Admin action:', action)
  }

  const tabs = [
    { id: 'overview' as const, label: 'Overview' },
    { id: 'incidents' as const, label: 'Incidents' },
    { id: 'actions' as const, label: 'Action Log' },
    { id: 'settings' as const, label: 'Admin Controls' },
  ]

  return (
    <div className="space-y-6">
      {/* Back Link & Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/dashboard/superadmin/tenants"
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
              <span className="px-2 py-1 rounded-full text-xs bg-success/10 text-success">
                {tenant.status}
              </span>
            </div>
            <p className="text-text-muted">{tenant.industry}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleAdminAction('support')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors"
          >
            <UserGroupIcon className="w-4 h-4" />
            Contact Support
          </button>
          <button
            onClick={() => handleAdminAction('override')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-warning/10 border border-warning/20 text-warning hover:bg-warning/20 transition-colors"
          >
            <ShieldExclamationIcon className="w-4 h-4" />
            Override Mode
          </button>
        </div>
      </div>

      {/* Trust Status */}
      <TrustStatusHeader
        emqScore={emqScore}
        autopilotMode={autopilotMode}
        budgetAtRisk={budgetAtRisk}
        svi={32}
        onViewDetails={() => setActiveTab('incidents')}
      />

      {/* Tenant Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-3 mb-2">
            <BuildingOfficeIcon className="w-5 h-5 text-text-muted" />
            <span className="text-text-muted">Platforms</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {tenant.platforms.map((p) => (
              <span key={p} className="px-2 py-1 rounded bg-surface-tertiary text-white text-sm">
                {p}
              </span>
            ))}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-3 mb-2">
            <UserGroupIcon className="w-5 h-5 text-text-muted" />
            <span className="text-text-muted">Account Manager</span>
          </div>
          <span className="text-white font-medium">{tenant.accountManager}</span>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-3 mb-2">
            <CalendarIcon className="w-5 h-5 text-text-muted" />
            <span className="text-text-muted">Customer Since</span>
          </div>
          <span className="text-white font-medium">
            {tenant.createdAt.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
          </span>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-3 mb-2">
            <Cog6ToothIcon className="w-5 h-5 text-text-muted" />
            <span className="text-text-muted">Features</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(tenant.features)
              .filter(([, enabled]) => enabled)
              .map(([feature]) => (
                <span key={feature} className="px-2 py-1 rounded bg-stratum-500/10 text-stratum-400 text-xs">
                  {feature}
                </span>
              ))}
          </div>
        </div>
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
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <EmqScoreCard
              score={emqScore}
              previousScore={emqData?.previousScore ?? 78}
              showDrivers
            />
            <EmqFixPlaybookPanel
              items={playbook}
              onItemClick={(item) => console.log('Clicked:', item)}
              onAssign={(item) => console.log('Assign:', item)}
              maxItems={5}
            />
          </div>
          <div>
            <EmqTimeline events={timeline} maxEvents={8} />
          </div>
        </div>
      )}

      {activeTab === 'incidents' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Incident History</h2>
            <select className="px-3 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500">
              <option value="30">Last 30 days</option>
              <option value="60">Last 60 days</option>
              <option value="90">Last 90 days</option>
            </select>
          </div>

          <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left p-4 text-text-muted font-medium">Incident</th>
                  <th className="text-left p-4 text-text-muted font-medium">Platform</th>
                  <th className="text-left p-4 text-text-muted font-medium">Severity</th>
                  <th className="text-left p-4 text-text-muted font-medium">Duration</th>
                  <th className="text-left p-4 text-text-muted font-medium">EMQ Impact</th>
                  <th className="text-left p-4 text-text-muted font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {timeline.map((event) => (
                  <tr key={event.id} className="hover:bg-white/5 transition-colors">
                    <td className="p-4">
                      <div className="font-medium text-white">{event.title}</div>
                      <div className="text-sm text-text-muted">{event.description}</div>
                    </td>
                    <td className="p-4 text-text-muted">{event.platform || '-'}</td>
                    <td className="p-4">
                      <span
                        className={cn(
                          'px-2 py-1 rounded-full text-xs font-medium',
                          event.severity === 'critical' && 'bg-danger/10 text-danger',
                          event.severity === 'high' && 'bg-orange-500/10 text-orange-400',
                          event.severity === 'medium' && 'bg-warning/10 text-warning',
                          event.severity === 'low' && 'bg-success/10 text-success'
                        )}
                      >
                        {event.severity}
                      </span>
                    </td>
                    <td className="p-4 text-text-muted">
                      {event.recoveryHours ? `${event.recoveryHours}h` : 'Ongoing'}
                    </td>
                    <td className="p-4">
                      {event.emqImpact ? (
                        <span className="text-danger">-{event.emqImpact} pts</span>
                      ) : (
                        <span className="text-text-muted">-</span>
                      )}
                    </td>
                    <td className="p-4">
                      {event.type === 'recovery' ? (
                        <span className="flex items-center gap-1 text-success">
                          <CheckCircleIcon className="w-4 h-4" />
                          Resolved
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-warning">
                          <ClockIcon className="w-4 h-4" />
                          Open
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'actions' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Action Log</h2>
            <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors">
              <ArrowPathIcon className="w-4 h-4" />
              Refresh
            </button>
          </div>

          <div className="rounded-2xl bg-surface-secondary border border-white/10 p-6">
            <div className="text-center text-text-muted py-8">
              <ClockIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Action log will display automated and manual actions taken.</p>
              <p className="text-sm mt-2">Coming soon</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-white">Admin Controls</h2>

          {/* Feature Toggles */}
          <div className="rounded-2xl bg-surface-secondary border border-white/10 p-6">
            <h3 className="font-medium text-white mb-4">Feature Access</h3>
            <div className="space-y-4">
              {Object.entries(tenant.features).map(([feature, enabled]) => (
                <div key={feature} className="flex items-center justify-between">
                  <div>
                    <span className="text-white capitalize">{feature.replace(/([A-Z])/g, ' $1')}</span>
                    <p className="text-sm text-text-muted">
                      {feature === 'autopilot' && 'Automated budget and bid adjustments'}
                      {feature === 'campaignBuilder' && 'Create and publish campaigns'}
                      {feature === 'competitorIntel' && 'Competitor tracking and analysis'}
                      {feature === 'predictions' && 'AI-powered performance predictions'}
                    </p>
                  </div>
                  <button
                    className={cn(
                      'relative w-12 h-6 rounded-full transition-colors',
                      enabled ? 'bg-stratum-500' : 'bg-surface-tertiary'
                    )}
                  >
                    <span
                      className={cn(
                        'absolute top-1 w-4 h-4 rounded-full bg-white transition-transform',
                        enabled ? 'left-7' : 'left-1'
                      )}
                    />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Mode Override */}
          <div className="rounded-2xl bg-surface-secondary border border-white/10 p-6">
            <h3 className="font-medium text-white mb-4">Autopilot Mode Override</h3>
            <p className="text-sm text-text-muted mb-4">
              Override the automated mode selection for this tenant. Use with caution.
            </p>
            <div className="flex flex-wrap gap-3">
              {(['normal', 'limited', 'cuts_only', 'frozen'] as AutopilotMode[]).map((mode) => (
                <button
                  key={mode}
                  className={cn(
                    'px-4 py-2 rounded-lg border transition-colors',
                    autopilotMode === mode
                      ? 'bg-stratum-500/10 border-stratum-500 text-stratum-400'
                      : 'bg-surface-tertiary border-white/10 text-text-muted hover:text-white'
                  )}
                >
                  {mode.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Restrictions */}
          <div className="rounded-2xl bg-surface-secondary border border-white/10 p-6">
            <h3 className="font-medium text-white mb-4">Active Restrictions</h3>
            {tenant.restrictions.length > 0 ? (
              <div className="space-y-2">
                {tenant.restrictions.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 text-warning">
                    <ExclamationTriangleIcon className="w-4 h-4" />
                    {r}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-success">
                <ShieldCheckIcon className="w-5 h-5" />
                <span>No restrictions applied</span>
              </div>
            )}
          </div>

          {/* Danger Zone */}
          <div className="rounded-2xl bg-danger/5 border border-danger/20 p-6">
            <h3 className="font-medium text-danger mb-4">Danger Zone</h3>
            <div className="flex items-center justify-between">
              <div>
                <span className="text-white">Suspend Tenant</span>
                <p className="text-sm text-text-muted">
                  Temporarily disable all access and automation
                </p>
              </div>
              <button className="px-4 py-2 rounded-lg bg-danger/10 border border-danger/20 text-danger hover:bg-danger/20 transition-colors">
                Suspend
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
