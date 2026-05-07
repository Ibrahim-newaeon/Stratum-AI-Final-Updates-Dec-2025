/**
 * Tier API — wraps /tier/all and /tier/compare for the BillingSettings
 * "Compare plans" surface. /tier/current is already covered by TierContext.
 */

import { useQuery } from '@tanstack/react-query';
import api from './client';
import type { TierInfo, SubscriptionTier } from '@/contexts/TierContext';

export interface AvailableTier extends TierInfo {
  is_current: boolean;
}

export interface AvailableTiersResponse {
  current_tier: SubscriptionTier;
  tiers: AvailableTier[];
}

export interface TierComparisonResponse {
  features: Record<string, Record<SubscriptionTier, boolean>>;
  limits: Record<SubscriptionTier, Record<string, number | string | null>>;
}

export function useAvailableTiers() {
  return useQuery({
    queryKey: ['tier', 'all'],
    queryFn: async () => {
      const res = await api.get<AvailableTiersResponse>('/tier/all');
      return res.data;
    },
    staleTime: 10 * 60 * 1000,
  });
}

export function useTierComparison() {
  return useQuery({
    queryKey: ['tier', 'compare'],
    queryFn: async () => {
      const res = await api.get<TierComparisonResponse>('/tier/compare');
      return res.data;
    },
    staleTime: 10 * 60 * 1000,
  });
}
