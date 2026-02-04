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
} from './useTenantDashboard';

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
} from './useSuperAdmin';

// Re-export from API modules
export * from '../auth';
export * from '../emqV2';
export * from '../campaigns';
export * from '../assets';
export * from '../rules';
export * from '../competitors';
// Exclude AlertSeverity from predictions (already exported from pacing)
export {
  type PredictionType,
  type Prediction,
  type PredictionAlert,
  type BudgetOptimization,
  type Scenario,
  type CreateScenarioRequest,
  predictionsApi,
  useLivePredictions,
  useCampaignPredictions,
  usePredictionAlerts,
  useMarkAlertRead,
  useRefreshPredictions,
  useBudgetOptimization,
  useApplyBudgetOptimization,
  useScenarios,
  useScenario,
  useCreateScenario,
  useDeleteScenario,
} from '../predictions';
// Exclude User from admin (already exported from auth)
export {
  type UserRole,
  type TenantStatus,
  type PlanTier,
  type Tenant,
  type TenantWithMetrics,
  type UserFilters,
  type TenantFilters,
  type CreateUserRequest,
  type UpdateUserRequest,
  type CreateTenantRequest,
  type UpdateTenantRequest,
  adminApi,
  useUsers,
  useUser,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useResetUserPassword,
  useTenants,
  useTenant,
  useCreateTenant,
  useUpdateTenant,
  useDeleteTenant,
  useSuspendTenant,
  useReactivateTenant,
  useTenantUsers,
} from '../admin';
export * from '../gdpr';
export * from '../attribution';
export * from '../pacing';
export * from '../profit';
export * from '../reporting';
export * from '../abTesting';
