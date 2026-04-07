/**
 * usePriceMetrics Hook Tests
 *
 * Tests for the price metrics toggle that reads the show_price_metrics feature flag.
 * Mocks the featureFlagsStore to control the toggle state.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mock featureFlagsStore
// ---------------------------------------------------------------------------

let mockCanFeatureValue = true;

vi.mock('@/stores/featureFlagsStore', () => ({
  useCanFeature: (flag: string) => {
    if (flag === 'show_price_metrics') return mockCanFeatureValue;
    return false;
  },
}));

import { usePriceMetrics } from './usePriceMetrics';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('usePriceMetrics', () => {
  beforeEach(() => {
    mockCanFeatureValue = true;
  });

  it('should return showPriceMetrics as true when feature flag is enabled', () => {
    mockCanFeatureValue = true;
    const { result } = renderHook(() => usePriceMetrics());

    expect(result.current.showPriceMetrics).toBe(true);
  });

  it('should return showPriceMetrics as false when feature flag is disabled', () => {
    mockCanFeatureValue = false;
    const { result } = renderHook(() => usePriceMetrics());

    expect(result.current.showPriceMetrics).toBe(false);
  });

  it('should return an object with showPriceMetrics property', () => {
    const { result } = renderHook(() => usePriceMetrics());

    expect(result.current).toHaveProperty('showPriceMetrics');
    expect(typeof result.current.showPriceMetrics).toBe('boolean');
  });

  it('should reflect changes when the feature flag toggles', () => {
    mockCanFeatureValue = true;
    const { result, rerender } = renderHook(() => usePriceMetrics());

    expect(result.current.showPriceMetrics).toBe(true);

    mockCanFeatureValue = false;
    rerender();

    expect(result.current.showPriceMetrics).toBe(false);
  });

  it('should read the show_price_metrics flag specifically', () => {
    // When the flag is on, price metrics are shown
    mockCanFeatureValue = true;
    const { result } = renderHook(() => usePriceMetrics());
    expect(result.current.showPriceMetrics).toBe(true);
  });
});
