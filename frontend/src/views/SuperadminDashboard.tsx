/**
 * Superadmin Dashboard
 * Comprehensive dashboard for system-wide management and monitoring
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Users,
  Building2,
  Server,
  Activity,
  DollarSign,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  ChevronRight,
  Shield,
  Clock,
  Globe,
  Database,
  Cpu,
  HardDrive,
  Zap,
  RefreshCw,
  Plus,
  Search,
  MoreVertical,
  CheckCircle2,
  XCircle,
  Eye,
  Edit,
  Trash2,
  Ban,
  Settings,
  Key,
  CreditCard,
  BarChart3,
  PieChart,
} from 'lucide-react'
import { cn, getPlatformColor } from '@/lib/utils'
import { useAuth } from '@/contexts/AuthContext'

// Types
interface SystemStats {
  totalTenants: number
  activeTenants: number
  totalUsers: number
  activeUsers: number
  totalCampaigns: number
  totalSpend: number
  apiRequestsToday: number
  systemHealth: 'healthy' | 'degraded' | 'critical'
}

interface Tenant {
  id: string
  name: string
  plan: 'starter' | 'pro' | 'enterprise'
  users: number
  campaigns: number
  monthlySpend: number
  status: 'active' | 'suspended' | 'trial'
  createdAt: string
  lastActive: string
}

interface SystemAlert {
  id: string
  type: 'error' | 'warning' | 'info'
  message: string
  component: string
  timestamp: string
}

interface APIUsage {
  endpoint: string
  requests: number
  avgLatency: number
  errors: number
}

// Mock data
const mockStats: SystemStats = {
  totalTenants: 156,
  activeTenants: 142,
  totalUsers: 1284,
  activeUsers: 967,
  totalCampaigns: 4521,
  totalSpend: 2458000,
  apiRequestsToday: 1245678,
  systemHealth: 'healthy',
}

const mockTenants: Tenant[] = [
  { id: '1', name: 'Acme Corp', plan: 'enterprise', users: 45, campaigns: 128, monthlySpend: 125000, status: 'active', createdAt: '2024-01-15', lastActive: '2 mins ago' },
  { id: '2', name: 'TechStart Inc', plan: 'pro', users: 12, campaigns: 34, monthlySpend: 28000, status: 'active', createdAt: '2024-03-22', lastActive: '15 mins ago' },
  { id: '3', name: 'Global Retail', plan: 'enterprise', users: 78, campaigns: 256, monthlySpend: 340000, status: 'active', createdAt: '2023-09-10', lastActive: '1 hour ago' },
  { id: '4', name: 'Fashion Hub', plan: 'pro', users: 8, campaigns: 45, monthlySpend: 45000, status: 'trial', createdAt: '2024-11-01', lastActive: '3 hours ago' },
  { id: '5', name: 'Local Shop', plan: 'starter', users: 2, campaigns: 5, monthlySpend: 1200, status: 'suspended', createdAt: '2024-06-15', lastActive: '5 days ago' },
]

const mockAlerts: SystemAlert[] = [
  { id: '1', type: 'warning', message: 'High API latency detected on Meta endpoints', component: 'API Gateway', timestamp: '5 mins ago' },
  { id: '2', type: 'info', message: 'Database backup completed successfully', component: 'Database', timestamp: '30 mins ago' },
  { id: '3', type: 'error', message: 'Failed to sync TikTok campaigns for 3 tenants', component: 'Sync Service', timestamp: '1 hour ago' },
  { id: '4', type: 'info', message: 'New version v2.4.1 deployed successfully', component: 'Deployment', timestamp: '2 hours ago' },
]

const mockAPIUsage: APIUsage[] = [
  { endpoint: '/api/campaigns', requests: 245678, avgLatency: 45, errors: 12 },
  { endpoint: '/api/analytics', requests: 189234, avgLatency: 120, errors: 5 },
  { endpoint: '/api/capi/events', requests: 567890, avgLatency: 28, errors: 89 },
  { endpoint: '/api/ml/predict', requests: 34567, avgLatency: 250, errors: 3 },
  { endpoint: '/api/users', requests: 12345, avgLatency: 35, errors: 0 },
]

export default function SuperadminDashboard() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState<'overview' | 'tenants' | 'users' | 'system' | 'billing'>('overview')
  const [searchQuery, setSearchQuery] = useState('')

  const handleRefresh = () => {
    setIsRefreshing(true)
    setTimeout(() => setIsRefreshing(false), 1500)
  }

  const getHealthColor = (health: string) => {
    switch (health) {
      case 'healthy': return 'text-green-500 bg-green-500/10'
      case 'degraded': return 'text-amber-500 bg-amber-500/10'
      case 'critical': return 'text-red-500 bg-red-500/10'
      default: return 'text-muted-foreground bg-muted'
    }
  }

  const getPlanBadge = (plan: string) => {
    const styles = {
      starter: 'bg-gray-500/10 text-gray-500',
      pro: 'bg-blue-500/10 text-blue-500',
      enterprise: 'bg-purple-500/10 text-purple-500',
    }
    return styles[plan as keyof typeof styles] || styles.starter
  }

  const getStatusBadge = (status: string) => {
    const styles = {
      active: 'bg-green-500/10 text-green-500',
      trial: 'bg-amber-500/10 text-amber-500',
      suspended: 'bg-red-500/10 text-red-500',
    }
    return styles[status as keyof typeof styles] || styles.active
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  const formatCurrency = (num: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(num)
  }

  const filteredTenants = mockTenants.filter(tenant =>
    tenant.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="w-7 h-7 text-primary" />
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
            className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <RefreshCw className={cn('w-4 h-4', isRefreshing && 'animate-spin')} />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-stratum text-white shadow-glow hover:shadow-glow-lg transition-all">
            <Plus className="w-4 h-4" />
            New Tenant
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-1 p-1 rounded-lg bg-muted/50 w-fit">
        {[
          { id: 'overview', label: 'Overview', icon: BarChart3 },
          { id: 'tenants', label: 'Tenants', icon: Building2 },
          { id: 'users', label: 'Users', icon: Users },
          { id: 'system', label: 'System', icon: Server },
          { id: 'billing', label: 'Billing', icon: CreditCard },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all',
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

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border bg-card">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-blue-500/10">
                  <Building2 className="w-5 h-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Tenants</p>
                  <p className="text-2xl font-bold">{mockStats.totalTenants}</p>
                  <p className="text-xs text-green-500">+12 this month</p>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl border bg-card">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-purple-500/10">
                  <Users className="w-5 h-5 text-purple-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Active Users</p>
                  <p className="text-2xl font-bold">{formatNumber(mockStats.activeUsers)}</p>
                  <p className="text-xs text-muted-foreground">of {formatNumber(mockStats.totalUsers)} total</p>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl border bg-card">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-green-500/10">
                  <DollarSign className="w-5 h-5 text-green-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total Ad Spend</p>
                  <p className="text-2xl font-bold">{formatCurrency(mockStats.totalSpend)}</p>
                  <p className="text-xs text-green-500 flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" /> +18.5%
                  </p>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-xl border bg-card">
              <div className="flex items-center gap-3">
                <div className={cn('p-2 rounded-lg', getHealthColor(mockStats.systemHealth))}>
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">System Health</p>
                  <p className="text-2xl font-bold capitalize">{mockStats.systemHealth}</p>
                  <p className="text-xs text-muted-foreground">All services operational</p>
                </div>
              </div>
            </div>
          </div>

          {/* System Alerts */}
          <div className="rounded-xl border bg-card p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-primary" />
              System Alerts
            </h3>
            <div className="space-y-3">
              {mockAlerts.map(alert => (
                <div
                  key={alert.id}
                  className={cn(
                    'flex items-start gap-3 p-3 rounded-lg border',
                    alert.type === 'error' && 'bg-red-500/5 border-red-500/20',
                    alert.type === 'warning' && 'bg-amber-500/5 border-amber-500/20',
                    alert.type === 'info' && 'bg-blue-500/5 border-blue-500/20'
                  )}
                >
                  {alert.type === 'error' && <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />}
                  {alert.type === 'warning' && <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />}
                  {alert.type === 'info' && <CheckCircle2 className="w-5 h-5 text-blue-500 flex-shrink-0" />}
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

          {/* API Usage */}
          <div className="rounded-xl border bg-card p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-primary" />
              API Usage Today
              <span className="text-sm font-normal text-muted-foreground ml-2">
                {formatNumber(mockStats.apiRequestsToday)} requests
              </span>
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 font-medium">Endpoint</th>
                    <th className="text-right py-2 font-medium">Requests</th>
                    <th className="text-right py-2 font-medium">Avg Latency</th>
                    <th className="text-right py-2 font-medium">Errors</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {mockAPIUsage.map((api, idx) => (
                    <tr key={idx} className="hover:bg-muted/30">
                      <td className="py-3 font-mono text-xs">{api.endpoint}</td>
                      <td className="text-right">{formatNumber(api.requests)}</td>
                      <td className="text-right">
                        <span className={cn(api.avgLatency > 100 ? 'text-amber-500' : 'text-green-500')}>
                          {api.avgLatency}ms
                        </span>
                      </td>
                      <td className="text-right">
                        <span className={cn(api.errors > 0 ? 'text-red-500' : 'text-green-500')}>
                          {api.errors}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tenants Tab */}
      {activeTab === 'tenants' && (
        <div className="space-y-4">
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
              <option>Pro</option>
              <option>Starter</option>
            </select>
            <select className="px-3 py-2 rounded-lg border bg-background">
              <option>All Status</option>
              <option>Active</option>
              <option>Trial</option>
              <option>Suspended</option>
            </select>
          </div>

          {/* Tenants Table */}
          <div className="rounded-xl border bg-card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/30">
                <tr>
                  <th className="text-left py-3 px-4 font-medium">Tenant</th>
                  <th className="text-left py-3 px-4 font-medium">Plan</th>
                  <th className="text-center py-3 px-4 font-medium">Users</th>
                  <th className="text-center py-3 px-4 font-medium">Campaigns</th>
                  <th className="text-right py-3 px-4 font-medium">Monthly Spend</th>
                  <th className="text-center py-3 px-4 font-medium">Status</th>
                  <th className="text-right py-3 px-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredTenants.map(tenant => (
                  <tr key={tenant.id} className="hover:bg-muted/30">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-stratum flex items-center justify-center text-white font-bold">
                          {tenant.name.charAt(0)}
                        </div>
                        <div>
                          <p className="font-medium">{tenant.name}</p>
                          <p className="text-xs text-muted-foreground">Last active: {tenant.lastActive}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className={cn('px-2 py-1 rounded-full text-xs font-medium capitalize', getPlanBadge(tenant.plan))}>
                        {tenant.plan}
                      </span>
                    </td>
                    <td className="text-center py-3 px-4">{tenant.users}</td>
                    <td className="text-center py-3 px-4">{tenant.campaigns}</td>
                    <td className="text-right py-3 px-4 font-medium">{formatCurrency(tenant.monthlySpend)}</td>
                    <td className="text-center py-3 px-4">
                      <span className={cn('px-2 py-1 rounded-full text-xs font-medium capitalize', getStatusBadge(tenant.status))}>
                        {tenant.status}
                      </span>
                    </td>
                    <td className="text-right py-3 px-4">
                      <div className="flex items-center justify-end gap-1">
                        <button className="p-1.5 rounded hover:bg-muted" title="View">
                          <Eye className="w-4 h-4" />
                        </button>
                        <button className="p-1.5 rounded hover:bg-muted" title="Edit">
                          <Edit className="w-4 h-4" />
                        </button>
                        <button className="p-1.5 rounded hover:bg-muted text-red-500" title="Suspend">
                          <Ban className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div className="rounded-xl border bg-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold flex items-center gap-2">
              <Users className="w-5 h-5 text-primary" />
              User Management
            </h3>
            <button className="flex items-center gap-2 px-3 py-2 rounded-lg border hover:bg-muted transition-colors">
              <Plus className="w-4 h-4" />
              Add User
            </button>
          </div>
          <div className="text-center py-12 text-muted-foreground">
            <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>User management features coming soon</p>
            <p className="text-sm">Manage users across all tenants from here</p>
          </div>
        </div>
      )}

      {/* System Tab */}
      {activeTab === 'system' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Infrastructure Status */}
          <div className="rounded-xl border bg-card p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Server className="w-5 h-5 text-primary" />
              Infrastructure Status
            </h3>
            <div className="space-y-4">
              {[
                { name: 'API Server', status: 'healthy', cpu: 45, memory: 62 },
                { name: 'Worker Nodes', status: 'healthy', cpu: 78, memory: 84 },
                { name: 'Database', status: 'healthy', cpu: 23, memory: 56 },
                { name: 'Redis Cache', status: 'healthy', cpu: 12, memory: 45 },
                { name: 'ML Service', status: 'healthy', cpu: 67, memory: 71 },
              ].map((service, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                  <div className="flex items-center gap-3">
                    <div className={cn('w-2 h-2 rounded-full', service.status === 'healthy' ? 'bg-green-500' : 'bg-red-500')} />
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

          {/* Quick Actions */}
          <div className="rounded-xl border bg-card p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Settings className="w-5 h-5 text-primary" />
              Quick Actions
            </h3>
            <div className="grid grid-cols-2 gap-3">
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
                  className="flex items-center gap-3 p-3 rounded-lg border hover:bg-muted transition-colors"
                >
                  <action.icon className={cn('w-5 h-5', action.color)} />
                  <span className="text-sm font-medium">{action.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Billing Tab */}
      {activeTab === 'billing' && (
        <div className="rounded-xl border bg-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-primary" />
              Billing Overview
            </h3>
            <button className="flex items-center gap-2 px-3 py-2 rounded-lg border hover:bg-muted transition-colors">
              <DollarSign className="w-4 h-4" />
              Generate Invoice
            </button>
          </div>

          {/* Billing Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 rounded-lg bg-green-500/10">
              <p className="text-sm text-muted-foreground">Monthly Revenue</p>
              <p className="text-2xl font-bold text-green-500">$124,500</p>
              <p className="text-xs text-green-600 flex items-center gap-1 mt-1">
                <TrendingUp className="w-3 h-3" /> +12.5% from last month
              </p>
            </div>
            <div className="p-4 rounded-lg bg-blue-500/10">
              <p className="text-sm text-muted-foreground">Outstanding</p>
              <p className="text-2xl font-bold text-blue-500">$8,450</p>
              <p className="text-xs text-muted-foreground mt-1">3 pending invoices</p>
            </div>
            <div className="p-4 rounded-lg bg-amber-500/10">
              <p className="text-sm text-muted-foreground">Overdue</p>
              <p className="text-2xl font-bold text-amber-500">$2,100</p>
              <p className="text-xs text-amber-600 mt-1">1 tenant overdue</p>
            </div>
          </div>

          <div className="text-center py-8 text-muted-foreground">
            <PieChart className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Detailed billing features coming soon</p>
            <p className="text-sm">Revenue breakdown, invoice management, and more</p>
          </div>
        </div>
      )}
    </div>
  )
}
