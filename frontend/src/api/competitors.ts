/**
 * Stratum AI - Competitor Intelligence API
 *
 * Competitor monitoring and share of voice tracking
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, ApiResponse, PaginatedResponse } from './client';

// Types
export interface Competitor {
  id: string;
  tenantId: number;
  name: string;
  domain: string;
  country: string;
  platforms: string[];
  createdAt: string;
  updatedAt: string;
  lastRefreshedAt: string | null;
  isActive?: boolean;
  estimatedSpend?: number;
  shareOfVoice?: number;
  activeCreatives?: number;
  lastUpdated?: string;
}

export interface CompetitorMetrics {
  competitorId: string;
  date: string;
  platform: string;
  shareOfVoice: number;
  estimatedSpend: number;
  impressionShare: number;
  adCount: number;
  topKeywords: string[];
  sentiment: number; // -1 to 1
}

export interface ShareOfVoice {
  date: string;
  data: {
    competitorId: string;
    competitorName: string;
    share: number;
    trend: 'up' | 'down' | 'flat';
  }[];
  tenantShare: number;
}

export interface KeywordOverlap {
  keyword: string;
  competitorId: string;
  competitorName: string;
  yourPosition: number | null;
  competitorPosition: number;
  searchVolume: number;
  competitionLevel: 'low' | 'medium' | 'high';
}

export interface CompetitorFilters {
  platform?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export interface CreateCompetitorRequest {
  name: string;
  domain: string;
  country?: string;
  platforms?: string[];
}

export interface CompetitorScanRequest {
  domain: string;
  name: string;
  country?: string;
}

export interface CompetitorScanResult {
  domain: string;
  social_links: {
    facebook: string | null;
    instagram: string | null;
    twitter: string | null;
    linkedin: string | null;
    tiktok: string | null;
    youtube: string | null;
  };
  meta_title: string | null;
  meta_description: string | null;
  fb_page_name: string | null;
  ig_account_name: string | null;
  ad_library: {
    has_ads: boolean;
    ad_count: number;
    ads: Array<{
      id: string;
      page_name: string;
      page_id: string;
      creative_body: string;
      link_title: string;
      start_date: string;
      snapshot_url: string;
      platforms: string[];
      impressions: { lower_bound: string; upper_bound: string } | null;
    }>;
    search_url: string;
    search_query: string | null;
    page_id: string | null;
    page_name: string | null;
    error: string | null;
  };
  scanned_at: string;
  scrape_error: string | null;
}

// API Functions
export const competitorsApi = {
  /**
   * Get all competitors
   */
  getCompetitors: async (
    filters: CompetitorFilters = {}
  ): Promise<PaginatedResponse<Competitor>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<Competitor>>>(
      '/competitors',
      { params: filters }
    );
    return response.data.data;
  },

  /**
   * Get a single competitor
   */
  getCompetitor: async (id: string): Promise<Competitor> => {
    const response = await apiClient.get<ApiResponse<Competitor>>(`/competitors/${id}`);
    return response.data.data;
  },

  /**
   * Create a competitor
   */
  createCompetitor: async (data: CreateCompetitorRequest): Promise<Competitor> => {
    const response = await apiClient.post<ApiResponse<Competitor>>('/competitors', data);
    return response.data.data;
  },

  /**
   * Update a competitor
   */
  updateCompetitor: async (
    id: string,
    data: Partial<CreateCompetitorRequest>
  ): Promise<Competitor> => {
    const response = await apiClient.patch<ApiResponse<Competitor>>(`/competitors/${id}`, data);
    return response.data.data;
  },

  /**
   * Delete a competitor
   */
  deleteCompetitor: async (id: string): Promise<void> => {
    await apiClient.delete(`/competitors/${id}`);
  },

  /**
   * Get share of voice data
   */
  getShareOfVoice: async (
    startDate: string,
    endDate: string,
    platform?: string
  ): Promise<ShareOfVoice[]> => {
    const params: Record<string, string> = { start_date: startDate, end_date: endDate };
    if (platform) params.platform = platform;
    const response = await apiClient.get<ApiResponse<ShareOfVoice[]>>(
      '/competitors/share-of-voice',
      { params }
    );
    return response.data.data;
  },

  /**
   * Get competitor keywords
   */
  getCompetitorKeywords: async (id: string): Promise<KeywordOverlap[]> => {
    const response = await apiClient.get<ApiResponse<KeywordOverlap[]>>(
      `/competitors/${id}/keywords`
    );
    return response.data.data;
  },

  /**
   * Get competitor metrics
   */
  getCompetitorMetrics: async (
    id: string,
    startDate: string,
    endDate: string
  ): Promise<CompetitorMetrics[]> => {
    const response = await apiClient.get<ApiResponse<CompetitorMetrics[]>>(
      `/competitors/${id}/metrics`,
      { params: { start_date: startDate, end_date: endDate } }
    );
    return response.data.data;
  },

  /**
   * Refresh competitor data
   */
  refreshCompetitor: async (id: string): Promise<Competitor> => {
    const response = await apiClient.post<ApiResponse<Competitor>>(`/competitors/${id}/refresh`);
    return response.data.data;
  },

  /**
   * Scan a competitor: scrape website for social links + search Meta Ad Library
   */
  scanCompetitor: async (data: CompetitorScanRequest): Promise<CompetitorScanResult> => {
    const response = await apiClient.post<ApiResponse<CompetitorScanResult>>(
      '/competitors/scan',
      data
    );
    return response.data.data;
  },

  /**
   * Scan an existing tracked competitor
   */
  scanExistingCompetitor: async (id: string, country?: string): Promise<CompetitorScanResult> => {
    const params = country ? { country } : {};
    const response = await apiClient.post<ApiResponse<CompetitorScanResult>>(
      `/competitors/${id}/scan`,
      null,
      { params }
    );
    return response.data.data;
  },
};

