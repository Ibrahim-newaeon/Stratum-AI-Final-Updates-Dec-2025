/**
 * Stratum AI - React Query Hooks
 *
 * Centralized exports for all API hooks.
 */

// Tenant Dashboard hooks
export {
  useTenantOverview,
  useTenantRecommendations,
  useTenantAlerts,
  useTenantSettings,
  useUpdateTenantSettings,
  useAcknowledgeAlert,
  useResolveAlert,
  useCommandCenter,
  tenantQueryKeys,
  type DashboardOverview,
  type Recommendation,
  type Alert,
  type TenantSettings,
  type CommandCenterItem,
  type CommandCenterResponse,
} from './useTenantDashboard'

// Super Admin hooks
export {
  useSuperAdminOverview,
  useSuperAdminTenants,
  useSuperAdminTenantDetails,
  useSuperAdminSystemHealth,
  useSuperAdminBillingPlans,
  useUpdateBillingPlan,
  useAuditLogs,
  useSuperAdminInvoices,
  useSuperAdminSubscriptions,
  superAdminQueryKeys,
  type SuperAdminOverview,
  type TenantSummary,
  type SystemHealth,
  type BillingPlan,
  type AuditLogEntry,
  type Invoice,
  type Subscription,
} from './useSuperAdmin'

// Re-export from API modules
export * from '../auth'
export * from '../emqV2'
export * from '../campaigns'
export * from '../assets'
export * from '../rules'
export * from '../competitors'
export * from '../predictions'
export * from '../admin'
export * from '../gdpr'
