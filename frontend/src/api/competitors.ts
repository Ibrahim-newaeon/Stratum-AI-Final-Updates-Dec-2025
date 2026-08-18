/**
 * Stratum AI - Competitor Intelligence API
 *
 * Competitor monitoring, limited to what the scanner can actually source:
 * the competitor's own site metadata and social links, plus Meta Ad Library
 * activity. Estimated traffic, share of voice, keyword sets and ad-spend
 * estimates need a paid ad-intelligence provider that is not wired, so the
 * API does not serve them and this client does not model them.
 *
 * Fields are snake_case because that is what the API returns. The previous
 * version of this interface used camelCase keys the backend has never sent
 * (`estimatedSpend`, `shareOfVoice`, `activeCreatives`), so every read was
 * `undefined` and every consumer coerced it to 0.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse, PaginatedResponse } from './client'

// Types
/** Where a competitor's current record came from. */
export type CompetitorDataSource = 'meta_ad_library' | 'website_scrape' | 'unavailable'

export interface Competitor {
  id: number
  tenant_id: number
  domain: string
  name: string | null
  is_primary: boolean
  fb_page_name: string | null

  /** Scraped from the competitor's own site. */
  meta_title: string | null
  meta_description: string | null
  social_links: Record<string, string | null> | null

  /**
   * Meta Ad Library. `null` means the lookup could not run (no Graph token,
   * or an API error) — which is "unknown", NOT "no ads running". Render the
   * two differently.
   */
  ad_creatives_count: number | null
  detected_ad_platforms: string[] | null

  data_source: CompetitorDataSource
  last_fetched_at: string | null
  fetch_error: string | null

  created_at: string
  updated_at: string
}

export interface CompetitorFilters {
  platform?: string
  search?: string
  skip?: number
  limit?: number
}

export interface CreateCompetitorRequest {
  name: string
  domain: string
  country?: string
  platforms?: string[]
}

export interface ScanCompetitorRequest {
  domain: string
  name: string
  country: string
  fb_page_name?: string
}

export interface CompetitorScanResult {
  domain: string
  social_links: {
    facebook: string | null
    instagram: string | null
    twitter: string | null
    linkedin: string | null
    tiktok: string | null
    youtube: string | null
  }
  meta_title: string | null
  meta_description: string | null
  fb_page_name: string | null
  ig_account_name: string | null
  ad_library: {
    has_ads: boolean
    ad_count: number
    ads: Array<{
      id?: string
      page_name?: string
      page_id?: string
      creative_body?: string
      link_title?: string
      start_date?: string
      snapshot_url?: string
      platforms?: string[]
      impressions?: unknown
    }>
    search_url: string
    search_query: string | null
    page_id: string | null
    page_name: string | null
    error: string | null
  }
  scanned_at: string
  scrape_error: string | null
}

// API Functions
export const competitorsApi = {
  /**
   * Get all competitors
   */
  getCompetitors: async (filters: CompetitorFilters = {}): Promise<PaginatedResponse<Competitor>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<Competitor>>>(
      '/competitors',
      { params: filters }
    )
    return response.data.data
  },

  /**
   * Get a single competitor
   */
  getCompetitor: async (id: number): Promise<Competitor> => {
    const response = await apiClient.get<ApiResponse<Competitor>>(`/competitors/${id}`)
    return response.data.data
  },

  /**
   * Create a competitor
   */
  createCompetitor: async (data: CreateCompetitorRequest): Promise<Competitor> => {
    const response = await apiClient.post<ApiResponse<Competitor>>('/competitors', data)
    return response.data.data
  },

  /**
   * Update a competitor
   */
  updateCompetitor: async (id: number, data: Partial<CreateCompetitorRequest>): Promise<Competitor> => {
    const response = await apiClient.patch<ApiResponse<Competitor>>(`/competitors/${id}`, data)
    return response.data.data
  },

  /**
   * Delete a competitor
   */
  deleteCompetitor: async (id: number): Promise<void> => {
    await apiClient.delete(`/competitors/${id}`)
  },

  /**
   * Refresh competitor data
   */
  refreshCompetitor: async (id: number): Promise<Competitor> => {
    const response = await apiClient.post<ApiResponse<Competitor>>(`/competitors/${id}/refresh`)
    return response.data.data
  },

  /**
   * Scan a competitor website and search Meta Ad Library
   */
  scanCompetitor: async (data: ScanCompetitorRequest): Promise<CompetitorScanResult> => {
    const response = await apiClient.post<ApiResponse<CompetitorScanResult>>('/competitors/scan', data)
    return response.data.data
  },
}

// React Query Hooks

export function useCompetitors(filters: CompetitorFilters = {}) {
  return useQuery({
    queryKey: ['competitors', filters],
    queryFn: () => competitorsApi.getCompetitors(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useCompetitor(id: number) {
  return useQuery({
    queryKey: ['competitors', id],
    queryFn: () => competitorsApi.getCompetitor(id),
    enabled: !!id,
  })
}

export function useCreateCompetitor() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: competitorsApi.createCompetitor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
    },
  })
}

export function useUpdateCompetitor() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<CreateCompetitorRequest> }) =>
      competitorsApi.updateCompetitor(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
      queryClient.invalidateQueries({ queryKey: ['competitors', variables.id] })
    },
  })
}

export function useDeleteCompetitor() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: competitorsApi.deleteCompetitor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
    },
  })
}

export function useRefreshCompetitor() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: competitorsApi.refreshCompetitor,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['competitors', id] })
    },
  })
}

export function useScanCompetitor() {
  return useMutation({
    mutationFn: competitorsApi.scanCompetitor,
  })
}
