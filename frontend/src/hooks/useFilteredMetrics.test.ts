/**
 * useFilteredMetrics Hook Tests
 *
 * Tests the metric filtering logic that combines cost toggle,
 * hidden metrics, and platform/category filters.
 *
 * External dependencies (usePriceMetrics, useMetricVisibility, METRIC_REGISTRY)
 * are fully mocked so we test only the filtering logic in isolation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mock dependencies before importing the hook
//
// vi.mock() factories are hoisted above variable declarations. Use
// vi.hoisted() so mock data and spy functions are available when the
// factory runs, preventing TDZ / undefined references that cause OOM.
// ---------------------------------------------------------------------------

const { mockShowPriceMetrics, mockVisibilityData, MOCK_METRICS } = vi.hoisted(() => {
  const mockShowPriceMetrics = vi.fn(() => true);
  const mockVisibilityData = vi.fn(() => ({
    data: { hidden_metrics: [] as string[] },
    isLoading: false,
  }));

  const MOCK_METRICS = {
    impressions: {
      id: 'impressions',
      label: 'Impressions',
      category: 'performance',
      platforms: ['meta', 'google'],
      isPriceMetric: false,
    },
    spend: {
      id: 'spend',
      label: 'Spend',
      category: 'cost',
      platforms: ['meta', 'google', 'tiktok'],
      isPriceMetric: true,
    },
    roas: {
      id: 'roas',
      label: 'ROAS',
      category: 'cost',
      platforms: ['meta', 'google'],
      isPriceMetric: true,
    },
    clicks: {
      id: 'clicks',
      label: 'Clicks',
      category: 'performance',
      platforms: ['meta', 'google', 'snapchat'],
      isPriceMetric: false,
    },
    conversions: {
      id: 'conversions',
      label: 'Conversions',
      category: 'conversion',
      platforms: ['tiktok'],
      isPriceMetric: false,
    },
  };

  return { mockShowPriceMetrics, mockVisibilityData, MOCK_METRICS };
});

vi.mock('@/hooks/usePriceMetrics', () => ({
  usePriceMetrics: () => ({ showPriceMetrics: mockShowPriceMetrics() }),
}));

vi.mock('@/api/dashboard', () => ({
  useMetricVisibility: () => {
    const result = mockVisibilityData();
    return { data: result.data, isLoading: result.isLoading };
  },
}));

vi.mock('@/constants/metrics', () => ({
  METRIC_REGISTRY: MOCK_METRICS,
}));

// Import after mocks are set up
import { useFilteredMetrics } from './useFilteredMetrics';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useFilteredMetrics', () => {
  beforeEach(() => {
    mockShowPriceMetrics.mockReturnValue(true);
    mockVisibilityData.mockReturnValue({ data: { hidden_metrics: [] }, isLoading: false });
  });

  // -------------------------------------------------------------------------
  // No filters
  // -------------------------------------------------------------------------

  describe('No Filters', () => {
    it('should return all metrics when no filters applied and price toggle is on', () => {
      const { result } = renderHook(() => useFilteredMetrics());

      expect(result.current.metrics).toHaveLength(5);
      expect(result.current.showPriceMetrics).toBe(true);
      expect(result.current.isLoading).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // Category filter
  // -------------------------------------------------------------------------

  describe('Category Filter', () => {
    it('should filter metrics by category', () => {
      const { result } = renderHook(() =>
        useFilteredMetrics({ categories: ['performance'] })
      );

      expect(result.current.metrics).toHaveLength(2);
      expect(result.current.metrics.every((m: any) => m.category === 'performance')).toBe(true);
    });

    it('should support multiple categories', () => {
      const { result } = renderHook(() =>
        useFilteredMetrics({ categories: ['performance', 'conversion'] })
      );

      expect(result.current.metrics).toHaveLength(3);
    });

    it('should return empty array for unknown category', () => {
      const { result } = renderHook(() =>
        useFilteredMetrics({ categories: ['nonexistent' as any] })
      );

      expect(result.current.metrics).toHaveLength(0);
    });
  });

  // -------------------------------------------------------------------------
  // Platform filter
  // -------------------------------------------------------------------------

  describe('Platform Filter', () => {
    it('should filter metrics by platform', () => {
      const { result } = renderHook(() =>
        useFilteredMetrics({ platform: 'tiktok' as any })
      );

      // spend (tiktok) + conversions (tiktok)
      expect(result.current.metrics).toHaveLength(2);
    });

    it('should filter metrics for snapchat platform', () => {
      const { result } = renderHook(() =>
        useFilteredMetrics({ platform: 'snapchat' as any })
      );

      // Only clicks has snapchat
      expect(result.current.metrics).toHaveLength(1);
      expect(result.current.metrics[0].id).toBe('clicks');
    });
  });

  // -------------------------------------------------------------------------
  // Hidden metrics
  // -------------------------------------------------------------------------

  describe('Hidden Metrics', () => {
    it('should exclude hidden metrics', () => {
      mockVisibilityData.mockReturnValue({
        data: { hidden_metrics: ['impressions', 'clicks'] },
        isLoading: false,
      });

      const { result } = renderHook(() => useFilteredMetrics());

      expect(result.current.metrics).toHaveLength(3);
      expect(result.current.metrics.find((m: any) => m.id === 'impressions')).toBeUndefined();
      expect(result.current.metrics.find((m: any) => m.id === 'clicks')).toBeUndefined();
    });

    it('should handle empty hidden metrics array', () => {
      mockVisibilityData.mockReturnValue({
        data: { hidden_metrics: [] },
        isLoading: false,
      });

      const { result } = renderHook(() => useFilteredMetrics());

      expect(result.current.metrics).toHaveLength(5);
    });
  });

  // -------------------------------------------------------------------------
  // Price/cost toggle
  // -------------------------------------------------------------------------

  describe('Price Metrics Toggle', () => {
    it('should exclude price metrics when toggle is off', () => {
      mockShowPriceMetrics.mockReturnValue(false);

      const { result } = renderHook(() => useFilteredMetrics());

      // Only non-price: impressions, clicks, conversions
      expect(result.current.metrics).toHaveLength(3);
      expect(result.current.metrics.every((m: any) => !m.isPriceMetric)).toBe(true);
    });

    it('should include price metrics when toggle is on', () => {
      mockShowPriceMetrics.mockReturnValue(true);

      const { result } = renderHook(() => useFilteredMetrics());

      const priceMetrics = result.current.metrics.filter((m: any) => m.isPriceMetric);
      expect(priceMetrics.length).toBe(2); // spend, roas
    });

    it('should force include price metrics when forceIncludePriceMetrics is true', () => {
      mockShowPriceMetrics.mockReturnValue(false);

      const { result } = renderHook(() =>
        useFilteredMetrics({ forceIncludePriceMetrics: true })
      );

      expect(result.current.metrics).toHaveLength(5);
    });
  });

  // -------------------------------------------------------------------------
  // Combined filters
  // -------------------------------------------------------------------------

  describe('Combined Filters', () => {
    it('should apply category + platform filters together', () => {
      const { result } = renderHook(() =>
        useFilteredMetrics({ categories: ['performance'], platform: 'meta' as any })
      );

      // performance + meta: impressions, clicks
      expect(result.current.metrics).toHaveLength(2);
    });

    it('should apply category + hidden + price toggle together', () => {
      mockShowPriceMetrics.mockReturnValue(false);
      mockVisibilityData.mockReturnValue({
        data: { hidden_metrics: ['clicks'] },
        isLoading: false,
      });

      const { result } = renderHook(() =>
        useFilteredMetrics({ categories: ['performance'] })
      );

      // performance = impressions, clicks
      // hidden = clicks removed
      // price toggle off = no change (both are non-price)
      // Result: impressions only
      expect(result.current.metrics).toHaveLength(1);
      expect(result.current.metrics[0].id).toBe('impressions');
    });
  });

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------

  describe('Loading State', () => {
    it('should expose isLoading from visibility query', () => {
      mockVisibilityData.mockReturnValue({
        data: null,
        isLoading: true,
      });

      const { result } = renderHook(() => useFilteredMetrics());

      expect(result.current.isLoading).toBe(true);
    });
  });
});
