/**
 * Stratum AI - Super Admin Dashboard Hooks
 *
 * React Query hooks for super admin platform-level data.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse } from '../client'

// =============================================================================
// Types
// =============================================================================

export interface SuperAdminOverview {
  mrr: number
  arr: number
  nrr: number
  churn_rate: number
  churn_trend: string
  gross_margin_pct: number
  total_tenants: number
  active_tenants: number
  trial_tenants: number
  total_revenue_30d: number
  total_cost_30d: number
  revenue_growth_pct: number
}

export interface TenantSummary {
  id: number
  name: string
  slug: string
  plan: string
  status: string
  mrr: number
  user_count: number
  campaign_count: number
  platforms_connected: string[]
  last_activity_at: string | null
  data_freshness_hours: number | null
  emq_score: number | null
  open_alerts: number
  churn_risk: number
  created_at: string
}

export interface SystemHealth {
  status: string
  components: {
    api: { status: string; latency_ms: number }
    database: { status: string; connections_used: number; connections_max: number }
    redis: { status: string; memory_used_mb: number }
    celery: { status: string; workers_active: number; tasks_pending: number }
  }
  platform_apis: {
    meta: { status: string; last_sync: string | null }
    google: { status: string; last_sync: string | null }
    tiktok: { status: string; last_sync: string | null }
    snapchat: { status: string; last_sync: string | null }
  }
  ingestion: {
    events_24h: number
    avg_latency_ms: number
    error_rate_pct: number
  }
}

export interface BillingPlan {
  id: number
  name: string
  slug: string
  price_monthly: number
  price_annual: number
  max_users: number
  max_campaigns: number
  max_platforms: number
  features: string[]
  is_active: boolean
}

export interface AuditLogEntry {
  id: number
  timestamp: string
  action: string
  user_id: number | null
  user_email: string | null
  tenant_id: number | null
  tenant_name: string | null
  resource_type: string | null
  resource_id: string | null
  details: Record<string, unknown>
  ip_address: string | null
  status: string
}

export interface Invoice {
  id: number
  tenant_id: number
  tenant_name: string
  amount: number
  currency: string
  status: string
  due_date: string
  paid_at: string | null
  stripe_invoice_id: string | null
}

export interface Subscription {
  id: number
  tenant_id: number
  tenant_name: string
  plan_id: number
  plan_name: string
  status: string
  current_period_start: string
  current_period_end: string
  cancel_at_period_end: boolean
  mrr: number
}

// =============================================================================
// Query Keys
// =============================================================================

export const superAdminQueryKeys = {
  all: ['superadmin'] as const,
  overview: (date?: string) => [...superAdminQueryKeys.all, 'overview', date] as const,
  tenants: (filters?: Record<string, unknown>) =>
    [...superAdminQueryKeys.all, 'tenants', filters] as const,
  tenant: (tenantId: number) => [...superAdminQueryKeys.all, 'tenant', tenantId] as const,
  systemHealth: (date?: string) =>
    [...superAdminQueryKeys.all, 'systemHealth', date] as const,
  plans: () => [...superAdminQueryKeys.all, 'plans'] as const,
  auditLogs: (filters?: Record<string, unknown>) =>
    [...superAdminQueryKeys.all, 'auditLogs', filters] as const,
  invoices: (filters?: Record<string, unknown>) =>
    [...superAdminQueryKeys.all, 'invoices', filters] as const,
  subscriptions: (filters?: Record<string, unknown>) =>
    [...superAdminQueryKeys.all, 'subscriptions', filters] as const,
}

// =============================================================================
// API Functions
// =============================================================================

const fetchSuperAdminOverview = async (date?: string): Promise<SuperAdminOverview> => {
  const params = date ? `?date=${date}` : ''
  const response = await apiClient.get<ApiResponse<SuperAdminOverview>>(
    `/superadmin/overview${params}`
  )
  return response.data.data
}

const fetchTenants = async (filters?: {
  sort?: string
  status?: string
  plan?: string
  skip?: number
  limit?: number
}): Promise<TenantSummary[]> => {
  const params = new URLSearchParams()
  if (filters?.sort) params.append('sort', filters.sort)
  if (filters?.status) params.append('status', filters.status)
  if (filters?.plan) params.append('plan', filters.plan)
  if (filters?.skip) params.append('skip', String(filters.skip))
  if (filters?.limit) params.append('limit', String(filters.limit))

  const response = await apiClient.get<ApiResponse<TenantSummary[]>>(
    `/superadmin/tenants?${params.toString()}`
  )
  return response.data.data
}

const fetchTenantDetails = async (tenantId: number): Promise<TenantSummary & Record<string, unknown>> => {
  const response = await apiClient.get<ApiResponse<TenantSummary & Record<string, unknown>>>(`/superadmin/tenants/${tenantId}`)
  return response.data.data
}

const fetchSystemHealth = async (date?: string): Promise<SystemHealth> => {
  const params = date ? `?date=${date}` : ''
  const response = await apiClient.get<ApiResponse<SystemHealth>>(
    `/superadmin/system-health${params}`
  )
  return response.data.data
}

const fetchBillingPlans = async (): Promise<BillingPlan[]> => {
  const response = await apiClient.get<ApiResponse<BillingPlan[]>>('/superadmin/billing/plans')
  return response.data.data
}

const updateBillingPlan = async (
  planId: number,
  data: Partial<BillingPlan>
): Promise<BillingPlan> => {
  const response = await apiClient.patch<ApiResponse<BillingPlan>>(
    `/superadmin/billing/plans/${planId}`,
    data
  )
  return response.data.data
}

const fetchAuditLogs = async (filters?: {
  tenant_id?: number
  action?: string
  user_id?: number
  start_date?: string
  end_date?: string
  skip?: number
  limit?: number
}): Promise<AuditLogEntry[]> => {
  const params = new URLSearchParams()
  if (filters?.tenant_id) params.append('tenant_id', String(filters.tenant_id))
  if (filters?.action) params.append('action', filters.action)
  if (filters?.user_id) params.append('user_id', String(filters.user_id))
  if (filters?.start_date) params.append('start_date', filters.start_date)
  if (filters?.end_date) params.append('end_date', filters.end_date)
  if (filters?.skip) params.append('skip', String(filters.skip))
  if (filters?.limit) params.append('limit', String(filters.limit))

  const response = await apiClient.get<ApiResponse<AuditLogEntry[]>>(
    `/superadmin/audit?${params.toString()}`
  )
  return response.data.data
}

const fetchInvoices = async (filters?: {
  tenant_id?: number
  status?: string
  skip?: number
  limit?: number
}): Promise<Invoice[]> => {
  const params = new URLSearchParams()
  if (filters?.tenant_id) params.append('tenant_id', String(filters.tenant_id))
  if (filters?.status) params.append('status', filters.status)
  if (filters?.skip) params.append('skip', String(filters.skip))
  if (filters?.limit) params.append('limit', String(filters.limit))

  const response = await apiClient.get<ApiResponse<Invoice[]>>(
    `/superadmin/billing/invoices?${params.toString()}`
  )
  return response.data.data
}

const fetchSubscriptions = async (filters?: {
  status?: string
  plan_id?: number
  skip?: number
  limit?: number
}): Promise<Subscription[]> => {
  const params = new URLSearchParams()
  if (filters?.status) params.append('status', filters.status)
  if (filters?.plan_id) params.append('plan_id', String(filters.plan_id))
  if (filters?.skip) params.append('skip', String(filters.skip))
  if (filters?.limit) params.append('limit', String(filters.limit))

  const response = await apiClient.get<ApiResponse<Subscription[]>>(
    `/superadmin/billing/subscriptions?${params.toString()}`
  )
  return response.data.data
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to fetch super admin overview data.
 */
