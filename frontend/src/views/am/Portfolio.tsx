/**
 * Account Manager Portfolio View
 *
 * Primary goal: Reduce firefighting, explain performance, drive renewals
 * Shows all assigned tenants with EMQ status, incidents, and health indicators
 */

import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  ConfidenceBandBadge,
  AutopilotModeBanner,
  BudgetAtRiskChip,
  type AutopilotMode,
} from '@/components/shared'
import { useTenants } from '@/api/hooks'
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ExclamationTriangleIcon,
  ChevronRightIcon,
  DocumentArrowDownIcon,
  BellAlertIcon,
  FireIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline'

type EmqStatus = 'ok' | 'risk' | 'degraded' | 'critical'
type SortField = 'name' | 'emq' | 'budgetAtRisk' | 'renewalDate'

interface TenantPortfolioItem {
  id: string
  name: string
  industry: string
  emqScore: number
  emqStatus: EmqStatus
  emqTrend: number
  autopilotMode: AutopilotMode
  budgetAtRisk: number
  activeIncidents: number
  incidentOpenTime: number | null // hours
  monthlySpend: number
  roas: number
  roasTrend: number
  renewalDate: Date | null
  plan: string
  lastContact: Date | null
  notes: string | null
}

export default function Portfolio() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<EmqStatus | 'all'>('all')
  const [sortField, setSortField] = useState<SortField>('emq')
  const [showAtRiskOnly, setShowAtRiskOnly] = useState(false)

  const { data: tenantsData } = useTenants()

  // Sample portfolio data
  const tenants: TenantPortfolioItem[] = tenantsData?.items?.map((t: any) => ({
    id: t.id,
    name: t.name,
    industry: t.industry || 'E-commerce',
    emqScore: Math.floor(Math.random() * 40) + 60,
    emqStatus: (['ok', 'risk', 'degraded', 'critical'] as EmqStatus[])[Math.floor(Math.random() * 4)],
    emqTrend: Math.floor(Math.random() * 20) - 10,
    autopilotMode: (['normal', 'limited', 'cuts_only', 'frozen'] as AutopilotMode[])[Math.floor(Math.random() * 4)],
    budgetAtRisk: Math.floor(Math.random() * 15000),
    activeIncidents: Math.floor(Math.random() * 5),
    incidentOpenTime: Math.random() > 0.5 ? Math.floor(Math.random() * 48) : null,
    monthlySpend: Math.floor(Math.random() * 100000) + 10000,
    roas: Math.random() * 4 + 1,
    roasTrend: Math.random() * 2 - 1,
    renewalDate: new Date(Date.now() + Math.random() * 180 * 24 * 60 * 60 * 1000),
    plan: ['Starter', 'Pro', 'Enterprise'][Math.floor(Math.random() * 3)],
    lastContact: new Date(Date.now() - Math.random() * 14 * 24 * 60 * 60 * 1000),
    notes: null,
  })) ?? [
    {
      id: '1',
      name: 'Acme Corporation',
      industry: 'E-commerce',
      emqScore: 92,
      emqStatus: 'ok' as EmqStatus,
      emqTrend: 5,
      autopilotMode: 'normal' as AutopilotMode,
      budgetAtRisk: 0,
      activeIncidents: 0,
      incidentOpenTime: null,
      monthlySpend: 85000,
      roas: 4.2,
      roasTrend: 0.3,
      renewalDate: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000),
      plan: 'Enterprise',
      lastContact: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
      notes: 'Happy with performance, considering expansion',
    },
    {
      id: '2',
      name: 'TechStart Inc',
      industry: 'SaaS',
      emqScore: 78,
      emqStatus: 'risk' as EmqStatus,
      emqTrend: -3,
      autopilotMode: 'limited' as AutopilotMode,
      budgetAtRisk: 4500,
      activeIncidents: 1,
      incidentOpenTime: 6,
      monthlySpend: 45000,
      roas: 3.1,
      roasTrend: -0.4,
      renewalDate: new Date(Date.now() + 45 * 24 * 60 * 60 * 1000),
      plan: 'Pro',
      lastContact: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      notes: 'Needs check-in, ROAS declining',
    },
    {
      id: '3',
      name: 'Fashion Forward',
      industry: 'Retail',
      emqScore: 65,
      emqStatus: 'degraded' as EmqStatus,
      emqTrend: -8,
      autopilotMode: 'cuts_only' as AutopilotMode,
      budgetAtRisk: 12000,
      activeIncidents: 2,
      incidentOpenTime: 18,
      monthlySpend: 120000,
      roas: 2.8,
      roasTrend: -0.6,
      renewalDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
      plan: 'Pro',
      lastContact: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      notes: 'Escalated - signal issues affecting campaigns',
    },
    {
      id: '4',
      name: 'HealthPlus',
      industry: 'Healthcare',
      emqScore: 45,
      emqStatus: 'critical' as EmqStatus,
      emqTrend: -15,
      autopilotMode: 'frozen' as AutopilotMode,
      budgetAtRisk: 25000,
      activeIncidents: 4,
      incidentOpenTime: 36,
      monthlySpend: 65000,
      roas: 1.8,
      roasTrend: -1.2,
      renewalDate: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000),
      plan: 'Pro',
      lastContact: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
      notes: 'CRITICAL - Churn risk, scheduled call tomorrow',
    },
    {
      id: '5',
      name: 'GreenGrow',
      industry: 'Agriculture',
      emqScore: 88,
      emqStatus: 'ok' as EmqStatus,
      emqTrend: 2,
      autopilotMode: 'normal' as AutopilotMode,
      budgetAtRisk: 0,
      activeIncidents: 0,
      incidentOpenTime: null,
      monthlySpend: 32000,
      roas: 5.1,
      roasTrend: 0.8,
      renewalDate: new Date(Date.now() + 120 * 24 * 60 * 60 * 1000),
      plan: 'Starter',
      lastContact: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000),
      notes: 'Strong performer, upgrade candidate',
    },
  ]

  // Filter and sort
  const filteredTenants = useMemo(() => {
    let result = [...tenants]

    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.industry.toLowerCase().includes(query)
      )
    }

    if (statusFilter !== 'all') {
      result = result.filter((t) => t.emqStatus === statusFilter)
    }

    if (showAtRiskOnly) {
      result = result.filter((t) => t.emqStatus !== 'ok' || t.budgetAtRisk > 0 || t.activeIncidents > 0)
    }

    result.sort((a, b) => {
      switch (sortField) {
        case 'name':
          return a.name.localeCompare(b.name)
        case 'emq':
          return a.emqScore - b.emqScore
        case 'budgetAtRisk':
          return b.budgetAtRisk - a.budgetAtRisk
        case 'renewalDate':
          return (a.renewalDate?.getTime() ?? 0) - (b.renewalDate?.getTime() ?? 0)
        default:
          return 0
      }
    })

    return result
  }, [tenants, searchQuery, statusFilter, sortField, showAtRiskOnly])

  const getStatusColor = (status: EmqStatus) => {
    switch (status) {
      case 'ok': return 'text-success bg-success/10'
      case 'risk': return 'text-warning bg-warning/10'
      case 'degraded': return 'text-orange-400 bg-orange-400/10'
      case 'critical': return 'text-danger bg-danger/10'
    }
  }

  const formatDaysUntil = (date: Date | null) => {
    if (!date) return '-'
    const days = Math.floor((date.getTime() - Date.now()) / (24 * 60 * 60 * 1000))
    if (days < 0) return 'Overdue'
    if (days === 0) return 'Today'
    if (days === 1) return '1 day'
    return `${days} days`
  }

  const formatLastContact = (date: Date | null) => {
    if (!date) return 'Never'
    const days = Math.floor((Date.now() - date.getTime()) / (24 * 60 * 60 * 1000))
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    return `${days}d ago`
  }

  // Portfolio stats
  const stats = {
    total: tenants.length,
    healthy: tenants.filter((t) => t.emqStatus === 'ok').length,
    atRisk: tenants.filter((t) => t.emqStatus !== 'ok').length,
    critical: tenants.filter((t) => t.emqStatus === 'critical').length,
    totalBudgetAtRisk: tenants.reduce((sum, t) => sum + t.budgetAtRisk, 0),
    totalMRR: tenants.reduce((sum, t) => sum + (t.plan === 'Enterprise' ? 1999 : t.plan === 'Pro' ? 499 : 99), 0),
    upcomingRenewals: tenants.filter((t) => t.renewalDate && (t.renewalDate.getTime() - Date.now()) < 30 * 24 * 60 * 60 * 1000).length,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">My Portfolio</h1>
          <p className="text-text-muted">Manage your assigned tenants</p>
        </div>
        <div className="flex items-center gap-3">
          <button data-tour="export-pdf" className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors">
            <DocumentArrowDownIcon className="w-4 h-4" />
            Export Summary
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Total Tenants</div>
          <div className="text-2xl font-bold text-white">{stats.total}</div>
        </div>
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Healthy</div>
          <div className="text-2xl font-bold text-success">{stats.healthy}</div>
        </div>
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">At Risk</div>
          <div className="text-2xl font-bold text-warning">{stats.atRisk}</div>
        </div>
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Critical</div>
          <div className="text-2xl font-bold text-danger">{stats.critical}</div>
        </div>
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Budget at Risk</div>
          <div className="text-2xl font-bold text-danger">${stats.totalBudgetAtRisk.toLocaleString()}</div>
        </div>
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Portfolio MRR</div>
          <div className="text-2xl font-bold text-white">${stats.totalMRR.toLocaleString()}</div>
        </div>
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Renewals (30d)</div>
          <div className="text-2xl font-bold text-warning">{stats.upcomingRenewals}</div>
        </div>
      </div>

      {/* Priority Alerts */}
      {stats.critical > 0 && (
        <div data-tour="priority-alerts" className="rounded-xl bg-danger/5 border border-danger/20 p-4">
          <div className="flex items-center gap-3 mb-3">
            <FireIcon className="w-5 h-5 text-danger" />
            <span className="font-semibold text-danger">Priority Alerts</span>
          </div>
          <div className="space-y-2">
            {tenants
              .filter((t) => t.emqStatus === 'critical')
              .map((t) => (
                <div
                  key={t.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-danger/10"
                >
                  <div>
                    <span className="font-medium text-white">{t.name}</span>
                    <span className="text-sm text-text-muted ml-2">
                      EMQ {t.emqScore} | {t.activeIncidents} incidents open {t.incidentOpenTime}h
                    </span>
                  </div>
                  <Link
                    to={`/dashboard/am/tenant/${t.id}`}
                    className="px-3 py-1 rounded-lg bg-danger/20 text-danger hover:bg-danger/30 text-sm transition-colors"
                  >
                    View Now
                  </Link>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            placeholder="Search tenants..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-stratum-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <FunnelIcon className="w-4 h-4 text-text-muted" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as EmqStatus | 'all')}
            className="px-3 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500"
          >
            <option value="all">All Status</option>
            <option value="ok">Healthy</option>
            <option value="risk">At Risk</option>
            <option value="degraded">Degraded</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        <select
          value={sortField}
          onChange={(e) => setSortField(e.target.value as SortField)}
          className="px-3 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500"
        >
          <option value="emq">Sort by EMQ</option>
          <option value="name">Sort by Name</option>
          <option value="budgetAtRisk">Sort by Budget at Risk</option>
          <option value="renewalDate">Sort by Renewal</option>
        </select>

        <button
          onClick={() => setShowAtRiskOnly(!showAtRiskOnly)}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
            showAtRiskOnly
              ? 'bg-warning/10 text-warning border border-warning/30'
              : 'bg-surface-secondary border border-white/10 text-text-muted hover:text-white'
          )}
        >
          <BellAlertIcon className="w-4 h-4" />
          At Risk Only
        </button>
      </div>

      {/* Tenant Cards */}
      <div data-tour="portfolio-list" className="grid gap-4">
        {filteredTenants.map((tenant) => (
          <div
            key={tenant.id}
            className={cn(
              'p-4 rounded-xl border transition-all hover:border-white/20',
              tenant.emqStatus === 'critical'
                ? 'bg-danger/5 border-danger/20'
                : 'bg-surface-secondary border-white/10'
            )}
          >
            <div className="flex items-start gap-4">
              {/* EMQ Score */}
              <div className="flex flex-col items-center p-3 rounded-xl bg-surface-tertiary min-w-[80px]">
                <span
                  className={cn(
                    'text-3xl font-bold',
                    tenant.emqScore >= 80 ? 'text-success' :
                    tenant.emqScore >= 60 ? 'text-warning' : 'text-danger'
                  )}
                >
                  {tenant.emqScore}
                </span>
                <ConfidenceBandBadge score={tenant.emqScore} size="sm" />
                <div className={cn(
                  'flex items-center gap-1 text-xs mt-1',
                  tenant.emqTrend >= 0 ? 'text-success' : 'text-danger'
                )}>
                  {tenant.emqTrend >= 0 ? (
                    <ArrowTrendingUpIcon className="w-3 h-3" />
                  ) : (
                    <ArrowTrendingDownIcon className="w-3 h-3" />
                  )}
                  {tenant.emqTrend >= 0 ? '+' : ''}{tenant.emqTrend}
                </div>
              </div>

              {/* Main Info */}
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="font-semibold text-white text-lg">{tenant.name}</h3>
                  <span className={cn(
                    'px-2 py-0.5 rounded-full text-xs',
                    getStatusColor(tenant.emqStatus)
                  )}>
                    {tenant.emqStatus}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-surface-tertiary text-text-muted text-xs">
                    {tenant.plan}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-sm">
                  <span className="text-text-muted">{tenant.industry}</span>
                  <AutopilotModeBanner mode={tenant.autopilotMode} compact />
                  {tenant.budgetAtRisk > 0 && (
                    <BudgetAtRiskChip amount={tenant.budgetAtRisk} />
                  )}
                  {tenant.activeIncidents > 0 && (
                    <span className="flex items-center gap-1 text-warning">
                      <ExclamationTriangleIcon className="w-4 h-4" />
                      {tenant.activeIncidents} incident{tenant.activeIncidents > 1 ? 's' : ''}
                      {tenant.incidentOpenTime && (
                        <span className="text-text-muted">({tenant.incidentOpenTime}h)</span>
                      )}
                    </span>
                  )}
                </div>

                {tenant.notes && (
                  <p className="mt-2 text-sm text-text-muted italic">{tenant.notes}</p>
                )}
              </div>

              {/* Metrics */}
              <div className="flex items-center gap-6 text-sm">
                <div className="text-right">
                  <div className="text-text-muted">ROAS</div>
                  <div className="flex items-center gap-1">
                    <span className="text-white font-medium">{tenant.roas.toFixed(1)}x</span>
                    <span className={cn(
                      'text-xs',
                      tenant.roasTrend >= 0 ? 'text-success' : 'text-danger'
                    )}>
                      {tenant.roasTrend >= 0 ? '+' : ''}{tenant.roasTrend.toFixed(1)}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-text-muted">Spend</div>
                  <div className="text-white font-medium">${(tenant.monthlySpend / 1000).toFixed(0)}k</div>
                </div>
                <div className="text-right">
                  <div className="text-text-muted">Renewal</div>
                  <div className={cn(
                    'font-medium',
                    tenant.renewalDate && (tenant.renewalDate.getTime() - Date.now()) < 30 * 24 * 60 * 60 * 1000
                      ? 'text-warning'
                      : 'text-white'
                  )}>
                    {formatDaysUntil(tenant.renewalDate)}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-text-muted">Last Contact</div>
                  <div className="text-white">{formatLastContact(tenant.lastContact)}</div>
                </div>
              </div>

              {/* Action */}
              <Link
                to={`/dashboard/am/tenant/${tenant.id}`}
                className="flex items-center gap-1 px-4 py-2 rounded-lg bg-surface-tertiary text-text-secondary hover:text-white transition-colors"
              >
                View
                <ChevronRightIcon className="w-4 h-4" />
              </Link>
            </div>
          </div>
        ))}

        {filteredTenants.length === 0 && (
          <div className="text-center py-12 text-text-muted">
            No tenants found matching your filters.
          </div>
        )}
      </div>
    </div>
  )
}
