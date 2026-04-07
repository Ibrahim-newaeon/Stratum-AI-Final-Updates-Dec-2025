/**
 * Stratum AI - Onboarding API
 *
 * API endpoints for the onboarding wizard flow.
 * Guides new users through platform setup in 5 steps:
 * 1. Business Profile
 * 2. Platform Selection
 * 3. Goals Setup
 * 4. Automation Preferences
 * 5. Trust Gate Configuration
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse } from './client';

// =============================================================================
// Types
// =============================================================================

export type OnboardingStatus = 'not_started' | 'in_progress' | 'completed' | 'skipped';

export type OnboardingStep =
  | 'business_profile'
  | 'platform_selection'
  | 'goals_setup'
  | 'automation_preferences'
  | 'trust_gate_config';

export type Industry =
  | 'ecommerce'
  | 'saas'
  | 'lead_gen'
  | 'mobile_app'
  | 'gaming'
  | 'finance'
  | 'healthcare'
  | 'education'
  | 'real_estate'
  | 'travel'
  | 'food_beverage'
  | 'retail'
  | 'automotive'
  | 'entertainment'
  | 'other';

export type MonthlyAdSpend =
  | 'under_10k'
  | '10k_50k'
  | '50k_100k'
  | '100k_500k'
  | '500k_1m'
  | 'over_1m';

export type TeamSize = 'solo' | '2_5' | '6_15' | '16_50' | '50_plus';

export type AutomationMode = 'manual' | 'assisted' | 'autopilot';

export type PrimaryKPI =
  | 'roas'
  | 'cpa'
  | 'cpl'
  | 'revenue'
  | 'conversions'
  | 'leads'
  | 'app_installs'
  | 'brand_awareness';

export type AdPlatform = 'meta' | 'google' | 'tiktok' | 'snapchat';

// Response types
export interface BusinessProfile {
  industry: Industry | null;
  industry_other: string | null;
  monthly_ad_spend: MonthlyAdSpend | null;
  team_size: TeamSize | null;
  company_website: string | null;
  target_markets: string[] | null;
}

export interface PlatformSelection {
  platforms: AdPlatform[] | null;
}

export interface GoalsSetup {
  primary_kpi: PrimaryKPI | null;
  target_roas: number | null;
  target_cpa: number | null;
  monthly_budget: number | null;
  currency: string;
  timezone: string;
}

export interface AutomationPreferences {
  automation_mode: AutomationMode | null;
  auto_pause_enabled: boolean;
  auto_scale_enabled: boolean;
  notification_email: boolean;
  notification_slack: boolean;
  notification_whatsapp: boolean;
}

export interface TrustGateConfig {
  trust_threshold_autopilot: number;
  trust_threshold_alert: number;
  require_approval_above: number | null;
  max_daily_actions: number;
}

export interface OnboardingStatusResponse {
  status: OnboardingStatus;
  current_step: OnboardingStep;
  completed_steps: OnboardingStep[];
  progress_percentage: number;
  started_at: string | null;
  completed_at: string | null;
  business_profile: BusinessProfile | null;
  platform_selection: PlatformSelection | null;
  goals_setup: GoalsSetup | null;
  automation_preferences: AutomationPreferences | null;
  trust_gate_config: TrustGateConfig;
}

export interface StepCompletionResponse {
  step: OnboardingStep;
  completed: boolean;
  next_step: OnboardingStep | null;
  progress_percentage: number;
  message: string;
}

// Request types
export interface BusinessProfileRequest {
  industry: Industry;
  industry_other?: string;
  monthly_ad_spend: MonthlyAdSpend;
  team_size: TeamSize;
  company_website?: string;
  target_markets?: string[];
}

export interface PlatformSelectionRequest {
  platforms: AdPlatform[];
}

export interface GoalsSetupRequest {
  primary_kpi: PrimaryKPI;
  target_roas?: number;
  target_cpa?: number;
  monthly_budget?: number;
  currency?: string;
  timezone?: string;
}

export interface AutomationPreferencesRequest {
  automation_mode: AutomationMode;
  auto_pause_enabled?: boolean;
  auto_scale_enabled?: boolean;
  notification_email?: boolean;
  notification_slack?: boolean;
  notification_whatsapp?: boolean;
}

export interface TrustGateConfigRequest {
  trust_threshold_autopilot?: number;
  trust_threshold_alert?: number;
  require_approval_above?: number;
  max_daily_actions?: number;
}

// =============================================================================
// API Functions
// =============================================================================

export const onboardingApi = {
  /**
   * Get current onboarding status
   */
  getStatus: async (): Promise<OnboardingStatusResponse> => {
    const response =
      await apiClient.get<ApiResponse<OnboardingStatusResponse>>('/onboarding/status');
    return response.data.data;
  },

  /**
   * Check if onboarding is required
   */
  checkRequired: async (): Promise<{ required: boolean; redirect_to: string | null }> => {
    const response =
      await apiClient.get<ApiResponse<{ required: boolean; redirect_to: string | null }>>(
        '/onboarding/check'
      );
    return response.data.data;
  },

  /**
   * Submit business profile (Step 1)
   */
  submitBusinessProfile: async (data: BusinessProfileRequest): Promise<StepCompletionResponse> => {
    const response = await apiClient.post<ApiResponse<StepCompletionResponse>>(
      '/onboarding/business-profile',
      data
    );
    return response.data.data;
  },

  /**
   * Submit platform selection (Step 2)
   */
  submitPlatformSelection: async (
    data: PlatformSelectionRequest
  ): Promise<StepCompletionResponse> => {
    const response = await apiClient.post<ApiResponse<StepCompletionResponse>>(
      '/onboarding/platform-selection',
      data
    );
    return response.data.data;
  },

  /**
   * Submit goals setup (Step 3)
   */
  submitGoalsSetup: async (data: GoalsSetupRequest): Promise<StepCompletionResponse> => {
    const response = await apiClient.post<ApiResponse<StepCompletionResponse>>(
      '/onboarding/goals-setup',
      data
    );
    return response.data.data;
  },

  /**
   * Submit automation preferences (Step 4)
   */
  submitAutomationPreferences: async (
    data: AutomationPreferencesRequest
  ): Promise<StepCompletionResponse> => {
    const response = await apiClient.post<ApiResponse<StepCompletionResponse>>(
      '/onboarding/automation-preferences',
      data
    );
    return response.data.data;
  },

  /**
   * Submit trust gate configuration (Step 5)
   */
  submitTrustGateConfig: async (data: TrustGateConfigRequest): Promise<StepCompletionResponse> => {
    const response = await apiClient.post<ApiResponse<StepCompletionResponse>>(
      '/onboarding/trust-gate-config',
      data
    );
    return response.data.data;
  },

  /**
   * Skip onboarding (use defaults)
   */
  skip: async (): Promise<{ message: string }> => {
    const response = await apiClient.post<ApiResponse<{ message: string }>>('/onboarding/skip');
    return response.data.data;
  },

  /**
   * Reset onboarding (start over)
   */
  reset: async (): Promise<{ message: string }> => {
    const response = await apiClient.post<ApiResponse<{ message: string }>>('/onboarding/reset');
    return response.data.data;
  },
};

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Get onboarding status
 */
