/**
 * Stratum AI - API Hooks
 *
 * Centralized barrel file that re-exports all API hooks
 * and adds new hooks for superadmin endpoints.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse, PaginatedResponse } from './client';

// =============================================================================
// Re-exports from other API files
// =============================================================================

// EMQ V2 hooks
export {
  useEmqScore,
  useConfidence,
  useEmqPlaybook,
  useUpdatePlaybookItem,
  useEmqIncidents,
  useEmqImpact,
  useEmqVolatility,
  useAutopilotState,
  useUpdateAutopilotMode,
  useEmqBenchmarks,
  useEmqPortfolio,
} from './emqV2';

// Admin hooks
export {
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
} from './admin';

// Superadmin Analytics hooks
export {
  usePlatformOverview,
  useTenantProfitability,
  useSignalHealthTrends,
  useActionsAnalytics,
} from './superadminAnalytics';

// Competitors hooks
export {
  useCompetitors,
  useCompetitor,
  useCreateCompetitor,
  useUpdateCompetitor,
  useDeleteCompetitor,
  useShareOfVoice,
  useCompetitorKeywords,
  useCompetitorMetrics,
  useRefreshCompetitor,
} from './competitors';

// Predictions hooks
export {
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
} from './predictions';

// Insights hooks
export { useInsights, useRecommendations, useAnomalies, useKPIs } from './insights';

// Trust Layer hooks
export {
  useSignalHealth,
  useSignalHealthHistory,
  useSignalHealthHistoryDetailed,
  useAttributionVariance,
  useTrustStatus,
  useTrustGateAuditLogs,
} from './trustLayer';

// Autopilot hooks
export {
  useAutopilotStatus,
  useAutopilotActions,
  useActionsSummary,
  useAutopilotAction,
  useQueueAction,
  useApproveAction,
  useApproveAllActions,
  useDismissAction,
  useDryRunAction,
} from './autopilot';

// Campaigns hooks
export {
  useCampaigns,
  useCampaign,
  useCreateCampaign,
  useUpdateCampaign,
  useDeleteCampaign,
  useCampaignMetrics,
  useSyncCampaign,
  useBulkUpdateCampaignStatus,
  usePauseCampaign,
  useActivateCampaign,
} from './campaigns';

// Assets hooks
export {
  useAssets,
  useAsset,
  useCreateAsset,
  useUploadAsset,
  useUpdateAsset,
  useDeleteAsset,
  useAssetFolders,
  useCreateFolder,
  useFatiguedAssets,
  useCalculateFatigue,
  useBulkArchiveAssets,
} from './assets';

// Rules hooks
export {
  useRules,
  useRule,
  useCreateRule,
  useUpdateRule,
  useDeleteRule,
  useToggleRule,
  useExecuteRule,
  useRuleExecutions,
  useRuleTemplates,
  useValidateConditions,
} from './rules';

// Feature flags hooks
export {
  useFeatureFlags,
  useUpdateFeatureFlags,
  useSuperadminFeatureFlags,
  useSuperadminUpdateFeatureFlags,
  useSuperadminResetFeatureFlags,
} from './featureFlags';

// GDPR hooks (exclude useAuditLogs since we have our own)
export {
  useExportData,
  useExportStatus,
  useExportHistory,
  useAnonymizeData,
  useAnonymizationStatus,
  useConsentRecords,
  useUpdateConsent,
  useDataCategories,
  useRequestDeletion,
  useCancelDeletion,
} from './gdpr';

// CRM/HubSpot Integration hooks
export {
  useCRMConnections,
  useCRMConnection,
  useConnectHubSpot,
  useDisconnectCRM,
  useTriggerCRMSync,
  useCRMContacts,
  useCRMContact,
  useContactJourney,
  useCRMDeals,
  useCRMDeal,
  usePipelineMetrics,
  usePipelineSummary,
  useWritebackConfig,
  useUpdateWritebackConfig,
  useWritebackHistory,
  useRetryWriteback,
} from './crm';

// Pacing & Forecasting hooks
export {
  useTargets,
  useTarget,
  useCreateTarget,
  useUpdateTarget,
  useDeleteTarget,
  usePacingStatus,
  useAllPacingStatus,
  usePacingSummary,
  useDailyKPIs,
  useForecast,
  useMetricForecast,
  useGenerateForecast,
  usePacingAlerts,
  usePacingAlert,
  useAcknowledgeAlert,
  useResolveAlert,
  useDismissAlert,
  useAlertStats,
} from './pacing';

// Profit ROAS hooks
export {
  useProducts,
  useProduct,
  useCreateProduct,
  useUpdateProduct,
  useDeleteProduct,
  useImportProducts,
  useProductMargins,
  useSetProductMargin,
  useMarginRules,
  useMarginRule,
  useCreateMarginRule,
  useUpdateMarginRule,
  useDeleteMarginRule,
  useUploadCOGS,
  useCOGSUploads,
  useCOGSUpload,
  useDailyProfitMetrics,
  useProfitSummary,
  useGenerateProfitReport,
  useProfitReports,
  useProfitReport,
  useTrueROAS,
} from './profit';

// Attribution hooks
export {
  useAttributionSummary,
  useDailyAttributedRevenue,
  useChannelTransitions,
  useTopConversionPaths,
  useAssistedConversions,
  useTimeLagReport,
  useTrainedModels,
  useTrainedModel,
  useTrainMarkovModel,
  useTrainShapleyModel,
  useCompareModels,
  useArchiveModel,
  useActivateModel,
} from './attribution';

// Reporting hooks
export {
  useReportTemplates,
  useReportTemplate,
  useCreateReportTemplate,
  useUpdateReportTemplate,
  useDeleteReportTemplate,
  useReportSchedules,
  useReportSchedule,
  useCreateReportSchedule,
  useUpdateReportSchedule,
  useDeleteReportSchedule,
  usePauseReportSchedule,
  useResumeReportSchedule,
  useGenerateReport,
  useReportExecutions,
  useReportExecution,
  useDeliveryStatus,
  useDeliveryChannelConfigs,
  useUpdateDeliveryChannelConfig,
  useVerifyDeliveryChannel,
} from './reporting';

// Tenant Dashboard hooks
export { useUpdateTenantSettings, useTestSlackWebhook } from './hooks/useTenantDashboard';

// Onboarding hooks
export {
  useOnboardingStatus,
  useOnboardingCheck,
  useSubmitBusinessProfile,
  useSubmitPlatformSelection,
  useSubmitGoalsSetup,
  useSubmitAutomationPreferences,
  useSubmitTrustGateConfig,
  useSkipOnboarding,
  useResetOnboarding,
} from './onboarding';

// Dashboard hooks
export {
  useDashboardOverview,
  useDashboardCampaigns,
  useDashboardRecommendations,
  useApproveRecommendation,
  useRejectRecommendation,
  useDashboardActivity,
  useDashboardQuickActions,
  useDashboardSignalHealth,
} from './dashboard';

// CDP (Customer Data Platform) hooks
export {
  // API client and types
  cdpApi,
  cdpQueryKeys,
  createTracker,
  // Profile hooks
  useCDPProfile,
  useCDPProfileLookup,
  useDeleteProfile,
  useSearchProfiles,
  useSearchProfilesMutation,
  useProfileStatistics,
  // Source hooks
  useCDPSources,
  useCreateSource,
  // Event hooks
  useIngestEvents,
  useIngestEvent,
  useEventStatistics,
  useEventTrends,
  // Health hook
  useCDPHealth,
  // Webhook hooks
  useCDPWebhooks,
  useCDPWebhook,
  useCreateWebhook,
  useUpdateWebhook,
  useDeleteWebhook,
  useTestWebhook,
  useRotateWebhookSecret,
  // Anomaly hooks
  useEventAnomalies,
  useAnomalySummary,
  // Identity Graph hooks
  useIdentityGraph,
  useCanonicalIdentity,
  useProfileMergeHistory,
  useMergeHistory,
  useIdentityLinks,
  useMergeProfiles,
  // Segment hooks
  useSegments,
  useSegment,
  useCreateSegment,
  useUpdateSegment,
  useDeleteSegment,
  useComputeSegment,
  usePreviewSegment,
  useSegmentProfiles,
  useProfileSegments,
  // Computed Traits hooks
  useComputedTraits,
  useComputedTrait,
  useCreateComputedTrait,
  useDeleteComputedTrait,
  useComputeAllTraits,
  // RFM hooks
  useProfileRFM,
  useComputeRFMBatch,
  useRFMSummary,
  // Funnel hooks
  useFunnels,
  useFunnel,
  useCreateFunnel,
  useUpdateFunnel,
  useDeleteFunnel,
  useComputeFunnel,
  useAnalyzeFunnel,
  useFunnelDropOffs,
  useProfileFunnelJourneys,
  // Export hooks
  useExportAudience,
  // Type exports
  type IdentifierType,
  type IdentifierInput,
  type Identifier,
  type EventInput,
  type EventBatchInput,
  type EventBatchResponse,
  type CDPEvent,
  type CDPProfile,
  type ProfileListResponse,
  type CDPSource,
  type SourceCreate,
  type SourceListResponse,
  type CDPWebhook,
  type WebhookCreate,
  type WebhookUpdate,
  type CDPSegment,
  type SegmentCreate,
  type SegmentUpdate,
  type SegmentRules,
  type CDPComputedTrait,
  type ComputedTraitCreate,
  type RFMScores,
  type RFMSegment,
  type CDPFunnel,
  type FunnelCreate,
  type FunnelUpdate,
  type FunnelStep,
  type ProfileSearchParams,
  type AudienceExportParams,
} from './cdp';

// =============================================================================
// Tenant Overview Hooks (for tenant dashboard)
// =============================================================================

/**
 * Get tenant overview data (wraps insights for common use case)
 */
