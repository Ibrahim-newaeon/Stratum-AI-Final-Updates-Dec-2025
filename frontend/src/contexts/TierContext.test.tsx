/**
 * Stratum AI - TierContext Tests
 *
 * Tests for TierProvider, useTier hook, feature gating,
 * tier hierarchy checks, limit checks, and gate components.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  TierProvider,
  useTier,
  FeatureGate,
  TierGate,
  UpgradePrompt,
  Features,
} from './TierContext';
import type { TierInfo, TierContextValue } from './TierContext';
import type { ReactNode } from 'react';

// =============================================================================
// Mock API client
// =============================================================================

const mockGet = vi.fn();
vi.mock('@/api/client', () => ({
  default: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}));

// =============================================================================
// Test Fixtures
// =============================================================================

const starterTierInfo: TierInfo = {
  tier: 'starter',
  features: [
    Features.AD_ACCOUNTS_BASIC,
    Features.SIGNAL_HEALTH_MONITORING,
    Features.ANOMALY_DETECTION,
    Features.CDP_PROFILES,
  ],
  limits: {
    max_ad_accounts: 3,
    max_users: 5,
    max_segments: 10,
    max_automations: 5,
    max_audience_sync_platforms: 1,
    api_rate_limit_per_minute: 60,
    data_retention_days: 90,
  },
  pricing: {
    name: 'Starter',
    price: 49,
    currency: 'USD',
    billing_period: 'monthly',
    ad_spend_limit: 10000,
    description: 'For small teams',
  },
};

const enterpriseTierInfo: TierInfo = {
  tier: 'enterprise',
  features: [
    Features.AD_ACCOUNTS_BASIC,
    Features.SIGNAL_HEALTH_MONITORING,
    Features.PREDICTIVE_CHURN,
    Features.CUSTOM_AUTOPILOT_RULES,
    Features.WHAT_IF_SIMULATOR,
    Features.API_ACCESS,
  ],
  limits: {
    max_ad_accounts: 999,
    max_users: 999,
    max_segments: 999,
    max_automations: 999,
    max_audience_sync_platforms: 10,
    api_rate_limit_per_minute: 1000,
    data_retention_days: 730,
  },
  pricing: {
    name: 'Enterprise',
    price: null,
    currency: 'USD',
    billing_period: 'annual',
    ad_spend_limit: null,
    description: 'Custom pricing',
  },
};

// =============================================================================
// Helpers
// =============================================================================

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
}

function createWrapper(tierData?: TierInfo) {
  const queryClient = createQueryClient();

  if (tierData) {
    mockGet.mockResolvedValue({ data: tierData });
  }

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <TierProvider>{children}</TierProvider>
    </QueryClientProvider>
  );
  Wrapper.displayName = 'TierTestWrapper';
  return Wrapper;
}

// =============================================================================
// Tests
// =============================================================================

describe('TierContext', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  // ---------------------------------------------------------------------------
  // useTier outside provider
  // ---------------------------------------------------------------------------

  describe('useTier outside provider', () => {
    it('throws an error when used outside TierProvider', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useTier());
      }).toThrow('useTier must be used within a TierProvider');

      spy.mockRestore();
    });
  });

  // ---------------------------------------------------------------------------
  // Default / loading state
  // ---------------------------------------------------------------------------

  describe('Default and loading state', () => {
    it('starts with loading=true before API response', () => {
      // Keep the promise pending
      mockGet.mockReturnValue(new Promise(() => {}));
      const wrapper = createWrapper();

      const { result } = renderHook(() => useTier(), { wrapper });

      expect(result.current.loading).toBe(true);
    });

    it('defaults to enterprise tier when no data is loaded yet', () => {
      mockGet.mockReturnValue(new Promise(() => {}));
      const wrapper = createWrapper();

      const { result } = renderHook(() => useTier(), { wrapper });

      // Before data loads, tier defaults to 'enterprise'
      expect(result.current.tier).toBe('enterprise');
    });

    it('has null tierInfo before data loads', () => {
      mockGet.mockReturnValue(new Promise(() => {}));
      const wrapper = createWrapper();

      const { result } = renderHook(() => useTier(), { wrapper });

      expect(result.current.tierInfo).toBeNull();
    });

    it('has empty features array before data loads', () => {
      mockGet.mockReturnValue(new Promise(() => {}));
      const wrapper = createWrapper();

      const { result } = renderHook(() => useTier(), { wrapper });

      expect(result.current.features).toEqual([]);
    });

    it('has null limits before data loads', () => {
      mockGet.mockReturnValue(new Promise(() => {}));
      const wrapper = createWrapper();

      const { result } = renderHook(() => useTier(), { wrapper });

      expect(result.current.limits).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  describe('Data loading', () => {
    it('loads tier data from API and updates state', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.tier).toBe('starter');
      expect(result.current.tierInfo).toEqual(starterTierInfo);
      expect(result.current.features).toEqual(starterTierInfo.features);
      expect(result.current.limits).toEqual(starterTierInfo.limits);
    });

    it('calls the correct API endpoint', async () => {
      const wrapper = createWrapper(enterpriseTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(mockGet).toHaveBeenCalledWith('/tier/current');
    });

    it('handles API errors gracefully', async () => {
      mockGet.mockRejectedValue(new Error('Network error'));
      // TierProvider uses retry: 2 in useQuery, so we need a longer timeout
      // to wait for all retry attempts to complete before the error state is set.
      const queryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            gcTime: 0,
          },
        },
      });

      // Override the retry behavior at the query client level.
      // TierProvider sets retry: 2, but the query function rejects instantly,
      // so we need enough time for react-query to exhaust retries.
      const wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>
          <TierProvider>{children}</TierProvider>
        </QueryClientProvider>
      );

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(
        () => {
          expect(result.current.loading).toBe(false);
        },
        { timeout: 10000 }
      );

      expect(result.current.error).toBeTruthy();
      // Should fall back to defaults
      expect(result.current.tier).toBe('enterprise');
    });
  });

  // ---------------------------------------------------------------------------
  // hasFeature
  // ---------------------------------------------------------------------------

  describe('hasFeature', () => {
    it('returns true for an included feature', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.hasFeature(Features.SIGNAL_HEALTH_MONITORING)).toBe(true);
    });

    it('returns false for a feature not in the tier', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.hasFeature(Features.PREDICTIVE_CHURN)).toBe(false);
    });

    it('returns false for any feature when features list is empty', () => {
      mockGet.mockReturnValue(new Promise(() => {}));
      const wrapper = createWrapper();

      const { result } = renderHook(() => useTier(), { wrapper });

      expect(result.current.hasFeature('any_feature')).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // checkLimit
  // ---------------------------------------------------------------------------

  describe('checkLimit', () => {
    it('returns true when current value is below the limit', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.checkLimit('max_ad_accounts', 2)).toBe(true);
    });

    it('returns false when current value equals the limit', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.checkLimit('max_ad_accounts', 3)).toBe(false);
    });

    it('returns false when current value exceeds the limit', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.checkLimit('max_ad_accounts', 5)).toBe(false);
    });

    it('returns true when limits are null (no limits loaded)', () => {
      mockGet.mockReturnValue(new Promise(() => {}));
      const wrapper = createWrapper();

      const { result } = renderHook(() => useTier(), { wrapper });

      expect(result.current.checkLimit('max_users', 100)).toBe(true);
    });
  });

  // ---------------------------------------------------------------------------
  // getRemainingLimit
  // ---------------------------------------------------------------------------

  describe('getRemainingLimit', () => {
    it('returns remaining capacity correctly', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.getRemainingLimit('max_ad_accounts', 1)).toBe(2);
    });

    it('returns 0 when at the limit', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.getRemainingLimit('max_ad_accounts', 3)).toBe(0);
    });

    it('returns 0 when over the limit (never negative)', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.getRemainingLimit('max_ad_accounts', 10)).toBe(0);
    });

    it('returns 999999 when limits are null', () => {
      mockGet.mockReturnValue(new Promise(() => {}));
      const wrapper = createWrapper();

      const { result } = renderHook(() => useTier(), { wrapper });

      expect(result.current.getRemainingLimit('max_users', 50)).toBe(999999);
    });
  });

  // ---------------------------------------------------------------------------
  // isAtLeastTier
  // ---------------------------------------------------------------------------

  describe('isAtLeastTier', () => {
    it('enterprise is at least starter', async () => {
      const wrapper = createWrapper(enterpriseTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.isAtLeastTier('starter')).toBe(true);
    });

    it('enterprise is at least professional', async () => {
      const wrapper = createWrapper(enterpriseTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.isAtLeastTier('professional')).toBe(true);
    });

    it('enterprise is at least enterprise', async () => {
      const wrapper = createWrapper(enterpriseTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.isAtLeastTier('enterprise')).toBe(true);
    });

    it('starter is NOT at least professional', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.isAtLeastTier('professional')).toBe(false);
    });

    it('starter is NOT at least enterprise', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.isAtLeastTier('enterprise')).toBe(false);
    });

    it('starter is at least starter', async () => {
      const wrapper = createWrapper(starterTierInfo);

      const { result } = renderHook(() => useTier(), { wrapper });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.isAtLeastTier('starter')).toBe(true);
    });
  });

  // ---------------------------------------------------------------------------
  // Provider rendering
  // ---------------------------------------------------------------------------

  describe('Provider rendering', () => {
    it('renders children correctly', async () => {
      mockGet.mockResolvedValue({ data: enterpriseTierInfo });
      const queryClient = createQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <TierProvider>
            <div data-testid="child">Content</div>
          </TierProvider>
        </QueryClientProvider>
      );

      expect(screen.getByTestId('child')).toBeDefined();
      expect(screen.getByText('Content')).toBeDefined();
    });
  });

  // ---------------------------------------------------------------------------
  // FeatureGate component
  // ---------------------------------------------------------------------------

  describe('FeatureGate component', () => {
    it('renders children when feature is available', async () => {
      mockGet.mockResolvedValue({ data: starterTierInfo });
      const queryClient = createQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <TierProvider>
            <FeatureGate feature={Features.SIGNAL_HEALTH_MONITORING}>
              <div data-testid="gated-content">Visible</div>
            </FeatureGate>
          </TierProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('gated-content')).toBeDefined();
      });
    });

    it('renders fallback when feature is not available', async () => {
      mockGet.mockResolvedValue({ data: starterTierInfo });
      const queryClient = createQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <TierProvider>
            <FeatureGate
              feature={Features.PREDICTIVE_CHURN}
              fallback={<div data-testid="fallback">Upgrade needed</div>}
            >
              <div data-testid="gated-content">Should not show</div>
            </FeatureGate>
          </TierProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('fallback')).toBeDefined();
      });

      expect(screen.queryByTestId('gated-content')).toBeNull();
    });

    it('renders nothing when feature is not available and no fallback', async () => {
      mockGet.mockResolvedValue({ data: starterTierInfo });
      const queryClient = createQueryClient();

      const { container } = render(
        <QueryClientProvider client={queryClient}>
          <TierProvider>
            <FeatureGate feature={Features.PREDICTIVE_CHURN}>
              <div data-testid="gated-content">Should not show</div>
            </FeatureGate>
          </TierProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.queryByTestId('gated-content')).toBeNull();
      });
    });
  });

  // ---------------------------------------------------------------------------
  // TierGate component
  // ---------------------------------------------------------------------------

  describe('TierGate component', () => {
    it('renders children when tier meets minimum', async () => {
      mockGet.mockResolvedValue({ data: enterpriseTierInfo });
      const queryClient = createQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <TierProvider>
            <TierGate minimumTier="professional">
              <div data-testid="tier-content">Enterprise content</div>
            </TierGate>
          </TierProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('tier-content')).toBeDefined();
      });
    });

    it('renders fallback when tier is below minimum', async () => {
      mockGet.mockResolvedValue({ data: starterTierInfo });
      const queryClient = createQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <TierProvider>
            <TierGate
              minimumTier="enterprise"
              fallback={<div data-testid="tier-fallback">Upgrade</div>}
            >
              <div data-testid="tier-content">Should not show</div>
            </TierGate>
          </TierProvider>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('tier-fallback')).toBeDefined();
      });

      expect(screen.queryByTestId('tier-content')).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // UpgradePrompt component
  // ---------------------------------------------------------------------------

  describe('UpgradePrompt component', () => {
    it('renders upgrade prompt with required tier', async () => {
      mockGet.mockResolvedValue({ data: starterTierInfo });
      const queryClient = createQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <TierProvider>
            <UpgradePrompt feature="predictive_churn" requiredTier="enterprise" />
          </TierProvider>
        </QueryClientProvider>
      );

      expect(screen.getByText('Upgrade Required')).toBeDefined();
      expect(screen.getByText(/enterprise/i)).toBeDefined();
      expect(screen.getByText('Upgrade Now')).toBeDefined();
    });

    it('renders upgrade prompt without specific tier', async () => {
      mockGet.mockResolvedValue({ data: starterTierInfo });
      const queryClient = createQueryClient();

      render(
        <QueryClientProvider client={queryClient}>
          <TierProvider>
            <UpgradePrompt feature="some_feature" />
          </TierProvider>
        </QueryClientProvider>
      );

      expect(screen.getByText(/a higher/i)).toBeDefined();
    });
  });

  // ---------------------------------------------------------------------------
  // Features constants
  // ---------------------------------------------------------------------------

  describe('Features constants', () => {
    it('has expected starter features defined', () => {
      expect(Features.AD_ACCOUNTS_BASIC).toBe('ad_accounts_basic');
      expect(Features.SIGNAL_HEALTH_MONITORING).toBe('signal_health_monitoring');
      expect(Features.ANOMALY_DETECTION).toBe('anomaly_detection');
    });

    it('has expected enterprise features defined', () => {
      expect(Features.PREDICTIVE_CHURN).toBe('predictive_churn');
      expect(Features.CUSTOM_AUTOPILOT_RULES).toBe('custom_autopilot_rules');
      expect(Features.WHAT_IF_SIMULATOR).toBe('what_if_simulator');
    });
  });
});
