/**
 * Stratum AI - Feature Flags Store
 *
 * Zustand store for managing tenant feature flags.
 * Provides gating helpers for conditional feature rendering.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

// =============================================================================
// Types
// =============================================================================

export interface FeatureFlags {
  // Trust Layer
  signal_health: boolean;
  attribution_variance: boolean;

  // Intelligence Layer
  ai_recommendations: boolean;
  anomaly_alerts: boolean;
  creative_fatigue: boolean;

  // Execution Layer
  campaign_builder: boolean;
  autopilot_level: number; // 0=suggest, 1=guarded auto, 2=approval required

  // Platform
  superadmin_profitability: boolean;

  // Limits
  max_campaigns: number;
  max_users: number;
  data_retention_days: number;

  // Dashboard
  show_price_metrics: boolean;
}

export interface FeatureCategory {
  name: string;
  description: string;
  features: string[];
}

export interface FeatureFlagsState {
  // Current tenant's feature flags
  features: FeatureFlags | null;
  categories: Record<string, FeatureCategory>;
  descriptions: Record<string, string>;

  // Loading state
  isLoading: boolean;
  error: string | null;

  // Actions
  setFeatures: (features: FeatureFlags) => void;
  setMetadata: (
    categories: Record<string, FeatureCategory>,
    descriptions: Record<string, string>
  ) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;

  // Gating helpers
  can: (feature: keyof FeatureFlags) => boolean;
  getAutopilotLevel: () => number;
  isAutopilotBlocked: (signalHealthStatus: string) => boolean;
}

// =============================================================================
// Default Values
// =============================================================================

export const defaultFeatures: FeatureFlags = {
  signal_health: false,
  attribution_variance: false,
  ai_recommendations: false,
  anomaly_alerts: false,
  creative_fatigue: false,
  campaign_builder: false,
  autopilot_level: 0,
  superadmin_profitability: false,
  max_campaigns: 20,
  max_users: 5,
  data_retention_days: 90,
  show_price_metrics: true,
};

// =============================================================================
// Store
// =============================================================================

export const useFeatureFlagsStore = create<FeatureFlagsState>()(
  devtools(
    (set, get) => ({
      // Initial state
      features: null,
      categories: {},
      descriptions: {},
      isLoading: false,
      error: null,

      // Actions
      setFeatures: (features) => set({ features, error: null }),

      setMetadata: (categories, descriptions) => set({ categories, descriptions }),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error, isLoading: false }),

      reset: () =>
        set({
          features: null,
          isLoading: false,
          error: null,
        }),

      // Gating helpers
      can: (feature) => {
        const { features } = get();
        if (!features) return false;

        const value = features[feature];
        if (typeof value === 'boolean') return value;
        if (typeof value === 'number') return value > 0;
        return Boolean(value);
      },

      getAutopilotLevel: () => {
        const { features } = get();
        return features?.autopilot_level ?? 0;
      },

      isAutopilotBlocked: (signalHealthStatus) => {
        const { features } = get();
        if (!features) return true;

        const level = features.autopilot_level;

        // Level 0 (suggest only) is never "blocked" since it doesn't auto-execute
        if (level === 0) return false;

        // Block if signal health is degraded or critical
        if (signalHealthStatus === 'degraded' || signalHealthStatus === 'critical') {
          return true;
        }

        return false;
      },
    }),
    { name: 'FeatureFlagsStore' }
  )
);

// =============================================================================
// Selectors
// =============================================================================

export const selectFeatures = (state: FeatureFlagsState) => state.features;
export const selectIsLoading = (state: FeatureFlagsState) => state.isLoading;
export const selectError = (state: FeatureFlagsState) => state.error;

// =============================================================================
// Convenience Hooks
// =============================================================================

export const useFeatures = () => useFeatureFlagsStore((state) => state.features);
export const useCanFeature = (feature: keyof FeatureFlags) =>
  useFeatureFlagsStore((state) => state.can(feature));
export const useAutopilotLevel = () => useFeatureFlagsStore((state) => state.getAutopilotLevel());

// =============================================================================
// Feature Gating Component Helper
// =============================================================================

/**
 * Check if a feature is enabled.
 * Use this for conditional rendering in components.
 *
 * @example
 * if (can('signal_health')) {
 *   return <SignalHealthPanel />
 * }
 */
export function can(feature: keyof FeatureFlags): boolean {
  return useFeatureFlagsStore.getState().can(feature);
}

/**
 * Get current autopilot level.
 * 0 = Suggest only
 * 1 = Guarded auto (safe actions with caps)
 * 2 = Approval required
 */
export function getAutopilotLevel(): number {
  return useFeatureFlagsStore.getState().getAutopilotLevel();
}

/**
 * Check if autopilot is blocked due to signal health.
 */
export function isAutopilotBlocked(signalHealthStatus: string): boolean {
  return useFeatureFlagsStore.getState().isAutopilotBlocked(signalHealthStatus);
}