export function useTenantOverview(tenantId: number) {
  return useQuery({
    queryKey: ['tenant', 'overview', tenantId],
    queryFn: async () => {
      const response = await apiClient.get<
        ApiResponse<{
          kpis: { total_spend: number; total_revenue: number; roas: number; cpa: number };
          signal_health_status: string;
          autopilot_status: string;
          recent_actions: number;
        }>
      >(`/analytics/tenant-overview`);
      return response.data.data;
    },
    staleTime: 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
  });
}

/**
 * Get tenant recommendations
 */
export function useTenantRecommendations(tenantId: number, options?: { limit?: number }) {
  return useQuery({
    queryKey: ['tenant', 'recommendations', tenantId, options],
    queryFn: async () => {
      const params = options?.limit ? `?limit=${options.limit}` : '';
      const response = await apiClient.get<
        ApiResponse<{
          recommendations: Array<{
            id: string;
            type: string;
            priority: string;
            title: string;
            description: string;
            expected_impact: number;
          }>;
          total: number;
        }>
      >(`/insights/tenant/${tenantId}/recommendations${params}`);
      return response.data.data;
    },
    staleTime: 60 * 1000,
  });
}

// =============================================================================
// Superadmin Dashboard Types
// =============================================================================

export interface RevenueMetrics {
  mrr: number;
  arr: number;
  nrr: number;
  mrrGrowth: number;
  arrGrowth: number;
  churnRate: number;
}

