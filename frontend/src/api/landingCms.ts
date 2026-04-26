/**
 * Stratum AI - Landing CMS API
 *
 * Public landing page and blog content.
 */

import { useQuery } from '@tanstack/react-query'
import { apiClient, ApiResponse } from './client'

// Types
export interface CMSPage {
  id: string
  title: string
  slug: string
  meta_title?: string
  meta_description?: string
  show_in_navigation: boolean
  navigation_label?: string
  navigation_order: number
  published_at?: string
  updated_at?: string
}

export interface CMSPageDetail extends CMSPage {
  content: string
  content_json?: Record<string, unknown>
}

export interface CMSPost {
  id: string
  title: string
  slug: string
  excerpt: string
  content_type?: string
  featured_image_url?: string
  is_featured: boolean
  author?: {
    name: string
    avatar_url?: string
  }
  category?: {
    name: string
    slug: string
  }
  tags: Array<{ name: string; slug: string }>
  published_at?: string
  reading_time_minutes?: number
}

export interface CMSPostDetail extends CMSPost {
  content: string
  content_json?: Record<string, unknown>
  og_image_url?: string
  meta_title?: string
  meta_description?: string
  updated_at?: string
}

export interface CMSCategory {
  id: string
  name: string
  slug: string
  color?: string
  icon?: string
  display_order: number
}

export interface CMSTag {
  id: string
  name: string
  slug: string
  usage_count: number
}

export interface PageFilters {
  skip?: number
  limit?: number
  navigation_only?: boolean
}

export interface PostFilters {
  skip?: number
  limit?: number
  category?: string
  tag?: string
  content_type?: string
  featured?: boolean
}

// API Functions
export const landingCmsApi = {
  getPages: async (filters: PageFilters = {}): Promise<{ pages: CMSPage[]; total: number; skip: number; limit: number }> => {
    const response = await apiClient.get<ApiResponse<{ pages: CMSPage[]; total: number; skip: number; limit: number }>>(
      '/landing-cms/pages',
      { params: filters }
    )
    return response.data.data
  },

  getPage: async (slug: string): Promise<CMSPageDetail> => {
    const response = await apiClient.get<ApiResponse<CMSPageDetail>>(`/landing-cms/pages/${slug}`)
    return response.data.data
  },

  getPosts: async (filters: PostFilters = {}): Promise<{ posts: CMSPost[]; total: number; skip: number; limit: number }> => {
    const response = await apiClient.get<ApiResponse<{ posts: CMSPost[]; total: number; skip: number; limit: number }>>(
      '/landing-cms/posts',
      { params: filters }
    )
    return response.data.data
  },

  getPost: async (slug: string): Promise<CMSPostDetail> => {
    const response = await apiClient.get<ApiResponse<CMSPostDetail>>(`/landing-cms/posts/${slug}`)
    return response.data.data
  },

  getCategories: async (): Promise<{ categories: CMSCategory[] }> => {
    const response = await apiClient.get<ApiResponse<{ categories: CMSCategory[] }>>('/landing-cms/categories')
    return response.data.data
  },

  getTags: async (): Promise<{ tags: CMSTag[] }> => {
    const response = await apiClient.get<ApiResponse<{ tags: CMSTag[] }>>('/landing-cms/tags')
    return response.data.data
  },
}

// React Query Hooks
export function useLandingPages(filters: PageFilters = {}) {
  return useQuery({
    queryKey: ['landing-cms', 'pages', filters],
    queryFn: () => landingCmsApi.getPages(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useLandingPage(slug: string) {
  return useQuery({
    queryKey: ['landing-cms', 'pages', slug],
    queryFn: () => landingCmsApi.getPage(slug),
    enabled: !!slug,
    staleTime: 5 * 60 * 1000,
  })
}

export function useLandingPosts(filters: PostFilters = {}) {
  return useQuery({
    queryKey: ['landing-cms', 'posts', filters],
    queryFn: () => landingCmsApi.getPosts(filters),
    staleTime: 5 * 60 * 1000,
  })
}

export function useLandingPost(slug: string) {
  return useQuery({
    queryKey: ['landing-cms', 'posts', slug],
    queryFn: () => landingCmsApi.getPost(slug),
    enabled: !!slug,
    staleTime: 5 * 60 * 1000,
  })
}

export function useLandingCategories() {
  return useQuery({
    queryKey: ['landing-cms', 'categories'],
    queryFn: landingCmsApi.getCategories,
    staleTime: 5 * 60 * 1000,
  })
}

export function useLandingTags() {
  return useQuery({
    queryKey: ['landing-cms', 'tags'],
    queryFn: landingCmsApi.getTags,
    staleTime: 5 * 60 * 1000,
  })
}
