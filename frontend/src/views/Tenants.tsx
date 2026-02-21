import { useState, useEffect, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Building2,
  Plus,
  Search,
  Edit,
  Trash2,
  Users,
  Crown,
  ChevronDown,
  MoreHorizontal,
  X,
  AlertTriangle,
  Calendar,
  Settings,
  Shield,
  RefreshCw,
  Filter,
  Globe,
  Zap,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { apiClient } from '@/api/client'

// Types
interface Tenant {
  id: number
  name: string
  slug: string
  domain: string | null
  plan: 'free' | 'starter' | 'professional' | 'enterprise'
  plan_expires_at: string | null
  max_users: number
  max_campaigns: number
  settings: Record<string, unknown>
  feature_flags: Record<string, boolean>
  created_at: string
  updated_at: string
  user_count?: number
}

interface TenantFormData {
  name: string
  slug: string
  domain: string
  plan: 'free' | 'starter' | 'professional' | 'enterprise'
}

const planConfig = {
  free: { color: 'bg-gray-500', label: 'Free', limits: { users: 5, campaigns: 10 } },
  starter: { color: 'bg-blue-500', label: 'Starter', limits: { users: 10, campaigns: 50 } },
  professional: { color: 'bg-purple-500', label: 'Professional', limits: { users: 25, campaigns: 200 } },
  enterprise: { color: 'bg-amber-500', label: 'Enterprise', limits: { users: 100, campaigns: 1000 } },
}

const featureFlags = [
  { key: 'advanced_analytics', label: 'Advanced Analytics', description: 'Deep dive analytics and custom reports' },
  { key: 'ai_insights', label: 'AI Insights', description: 'AI-powered campaign recommendations' },
  { key: 'white_label', label: 'White Label', description: 'Custom branding and domain' },
  { key: 'api_access', label: 'API Access', description: 'Full REST API access' },
  { key: 'sso', label: 'Single Sign-On', description: 'SAML/OAuth SSO integration' },
  { key: 'audit_logs', label: 'Audit Logs', description: 'Detailed activity logging' },
]

export function Tenants() {
  const { t: _t } = useTranslation()
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [planFilter, setPlanFilter] = useState<string>('all')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showFeaturesModal, setShowFeaturesModal] = useState(false)
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<'name' | 'created_at' | 'user_count'>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  // Fetch tenants from API
  const fetchTenants = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await apiClient.get('/tenants', {
        params: { limit: 100 },
      })
      const data = response.data?.data || response.data || []
      setTenants(Array.isArray(data) ? data : [])
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string; error?: string } }; message?: string };
      const message = axiosErr?.response?.data?.detail || axiosErr?.response?.data?.error || axiosErr?.message || 'Failed to load tenants'
      setError(message)
      setTenants([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTenants()
  }, [fetchTenants])

  // Filter and sort tenants
  const filteredTenants = useMemo(() => {
    let result = [...tenants]

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(query) ||
          t.slug.toLowerCase().includes(query) ||
          t.domain?.toLowerCase().includes(query)
      )
    }

    // Apply plan filter
    if (planFilter !== 'all') {
      result = result.filter((t) => t.plan === planFilter)
    }

    // Apply sorting
    result.sort((a, b) => {
      let comparison = 0
      if (sortBy === 'name') {
        comparison = a.name.localeCompare(b.name)
      } else if (sortBy === 'created_at') {
        comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      } else if (sortBy === 'user_count') {
        comparison = (a.user_count || 0) - (b.user_count || 0)
      }
      return sortOrder === 'asc' ? comparison : -comparison
    })

    return result
  }, [tenants, searchQuery, planFilter, sortBy, sortOrder])

  // Stats
  const stats = useMemo(() => {
    return {
      total: tenants.length,
      enterprise: tenants.filter((t) => t.plan === 'enterprise').length,
      professional: tenants.filter((t) => t.plan === 'professional').length,
      starter: tenants.filter((t) => t.plan === 'starter').length,
      free: tenants.filter((t) => t.plan === 'free').length,
      totalUsers: tenants.reduce((sum, t) => sum + (t.user_count || 0), 0),
    }
  }, [tenants])

  const handleCreateTenant = async (data: TenantFormData) => {
    try {
      await apiClient.post('/tenants', {
        name: data.name,
        slug: data.slug,
        domain: data.domain || null,
        plan: data.plan,
      })
      setShowCreateModal(false)
      fetchTenants()
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr?.response?.data?.detail || 'Failed to create tenant'
      alert(message)
    }
  }

  const handleUpdateTenant = async (data: TenantFormData) => {
    if (!selectedTenant) return
    try {
      await apiClient.patch(`/api/v1/tenants/${selectedTenant.id}`, {
        name: data.name,
        slug: data.slug,
        domain: data.domain || null,
        plan: data.plan,
      })
      setShowEditModal(false)
      setSelectedTenant(null)
      fetchTenants()
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr?.response?.data?.detail || 'Failed to update tenant'
      alert(message)
    }
  }

  const handleDeleteTenant = async () => {
    if (!selectedTenant) return
    try {
      await apiClient.delete(`/api/v1/tenants/${selectedTenant.id}`)
      setShowDeleteModal(false)
      setSelectedTenant(null)
      fetchTenants()
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr?.response?.data?.detail || 'Failed to delete tenant'
      alert(message)
    }
  }

  const handleUpdateFeatures = async (features: Record<string, boolean>) => {
    if (!selectedTenant) return
    try {
      await apiClient.patch(`/tenants/${selectedTenant.id}/features`, features)
      setShowFeaturesModal(false)
      setSelectedTenant(null)
      fetchTenants()
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      const message = axiosErr?.response?.data?.detail || 'Failed to update features'
      alert(message)
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
          <p className="text-muted-foreground">Loading tenants...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4 max-w-md">
          <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto">
            <AlertTriangle className="h-6 w-6 text-red-500" />
          </div>
          <h2 className="text-lg font-semibold">Failed to Load Tenants</h2>
          <p className="text-muted-foreground text-sm">{error}</p>
          <button
            onClick={fetchTenants}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Building2 className="h-7 w-7 text-primary" />
            Tenant Management
          </h1>
          <p className="text-muted-foreground">Manage organizations and their subscriptions</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchTenants}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border hover:bg-muted transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Tenant
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatsCard icon={Building2} label="Total Tenants" value={stats.total} />
        <StatsCard icon={Crown} label="Enterprise" value={stats.enterprise} color="amber" />
        <StatsCard icon={Zap} label="Professional" value={stats.professional} color="purple" />
        <StatsCard icon={Shield} label="Starter" value={stats.starter} color="blue" />
        <StatsCard icon={Globe} label="Free" value={stats.free} color="gray" />
        <StatsCard icon={Users} label="Total Users" value={stats.totalUsers} color="green" />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search tenants by name, slug, or domain..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={planFilter}
            onChange={(e) => setPlanFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All Plans</option>
            <option value="enterprise">Enterprise</option>
            <option value="professional">Professional</option>
            <option value="starter">Starter</option>
            <option value="free">Free</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="px-3 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="name">Sort by Name</option>
            <option value="created_at">Sort by Created</option>
            <option value="user_count">Sort by Users</option>
          </select>
          <button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            className="p-2 rounded-lg border hover:bg-muted transition-colors"
          >
            <ChevronDown className={cn('h-4 w-4 transition-transform', sortOrder === 'asc' && 'rotate-180')} />
          </button>
        </div>
      </div>

      {/* Tenants Table */}
      <div className="rounded-xl border bg-card overflow-hidden">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium">Organization</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Plan</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Users</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Features</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Created</th>
              <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {filteredTenants.map((tenant) => (
              <TenantRow
                key={tenant.id}
                tenant={tenant}
                onEdit={() => {
                  setSelectedTenant(tenant)
                  setShowEditModal(true)
                }}
                onDelete={() => {
                  setSelectedTenant(tenant)
                  setShowDeleteModal(true)
                }}
                onManageFeatures={() => {
                  setSelectedTenant(tenant)
                  setShowFeaturesModal(true)
                }}
              />
            ))}
            {filteredTenants.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-muted-foreground">
                  {tenants.length === 0
                    ? 'No tenants found. Create your first tenant to get started.'
                    : 'No tenants found matching your criteria'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <TenantFormModal
          title="Create New Tenant"
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateTenant}
        />
      )}

      {/* Edit Modal */}
      {showEditModal && selectedTenant && (
        <TenantFormModal
          title="Edit Tenant"
          tenant={selectedTenant}
          onClose={() => {
            setShowEditModal(false)
            setSelectedTenant(null)
          }}
          onSubmit={handleUpdateTenant}
        />
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && selectedTenant && (
        <DeleteConfirmModal
          tenant={selectedTenant}
          onClose={() => {
            setShowDeleteModal(false)
            setSelectedTenant(null)
          }}
          onConfirm={handleDeleteTenant}
        />
      )}

      {/* Features Modal */}
      {showFeaturesModal && selectedTenant && (
        <FeaturesModal
          tenant={selectedTenant}
          onClose={() => {
            setShowFeaturesModal(false)
            setSelectedTenant(null)
          }}
          onSave={handleUpdateFeatures}
        />
      )}
    </div>
  )
}

