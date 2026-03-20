/**
 * Stratum AI - Feature Flags Store Tests
 *
 * Comprehensive test suite for the Zustand feature flags store,
 * covering state management, actions, gating helpers, selectors,
 * convenience hooks, and standalone utility functions.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  useFeatureFlagsStore,
  defaultFeatures,
  selectFeatures,
  selectIsLoading,
  selectError,
  useFeatures,
  useCanFeature,
  useAutopilotLevel,
  can,
  getAutopilotLevel,
  isAutopilotBlocked,
} from './featureFlagsStore';
import type { FeatureFlags, FeatureFlagsState, FeatureCategory } from './featureFlagsStore';

// =============================================================================
// Test Fixtures
// =============================================================================

const createMockFeatures = (overrides: Partial<FeatureFlags> = {}): FeatureFlags => ({
  ...defaultFeatures,
  ...overrides,
});

const createEnabledFeatures = (): FeatureFlags => ({
  signal_health: true,
  attribution_variance: true,
  ai_recommendations: true,
  anomaly_alerts: true,
  creative_fatigue: true,
  campaign_builder: true,
  autopilot_level: 2,
  superadmin_profitability: true,
  show_price_metrics: true,
  max_campaigns: 100,
  max_users: 50,
  data_retention_days: 365,
});

const mockCategories: Record<string, FeatureCategory> = {
  trust_layer: {
    name: 'Trust Layer',
    description: 'Signal health and attribution features',
    features: ['signal_health', 'attribution_variance'],
  },
  intelligence: {
    name: 'Intelligence Layer',
    description: 'AI and recommendation features',
    features: ['ai_recommendations', 'anomaly_alerts', 'creative_fatigue'],
  },
};

const mockDescriptions: Record<string, string> = {
  signal_health: 'Real-time signal health monitoring',
  attribution_variance: 'Cross-platform attribution variance detection',
  ai_recommendations: 'AI-powered optimization recommendations',
};

// =============================================================================
// Reset helper
// =============================================================================

const resetStore = () => {
  useFeatureFlagsStore.getState().reset();
};

// =============================================================================
// Tests
// =============================================================================

describe('featureFlagsStore', () => {
  beforeEach(resetStore);

  // ---------------------------------------------------------------------------
  // Initial state
  // ---------------------------------------------------------------------------

  describe('Initial state', () => {
    it('should have null features initially', () => {
      const state = useFeatureFlagsStore.getState();
      expect(state.features).toBeNull();
    });

    it('should have empty categories initially', () => {
      const state = useFeatureFlagsStore.getState();
      expect(state.categories).toEqual({});
    });

    it('should have empty descriptions initially', () => {
      const state = useFeatureFlagsStore.getState();
      expect(state.descriptions).toEqual({});
    });

    it('should have isLoading=false initially', () => {
      const state = useFeatureFlagsStore.getState();
      expect(state.isLoading).toBe(false);
    });

    it('should have error=null initially', () => {
      const state = useFeatureFlagsStore.getState();
      expect(state.error).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Default features constant
  // ---------------------------------------------------------------------------

  describe('defaultFeatures', () => {
    it('has all boolean features set to false by default', () => {
      expect(defaultFeatures.signal_health).toBe(false);
      expect(defaultFeatures.attribution_variance).toBe(false);
      expect(defaultFeatures.ai_recommendations).toBe(false);
      expect(defaultFeatures.anomaly_alerts).toBe(false);
      expect(defaultFeatures.creative_fatigue).toBe(false);
      expect(defaultFeatures.campaign_builder).toBe(false);
      expect(defaultFeatures.superadmin_profitability).toBe(false);
    });

    it('has autopilot_level set to 0 (suggest only)', () => {
      expect(defaultFeatures.autopilot_level).toBe(0);
    });

    it('has numeric limits with reasonable defaults', () => {
      expect(defaultFeatures.max_campaigns).toBe(20);
      expect(defaultFeatures.max_users).toBe(5);
      expect(defaultFeatures.data_retention_days).toBe(90);
    });

    it('has show_price_metrics enabled by default', () => {
      expect(defaultFeatures.show_price_metrics).toBe(true);
    });
  });

  // ---------------------------------------------------------------------------
  // Actions: setFeatures
  // ---------------------------------------------------------------------------

  describe('setFeatures', () => {
    it('should set features and clear error', () => {
      const features = createMockFeatures({ signal_health: true });

      // Set an error first
      useFeatureFlagsStore.getState().setError('some error');
      expect(useFeatureFlagsStore.getState().error).toBe('some error');

      // Set features should clear the error
      useFeatureFlagsStore.getState().setFeatures(features);

      const state = useFeatureFlagsStore.getState();
      expect(state.features).toEqual(features);
      expect(state.error).toBeNull();
    });

    it('should overwrite previous features completely', () => {
      const first = createMockFeatures({ signal_health: true });
      const second = createMockFeatures({ signal_health: false, campaign_builder: true });

      useFeatureFlagsStore.getState().setFeatures(first);
      expect(useFeatureFlagsStore.getState().features?.signal_health).toBe(true);

      useFeatureFlagsStore.getState().setFeatures(second);
      expect(useFeatureFlagsStore.getState().features?.signal_health).toBe(false);
      expect(useFeatureFlagsStore.getState().features?.campaign_builder).toBe(true);
    });
  });

  // ---------------------------------------------------------------------------
  // Actions: setMetadata
  // ---------------------------------------------------------------------------

  describe('setMetadata', () => {
    it('should set categories and descriptions', () => {
      useFeatureFlagsStore.getState().setMetadata(mockCategories, mockDescriptions);

      const state = useFeatureFlagsStore.getState();
      expect(state.categories).toEqual(mockCategories);
      expect(state.descriptions).toEqual(mockDescriptions);
    });

    it('should overwrite previous metadata', () => {
      useFeatureFlagsStore.getState().setMetadata(mockCategories, mockDescriptions);

      const newCategories = { new_cat: { name: 'New', description: 'New category', features: [] } };
      const newDescriptions = { new_feature: 'New feature desc' };

      useFeatureFlagsStore.getState().setMetadata(newCategories, newDescriptions);

      const state = useFeatureFlagsStore.getState();
      expect(state.categories).toEqual(newCategories);
      expect(state.descriptions).toEqual(newDescriptions);
    });
  });

  // ---------------------------------------------------------------------------
  // Actions: setLoading
  // ---------------------------------------------------------------------------

  describe('setLoading', () => {
    it('should set loading to true', () => {
      useFeatureFlagsStore.getState().setLoading(true);
      expect(useFeatureFlagsStore.getState().isLoading).toBe(true);
    });

    it('should set loading to false', () => {
      useFeatureFlagsStore.getState().setLoading(true);
      useFeatureFlagsStore.getState().setLoading(false);
      expect(useFeatureFlagsStore.getState().isLoading).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // Actions: setError
  // ---------------------------------------------------------------------------

  describe('setError', () => {
    it('should set error message and disable loading', () => {
      useFeatureFlagsStore.getState().setLoading(true);
      useFeatureFlagsStore.getState().setError('Failed to fetch');

      const state = useFeatureFlagsStore.getState();
      expect(state.error).toBe('Failed to fetch');
      expect(state.isLoading).toBe(false);
    });

    it('should clear error when set to null', () => {
      useFeatureFlagsStore.getState().setError('error');
      useFeatureFlagsStore.getState().setError(null);

      expect(useFeatureFlagsStore.getState().error).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Actions: reset
  // ---------------------------------------------------------------------------

  describe('reset', () => {
    it('should reset features, isLoading, and error to initial values', () => {
      const features = createEnabledFeatures();
      useFeatureFlagsStore.getState().setFeatures(features);
      useFeatureFlagsStore.getState().setLoading(true);
      useFeatureFlagsStore.getState().setError('some error');

      useFeatureFlagsStore.getState().reset();

      const state = useFeatureFlagsStore.getState();
      expect(state.features).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should not reset categories and descriptions (metadata persists)', () => {
      useFeatureFlagsStore.getState().setMetadata(mockCategories, mockDescriptions);
      useFeatureFlagsStore.getState().reset();

      const state = useFeatureFlagsStore.getState();
      // reset only resets features, isLoading, error - not metadata
      expect(state.categories).toEqual(mockCategories);
      expect(state.descriptions).toEqual(mockDescriptions);
    });
  });

  // ---------------------------------------------------------------------------
  // Gating: can
  // ---------------------------------------------------------------------------

  describe('can (gating helper)', () => {
    it('returns false when features are null', () => {
      expect(useFeatureFlagsStore.getState().can('signal_health')).toBe(false);
    });

    it('returns true for enabled boolean features', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ signal_health: true })
      );

      expect(useFeatureFlagsStore.getState().can('signal_health')).toBe(true);
    });

    it('returns false for disabled boolean features', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ signal_health: false })
      );

      expect(useFeatureFlagsStore.getState().can('signal_health')).toBe(false);
    });

    it('returns true for numeric features greater than 0', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 1 })
      );

      expect(useFeatureFlagsStore.getState().can('autopilot_level')).toBe(true);
    });

    it('returns false for numeric features equal to 0', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 0 })
      );

      expect(useFeatureFlagsStore.getState().can('autopilot_level')).toBe(false);
    });

    it('returns true for positive max_campaigns', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ max_campaigns: 50 })
      );

      expect(useFeatureFlagsStore.getState().can('max_campaigns')).toBe(true);
    });

    it('checks show_price_metrics correctly (default true)', () => {
      useFeatureFlagsStore.getState().setFeatures(createMockFeatures());

      expect(useFeatureFlagsStore.getState().can('show_price_metrics')).toBe(true);
    });
  });

  // ---------------------------------------------------------------------------
  // Gating: getAutopilotLevel
  // ---------------------------------------------------------------------------

  describe('getAutopilotLevel', () => {
    it('returns 0 when features are null', () => {
      expect(useFeatureFlagsStore.getState().getAutopilotLevel()).toBe(0);
    });

    it('returns the autopilot_level from features', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 2 })
      );

      expect(useFeatureFlagsStore.getState().getAutopilotLevel()).toBe(2);
    });

    it('returns 0 for suggest-only level', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 0 })
      );

      expect(useFeatureFlagsStore.getState().getAutopilotLevel()).toBe(0);
    });

    it('returns 1 for guarded auto level', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 1 })
      );

      expect(useFeatureFlagsStore.getState().getAutopilotLevel()).toBe(1);
    });
  });

  // ---------------------------------------------------------------------------
  // Gating: isAutopilotBlocked
  // ---------------------------------------------------------------------------

  describe('isAutopilotBlocked', () => {
    it('returns true when features are null', () => {
      expect(useFeatureFlagsStore.getState().isAutopilotBlocked('healthy')).toBe(true);
    });

    it('returns false for level 0 (suggest only) regardless of health', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 0 })
      );

      expect(useFeatureFlagsStore.getState().isAutopilotBlocked('degraded')).toBe(false);
      expect(useFeatureFlagsStore.getState().isAutopilotBlocked('critical')).toBe(false);
      expect(useFeatureFlagsStore.getState().isAutopilotBlocked('healthy')).toBe(false);
    });

    it('returns true for level 1 when signal health is degraded', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 1 })
      );

      expect(useFeatureFlagsStore.getState().isAutopilotBlocked('degraded')).toBe(true);
    });

    it('returns true for level 1 when signal health is critical', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 1 })
      );

      expect(useFeatureFlagsStore.getState().isAutopilotBlocked('critical')).toBe(true);
    });

    it('returns false for level 1 when signal health is healthy', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 1 })
      );

      expect(useFeatureFlagsStore.getState().isAutopilotBlocked('healthy')).toBe(false);
    });

    it('returns true for level 2 when signal health is degraded', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 2 })
      );

      expect(useFeatureFlagsStore.getState().isAutopilotBlocked('degraded')).toBe(true);
    });

    it('returns false for level 2 when signal health is healthy', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 2 })
      );

      expect(useFeatureFlagsStore.getState().isAutopilotBlocked('healthy')).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // Selectors
  // ---------------------------------------------------------------------------

  describe('Selectors', () => {
    it('selectFeatures returns features from state', () => {
      const features = createEnabledFeatures();
      useFeatureFlagsStore.getState().setFeatures(features);

      const state = useFeatureFlagsStore.getState();
      expect(selectFeatures(state)).toEqual(features);
    });

    it('selectFeatures returns null when no features set', () => {
      const state = useFeatureFlagsStore.getState();
      expect(selectFeatures(state)).toBeNull();
    });

    it('selectIsLoading returns loading state', () => {
      useFeatureFlagsStore.getState().setLoading(true);
      expect(selectIsLoading(useFeatureFlagsStore.getState())).toBe(true);

      useFeatureFlagsStore.getState().setLoading(false);
      expect(selectIsLoading(useFeatureFlagsStore.getState())).toBe(false);
    });

    it('selectError returns error from state', () => {
      useFeatureFlagsStore.getState().setError('Test error');
      expect(selectError(useFeatureFlagsStore.getState())).toBe('Test error');

      useFeatureFlagsStore.getState().setError(null);
      expect(selectError(useFeatureFlagsStore.getState())).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Convenience hooks
  // ---------------------------------------------------------------------------

  describe('Convenience hooks', () => {
    it('useFeatures returns current features', () => {
      const features = createEnabledFeatures();
      useFeatureFlagsStore.getState().setFeatures(features);

      const { result } = renderHook(() => useFeatures());
      expect(result.current).toEqual(features);
    });

    it('useFeatures returns null when no features set', () => {
      const { result } = renderHook(() => useFeatures());
      expect(result.current).toBeNull();
    });

    it('useCanFeature returns true for enabled feature', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ signal_health: true })
      );

      const { result } = renderHook(() => useCanFeature('signal_health'));
      expect(result.current).toBe(true);
    });

    it('useCanFeature returns false for disabled feature', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ signal_health: false })
      );

      const { result } = renderHook(() => useCanFeature('signal_health'));
      expect(result.current).toBe(false);
    });

    it('useAutopilotLevel returns current autopilot level', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 2 })
      );

      const { result } = renderHook(() => useAutopilotLevel());
      expect(result.current).toBe(2);
    });

    it('useAutopilotLevel returns 0 when features are null', () => {
      const { result } = renderHook(() => useAutopilotLevel());
      expect(result.current).toBe(0);
    });
  });

  // ---------------------------------------------------------------------------
  // Standalone utility functions
  // ---------------------------------------------------------------------------

  describe('Standalone utility functions', () => {
    it('can() checks feature directly from store state', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ ai_recommendations: true })
      );

      expect(can('ai_recommendations')).toBe(true);
      expect(can('creative_fatigue')).toBe(false);
    });

    it('can() returns false when features are null', () => {
      expect(can('signal_health')).toBe(false);
    });

    it('getAutopilotLevel() reads from store state', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 1 })
      );

      expect(getAutopilotLevel()).toBe(1);
    });

    it('getAutopilotLevel() returns 0 when features are null', () => {
      expect(getAutopilotLevel()).toBe(0);
    });

    it('isAutopilotBlocked() reads from store state', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 2 })
      );

      expect(isAutopilotBlocked('degraded')).toBe(true);
      expect(isAutopilotBlocked('healthy')).toBe(false);
    });

    it('isAutopilotBlocked() returns true when features are null', () => {
      expect(isAutopilotBlocked('healthy')).toBe(true);
    });
  });

  // ---------------------------------------------------------------------------
  // Store reactivity via hooks
  // ---------------------------------------------------------------------------

  describe('Store reactivity', () => {
    it('updates hook consumers when features change', () => {
      const { result } = renderHook(() => useFeatures());
      expect(result.current).toBeNull();

      act(() => {
        useFeatureFlagsStore.getState().setFeatures(createEnabledFeatures());
      });

      expect(result.current).not.toBeNull();
      expect(result.current?.signal_health).toBe(true);
    });

    it('updates useCanFeature when features change', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ anomaly_alerts: false })
      );

      const { result } = renderHook(() => useCanFeature('anomaly_alerts'));
      expect(result.current).toBe(false);

      act(() => {
        useFeatureFlagsStore.getState().setFeatures(
          createMockFeatures({ anomaly_alerts: true })
        );
      });

      expect(result.current).toBe(true);
    });

    it('updates useAutopilotLevel when features change', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({ autopilot_level: 0 })
      );

      const { result } = renderHook(() => useAutopilotLevel());
      expect(result.current).toBe(0);

      act(() => {
        useFeatureFlagsStore.getState().setFeatures(
          createMockFeatures({ autopilot_level: 2 })
        );
      });

      expect(result.current).toBe(2);
    });
  });

  // ---------------------------------------------------------------------------
  // Edge cases
  // ---------------------------------------------------------------------------

  describe('Edge cases', () => {
    it('handles setting features multiple times', () => {
      const store = useFeatureFlagsStore.getState();

      store.setFeatures(createMockFeatures({ signal_health: true }));
      store.setFeatures(createMockFeatures({ signal_health: false }));
      store.setFeatures(createMockFeatures({ signal_health: true, campaign_builder: true }));

      const state = useFeatureFlagsStore.getState();
      expect(state.features?.signal_health).toBe(true);
      expect(state.features?.campaign_builder).toBe(true);
    });

    it('handles reset followed by setFeatures', () => {
      useFeatureFlagsStore.getState().setFeatures(createEnabledFeatures());
      useFeatureFlagsStore.getState().reset();
      expect(useFeatureFlagsStore.getState().features).toBeNull();

      useFeatureFlagsStore.getState().setFeatures(createMockFeatures({ signal_health: true }));
      expect(useFeatureFlagsStore.getState().features?.signal_health).toBe(true);
    });

    it('handles all autopilot levels (0, 1, 2)', () => {
      for (const level of [0, 1, 2]) {
        useFeatureFlagsStore.getState().setFeatures(
          createMockFeatures({ autopilot_level: level })
        );
        expect(useFeatureFlagsStore.getState().getAutopilotLevel()).toBe(level);
      }
    });

    it('can check multiple features sequentially', () => {
      useFeatureFlagsStore.getState().setFeatures(
        createMockFeatures({
          signal_health: true,
          ai_recommendations: false,
          campaign_builder: true,
        })
      );

      const state = useFeatureFlagsStore.getState();
      expect(state.can('signal_health')).toBe(true);
      expect(state.can('ai_recommendations')).toBe(false);
      expect(state.can('campaign_builder')).toBe(true);
    });
  });
});