export function useOnboardingStatus(enabled = true) {
  return useQuery({
    queryKey: ['onboarding', 'status'],
    queryFn: onboardingApi.getStatus,
    enabled,
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Check if onboarding is required
 */
export function useOnboardingCheck(enabled = true) {
  return useQuery({
    queryKey: ['onboarding', 'check'],
    queryFn: onboardingApi.checkRequired,
    enabled,
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Submit business profile
 */
export function useSubmitBusinessProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: onboardingApi.submitBusinessProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    },
  });
}

/**
 * Submit platform selection
 */
export function useSubmitPlatformSelection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: onboardingApi.submitPlatformSelection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    },
  });
}

/**
 * Submit goals setup
 */
export function useSubmitGoalsSetup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: onboardingApi.submitGoalsSetup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    },
  });
}

/**
 * Submit automation preferences
 */
export function useSubmitAutomationPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: onboardingApi.submitAutomationPreferences,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    },
  });
}

/**
 * Submit trust gate configuration
 */
export function useSubmitTrustGateConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: onboardingApi.submitTrustGateConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    },
  });
}

/**
 * Skip onboarding
 */
export function useSkipOnboarding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: onboardingApi.skip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    },
  });
}

/**
 * Reset onboarding
 */
export function useResetOnboarding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: onboardingApi.reset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    },
  });
}
