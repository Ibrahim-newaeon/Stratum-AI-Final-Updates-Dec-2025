/**
 * Stratum AI - Filtered Metrics Hook
 *
 * Combines the cost toggle (usePriceMetrics), hidden metrics (useMetricVisibility),
 * and optional platform / category filters to return a filtered list of metrics.
 */

import { useMemo } from 'react';
import { usePriceMetrics } from '@/hooks/usePriceMetrics';
import { useMetricVisibility } from '@/api/dashboard';
import {
  METRIC_REGISTRY,
  type MetricDefinition,
  type MetricCategory,
  type AdPlatform,
} from '@/constants/metrics';

export interface UseFilteredMetricsOptions {
  /** Only include metrics from these categories */
  categories?: MetricCategory[];
  /** Only include metrics available on this platform */
  platform?: AdPlatform;
  /** Include price metrics regardless of cost toggle state */
  forceIncludePriceMetrics?: boolean;
}

export interface UseFilteredMetricsReturn {
  /** Filtered metric definitions */
  metrics: MetricDefinition[];
  /** Whether price metrics are currently shown */
  showPriceMetrics: boolean;
  /** Loading state */
  isLoading: boolean;
}

export function useFilteredMetrics(
  options: UseFilteredMetricsOptions = {}
): UseFilteredMetricsReturn {
  const { categories, platform, forceIncludePriceMetrics = false } = options;
  const { showPriceMetrics } = usePriceMetrics();
  const { data: visibility, isLoading } = useMetricVisibility();

  const hiddenMetrics = visibility?.hidden_metrics || [];

  const metrics = useMemo(() => {
    let result = Object.values(METRIC_REGISTRY);

    // Filter by category
    if (categories && categories.length > 0) {
      result = result.filter((m) => categories.includes(m.category));
    }

    // Filter by platform
    if (platform) {
      result = result.filter((m) => m.platforms.includes(platform));
    }

    // Filter out hidden metrics
    if (hiddenMetrics.length > 0) {
      result = result.filter((m) => !hiddenMetrics.includes(m.id));
    }

    // Apply cost toggle logic
    if (!showPriceMetrics && !forceIncludePriceMetrics) {
      result = result.filter((m) => {
        // Remove price metrics when cost toggle is OFF
        if (m.isPriceMetric) return false;
        // Keep non-price metrics (showWithCostTrigger metrics show regardless)
        return true;
      });
    }

    return result;
  }, [categories, platform, hiddenMetrics, showPriceMetrics, forceIncludePriceMetrics]);

  return { metrics, showPriceMetrics, isLoading };
}