// React Query Hooks

export function useCompetitors(filters: CompetitorFilters = {}) {
  return useQuery({
    queryKey: ['competitors', filters],
    queryFn: () => competitorsApi.getCompetitors(filters),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompetitor(id: string) {
  return useQuery({
    queryKey: ['competitors', id],
    queryFn: () => competitorsApi.getCompetitor(id),
    enabled: !!id,
  });
}

export function useCreateCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: competitorsApi.createCompetitor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
    },
  });
}

export function useUpdateCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<CreateCompetitorRequest> }) =>
      competitorsApi.updateCompetitor(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
      queryClient.invalidateQueries({ queryKey: ['competitors', variables.id] });
    },
  });
}

export function useDeleteCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: competitorsApi.deleteCompetitor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
    },
  });
}

export function useShareOfVoice(startDate: string, endDate: string, platform?: string) {
  return useQuery({
    queryKey: ['competitors', 'sov', startDate, endDate, platform],
    queryFn: () => competitorsApi.getShareOfVoice(startDate, endDate, platform),
    enabled: !!startDate && !!endDate,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCompetitorKeywords(id: string) {
  return useQuery({
    queryKey: ['competitors', id, 'keywords'],
    queryFn: () => competitorsApi.getCompetitorKeywords(id),
    enabled: !!id,
  });
}

export function useCompetitorMetrics(id: string, startDate: string, endDate: string) {
  return useQuery({
    queryKey: ['competitors', id, 'metrics', startDate, endDate],
    queryFn: () => competitorsApi.getCompetitorMetrics(id, startDate, endDate),
    enabled: !!id && !!startDate && !!endDate,
  });
}

export function useRefreshCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: competitorsApi.refreshCompetitor,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['competitors', id] });
    },
  });
}

export function useScanCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: competitorsApi.scanCompetitor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
    },
  });
}

export function useScanExistingCompetitor() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, country }: { id: string; country?: string }) =>
      competitorsApi.scanExistingCompetitor(id, country),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['competitors', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['competitors'] });
    },
  });
}
