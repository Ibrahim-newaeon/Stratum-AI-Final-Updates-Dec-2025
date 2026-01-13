/**
 * Super Admin Control Tower
 *
 * Primary goal: Platform profitability + tenant health + systemic risk
 * Shows portfolio KPIs, system risk, and action queue safety
 */

import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  ConfidenceBandBadge,
} from '@/components/shared'
import {
  useEmqBenchmarks,
  useEmqPortfolio,
  useSuperAdminOverview,
  useSuperAdminTenants,
  useRevenue,
  useChurnRisks,
} from '@/api/hooks'
import {
  BuildingOffice2Icon,
  CurrencyDollarIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline'

interface TenantHealthCard {
  id: number
  name: string
  emqScore: number
  status: 'ok' | 'risk' | 'degraded' | 'critical'
  budgetAtRisk: number
  activeIncidents: number
  autopilotMode: string
}

export default function ControlTower() {
  const navigate = useNavigate()

  // Fetch data from multiple endpoints
  const { data: portfolioData } = useEmqPortfolio()
  const { data: benchmarksData } = useEmqBenchmarks()
  const { data: overviewData } = useSuperAdminOverview()
  const { data: tenantsData } = useSuperAdminTenants()
  const { data: revenueData } = useRevenue()
  const { data: churnRisksData } = useChurnRisks({ minRisk: 0.3, limit: 10 })

  // KPIs - use API data with fallbacks
  const portfolioKpis = {
    mrr: revenueData?.mrr ?? overviewData?.totalRevenue ?? 125000,
    arr: revenueData?.arr ?? (overviewData?.totalRevenue ?? 125000) * 12,
    churnRisk: churnRisksData?.length ?? overviewData?.atRiskTenants ?? 3,
    margin: 68,
    totalBudgetAtRisk: portfolioData?.atRiskBudget ?? overviewData?.totalBudgetAtRisk ?? 45000,
  }

  // Tenant health data
  const tenantHealth: TenantHealthCard[] = tenantsData?.items?.map((t) => ({
    id: t.id,
    name: t.name,
    emqScore: t.emqScore ?? 85,
    status: (t.emqScore ?? 85) >= 90 ? 'ok' : (t.emqScore ?? 85) >= 60 ? 'risk' : (t.emqScore ?? 85) >= 40 ? 'degraded' : 'critical',
    budgetAtRisk: t.budgetAtRisk ?? 0,
    activeIncidents: t.activeIncidents ?? 0,
    autopilotMode: 'normal',
  })) ?? [
    { id: 1, name: 'Acme Corp', emqScore: 94, status: 'ok', budgetAtRisk: 0, activeIncidents: 0, autopilotMode: 'normal' },
    { id: 2, name: 'TechStart Inc', emqScore: 72, status: 'risk', budgetAtRisk: 8500, activeIncidents: 1, autopilotMode: 'limited' },
    { id: 3, name: 'GlobalBrand', emqScore: 88, status: 'ok', budgetAtRisk: 2000, activeIncidents: 0, autopilotMode: 'normal' },
    { id: 4, name: 'FastGrowth Co', emqScore: 45, status: 'critical', budgetAtRisk: 25000, activeIncidents: 3, autopilotMode: 'frozen' },
    { id: 5, name: 'RetailMax', emqScore: 91, status: 'ok', budgetAtRisk: 0, activeIncidents: 0, autopilotMode: 'normal' },
  ]

  // EMQ benchmarks
  const benchmarks = benchmarksData ?? [
    { platform: 'Meta', p25: 65, p50: 78, p75: 89, tenantScore: 82, percentile: 68 },
    { platform: 'Google', p25: 72, p50: 85, p75: 94, tenantScore: 88, percentile: 72 },
    { platform: 'TikTok', p25: 55, p50: 70, p75: 82, tenantScore: 75, percentile: 65 },
  ]

  // Top issues
  const topIssues = portfolioData?.topIssues ?? [
    { driver: 'Freshness', affectedTenants: 3 },
    { driver: 'Data Loss', affectedTenants: 2 },
    { driver: 'Variance', affectedTenants: 4 },
  ]

  // Count by status
  const statusCounts = tenantHealth.reduce((acc, t) => {
    acc[t.status] = (acc[t.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ok': return 'text-success bg-success/10 border-success/20'
      case 'risk': return 'text-warning bg-warning/10 border-warning/20'
      case 'degraded': return 'text-orange-400 bg-orange-500/10 border-orange-500/20'
      case 'critical': return 'text-danger bg-danger/10 border-danger/20'
      default: return 'text-text-muted bg-surface-tertiary border-white/10'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Control Tower</h1>
          <p className="text-text-muted">Platform overview & tenant health</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/dashboard/superadmin')}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-secondary border border-white/10 text-text-secondary hover:text-white transition-colors"
          >
            <Cog6ToothIcon className="w-4 h-4" />
            System Settings
          </button>
        </div>
      </div>

      {/* Portfolio KPIs */}
      <div data-tour="portfolio-kpis" className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted mb-2">
            <CurrencyDollarIcon className="w-4 h-4" />
            <span className="text-sm">MRR</span>
          </div>
          <div className="text-2xl font-bold text-white">
            ${(portfolioKpis.mrr / 1000).toFixed(0)}K
          </div>
          <div className="flex items-center gap-1 text-success text-sm mt-1">
            <ArrowTrendingUpIcon className="w-4 h-4" />
            +12% vs last month
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted mb-2">
            <BuildingOffice2Icon className="w-4 h-4" />
            <span className="text-sm">Active Tenants</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {portfolioData?.totalTenants ?? tenantHealth.length}
          </div>
          <div className="flex items-center gap-1 text-success text-sm mt-1">
            <ArrowTrendingUpIcon className="w-4 h-4" />
            +3 this month
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted mb-2">
            <ExclamationTriangleIcon className="w-4 h-4" />
            <span className="text-sm">Churn Risk</span>
          </div>
          <div className="text-2xl font-bold text-warning">
            {portfolioKpis.churnRisk}
          </div>
          <div className="text-sm text-text-muted mt-1">
            tenants at risk
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-2 text-text-muted mb-2">
            <ChartBarIcon className="w-4 h-4" />
            <span className="text-sm">Margin</span>
          </div>
          <div className="text-2xl font-bold text-success">
            {portfolioKpis.margin}%
          </div>
          <div className="flex items-center gap-1 text-success text-sm mt-1">
            <ArrowTrendingUpIcon className="w-4 h-4" />
            +2% vs target
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-danger/20">
          <div className="flex items-center gap-2 text-text-muted mb-2">
            <ExclamationTriangleIcon className="w-4 h-4 text-danger" />
            <span className="text-sm">Budget at Risk</span>
          </div>
          <div className="text-2xl font-bold text-danger">
            ${(portfolioKpis.totalBudgetAtRisk / 1000).toFixed(0)}K
          </div>
          <div className="text-sm text-text-muted mt-1">
            across all tenants
          </div>
        </div>
      </div>

      {/* Tenant Health by Status */}
      <div className="grid grid-cols-4 gap-4">
        {(['ok', 'risk', 'degraded', 'critical'] as const).map((status) => (
          <div
            key={status}
            className={cn(
              'p-4 rounded-xl border',
              getStatusColor(status)
            )}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm capitalize">{status}</span>
              <span className="text-2xl font-bold">{statusCounts[status] || 0}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left - Tenant List */}
        <div className="lg:col-span-2" data-tour="tenant-health">
          <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-white/10">
              <h3 className="font-semibold text-white">Tenant Health</h3>
              <button
                onClick={() => navigate('/dashboard/tenants')}
                className="text-sm text-stratum-400 hover:text-stratum-300 flex items-center gap-1"
              >
                View all
                <ChevronRightIcon className="w-4 h-4" />
              </button>
            </div>
            <div className="divide-y divide-white/5">
              {tenantHealth.map((tenant) => (
                <div
                  key={tenant.id}
                  className="p-4 hover:bg-white/5 cursor-pointer transition-colors"
                  onClick={() => navigate(`/app/${tenant.id}/overview`)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-lg bg-surface-tertiary flex items-center justify-center">
                        <span className="text-white font-medium">
                          {tenant.name.charAt(0)}
                        </span>
                      </div>
                      <div>
                        <h4 className="font-medium text-white">{tenant.name}</h4>
                        <div className="flex items-center gap-2 mt-0.5">
                          <ConfidenceBandBadge score={tenant.emqScore} size="sm" />
                          <span className={cn(
                            'text-xs px-2 py-0.5 rounded capitalize',
                            getStatusColor(tenant.status)
                          )}>
                            {tenant.status}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-white">{tenant.emqScore}</div>
                      <div className="text-xs text-text-muted">EMQ</div>
                    </div>
                  </div>
                  {(tenant.budgetAtRisk > 0 || tenant.activeIncidents > 0) && (
                    <div className="flex items-center gap-4 mt-3 pt-3 border-t border-white/5">
                      {tenant.budgetAtRisk > 0 && (
                        <span className="text-sm text-danger">
                          ${tenant.budgetAtRisk.toLocaleString()} at risk
                        </span>
                      )}
                      {tenant.activeIncidents > 0 && (
                        <span className="text-sm text-warning">
                          {tenant.activeIncidents} active incident{tenant.activeIncidents > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right - System Health */}
        <div className="space-y-6">
          {/* EMQ Benchmarks */}
          <div data-tour="emq-benchmarks" className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
            <div className="p-4 border-b border-white/10">
              <h3 className="font-semibold text-white">EMQ Benchmarks</h3>
              <p className="text-sm text-text-muted">P25 / P50 / P75 by platform</p>
            </div>
            <div className="p-4 space-y-4">
              {benchmarks.map((b) => (
                <div key={b.platform}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white">{b.platform}</span>
                    <span className="text-sm text-text-muted">
                      {b.p25} / {b.p50} / {b.p75}
                    </span>
                  </div>
                  <div className="relative h-2 bg-white/10 rounded-full">
                    {/* P25 marker */}
                    <div
                      className="absolute top-0 h-2 bg-danger/50 rounded-l-full"
                      style={{ width: `${b.p25}%` }}
                    />
                    {/* P50 marker */}
                    <div
                      className="absolute top-0 h-2 bg-warning/50"
                      style={{ left: `${b.p25}%`, width: `${b.p50 - b.p25}%` }}
                    />
                    {/* P75 marker */}
                    <div
                      className="absolute top-0 h-2 bg-success/50 rounded-r-full"
                      style={{ left: `${b.p50}%`, width: `${b.p75 - b.p50}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Issues */}
          <div data-tour="top-issues" className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
            <div className="p-4 border-b border-white/10">
              <h3 className="font-semibold text-white">Top Issues</h3>
              <p className="text-sm text-text-muted">Affecting most tenants</p>
            </div>
            <div className="p-4 space-y-3">
              {topIssues.map((issue, i) => (
                <div key={i} className="flex items-center justify-between">
                  <span className="text-sm text-white">{issue.driver}</span>
                  <span className="text-sm text-danger">
                    {issue.affectedTenants} tenants
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Autopilot Distribution */}
          <div data-tour="autopilot-distribution" className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
            <div className="p-4 border-b border-white/10">
              <h3 className="font-semibold text-white">Autopilot Modes</h3>
            </div>
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="flex-1 h-3 rounded-full overflow-hidden flex">
                  <div className="bg-success h-full" style={{ width: '60%' }} />
                  <div className="bg-warning h-full" style={{ width: '20%' }} />
                  <div className="bg-orange-500 h-full" style={{ width: '10%' }} />
                  <div className="bg-danger h-full" style={{ width: '10%' }} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-success" />
                  <span className="text-text-muted">Normal (60%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-warning" />
                  <span className="text-text-muted">Limited (20%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-orange-500" />
                  <span className="text-text-muted">Cuts Only (10%)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-danger" />
                  <span className="text-text-muted">Frozen (10%)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