export interface RevenueBreakdown {
  plan: string;
  tenantCount: number;
  mrr: number;
  percentage: number;
}

export interface TenantPortfolioItem {
  id: number;
  name: string;
  plan: string;
  status: string;
  emqScore: number | null;
  budgetAtRisk: number;
  activeIncidents: number;
  monthlySpend: number;
  churnRisk: number;
  lastActivityAt: string | null;
}

export interface SystemHealthMetrics {
  overallStatus: 'healthy' | 'degraded' | 'down';
  services: Array<{
    name: string;
    status: 'healthy' | 'degraded' | 'down';
    uptime: number;
    latency: number;
    version: string;
  }>;
  connectors: Array<{
    platform: string;
    status: 'healthy' | 'degraded' | 'down';
    lastSync: string;
    errors: number;
    recordsProcessed: number;
  }>;
  queues: Array<{
    name: string;
    status: 'running' | 'paused' | 'stalled';
    pending: number;
    processing: number;
    completed: number;
    failed: number;
    avgProcessTime: number;
  }>;
  metrics: {
    cpu: number;
    memory: number;
    disk: number;
    network: number;
    activeConnections: number;
    requestsPerMinute: number;
    errorRate: number;
  };
}

export interface ChurnRisk {
  tenantId: number;
  tenantName: string;
  riskScore: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  factors: string[];
  lastActivityAt: string | null;
  monthlySpend: number;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: string;
  details: string;
  userId: string;
  userName: string | null;
  tenantId: number | null;
  tenantName: string | null;
  ipAddress: string | null;
  userAgent: string | null;
  severity: 'info' | 'warning' | 'error' | 'critical';
  metadata: Record<string, unknown>;
}