// Stats Card Component
function StatsCard({
  icon: Icon,
  label,
  value,
  color = 'primary',
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  color?: string
}) {
  const colorClasses: Record<string, string> = {
    primary: 'bg-primary/10 text-primary',
    amber: 'bg-amber-500/10 text-amber-500',
    purple: 'bg-purple-500/10 text-purple-500',
    blue: 'bg-blue-500/10 text-blue-500',
    gray: 'bg-gray-500/10 text-gray-500',
    green: 'bg-green-500/10 text-green-500',
  }

  return (
    <div className="p-4 rounded-xl border bg-card">
      <div className="flex items-center gap-3">
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </div>
    </div>
  )
}

// Tenant Row Component
function TenantRow({
  tenant,
  onEdit,
  onDelete,
  onManageFeatures,
}: {
  tenant: Tenant
  onEdit: () => void
  onDelete: () => void
  onManageFeatures: () => void
}) {
  const [showMenu, setShowMenu] = useState(false)
  const plan = planConfig[tenant.plan]
  const enabledFeatures = Object.values(tenant.feature_flags).filter(Boolean).length

  return (
    <tr className="hover:bg-muted/30 transition-colors">
      <td className="px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary font-semibold">
            {tenant.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="font-medium">{tenant.name}</p>
            <p className="text-sm text-muted-foreground">{tenant.slug}</p>
            {tenant.domain && <p className="text-xs text-primary">{tenant.domain}</p>}
          </div>
        </div>
      </td>
      <td className="px-4 py-4">
        <span className={cn('px-2 py-1 rounded-full text-xs font-medium text-white', plan.color)}>
          {plan.label}
        </span>
        {tenant.plan_expires_at && (
          <p className="text-xs text-muted-foreground mt-1">
            Expires: {new Date(tenant.plan_expires_at).toLocaleDateString()}
          </p>
        )}
      </td>
      <td className="px-4 py-4">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-muted-foreground" />
          <span>
            {tenant.user_count || 0} / {tenant.max_users}
          </span>
        </div>
        <div className="w-24 h-1.5 bg-muted rounded-full mt-1">
          <div
            className="h-full bg-primary rounded-full"
            style={{ width: `${Math.min(100, ((tenant.user_count || 0) / tenant.max_users) * 100)}%` }}
          />
        </div>
      </td>
      <td className="px-4 py-4">
        <button onClick={onManageFeatures} className="flex items-center gap-2 text-sm hover:text-primary transition-colors">
          <Zap className="h-4 w-4" />
          {enabledFeatures} enabled
        </button>
      </td>
      <td className="px-4 py-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="h-4 w-4" />
          {new Date(tenant.created_at).toLocaleDateString()}
        </div>
      </td>
      <td className="px-4 py-4 text-right">
        <div className="relative inline-block">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <MoreHorizontal className="h-4 w-4" />
          </button>
          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 top-full mt-1 w-48 rounded-lg border bg-card shadow-lg z-20">
                <button
                  onClick={() => {
                    setShowMenu(false)
                    onEdit()
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted transition-colors"
                >
                  <Edit className="h-4 w-4" />
                  Edit Tenant
                </button>
                <button
                  onClick={() => {
                    setShowMenu(false)
                    onManageFeatures()
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-muted transition-colors"
                >
                  <Settings className="h-4 w-4" />
                  Manage Features
                </button>
                <hr className="my-1" />
                <button
                  onClick={() => {
                    setShowMenu(false)
                    onDelete()
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete Tenant
                </button>
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

// Tenant Form Modal
function TenantFormModal({
  title,
  tenant,
  onClose,
  onSubmit,
}: {
  title: string
  tenant?: Tenant
  onClose: () => void
  onSubmit: (data: TenantFormData) => void
}) {
  const [formData, setFormData] = useState<TenantFormData>({
    name: tenant?.name || '',
    slug: tenant?.slug || '',
    domain: tenant?.domain || '',
    plan: tenant?.plan || 'free',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
  }

  const handleNameChange = (name: string) => {
    setFormData({
      ...formData,
      name,
      slug: tenant ? formData.slug : generateSlug(name),
    })
  }

  const validate = () => {
    const newErrors: Record<string, string> = {}
    if (!formData.name.trim()) newErrors.name = 'Name is required'
    if (!formData.slug.trim()) newErrors.slug = 'Slug is required'
    if (formData.slug && !/^[a-z0-9-]+$/.test(formData.slug)) {
      newErrors.slug = 'Slug can only contain lowercase letters, numbers, and hyphens'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validate()) {
      onSubmit(formData)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg bg-card rounded-xl shadow-xl border">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Organization Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleNameChange(e.target.value)}
              className={cn(
                'w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20',
                errors.name && 'border-red-500'
              )}
              placeholder="Acme Corporation"
            />
            {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Slug *</label>
            <input
              type="text"
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase() })}
              className={cn(
                'w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20',
                errors.slug && 'border-red-500'
              )}
              placeholder="acme-corp"
            />
            {errors.slug && <p className="text-xs text-red-500 mt-1">{errors.slug}</p>}
            <p className="text-xs text-muted-foreground mt-1">Used in URLs: {formData.slug || 'slug'}.stratum.ai</p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Custom Domain</label>
            <input
              type="text"
              value={formData.domain}
              onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
              className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
              placeholder="dashboard.company.com"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Subscription Plan</label>
            <div className="grid grid-cols-2 gap-2">
              {(Object.entries(planConfig) as [keyof typeof planConfig, typeof planConfig.free][]).map(
                ([key, config]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setFormData({ ...formData, plan: key })}
                    className={cn(
                      'p-3 rounded-lg border text-left transition-colors',
                      formData.plan === key
                        ? 'border-primary bg-primary/10'
                        : 'hover:bg-muted'
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className={cn('w-2 h-2 rounded-full', config.color)} />
                      <span className="font-medium">{config.label}</span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {config.limits.users} users, {config.limits.campaigns} campaigns
                    </p>
                  </button>
                )
              )}
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              {tenant ? 'Save Changes' : 'Create Tenant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Delete Confirmation Modal
function DeleteConfirmModal({
  tenant,
  onClose,
  onConfirm,
}: {
  tenant: Tenant
  onClose: () => void
  onConfirm: () => void
}) {
  const [confirmText, setConfirmText] = useState('')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md bg-card rounded-xl shadow-xl border">
        <div className="p-6 text-center">
          <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="h-6 w-6 text-red-500" />
          </div>
          <h2 className="text-lg font-semibold mb-2">Delete Tenant</h2>
          <p className="text-muted-foreground mb-4">
            Are you sure you want to delete <strong>{tenant.name}</strong>? This action cannot be undone and will delete
            all associated data.
          </p>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1 text-left">
              Type "{tenant.slug}" to confirm
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-red-500/20"
              placeholder={tenant.slug}
            />
          </div>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={confirmText !== tenant.slug}
              className="flex-1 px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Delete Tenant
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Features Modal
function FeaturesModal({
  tenant,
  onClose,
  onSave,
}: {
  tenant: Tenant
  onClose: () => void
  onSave: (features: Record<string, boolean>) => void
}) {
  const [features, setFeatures] = useState<Record<string, boolean>>(
    featureFlags.reduce(
      (acc, flag) => ({
        ...acc,
        [flag.key]: tenant.feature_flags[flag.key] || false,
      }),
      {}
    )
  )

  const toggleFeature = (key: string) => {
    setFeatures({ ...features, [key]: !features[key] })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-lg bg-card rounded-xl shadow-xl border">
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h2 className="text-lg font-semibold">Feature Flags</h2>
            <p className="text-sm text-muted-foreground">{tenant.name}</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-4 space-y-3 max-h-96 overflow-y-auto">
          {featureFlags.map((flag) => (
            <div
              key={flag.key}
              className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted/30 transition-colors"
            >
              <div>
                <p className="font-medium">{flag.label}</p>
                <p className="text-sm text-muted-foreground">{flag.description}</p>
              </div>
              <button
                onClick={() => toggleFeature(flag.key)}
                className={cn(
                  'relative w-12 h-6 rounded-full transition-colors',
                  features[flag.key] ? 'bg-primary' : 'bg-muted'
                )}
              >
                <span
                  className={cn(
                    'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                    features[flag.key] ? 'translate-x-7' : 'translate-x-1'
                  )}
                />
              </button>
            </div>
          ))}
        </div>

        <div className="flex gap-3 p-4 border-t">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave(features)}
            className="flex-1 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Save Features
          </button>
        </div>
      </div>
    </div>
  )
}

export default Tenants
