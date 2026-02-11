// =============================================================================
// Stratum AI - Subscription Tier Context
// =============================================================================
/**
 * React context for managing subscription tier state and feature access.
 *
 * Usage:
 *   const { tier, hasFeature, checkLimit } = useTier();
 *   if (hasFeature('predictive_churn')) { ... }
 */

import { createContext, ReactNode, useContext } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/api/client';

// =============================================================================
// Types
// =============================================================================

export type SubscriptionTier = 'starter' | 'professional' | 'enterprise';

export interface TierLimits {
  max_ad_accounts: number;
  max_users: number;
  max_segments: number;
  max_automations: number;
  max_audience_sync_platforms: number;
  api_rate_limit_per_minute: number;
  data_retention_days: number;
}

export interface TierPricing {
  name: string;
  price: number | null;
  currency: string;
  billing_period: string;
  ad_spend_limit: number | null;
  description: string;
}

export interface TierInfo {
  tier: SubscriptionTier;
  features: string[];
  limits: TierLimits;
  pricing: TierPricing;
}

export interface TierContextValue {
  tier: SubscriptionTier;
  tierInfo: TierInfo | null;
  features: string[];
  limits: TierLimits | null;
  loading: boolean;
  error: Error | null;
  hasFeature: (feature: string) => boolean;
  checkLimit: (limitName: keyof TierLimits, currentValue: number) => boolean;
  getRemainingLimit: (limitName: keyof TierLimits, currentValue: number) => number;
  isAtLeastTier: (minimumTier: SubscriptionTier) => boolean;
  refetch: () => void;
}

// =============================================================================
// Feature Constants (for type safety)
// =============================================================================

export const Features = {
  // Starter
  AD_ACCOUNTS_BASIC: 'ad_accounts_basic',
  SIGNAL_HEALTH_MONITORING: 'signal_health_monitoring',
  ANOMALY_DETECTION: 'anomaly_detection',
  CDP_PROFILES: 'cdp_profiles',
  CDP_EVENTS: 'cdp_events',
  RFM_ANALYSIS: 'rfm_analysis',
  DASHBOARD_EXPORTS: 'dashboard_exports',
  SLACK_NOTIFICATIONS: 'slack_notifications',
  EMAIL_NOTIFICATIONS: 'email_notifications',

  // Professional
  AD_ACCOUNTS_EXTENDED: 'ad_accounts_extended',
  FUNNEL_BUILDER: 'funnel_builder',
  COMPUTED_TRAITS: 'computed_traits',
  SEGMENT_BUILDER: 'segment_builder',
  TRUST_GATE_AUDIT_LOGS: 'trust_gate_audit_logs',
  ACTION_DRY_RUN: 'action_dry_run',
  PIPEDRIVE_INTEGRATION: 'pipedrive_integration',
  HUBSPOT_INTEGRATION: 'hubspot_integration',
  AUDIENCE_SYNC_BASIC: 'audience_sync_basic',

  // Enterprise
  AD_ACCOUNTS_UNLIMITED: 'ad_accounts_unlimited',
  PREDICTIVE_CHURN: 'predictive_churn',
  CUSTOM_AUTOPILOT_RULES: 'custom_autopilot_rules',
  CUSTOM_REPORT_BUILDER: 'custom_report_builder',
  WHAT_IF_SIMULATOR: 'what_if_simulator',
  SALESFORCE_INTEGRATION: 'salesforce_integration',
  ZOHO_INTEGRATION: 'zoho_integration',
  CRM_WRITEBACK: 'crm_writeback',
  CONSENT_MANAGEMENT: 'consent_management',
  GDPR_TOOLS: 'gdpr_tools',
  AUDIT_EXPORT: 'audit_export',
  AUDIENCE_SYNC_ALL: 'audience_sync_all',
  IDENTITY_GRAPH: 'identity_graph',
  API_ACCESS: 'api_access',
  WEBHOOKS: 'webhooks',
} as const;

// =============================================================================
// Context
// =============================================================================

const TierContext = createContext<TierContextValue | undefined>(undefined);

// Tier hierarchy for comparison
const TIER_HIERARCHY: SubscriptionTier[] = ['starter', 'professional', 'enterprise'];

// =============================================================================
// Provider
// =============================================================================

interface TierProviderProps {
  children: ReactNode;
}

export function TierProvider({ children }: TierProviderProps) {
  const {
    data: tierInfo,
    isLoading: loading,
    error,
    refetch,
  } = useQuery<TierInfo>({
    queryKey: ['tier', 'current'],
    queryFn: async () => {
      const response = await api.get('/api/v1/tier/current');
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });

  const tier = tierInfo?.tier || 'enterprise';
  const features = tierInfo?.features || [];
  const limits = tierInfo?.limits || null;

  const hasFeature = (feature: string): boolean => {
    return features.includes(feature);
  };

  const checkLimit = (limitName: keyof TierLimits, currentValue: number): boolean => {
    if (!limits) return true;
    const maxValue = limits[limitName];
    return currentValue < maxValue;
  };

  const getRemainingLimit = (limitName: keyof TierLimits, currentValue: number): number => {
    if (!limits) return 999999;
    const maxValue = limits[limitName];
    return Math.max(0, maxValue - currentValue);
  };

  const isAtLeastTier = (minimumTier: SubscriptionTier): boolean => {
    const currentIndex = TIER_HIERARCHY.indexOf(tier);
    const minIndex = TIER_HIERARCHY.indexOf(minimumTier);
    return currentIndex >= minIndex;
  };

  const value: TierContextValue = {
    tier,
    tierInfo: tierInfo || null,
    features,
    limits,
    loading,
    error: error,
    hasFeature,
    checkLimit,
    getRemainingLimit,
    isAtLeastTier,
    refetch,
  };

  return <TierContext.Provider value={value}>{children}</TierContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

export function useTier(): TierContextValue {
  const context = useContext(TierContext);
  if (context === undefined) {
    throw new Error('useTier must be used within a TierProvider');
  }
  return context;
}

// =============================================================================
// Feature Gate Component
// =============================================================================

interface FeatureGateProps {
  feature: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export function FeatureGate({ feature, children, fallback = null }: FeatureGateProps) {
  const { hasFeature } = useTier();

  if (!hasFeature(feature)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// =============================================================================
// Tier Gate Component
// =============================================================================

interface TierGateProps {
  minimumTier: SubscriptionTier;
  children: ReactNode;
  fallback?: ReactNode;
}

export function TierGate({ minimumTier, children, fallback = null }: TierGateProps) {
  const { isAtLeastTier } = useTier();

  if (!isAtLeastTier(minimumTier)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

// =============================================================================
// Upgrade Prompt Component
// =============================================================================

interface UpgradePromptProps {
  feature: string;
  requiredTier?: SubscriptionTier;
  className?: string;
}

export function UpgradePrompt({ feature: _feature, requiredTier, className = '' }: UpgradePromptProps) {
  return (
    <div
      className={`p-6 bg-gray-800/50 border border-orange-500/30 rounded-lg text-center ${className}`}
    >
      <div className="text-orange-400 text-lg font-semibold mb-2">Upgrade Required</div>
      <p className="text-gray-400 mb-4">This feature requires {requiredTier || 'a higher'} tier.</p>
      <a
        href="/settings/billing"
        className="inline-block px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg transition-colors"
      >
        Upgrade Now
      </a>
    </div>
  );
}
