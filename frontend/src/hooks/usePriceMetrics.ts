/**
 * Stratum AI - Price Metrics Toggle Hook
 *
 * Reads the show_price_metrics feature flag to control
 * visibility of price-related columns and cards
 * (spend, revenue, ROAS, CPA, budget, cost, profit, margin).
 */

import { useCanFeature } from '@/stores/featureFlagsStore';

export function usePriceMetrics() {
  const showPriceMetrics = useCanFeature('show_price_metrics');
  return { showPriceMetrics };
}