export function useSuperAdminOverview(date?: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: superAdminQueryKeys.overview(date),
    queryFn: () => fetchSuperAdminOverview(date),
    enabled: options?.enabled !== false,
    staleTime: 1000 * 60 * 2, // 2 minutes
  })
}

/**
 * Hook to fetch tenants list.
 */
export function useSuperAdminTenants(
  filters?: {
    sort?: string
    status?: string
    plan?: string
    skip?: number
    limit?: number
  },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: superAdminQueryKeys.tenants(filters),
    queryFn: () => fetchTenants(filters),
    enabled: options?.enabled !== false,
    staleTime: 1000 * 60, // 1 minute
  })
}

/**
 * Hook to fetch single tenant details.
 */
export function useSuperAdminTenantDetails(
  tenantId: number,
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: superAdminQueryKeys.tenant(tenantId),
    queryFn: () => fetchTenantDetails(tenantId),
    enabled: options?.enabled !== false && !!tenantId,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })
}

/**
 * Hook to fetch system health data.
 */
export function useSuperAdminSystemHealth(date?: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: superAdminQueryKeys.systemHealth(date),
    queryFn: () => fetchSystemHealth(date),
    enabled: options?.enabled !== false,
    refetchInterval: 1000 * 30, // 30 seconds
    staleTime: 1000 * 15, // 15 seconds
  })
}

/**
 * Hook to fetch billing plans.
 */
export function useSuperAdminBillingPlans(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: superAdminQueryKeys.plans(),
    queryFn: () => fetchBillingPlans(),
    enabled: options?.enabled !== false,
    staleTime: 1000 * 60 * 10, // 10 minutes
  })
}

/**
 * Hook to update a billing plan.
 */
export function useUpdateBillingPlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ planId, data }: { planId: number; data: Partial<BillingPlan> }) =>
      updateBillingPlan(planId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: superAdminQueryKeys.plans() })
    },
  })
}

/**
 * Hook to fetch audit logs.
 */
export function useAuditLogs(
  filters?: {
    tenant_id?: number
    action?: string
    user_id?: number
    start_date?: string
    end_date?: string
    skip?: number
    limit?: number
  },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: superAdminQueryKeys.auditLogs(filters),
    queryFn: () => fetchAuditLogs(filters),
    enabled: options?.enabled !== false,
    staleTime: 1000 * 30, // 30 seconds
  })
}

/**
 * Hook to fetch invoices.
 */
export function useSuperAdminInvoices(
  filters?: {
    tenant_id?: number
    status?: string
    skip?: number
    limit?: number
  },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: superAdminQueryKeys.invoices(filters),
    queryFn: () => fetchInvoices(filters),
    enabled: options?.enabled !== false,
    staleTime: 1000 * 60, // 1 minute
  })
}

/**
 * Hook to fetch subscriptions.
 */
export function useSuperAdminSubscriptions(
  filters?: {
    status?: string
    plan_id?: number
    skip?: number
    limit?: number
  },
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: superAdminQueryKeys.subscriptions(filters),
    queryFn: () => fetchSubscriptions(filters),
    enabled: options?.enabled !== false,
    staleTime: 1000 * 60, // 1 minute
  })
}