export interface BillingPlan {
  id: string;
  name: string;
  price: number;
  features: string[];
  subscriberCount: number;
  mrr: number;
}

export interface BillingInvoice {
  id: string;
  tenantId: number;
  tenantName: string;
  amount: number;
  status: 'paid' | 'pending' | 'overdue' | 'failed';
  dueDate: string;
  paidAt: string | null;
}

export interface BillingSubscription {
  id: string;
  tenantId: number;
  tenantName: string;
  plan: string;
  status: 'active' | 'past_due' | 'canceled' | 'trialing';
  mrr: number;
  startDate: string;
  nextBillingDate: string;
  paymentMethod: string;
  failedPayments: number;
}

export interface SuperadminDashboard {
  totalRevenue: number;
  mrrGrowth: number;
  activeTenants: number;
  atRiskTenants: number;
  totalBudgetAtRisk: number;
  systemStatus: 'healthy' | 'degraded' | 'down';
}

// =============================================================================
// Superadmin API Functions
// =============================================================================

export const superadminApi = {
  // Dashboard
  getDashboard: async (): Promise<SuperadminDashboard> => {
    const response = await apiClient.get<ApiResponse<SuperadminDashboard>>('/superadmin/dashboard');
    return response.data.data;
  },

  // Revenue
  getRevenue: async (): Promise<RevenueMetrics> => {
    const response = await apiClient.get<ApiResponse<RevenueMetrics>>('/superadmin/revenue');
    return response.data.data;
  },

  getRevenueBreakdown: async (): Promise<RevenueBreakdown[]> => {
    const response = await apiClient.get<ApiResponse<RevenueBreakdown[]>>(
      '/superadmin/revenue/breakdown'
    );
    return response.data.data;
  },

  // Tenants Portfolio
  getTenantsPortfolio: async (params?: {
    status?: string;
    plan?: string;
    sortBy?: string;
    sortOrder?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<TenantPortfolioItem>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<TenantPortfolioItem>>>(
      '/superadmin/tenants/portfolio',
      { params }
    );
    return response.data.data;
  },

  // System Health
  getSystemHealth: async (): Promise<SystemHealthMetrics> => {
    const response = await apiClient.get<ApiResponse<SystemHealthMetrics>>(
      '/superadmin/system/health'
    );
    return response.data.data;
  },

  // Churn Risks
  getChurnRisks: async (params?: { minRisk?: number; limit?: number }): Promise<ChurnRisk[]> => {
    const response = await apiClient.get<ApiResponse<ChurnRisk[]>>('/superadmin/churn/risks', {
      params,
    });
    return response.data.data;
  },

  // Audit Logs
  getAuditLogs: async (params?: {
    startDate?: string;
    endDate?: string;
    action?: string;
    userId?: string;
    tenantId?: number;
    severity?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<AuditLogEntry>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<AuditLogEntry>>>(
      '/superadmin/audit',
      { params }
    );
    return response.data.data;
  },

  // Billing - Plans
  getBillingPlans: async (): Promise<BillingPlan[]> => {
    const response = await apiClient.get<ApiResponse<BillingPlan[]>>('/superadmin/billing/plans');
    return response.data.data;
  },

  // Billing - Invoices
  getBillingInvoices: async (params?: {
    status?: string;
    tenantId?: number;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<BillingInvoice>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<BillingInvoice>>>(
      '/superadmin/billing/invoices',
      { params }
    );
    return response.data.data;
  },

  // Billing - Subscriptions
  getBillingSubscriptions: async (params?: {
    status?: string;
    plan?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedResponse<BillingSubscription>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<BillingSubscription>>>(
      '/superadmin/billing/subscriptions',
      { params }
    );
    return response.data.data;
  },

  // Retry failed payment
  retryPayment: async (subscriptionId: string): Promise<{ success: boolean }> => {
    const response = await apiClient.post<ApiResponse<{ success: boolean }>>(
      `/superadmin/billing/subscriptions/${subscriptionId}/retry-payment`
    );
    return response.data.data;
  },
};

// =============================================================================
// Superadmin React Query Hooks
// =============================================================================

/**
 * Get superadmin dashboard overview
 */
export function useSuperAdminOverview() {
  return useQuery({
    queryKey: ['superadmin', 'dashboard'],
    queryFn: superadminApi.getDashboard,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

/**
 * Get superadmin tenant portfolio
 */
export function useSuperAdminTenants(params?: {
  status?: string;
  plan?: string;
  sortBy?: string;
  sortOrder?: string;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['superadmin', 'tenants', params],
    queryFn: () => superadminApi.getTenantsPortfolio(params),
    staleTime: 30 * 1000,
  });
}

/**
 * Get revenue metrics
 */
export function useRevenue() {
  return useQuery({
    queryKey: ['superadmin', 'revenue'],
    queryFn: superadminApi.getRevenue,
    staleTime: 60 * 1000,
  });
}

/**
 * Get revenue breakdown by plan
 */
export function useRevenueBreakdown() {
  return useQuery({
    queryKey: ['superadmin', 'revenue', 'breakdown'],
    queryFn: superadminApi.getRevenueBreakdown,
    staleTime: 60 * 1000,
  });
}

/**
 * Get system health metrics
 */
export function useSystemHealth() {
  return useQuery({
    queryKey: ['superadmin', 'system', 'health'],
    queryFn: superadminApi.getSystemHealth,
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000, // Refresh every 30 seconds
  });
}

/**
 * Get churn risk tenants
 */
export function useChurnRisks(params?: { minRisk?: number; limit?: number }) {
  return useQuery({
    queryKey: ['superadmin', 'churn', 'risks', params],
    queryFn: () => superadminApi.getChurnRisks(params),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Get audit logs
 */
export function useAuditLogs(params?: {
  startDate?: string;
  endDate?: string;
  action?: string;
  userId?: string;
  tenantId?: number;
  severity?: string;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['superadmin', 'audit', params],
    queryFn: () => superadminApi.getAuditLogs(params),
    staleTime: 30 * 1000,
  });
}

/**
 * Get billing plans
 */
export function useBillingPlans() {
  return useQuery({
    queryKey: ['superadmin', 'billing', 'plans'],
    queryFn: superadminApi.getBillingPlans,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Get billing invoices
 */
export function useBillingInvoices(params?: {
  status?: string;
  tenantId?: number;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['superadmin', 'billing', 'invoices', params],
    queryFn: () => superadminApi.getBillingInvoices(params),
    staleTime: 60 * 1000,
  });
}

/**
 * Get billing subscriptions
 */
export function useBillingSubscriptions(params?: {
  status?: string;
  plan?: string;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['superadmin', 'billing', 'subscriptions', params],
    queryFn: () => superadminApi.getBillingSubscriptions(params),
    staleTime: 60 * 1000,
  });
}

/**
 * Retry failed payment
 */
export function useRetryPayment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: superadminApi.retryPayment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superadmin', 'billing', 'subscriptions'] });
      queryClient.invalidateQueries({ queryKey: ['superadmin', 'billing', 'invoices'] });
    },
  });
}
