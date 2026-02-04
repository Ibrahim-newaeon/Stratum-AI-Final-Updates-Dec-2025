/**
 * Superadmin Dashboard
 * Comprehensive dashboard for system-wide management and monitoring
 * Blends MRR/ARR metrics, churn prediction, system health, and tenant management
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Ban,
  BarChart3,
  Building2,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Cpu,
  CreditCard,
  Crown,
  Database,
  DollarSign,
  Edit,
  Eye,
  FileText,
  Globe,
  HardDrive,
  Key,
  Loader2,
  Package,
  PieChart,
  Plus,
  Receipt,
  RefreshCw,
  Search,
  Server,
  Settings,
  Shield,
  TrendingUp,
  Users,
  XCircle,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// =============================================================================
// Types
// =============================================================================
interface RevenueMetrics {
  mrr: number;
  arr: number;
  mrr_growth_pct: number;
  gross_margin_pct: number;
  arpa: number;
  nrr: number;
  churn_rate: number;
  active_tenants: number;
  trial_tenants: number;
  total_tenants: number;
}

interface TenantPortfolioItem {
  id: number;
  name: string;
  slug: string;
  plan: string;
  status: string;
  mrr: number;
  users_count: number;
  users_limit: number;
  campaigns_count: number;
  connectors: string[];
  signal_health: string;
  churn_risk: number | null;
  last_admin_login: string | null;
  created_at: string;
}

interface ChurnRisk {
  tenant_id: number;
  tenant_name: string;
  plan: string;
  risk_score: number;
  risk_factors: string[];
  recommended_actions: string[];
  mrr_at_risk: number;
}

interface SystemHealth {
  pipeline: { success_rate_24h: number; jobs_total_24h: number; jobs_failed_24h: number };
  api: {
    requests_24h: number;
    error_rate: number;
    latency_p50_ms: number;
    latency_p99_ms?: number;
  };
  platforms: Record<string, { status: string; success_rate: number }>;
  resources: { cpu_percent: number; memory_percent: number; disk_percent: number };
}

interface SystemAlert {
  id: string;
  type: 'error' | 'warning' | 'info';
  message: string;
  component: string;
  timestamp: string;
}

// =============================================================================
// Mock data for features not yet connected
// =============================================================================
const mockAlerts: SystemAlert[] = [
  {
    id: '1',
    type: 'warning',
    message: 'High API latency detected on Meta endpoints',
    component: 'API Gateway',
    timestamp: '5 mins ago',
  },
  {
    id: '2',
    type: 'info',
    message: 'Database backup completed successfully',
    component: 'Database',
    timestamp: '30 mins ago',
  },
  {
    id: '3',
    type: 'error',
    message: 'Failed to sync TikTok campaigns for 3 tenants',
    component: 'Sync Service',
    timestamp: '1 hour ago',
  },
  {
    id: '4',
    type: 'info',
    message: 'New version v2.4.1 deployed successfully',
    component: 'Deployment',
    timestamp: '2 hours ago',
  },
];

// =============================================================================
// Main Component
// =============================================================================
export default function SuperadminDashboard() {
  const { user } = useAuth();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<
    'overview' | 'tenants' | 'system' | 'churn' | 'billing' | 'audit'
  >('overview');
  const [billingSubTab, setBillingSubTab] = useState<
    'overview' | 'plans' | 'invoices' | 'subscriptions'
  >('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [auditFilter, setAuditFilter] = useState({ action: '', tenant_id: '' });

  // API Data
  const [revenueMetrics, setRevenueMetrics] = useState<RevenueMetrics | null>(null);
  const [tenants, setTenants] = useState<TenantPortfolioItem[]>([]);
  const [churnRisks, setChurnRisks] = useState<ChurnRisk[]>([]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [revenueRes, tenantsRes, healthRes, churnRes, plansRes, invoicesRes, auditRes] =
        await Promise.allSettled([
          axios.get(`${API_BASE_URL}/api/v1/superadmin/revenue`, { headers: getAuthHeaders() }),
          axios.get(`${API_BASE_URL}/api/v1/superadmin/tenants/portfolio`, {
            headers: getAuthHeaders(),
          }),
          axios.get(`${API_BASE_URL}/api/v1/superadmin/system/health`, {
            headers: getAuthHeaders(),
          }),
          axios.get(`${API_BASE_URL}/api/v1/superadmin/churn/risks`, { headers: getAuthHeaders() }),
          axios.get(`${API_BASE_URL}/api/v1/superadmin/billing/plans`, {
            headers: getAuthHeaders(),
          }),
          axios.get(`${API_BASE_URL}/api/v1/superadmin/billing/invoices`, {
            headers: getAuthHeaders(),
          }),
          axios.get(`${API_BASE_URL}/api/v1/superadmin/audit?limit=100`, {
            headers: getAuthHeaders(),
          }),
        ]);

      // Handle each response individually
      if (revenueRes.status === 'fulfilled' && revenueRes.value.data.success) {
        setRevenueMetrics(revenueRes.value.data.data);
      }
      if (tenantsRes.status === 'fulfilled' && tenantsRes.value.data.success) {
        setTenants(tenantsRes.value.data.data.tenants || []);
      }
      if (healthRes.status === 'fulfilled' && healthRes.value.data.success) {
        setSystemHealth(healthRes.value.data.data);
      }
      if (churnRes.status === 'fulfilled' && churnRes.value.data.success) {
        setChurnRisks(churnRes.value.data.data.at_risk_tenants || []);
      }
      if (plansRes.status === 'fulfilled' && plansRes.value.data.success) {
        setPlans(plansRes.value.data.data.plans || []);
      }
      if (invoicesRes.status === 'fulfilled' && invoicesRes.value.data.success) {
        setInvoices(invoicesRes.value.data.data.invoices || []);
      }
      if (auditRes.status === 'fulfilled' && auditRes.value.data.success) {
        setAuditLogs(auditRes.value.data.data.logs || []);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchData().finally(() => setIsRefreshing(false));
  };

  const filteredTenants = useMemo(() => {
    if (!searchQuery) return tenants;
    const query = searchQuery.toLowerCase();
    return tenants.filter(
      (t) =>
        t.name.toLowerCase().includes(query) ||
        t.slug.toLowerCase().includes(query) ||
        t.plan.toLowerCase().includes(query)
    );
  }, [tenants, searchQuery]);

  const formatCurrency = (num: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(num);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96 motion-enter">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading Super Admin Dashboard...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 motion-enter">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Crown className="w-7 h-7 text-amber-500" />
            Superadmin Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            System-wide management and monitoring • Welcome back, {user?.name}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors motion-card"
          >
            <RefreshCw className={cn('w-4 h-4', isRefreshing && 'animate-spin')} />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-stratum text-white shadow-glow hover:shadow-glow-lg transition-all motion-card">
            <Plus className="w-4 h-4" />
            New Tenant
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 motion-critical">
          <AlertTriangle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 p-1 rounded-lg bg-muted/50 w-fit motion-enter overflow-x-auto">
        {[
          { id: 'overview', label: 'Overview', icon: BarChart3 },
          { id: 'tenants', label: 'Tenants', icon: Building2 },
          { id: 'system', label: 'System', icon: Server },
          { id: 'churn', label: 'Churn Risk', icon: AlertTriangle },
          { id: 'billing', label: 'Billing', icon: CreditCard },
          { id: 'audit', label: 'Audit Log', icon: FileText },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap',
              activeTab === tab.id
                ? 'bg-background shadow text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* =========================================================================
          Overview Tab - Revenue KPIs + Quick Stats
      ========================================================================= */}
      {activeTab === 'overview' && (
        <div className="space-y-6 motion-enter">
          {/* Revenue KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPICard
              icon={DollarSign}
              label="MRR"
              value={revenueMetrics ? formatCurrency(revenueMetrics.mrr) : '$0'}
              delta={revenueMetrics?.mrr_growth_pct}
              deltaLabel="vs last month"
              color="green"
            />
            <KPICard
              icon={TrendingUp}
              label="ARR"
              value={revenueMetrics ? formatCurrency(revenueMetrics.arr) : '$0'}
              color="purple"
            />
            <KPICard
              icon={Building2}
              label="Active Tenants"
              value={revenueMetrics?.active_tenants || 0}
              subValue={`${revenueMetrics?.trial_tenants || 0} trials`}
              color="blue"
            />
            <KPICard
              icon={BarChart3}
              label="ARPA"
              value={revenueMetrics ? formatCurrency(revenueMetrics.arpa) : '$0'}
              color="amber"
            />
          </div>

          {/* Secondary Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="NRR"
              value={`${revenueMetrics?.nrr || 0}%`}
              status={(revenueMetrics?.nrr || 0) >= 100 ? 'green' : 'amber'}
            />
            <MetricCard
              label="Churn Rate"
              value={`${revenueMetrics?.churn_rate || 0}%`}
              status={(revenueMetrics?.churn_rate || 0) < 5 ? 'green' : 'red'}
            />
            <MetricCard
              label="Gross Margin"
              value={`${revenueMetrics?.gross_margin_pct || 0}%`}
              status="green"
            />
            <MetricCard
              label="Total Tenants"
              value={revenueMetrics?.total_tenants || 0}
              status="blue"
            />
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* At Risk Tenants */}
            <div className="rounded-xl border bg-card p-5 shadow-card motion-card">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Tenants at Churn Risk
                {churnRisks.length > 0 && (
                  <span className="ml-auto text-sm font-normal text-amber-500">
                    ${churnRisks.reduce((sum, r) => sum + r.mrr_at_risk, 0).toLocaleString()}/mo at
                    risk
                  </span>
                )}
              </h3>
              {churnRisks.length === 0 ? (
                <p className="text-muted-foreground py-4 text-center">
                  No tenants at high churn risk 🎉
                </p>
              ) : (
                <div className="space-y-3">
                  {churnRisks.slice(0, 5).map((risk, idx) => (
                    <div
                      key={risk.tenant_id}
                      className="flex items-center justify-between p-3 rounded-lg bg-muted/50 motion-enter"
                      style={{ animationDelay: `${idx * 50}ms` }}
                    >
                      <div>
                        <p className="font-medium">{risk.tenant_name}</p>
                        <p className="text-xs text-muted-foreground">{risk.risk_factors[0]}</p>
                      </div>
                      <div className="text-right">
                        <p
                          className={cn(
                            'font-bold',
                            risk.risk_score >= 0.7
                              ? 'text-red-500'
                              : risk.risk_score >= 0.5
                                ? 'text-amber-500'
                                : 'text-green-500'
                          )}
                        >
                          {(risk.risk_score * 100).toFixed(0)}% risk
                        </p>
                        <p className="text-xs text-muted-foreground">${risk.mrr_at_risk}/mo</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* System Health Summary */}
            <div className="rounded-xl border bg-card p-5 shadow-card motion-card">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-green-500" />
                System Health
              </h3>
              {systemHealth ? (
                <div className="space-y-3">
                  <HealthRow
                    label="Pipeline Success Rate"
                    value={`${systemHealth.pipeline.success_rate_24h}%`}
                    status={systemHealth.pipeline.success_rate_24h >= 99 ? 'green' : 'amber'}
                  />
                  <HealthRow
                    label="API Error Rate"
                    value={`${systemHealth.api.error_rate}%`}
                    status={systemHealth.api.error_rate < 1 ? 'green' : 'amber'}
                  />
                  <HealthRow
                    label="API Latency (p50)"
                    value={`${systemHealth.api.latency_p50_ms}ms`}
                    status={systemHealth.api.latency_p50_ms < 100 ? 'green' : 'amber'}
                  />
                  <HealthRow
                    label="CPU Usage"
                    value={`${systemHealth.resources.cpu_percent}%`}
                    status={systemHealth.resources.cpu_percent < 70 ? 'green' : 'amber'}
                  />
                </div>
              ) : (
                <p className="text-muted-foreground py-4 text-center">Loading health metrics...</p>
              )}
            </div>
          </div>

          {/* System Alerts */}
          <div className="rounded-xl border bg-card p-6 shadow-card motion-card">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-primary" />
              System Alerts
            </h3>
            <div className="space-y-3">
              {mockAlerts.map((alert, idx) => (
                <div
                  key={alert.id}
                  className={cn(
                    'flex items-start gap-3 p-3 rounded-lg border motion-enter',
                    alert.type === 'error' && 'bg-red-500/5 border-red-500/20',
                    alert.type === 'warning' && 'bg-amber-500/5 border-amber-500/20',
                    alert.type === 'info' && 'bg-blue-500/5 border-blue-500/20'
                  )}
                  style={{ animationDelay: `${idx * 30}ms` }}
                >
                  {alert.type === 'error' && (
                    <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                  )}
                  {alert.type === 'warning' && (
                    <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />
                  )}
                  {alert.type === 'info' && (
                    <CheckCircle2 className="w-5 h-5 text-blue-500 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm font-medium">{alert.message}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {alert.component} • {alert.timestamp}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Usage Limits & Overage Warnings */}
          <div className="rounded-xl border bg-card p-6 shadow-card motion-card">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Package className="w-5 h-5 text-purple-500" />
              Usage Limits
              <span className="ml-auto text-xs font-normal text-muted-foreground">
                Tenants approaching plan limits
              </span>
            </h3>
            {(() => {
              // Calculate tenants near limits
              const tenantsNearLimits = tenants.filter((t) => {
                const usersPct = (t.users_count / t.users_limit) * 100;
                return usersPct >= 75;
              });

              if (tenantsNearLimits.length === 0) {
                return (
                  <p className="text-muted-foreground text-center py-4">
                    All tenants are within their usage limits
                  </p>
                );
              }

              return (
                <div className="space-y-3">
                  {tenantsNearLimits.slice(0, 5).map((tenant, idx) => {
                    const usersPct = (tenant.users_count / tenant.users_limit) * 100;
                    const isOverLimit = usersPct >= 100;
                    const isNearLimit = usersPct >= 90;

                    return (
                      <div
                        key={tenant.id}
                        className={cn(
                          'flex items-center justify-between p-3 rounded-lg border motion-enter',
                          isOverLimit
                            ? 'bg-red-500/5 border-red-500/20'
                            : isNearLimit
                              ? 'bg-amber-500/5 border-amber-500/20'
                              : 'bg-blue-500/5 border-blue-500/20'
                        )}
                        style={{ animationDelay: `${idx * 40}ms` }}
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={cn(
                              'w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-xs',
                              isOverLimit
                                ? 'bg-red-500'
                                : isNearLimit
                                  ? 'bg-amber-500'
                                  : 'bg-blue-500'
                            )}
                          >
                            {tenant.name.charAt(0)}
                          </div>
                          <div>
                            <p className="font-medium">{tenant.name}</p>
                            <p className="text-xs text-muted-foreground capitalize">
                              {tenant.plan} plan
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-2">
                            <Users className="w-4 h-4 text-muted-foreground" />
                            <span
                              className={cn(
                                'font-medium',
                                isOverLimit
                                  ? 'text-red-500'
                                  : isNearLimit
                                    ? 'text-amber-500'
                                    : 'text-blue-500'
                              )}
                            >
                              {tenant.users_count}/{tenant.users_limit}
                            </span>
                          </div>
                          <div className="w-20 h-1.5 bg-muted rounded-full mt-1">
                            <div
                              className={cn(
                                'h-full rounded-full transition-all',
                                isOverLimit
                                  ? 'bg-red-500'
                                  : isNearLimit
                                    ? 'bg-amber-500'
                                    : 'bg-blue-500'
                              )}
                              style={{ width: `${Math.min(100, usersPct)}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {tenantsNearLimits.length > 5 && (
                    <button
                      onClick={() => setActiveTab('tenants')}
                      className="w-full text-center text-sm text-primary hover:underline py-2"
                    >
                      View all {tenantsNearLimits.length} tenants approaching limits →
                    </button>
                  )}
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* =========================================================================
          Tenants Tab - Tenant Portfolio with Health & Churn Indicators
      ========================================================================= */}
      {activeTab === 'tenants' && (
        <div className="space-y-4 motion-enter">
          {/* Search and Filters */}
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search tenants..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <select className="px-3 py-2 rounded-lg border bg-background">
              <option>All Plans</option>
              <option>Enterprise</option>
              <option>Professional</option>
              <option>Starter</option>
              <option>Free</option>
            </select>
            <select className="px-3 py-2 rounded-lg border bg-background">
              <option>All Status</option>
              <option>Active</option>
              <option>Trial</option>
              <option>Suspended</option>
            </select>
          </div>

          {/* Tenants Table */}
          <div className="rounded-xl border bg-card overflow-hidden shadow-card">
            <table className="w-full text-sm">
              <thead className="bg-muted/30">
                <tr>
                  <th className="text-left py-3 px-4 font-medium">Tenant</th>
                  <th className="text-left py-3 px-4 font-medium">Plan</th>
                  <th className="text-right py-3 px-4 font-medium">MRR</th>
                  <th className="text-center py-3 px-4 font-medium">Users</th>
                  <th className="text-center py-3 px-4 font-medium">Signal Health</th>
                  <th className="text-center py-3 px-4 font-medium">Churn Risk</th>
                  <th className="text-right py-3 px-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredTenants.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-muted-foreground">
                      No tenants found
                    </td>
                  </tr>
                ) : (
                  filteredTenants.map((tenant, idx) => (
                    <tr
                      key={tenant.id}
                      className="hover:bg-muted/30 motion-enter"
                      style={{ animationDelay: `${idx * 20}ms` }}
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-lg bg-gradient-stratum flex items-center justify-center text-white font-bold">
                            {tenant.name.charAt(0)}
                          </div>
                          <div>
                            <p className="font-medium">{tenant.name}</p>
                            <p className="text-xs text-muted-foreground">{tenant.slug}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <PlanBadge plan={tenant.plan} />
                      </td>
                      <td className="text-right py-3 px-4 font-medium">
                        {formatCurrency(tenant.mrr)}
                      </td>
                      <td className="text-center py-3 px-4">
                        <div className="flex items-center justify-center gap-2">
                          <span>
                            {tenant.users_count}/{tenant.users_limit}
                          </span>
                          <div className="w-12 h-1.5 bg-muted rounded-full">
                            <div
                              className={cn(
                                'h-full rounded-full',
                                tenant.users_count / tenant.users_limit >= 0.9
                                  ? 'bg-red-500'
                                  : tenant.users_count / tenant.users_limit >= 0.7
                                    ? 'bg-amber-500'
                                    : 'bg-green-500'
                              )}
                              style={{
                                width: `${Math.min(100, (tenant.users_count / tenant.users_limit) * 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="text-center py-3 px-4">
                        <HealthBadge status={tenant.signal_health} />
                      </td>
                      <td className="text-center py-3 px-4">
                        {tenant.churn_risk !== null ? (
                          <span
                            className={cn(
                              'font-medium',
                              tenant.churn_risk >= 0.7
                                ? 'text-red-500'
                                : tenant.churn_risk >= 0.4
                                  ? 'text-amber-500'
                                  : 'text-green-500'
                            )}
                          >
                            {(tenant.churn_risk * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                      <td className="text-right py-3 px-4">
                        <div className="flex items-center justify-end gap-1">
                          <button className="p-1.5 rounded hover:bg-muted" title="View">
                            <Eye className="w-4 h-4" />
                          </button>
                          <button className="p-1.5 rounded hover:bg-muted" title="Edit">
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            className="p-1.5 rounded hover:bg-muted text-red-500"
                            title="Suspend"
                          >
                            <Ban className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* =========================================================================
          System Tab - Infrastructure Status & Platform Health
      ========================================================================= */}
      {activeTab === 'system' && (
        <div className="space-y-6 motion-enter">
          {/* Platform Health Grid */}
          {systemHealth && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(systemHealth.platforms).map(([platform, data], idx) => (
                <div
                  key={platform}
                  className="rounded-xl border bg-card p-4 shadow-card motion-card"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium capitalize">{platform}</span>
                    <HealthBadge status={data.status} />
                  </div>
                  <p className="text-2xl font-bold">{data.success_rate}%</p>
                  <p className="text-xs text-muted-foreground">Success Rate</p>
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Infrastructure Status */}
            <div className="rounded-xl border bg-card p-6 shadow-card motion-card">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Server className="w-5 h-5 text-primary" />
                Infrastructure Status
              </h3>
              <div className="space-y-4">
                {[
                  {
                    name: 'API Server',
                    status: 'healthy',
                    cpu: systemHealth?.resources.cpu_percent || 45,
                    memory: systemHealth?.resources.memory_percent || 62,
                  },
                  { name: 'Worker Nodes', status: 'healthy', cpu: 78, memory: 84 },
                  { name: 'Database', status: 'healthy', cpu: 23, memory: 56 },
                  { name: 'Redis Cache', status: 'healthy', cpu: 12, memory: 45 },
                  { name: 'ML Service', status: 'healthy', cpu: 67, memory: 71 },
                ].map((service, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/30 motion-enter"
                    style={{ animationDelay: `${idx * 30}ms` }}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          'w-2 h-2 rounded-full',
                          service.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                        )}
                      />
                      <span className="font-medium">{service.name}</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="flex items-center gap-1">
                        <Cpu className="w-4 h-4 text-muted-foreground" />
                        {service.cpu}%
                      </span>
                      <span className="flex items-center gap-1">
                        <HardDrive className="w-4 h-4 text-muted-foreground" />
                        {service.memory}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Detailed API Metrics */}
            {systemHealth && (
              <div className="rounded-xl border bg-card p-6 shadow-card motion-card">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-amber-500" />
                  API Metrics (24h)
                </h3>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="p-4 rounded-lg bg-muted/30">
                    <p className="text-2xl font-bold">
                      {systemHealth.api.requests_24h.toLocaleString()}
                    </p>
                    <p className="text-xs text-muted-foreground">Total Requests</p>
                  </div>
                  <div className="p-4 rounded-lg bg-muted/30">
                    <p
                      className={cn(
                        'text-2xl font-bold',
                        systemHealth.api.error_rate < 1 ? 'text-green-500' : 'text-red-500'
                      )}
                    >
                      {systemHealth.api.error_rate}%
                    </p>
                    <p className="text-xs text-muted-foreground">Error Rate</p>
                  </div>
                </div>
                <div className="space-y-3">
                  <ResourceBar
                    label="Latency p50"
                    value={systemHealth.api.latency_p50_ms}
                    max={500}
                    unit="ms"
                  />
                  <ResourceBar
                    label="CPU"
                    value={systemHealth.resources.cpu_percent}
                    max={100}
                    unit="%"
                  />
                  <ResourceBar
                    label="Memory"
                    value={systemHealth.resources.memory_percent}
                    max={100}
                    unit="%"
                  />
                  <ResourceBar
                    label="Disk"
                    value={systemHealth.resources.disk_percent}
                    max={100}
                    unit="%"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="rounded-xl border bg-card p-6 shadow-card motion-card">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5 text-primary" />
              Quick Actions
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {[
                { icon: Database, label: 'Backup Database', color: 'text-blue-500' },
                { icon: RefreshCw, label: 'Clear Cache', color: 'text-green-500' },
                { icon: Key, label: 'Rotate Keys', color: 'text-amber-500' },
                { icon: Globe, label: 'CDN Purge', color: 'text-purple-500' },
                { icon: Activity, label: 'Health Check', color: 'text-cyan-500' },
                { icon: Shield, label: 'Security Scan', color: 'text-red-500' },
              ].map((action, idx) => (
                <button
                  key={idx}
                  className="flex flex-col items-center gap-2 p-4 rounded-lg border hover:bg-muted transition-colors motion-card"
                >
                  <action.icon className={cn('w-6 h-6', action.color)} />
                  <span className="text-xs font-medium text-center">{action.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          Churn Risk Tab - Detailed Churn Analysis
      ========================================================================= */}
      {activeTab === 'churn' && (
        <div className="space-y-6 motion-enter">
          {/* Summary */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-xl border bg-card p-5 shadow-card motion-card">
              <p className="text-muted-foreground text-sm mb-2">Tenants at Risk</p>
              <p className="text-3xl font-bold text-red-500">{churnRisks.length}</p>
            </div>
            <div className="rounded-xl border bg-card p-5 shadow-card motion-card">
              <p className="text-muted-foreground text-sm mb-2">MRR at Risk</p>
              <p className="text-3xl font-bold text-amber-500">
                {formatCurrency(churnRisks.reduce((sum, r) => sum + r.mrr_at_risk, 0))}
              </p>
            </div>
            <div className="rounded-xl border bg-card p-5 shadow-card motion-card">
              <p className="text-muted-foreground text-sm mb-2">Avg Risk Score</p>
              <p className="text-3xl font-bold">
                {churnRisks.length > 0
                  ? (
                      (churnRisks.reduce((sum, r) => sum + r.risk_score, 0) / churnRisks.length) *
                      100
                    ).toFixed(0)
                  : 0}
                %
              </p>
            </div>
          </div>

          {/* Churn Risk List */}
          {churnRisks.length === 0 ? (
            <div className="rounded-xl border bg-card p-8 text-center shadow-card motion-card">
              <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <p className="text-lg font-medium">All Clear!</p>
              <p className="text-muted-foreground">
                No tenants are at high churn risk at this time.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {churnRisks.map((risk, idx) => (
                <div
                  key={risk.tenant_id}
                  className="rounded-xl border bg-card p-5 shadow-card motion-enter"
                  style={{ animationDelay: `${idx * 50}ms` }}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold">{risk.tenant_name}</h3>
                      <p className="text-sm text-muted-foreground">{risk.plan} plan</p>
                    </div>
                    <div className="text-right">
                      <p
                        className={cn(
                          'text-2xl font-bold motion-delta',
                          risk.risk_score >= 0.7
                            ? 'text-red-500'
                            : risk.risk_score >= 0.5
                              ? 'text-amber-500'
                              : 'text-green-500'
                        )}
                      >
                        {(risk.risk_score * 100).toFixed(0)}%
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {formatCurrency(risk.mrr_at_risk)}/mo at risk
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground mb-2">Risk Factors</p>
                      <ul className="space-y-2">
                        {risk.risk_factors.map((factor, i) => (
                          <li
                            key={i}
                            className="flex items-center gap-2 text-sm motion-enter"
                            style={{ animationDelay: `${i * 30}ms` }}
                          >
                            <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                            {factor}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground mb-2">
                        Recommended Actions
                      </p>
                      <ul className="space-y-2">
                        {risk.recommended_actions.map((action, i) => (
                          <li
                            key={i}
                            className="flex items-center gap-2 text-sm motion-enter"
                            style={{ animationDelay: `${i * 30}ms` }}
                          >
                            <ChevronRight className="w-4 h-4 text-primary flex-shrink-0" />
                            {action}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          Billing Tab - Enhanced with Sub-tabs
      ========================================================================= */}
      {activeTab === 'billing' && (
        <div className="space-y-6 motion-enter">
          {/* Billing Sub-tabs */}
          <div className="flex items-center gap-2 border-b pb-3">
            {[
              { id: 'overview', label: 'Overview', icon: BarChart3 },
              { id: 'plans', label: 'Plans Catalog', icon: Package },
              { id: 'invoices', label: 'Invoices', icon: Receipt },
              { id: 'subscriptions', label: 'Subscriptions', icon: Calendar },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setBillingSubTab(tab.id as any)}
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-all',
                  billingSubTab === tab.id
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Billing Overview */}
          {billingSubTab === 'overview' && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="p-5 rounded-xl bg-green-500/10 border border-green-500/20 shadow-card motion-card">
                  <p className="text-sm text-muted-foreground">MRR</p>
                  <p className="text-3xl font-bold text-green-500">
                    {revenueMetrics ? formatCurrency(revenueMetrics.mrr) : '$0'}
                  </p>
                  <p className="text-xs text-green-600 flex items-center gap-1 mt-2">
                    <TrendingUp className="w-3 h-3" />+{revenueMetrics?.mrr_growth_pct || 0}% growth
                  </p>
                </div>
                <div className="p-5 rounded-xl bg-purple-500/10 border border-purple-500/20 shadow-card motion-card">
                  <p className="text-sm text-muted-foreground">ARR</p>
                  <p className="text-3xl font-bold text-purple-500">
                    {revenueMetrics ? formatCurrency(revenueMetrics.arr) : '$0'}
                  </p>
                </div>
                <div className="p-5 rounded-xl bg-blue-500/10 border border-blue-500/20 shadow-card motion-card">
                  <p className="text-sm text-muted-foreground">Pending</p>
                  <p className="text-3xl font-bold text-blue-500">
                    {formatCurrency(
                      invoices
                        .filter((i) => i.status === 'pending')
                        .reduce((s, i) => s + i.total, 0)
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">
                    {invoices.filter((i) => i.status === 'pending').length} invoices
                  </p>
                </div>
                <div className="p-5 rounded-xl bg-amber-500/10 border border-amber-500/20 shadow-card motion-card">
                  <p className="text-sm text-muted-foreground">Overdue</p>
                  <p className="text-3xl font-bold text-amber-500">
                    {formatCurrency(
                      invoices
                        .filter((i) => i.status === 'overdue')
                        .reduce((s, i) => s + i.total, 0)
                    )}
                  </p>
                  <p className="text-xs text-amber-600 mt-2">
                    {invoices.filter((i) => i.status === 'overdue').length} invoices
                  </p>
                </div>
              </div>

              {/* Plan Distribution */}
              <div className="rounded-xl border bg-card p-6 shadow-card motion-card">
                <h3 className="font-semibold flex items-center gap-2 mb-4">
                  <PieChart className="w-5 h-5 text-primary" />
                  Revenue by Plan
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {plans.map((plan, idx) => (
                    <div
                      key={plan.id}
                      className="p-4 rounded-lg bg-muted/30 motion-enter"
                      style={{ animationDelay: `${idx * 50}ms` }}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <div
                          className={cn(
                            'w-3 h-3 rounded-full',
                            plan.tier === 'enterprise'
                              ? 'bg-purple-500'
                              : plan.tier === 'professional'
                                ? 'bg-blue-500'
                                : plan.tier === 'starter'
                                  ? 'bg-green-500'
                                  : 'bg-gray-500'
                          )}
                        />
                        <span className="font-medium">{plan.display_name || plan.name}</span>
                      </div>
                      <p className="text-xl font-bold">{formatCurrency(plan.price || 0)}/mo</p>
                      <p className="text-xs text-muted-foreground">
                        {plan.limits?.max_users || 0} users, {plan.limits?.max_campaigns || 0}{' '}
                        campaigns
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Plans Catalog */}
          {billingSubTab === 'plans' && (
            <div className="rounded-xl border bg-card shadow-card overflow-hidden">
              <div className="p-4 border-b flex items-center justify-between">
                <h3 className="font-semibold">Subscription Plans</h3>
                <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-sm">
                  <Plus className="w-4 h-4" />
                  Add Plan
                </button>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-muted/30">
                  <tr>
                    <th className="text-left py-3 px-4 font-medium">Plan</th>
                    <th className="text-left py-3 px-4 font-medium">Tier</th>
                    <th className="text-right py-3 px-4 font-medium">Price</th>
                    <th className="text-center py-3 px-4 font-medium">Users</th>
                    <th className="text-center py-3 px-4 font-medium">Campaigns</th>
                    <th className="text-center py-3 px-4 font-medium">Connectors</th>
                    <th className="text-center py-3 px-4 font-medium">Status</th>
                    <th className="text-right py-3 px-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {plans.map((plan, idx) => (
                    <tr
                      key={plan.id}
                      className="hover:bg-muted/30 motion-enter"
                      style={{ animationDelay: `${idx * 20}ms` }}
                    >
                      <td className="py-3 px-4 font-medium">{plan.display_name || plan.name}</td>
                      <td className="py-3 px-4">
                        <PlanBadge plan={plan.tier} />
                      </td>
                      <td className="py-3 px-4 text-right font-medium">
                        {formatCurrency(plan.price || 0)}
                        <span className="text-muted-foreground text-xs">
                          /{plan.billing_period || 'mo'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">{plan.limits?.max_users || '-'}</td>
                      <td className="py-3 px-4 text-center">{plan.limits?.max_campaigns || '-'}</td>
                      <td className="py-3 px-4 text-center">
                        {plan.limits?.max_connectors || '-'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={cn(
                            'px-2 py-1 rounded-full text-xs',
                            plan.is_active !== false
                              ? 'bg-green-500/10 text-green-500'
                              : 'bg-gray-500/10 text-gray-500'
                          )}
                        >
                          {plan.is_active !== false ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button className="p-1.5 rounded hover:bg-muted" title="Edit">
                          <Edit className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Invoices */}
          {billingSubTab === 'invoices' && (
            <div className="rounded-xl border bg-card shadow-card overflow-hidden">
              <div className="p-4 border-b flex items-center justify-between">
                <h3 className="font-semibold">Invoices</h3>
                <div className="flex items-center gap-2">
                  <select className="px-3 py-1.5 rounded-lg border bg-background text-sm">
                    <option>All Status</option>
                    <option>Paid</option>
                    <option>Pending</option>
                    <option>Overdue</option>
                  </select>
                  <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-sm">
                    <Plus className="w-4 h-4" />
                    Generate Invoice
                  </button>
                </div>
              </div>
              {invoices.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Receipt className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No invoices found</p>
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-muted/30">
                    <tr>
                      <th className="text-left py-3 px-4 font-medium">Invoice</th>
                      <th className="text-left py-3 px-4 font-medium">Tenant</th>
                      <th className="text-right py-3 px-4 font-medium">Amount</th>
                      <th className="text-center py-3 px-4 font-medium">Status</th>
                      <th className="text-left py-3 px-4 font-medium">Due Date</th>
                      <th className="text-right py-3 px-4 font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {invoices.map((inv) => (
                      <tr key={inv.id} className="hover:bg-muted/30">
                        <td className="py-3 px-4 font-medium">{inv.invoice_number}</td>
                        <td className="py-3 px-4">{inv.tenant_name}</td>
                        <td className="py-3 px-4 text-right font-medium">
                          {formatCurrency(inv.total)}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={cn(
                              'px-2 py-1 rounded-full text-xs',
                              inv.status === 'paid'
                                ? 'bg-green-500/10 text-green-500'
                                : inv.status === 'pending'
                                  ? 'bg-blue-500/10 text-blue-500'
                                  : inv.status === 'overdue'
                                    ? 'bg-red-500/10 text-red-500'
                                    : 'bg-gray-500/10 text-gray-500'
                            )}
                          >
                            {inv.status}
                          </span>
                        </td>
                        <td className="py-3 px-4">{inv.due_date || '-'}</td>
                        <td className="py-3 px-4 text-right">
                          <button className="p-1.5 rounded hover:bg-muted" title="View">
                            <Eye className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* Subscriptions */}
          {billingSubTab === 'subscriptions' && (
            <div className="rounded-xl border bg-card p-6 shadow-card">
              <h3 className="font-semibold mb-4">Active Subscriptions</h3>
              <p className="text-muted-foreground text-center py-8">
                Subscription management coming soon. View and manage tenant subscriptions, trials,
                and upgrades.
              </p>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          Audit Log Tab
      ========================================================================= */}
      {activeTab === 'audit' && (
        <div className="space-y-4 motion-enter">
          {/* Filters */}
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search actions..."
                value={auditFilter.action}
                onChange={(e) => setAuditFilter((f) => ({ ...f, action: e.target.value }))}
                className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <select
              className="px-3 py-2 rounded-lg border bg-background"
              value={auditFilter.tenant_id}
              onChange={(e) => setAuditFilter((f) => ({ ...f, tenant_id: e.target.value }))}
            >
              <option value="">All Tenants</option>
              {tenants.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border hover:bg-muted"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {/* Audit Log Table */}
          <div className="rounded-xl border bg-card shadow-card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/30">
                <tr>
                  <th className="text-left py-3 px-4 font-medium">Timestamp</th>
                  <th className="text-left py-3 px-4 font-medium">Action</th>
                  <th className="text-left py-3 px-4 font-medium">User</th>
                  <th className="text-left py-3 px-4 font-medium">Resource</th>
                  <th className="text-center py-3 px-4 font-medium">Status</th>
                  <th className="text-left py-3 px-4 font-medium">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {auditLogs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-muted-foreground">
                      <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No audit logs found</p>
                      <p className="text-xs mt-1">
                        Admin actions will appear here after the database migration
                      </p>
                    </td>
                  </tr>
                ) : (
                  auditLogs
                    .filter((log) => {
                      if (
                        auditFilter.action &&
                        !log.action?.toLowerCase().includes(auditFilter.action.toLowerCase())
                      ) {
                        return false;
                      }
                      if (
                        auditFilter.tenant_id &&
                        log.tenant_id !== parseInt(auditFilter.tenant_id)
                      ) {
                        return false;
                      }
                      return true;
                    })
                    .map((log, idx) => (
                      <tr
                        key={log.id}
                        className="hover:bg-muted/30 motion-enter"
                        style={{ animationDelay: `${idx * 10}ms` }}
                      >
                        <td className="py-3 px-4 text-muted-foreground">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : '-'}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-medium">{log.action}</span>
                        </td>
                        <td className="py-3 px-4">{log.user_email || `User #${log.user_id}`}</td>
                        <td className="py-3 px-4">
                          {log.resource_type && (
                            <span className="text-muted-foreground">
                              {log.resource_type}
                              {log.resource_id && <span className="ml-1">#{log.resource_id}</span>}
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-center">
                          {log.success ? (
                            <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" />
                          ) : (
                            <XCircle className="w-4 h-4 text-red-500 mx-auto" />
                          )}
                        </td>
                        <td className="py-3 px-4 text-muted-foreground text-xs max-w-[200px] truncate">
                          {log.details ? JSON.stringify(log.details) : '-'}
                        </td>
                      </tr>
                    ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Sub-Components
// =============================================================================
function KPICard({
  icon: Icon,
  label,
  value,
  delta,
  deltaLabel,
  subValue,
  color = 'blue',
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  delta?: number;
  deltaLabel?: string;
  subValue?: string;
  color?: 'blue' | 'green' | 'amber' | 'red' | 'purple';
}) {
  const colorClasses = {
    blue: 'bg-blue-500/10 text-blue-500',
    green: 'bg-green-500/10 text-green-500',
    amber: 'bg-amber-500/10 text-amber-500',
    red: 'bg-red-500/10 text-red-500',
    purple: 'bg-purple-500/10 text-purple-500',
  };

  return (
    <div className="rounded-xl border bg-card p-5 shadow-card hover:shadow-card-hover transition-all motion-card">
      <div className="flex items-center gap-3 mb-3">
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>
          <Icon className="w-5 h-5" />
        </div>
        <span className="text-sm text-muted-foreground">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {delta !== undefined && (
        <div className="flex items-center gap-1 mt-1">
          {delta >= 0 ? (
            <ArrowUpRight className="w-4 h-4 text-green-500" />
          ) : (
            <ArrowDownRight className="w-4 h-4 text-red-500" />
          )}
          <span
            className={cn('text-sm font-medium', delta >= 0 ? 'text-green-500' : 'text-red-500')}
          >
            {delta >= 0 ? '+' : ''}
            {delta}%
          </span>
          {deltaLabel && <span className="text-xs text-muted-foreground">{deltaLabel}</span>}
        </div>
      )}
      {subValue && <p className="text-sm text-muted-foreground mt-1">{subValue}</p>}
    </div>
  );
}

function MetricCard({
  label,
  value,
  status,
}: {
  label: string;
  value: string | number;
  status: 'green' | 'amber' | 'red' | 'blue';
}) {
  const statusColors = {
    green: 'text-green-500',
    amber: 'text-amber-500',
    red: 'text-red-500',
    blue: 'text-blue-500',
  };

  return (
    <div className="rounded-xl border bg-card p-4 shadow-card motion-card">
      <p className="text-sm text-muted-foreground mb-1">{label}</p>
      <p className={cn('text-xl font-bold', statusColors[status])}>{value}</p>
    </div>
  );
}

function HealthRow({
  label,
  value,
  status,
}: {
  label: string;
  value: string;
  status: 'green' | 'amber' | 'red';
}) {
  const icons = {
    green: <CheckCircle2 className="w-4 h-4 text-green-500" />,
    amber: <AlertCircle className="w-4 h-4 text-amber-500" />,
    red: <AlertTriangle className="w-4 h-4 text-red-500" />,
  };

  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
      <span className="text-sm">{label}</span>
      <div className="flex items-center gap-2">
        <span className="font-medium">{value}</span>
        {icons[status]}
      </div>
    </div>
  );
}

function PlanBadge({ plan }: { plan: string }) {
  const colors: Record<string, string> = {
    free: 'bg-gray-500/10 text-gray-500',
    trial: 'bg-cyan-500/10 text-cyan-500',
    starter: 'bg-green-500/10 text-green-500',
    professional: 'bg-blue-500/10 text-blue-500',
    enterprise: 'bg-purple-500/10 text-purple-500',
  };

  return (
    <span
      className={cn(
        'px-2 py-1 rounded-md text-xs font-medium capitalize',
        colors[plan] || colors.free
      )}
    >
      {plan}
    </span>
  );
}

function HealthBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    healthy: 'bg-green-500/10 text-green-500',
    risk: 'bg-amber-500/10 text-amber-500',
    degraded: 'bg-orange-500/10 text-orange-500',
    critical: 'bg-red-500/10 text-red-500',
  };

  const icons: Record<string, React.ReactNode> = {
    healthy: <CheckCircle2 className="w-3 h-3" />,
    risk: <AlertCircle className="w-3 h-3" />,
    degraded: <AlertTriangle className="w-3 h-3" />,
    critical: <XCircle className="w-3 h-3" />,
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium capitalize',
        colors[status] || colors.healthy
      )}
    >
      {icons[status]}
      {status}
    </span>
  );
}

function ResourceBar({
  label,
  value,
  max = 100,
  unit = '%',
}: {
  label: string;
  value: number;
  max?: number;
  unit?: string;
}) {
  const percentage = (value / max) * 100;
  const getColor = (v: number) => {
    if (v >= 80) return 'bg-red-500';
    if (v >= 60) return 'bg-amber-500';
    return 'bg-green-500';
  };

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">
          {value}
          {unit}
        </span>
      </div>
      <div className="w-full h-2 bg-muted rounded-full">
        <div
          className={cn('h-full rounded-full transition-all', getColor(percentage))}
          style={{ width: `${Math.min(100, percentage)}%` }}
        />
      </div>
    </div>
  );
}
