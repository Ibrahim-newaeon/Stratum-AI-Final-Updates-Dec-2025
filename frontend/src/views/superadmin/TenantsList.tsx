/**
 * Tenants List (Super Admin Portfolio View)
 *
 * Shows all tenants with EMQ status, autopilot mode, budget-at-risk
 * Allows filtering and sorting by various metrics
 */

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  type AutopilotMode,
  AutopilotModeBanner,
  BudgetAtRiskChip,
  ConfidenceBandBadge,
} from '@/components/shared';
import { useSuperAdminTenants } from '@/api/hooks';
import {
  ArrowsUpDownIcon,
  BuildingOfficeIcon,
  CheckCircleIcon,
  ChevronRightIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

type EmqStatus = 'ok' | 'risk' | 'degraded' | 'critical';
type SortField = 'name' | 'emq' | 'budgetAtRisk' | 'activeIncidents' | 'lastActivity';
type SortDirection = 'asc' | 'desc';

interface TenantListItem {
  id: string;
  name: string;
  industry: string;
  emqScore: number;
  emqStatus: EmqStatus;
  autopilotMode: AutopilotMode;
  budgetAtRisk: number;
  activeIncidents: number;
  totalSpend: number;
  platforms: string[];
  lastActivity: Date;
  accountManager: string | null;
}

export default function TenantsList() {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<EmqStatus | 'all'>('all');
  const [modeFilter, setModeFilter] = useState<AutopilotMode | 'all'>('all');
  const [sortField, setSortField] = useState<SortField>('emq');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Fetch tenants from superadmin API
  const { data: tenantsData } = useSuperAdminTenants();

  // Default mock tenants
  const mockTenants: TenantListItem[] = [
    {
      id: '1',
      name: 'Acme Corporation',
      industry: 'E-commerce',
      emqScore: 92,
      emqStatus: 'ok' as EmqStatus,
      autopilotMode: 'normal' as AutopilotMode,
      budgetAtRisk: 0,
      activeIncidents: 0,
      totalSpend: 85000,
      platforms: ['Meta', 'Google', 'TikTok'],
      lastActivity: new Date(Date.now() - 2 * 60 * 60 * 1000),
      accountManager: 'Sarah Johnson',
    },
    {
      id: '2',
      name: 'TechStart Inc',
      industry: 'SaaS',
      emqScore: 78,
      emqStatus: 'risk' as EmqStatus,
      autopilotMode: 'limited' as AutopilotMode,
      budgetAtRisk: 4500,
      activeIncidents: 1,
      totalSpend: 45000,
      platforms: ['Meta', 'Google'],
      lastActivity: new Date(Date.now() - 30 * 60 * 1000),
      accountManager: 'Mike Chen',
    },
    {
      id: '3',
      name: 'Fashion Forward',
      industry: 'Retail',
      emqScore: 65,
      emqStatus: 'degraded' as EmqStatus,
      autopilotMode: 'cuts_only' as AutopilotMode,
      budgetAtRisk: 12000,
      activeIncidents: 2,
      totalSpend: 120000,
      platforms: ['Meta', 'TikTok', 'Snapchat'],
      lastActivity: new Date(Date.now() - 4 * 60 * 60 * 1000),
      accountManager: 'Sarah Johnson',
    },
    {
      id: '4',
      name: 'HealthPlus',
      industry: 'Healthcare',
      emqScore: 45,
      emqStatus: 'critical' as EmqStatus,
      autopilotMode: 'frozen' as AutopilotMode,
      budgetAtRisk: 25000,
      activeIncidents: 4,
      totalSpend: 65000,
      platforms: ['Google'],
      lastActivity: new Date(Date.now() - 24 * 60 * 60 * 1000),
      accountManager: null,
    },
    {
      id: '5',
      name: 'GreenGrow',
      industry: 'Agriculture',
      emqScore: 88,
      emqStatus: 'ok' as EmqStatus,
      autopilotMode: 'normal' as AutopilotMode,
      budgetAtRisk: 0,
      activeIncidents: 0,
      totalSpend: 32000,
      platforms: ['Meta', 'Google'],
      lastActivity: new Date(Date.now() - 1 * 60 * 60 * 1000),
      accountManager: 'Mike Chen',
    },
  ];

  // Helper to determine EMQ status from score
  const getEmqStatus = (score: number | null): EmqStatus => {
    if (score === null) return 'risk';
    if (score >= 80) return 'ok';
    if (score >= 60) return 'risk';
    if (score >= 40) return 'degraded';
    return 'critical';
  };

  // Helper to determine autopilot mode from churn risk
  const getAutopilotMode = (churnRisk: number): AutopilotMode => {
    if (churnRisk >= 0.8) return 'frozen';
    if (churnRisk >= 0.6) return 'cuts_only';
    if (churnRisk >= 0.4) return 'limited';
    return 'normal';
  };

  // Map API data to tenant list items
  const tenants: TenantListItem[] =
    tenantsData?.items?.map((t) => ({
      id: String(t.id),
      name: t.name,
      industry: 'E-commerce', // Not in API, use default
      emqScore: t.emqScore ?? 0,
      emqStatus: getEmqStatus(t.emqScore),
      autopilotMode: getAutopilotMode(t.churnRisk),
      budgetAtRisk: t.budgetAtRisk,
      activeIncidents: t.activeIncidents,
      totalSpend: t.monthlySpend,
      platforms: ['Meta', 'Google'], // Not in API, use defaults
      lastActivity: t.lastActivityAt ? new Date(t.lastActivityAt) : new Date(),
      accountManager: null, // Not in API
    })) ?? mockTenants;

  // Filter and sort tenants
  const filteredTenants = useMemo(() => {
    let result = [...tenants];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.industry.toLowerCase().includes(query) ||
          t.accountManager?.toLowerCase().includes(query)
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      result = result.filter((t) => t.emqStatus === statusFilter);
    }

    // Mode filter
    if (modeFilter !== 'all') {
      result = result.filter((t) => t.autopilotMode === modeFilter);
    }

    // Sort
    result.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'emq':
          comparison = a.emqScore - b.emqScore;
          break;
        case 'budgetAtRisk':
          comparison = a.budgetAtRisk - b.budgetAtRisk;
          break;
        case 'activeIncidents':
          comparison = a.activeIncidents - b.activeIncidents;
          break;
        case 'lastActivity':
          comparison = a.lastActivity.getTime() - b.lastActivity.getTime();
          break;
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return result;
  }, [tenants, searchQuery, statusFilter, modeFilter, sortField, sortDirection]);

  const getStatusColor = (status: EmqStatus) => {
    switch (status) {
      case 'ok':
        return 'text-success bg-success/10';
      case 'risk':
        return 'text-warning bg-warning/10';
      case 'degraded':
        return 'text-orange-400 bg-orange-400/10';
      case 'critical':
        return 'text-danger bg-danger/10';
    }
  };

  const getStatusLabel = (status: EmqStatus) => {
    switch (status) {
      case 'ok':
        return 'Healthy';
      case 'risk':
        return 'At Risk';
      case 'degraded':
        return 'Degraded';
      case 'critical':
        return 'Critical';
    }
  };

  const formatLastActivity = (date: Date) => {
    const mins = Math.floor((Date.now() - date.getTime()) / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  // Summary stats
  const stats = {
    total: tenants.length,
    healthy: tenants.filter((t) => t.emqStatus === 'ok').length,
    atRisk: tenants.filter((t) => t.emqStatus !== 'ok').length,
    totalBudgetAtRisk: tenants.reduce((sum, t) => sum + t.budgetAtRisk, 0),
    totalIncidents: tenants.reduce((sum, t) => sum + t.activeIncidents, 0),
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Tenant Portfolio</h1>
          <p className="text-text-muted">Monitor and manage all tenants</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-secondary border border-white/10">
            <BuildingOfficeIcon className="w-5 h-5 text-stratum-400" />
            <span className="text-white font-semibold">{stats.total}</span>
            <span className="text-text-muted">Tenants</span>
          </div>
          {stats.atRisk > 0 && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-warning/10 border border-warning/20">
              <ExclamationTriangleIcon className="w-5 h-5 text-warning" />
              <span className="text-warning font-semibold">{stats.atRisk}</span>
              <span className="text-warning/80">Need Attention</span>
            </div>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-3 mb-2">
            <CheckCircleIcon className="w-5 h-5 text-success" />
            <span className="text-text-muted">Healthy</span>
          </div>
          <span className="text-2xl font-bold text-white">{stats.healthy}</span>
          <span className="text-text-muted ml-2">/ {stats.total}</span>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-3 mb-2">
            <ExclamationTriangleIcon className="w-5 h-5 text-warning" />
            <span className="text-text-muted">At Risk</span>
          </div>
          <span className="text-2xl font-bold text-white">{stats.atRisk}</span>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-text-muted">Budget at Risk</span>
          </div>
          <span className="text-2xl font-bold text-danger">
            ${stats.totalBudgetAtRisk.toLocaleString()}
          </span>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-text-muted">Active Incidents</span>
          </div>
          <span className="text-2xl font-bold text-warning">{stats.totalIncidents}</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Search */}
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

        {/* Status Filter */}
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

        {/* Mode Filter */}
        <select
          value={modeFilter}
          onChange={(e) => setModeFilter(e.target.value as AutopilotMode | 'all')}
          className="px-3 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500"
        >
          <option value="all">All Modes</option>
          <option value="normal">Normal</option>
          <option value="limited">Limited</option>
          <option value="cuts_only">Cuts Only</option>
          <option value="frozen">Frozen</option>
        </select>

        {/* Sort */}
        <div className="flex items-center gap-2">
          <ArrowsUpDownIcon className="w-4 h-4 text-text-muted" />
          <select
            value={sortField}
            onChange={(e) => setSortField(e.target.value as SortField)}
            className="px-3 py-2 rounded-lg bg-surface-secondary border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-stratum-500"
          >
            <option value="emq">Sort by EMQ</option>
            <option value="name">Sort by Name</option>
            <option value="budgetAtRisk">Sort by Budget at Risk</option>
            <option value="activeIncidents">Sort by Incidents</option>
            <option value="lastActivity">Sort by Activity</option>
          </select>
          <button
            onClick={() => setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'))}
            className="p-2 rounded-lg bg-surface-secondary border border-white/10 text-text-muted hover:text-white transition-colors"
          >
            {sortDirection === 'asc' ? '↑' : '↓'}
          </button>
        </div>
      </div>

      {/* Tenants Table */}
      <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left p-4 text-text-muted font-medium">Tenant</th>
              <th className="text-left p-4 text-text-muted font-medium">EMQ</th>
              <th className="text-left p-4 text-text-muted font-medium">Status</th>
              <th className="text-left p-4 text-text-muted font-medium">Mode</th>
              <th className="text-left p-4 text-text-muted font-medium">Budget at Risk</th>
              <th className="text-left p-4 text-text-muted font-medium">Incidents</th>
              <th className="text-left p-4 text-text-muted font-medium">Last Activity</th>
              <th className="text-left p-4 text-text-muted font-medium" />
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filteredTenants.map((tenant) => (
              <tr key={tenant.id} className="hover:bg-white/5 transition-colors">
                <td className="p-4">
                  <div>
                    <div className="font-medium text-white">{tenant.name}</div>
                    <div className="text-sm text-text-muted">{tenant.industry}</div>
                    {tenant.accountManager && (
                      <div className="text-xs text-text-muted mt-1">
                        AM: {tenant.accountManager}
                      </div>
                    )}
                  </div>
                </td>
                <td className="p-4">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'text-xl font-bold',
                        tenant.emqScore >= 80
                          ? 'text-success'
                          : tenant.emqScore >= 60
                            ? 'text-warning'
                            : 'text-danger'
                      )}
                    >
                      {tenant.emqScore}
                    </span>
                    <ConfidenceBandBadge score={tenant.emqScore} size="sm" />
                  </div>
                </td>
                <td className="p-4">
                  <span
                    className={cn(
                      'px-2 py-1 rounded-full text-xs font-medium',
                      getStatusColor(tenant.emqStatus)
                    )}
                  >
                    {getStatusLabel(tenant.emqStatus)}
                  </span>
                </td>
                <td className="p-4">
                  <AutopilotModeBanner mode={tenant.autopilotMode} compact />
                </td>
                <td className="p-4">
                  {tenant.budgetAtRisk > 0 ? (
                    <BudgetAtRiskChip amount={tenant.budgetAtRisk} />
                  ) : (
                    <span className="text-text-muted">-</span>
                  )}
                </td>
                <td className="p-4">
                  {tenant.activeIncidents > 0 ? (
                    <span className="flex items-center gap-1 text-warning">
                      <ExclamationTriangleIcon className="w-4 h-4" />
                      {tenant.activeIncidents}
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-success">
                      <CheckCircleIcon className="w-4 h-4" />
                      None
                    </span>
                  )}
                </td>
                <td className="p-4">
                  <span className="flex items-center gap-1 text-text-muted text-sm">
                    <ClockIcon className="w-4 h-4" />
                    {formatLastActivity(tenant.lastActivity)}
                  </span>
                </td>
                <td className="p-4">
                  <Link
                    to={`/dashboard/superadmin/tenants/${tenant.id}`}
                    className="flex items-center gap-1 text-stratum-400 hover:text-stratum-300 transition-colors"
                  >
                    View
                    <ChevronRightIcon className="w-4 h-4" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filteredTenants.length === 0 && (
          <div className="p-8 text-center text-text-muted">
            No tenants found matching your filters.
          </div>
        )}
      </div>
    </div>
  );
}
