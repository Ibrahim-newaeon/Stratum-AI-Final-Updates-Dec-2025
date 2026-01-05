/**
 * Stratum AI - Digital Assets API
 *
 * Digital Asset Management endpoints with fatigue scoring
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse, PaginatedResponse } from './client'

// Types
export type AssetType = 'image' | 'video' | 'carousel' | 'text' | 'html5'
export type AssetStatus = 'active' | 'paused' | 'archived'
export type FatigueStatus = 'fresh' | 'moderate' | 'fatigued' | 'critical'

export interface Asset {
  id: string
  tenantId: number
  name: string
  type: AssetType
  status: AssetStatus
  url: string
  thumbnailUrl: string | null
  folderId: string | null
  platforms: string[]
  campaignIds: string[]
  createdAt: string
  updatedAt: string
  meta: {
    width?: number
    height?: number
    duration?: number
    size?: number
    format?: string
  }
}

export interface AssetFatigue {
  assetId: string
  score: number // 0-100, higher = more fatigued
  status: FatigueStatus
  frequency: number
  impressions: number
  uniqueReach: number
  lastCalculated: string
  trend: 'increasing' | 'decreasing' | 'stable'
  recommendedAction: string | null
}

export interface AssetWithFatigue extends Asset {
  fatigue: AssetFatigue | null
}

export interface AssetFolder {
  id: string
  tenantId: number
  name: string
  parentId: string | null
  assetCount: number
  createdAt: string
}

export interface AssetFilters {
  type?: AssetType
  status?: AssetStatus
  fatigueStatus?: FatigueStatus
  folderId?: string
  platform?: string
  campaignId?: string
  search?: string
  skip?: number
  limit?: number
}

export interface CreateAssetRequest {
  name: string
  type: AssetType
  url: string
  thumbnailUrl?: string
  folderId?: string
  platforms?: string[]
  meta?: Record<string, unknown>
}

export interface UpdateAssetRequest {
  name?: string
  status?: AssetStatus
  folderId?: string
  platforms?: string[]
}

// API Functions
export const assetsApi = {
  /**
   * Get all assets with optional filters
   */
  getAssets: async (filters: AssetFilters = {}): Promise<PaginatedResponse<AssetWithFatigue>> => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<AssetWithFatigue>>>(
      '/assets',
      { params: filters }
    )
    return response.data.data
  },

  /**
   * Get a single asset by ID
   */
  getAsset: async (id: string): Promise<AssetWithFatigue> => {
    const response = await apiClient.get<ApiResponse<AssetWithFatigue>>(`/assets/${id}`)
    return response.data.data
  },

  /**
   * Create a new asset
   */
  createAsset: async (data: CreateAssetRequest): Promise<Asset> => {
    const response = await apiClient.post<ApiResponse<Asset>>('/assets', data)
    return response.data.data
  },

  /**
   * Upload an asset file
   */
  uploadAsset: async (file: File, folderId?: string): Promise<Asset> => {
    const formData = new FormData()
    formData.append('file', file)
    if (folderId) formData.append('folder_id', folderId)

    const response = await apiClient.post<ApiResponse<Asset>>('/assets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data.data
  },

  /**
   * Update an existing asset
   */
  updateAsset: async (id: string, data: UpdateAssetRequest): Promise<Asset> => {
    const response = await apiClient.patch<ApiResponse<Asset>>(`/assets/${id}`, data)
    return response.data.data
  },

  /**
   * Delete an asset
   */
  deleteAsset: async (id: string): Promise<void> => {
    await apiClient.delete(`/assets/${id}`)
  },

  /**
   * Get asset folders
   */
  getFolders: async (parentId?: string): Promise<AssetFolder[]> => {
    const params = parentId ? { parent_id: parentId } : {}
    const response = await apiClient.get<ApiResponse<AssetFolder[]>>('/assets/folders', { params })
    return response.data.data
  },

  /**
   * Create a folder
   */
  createFolder: async (name: string, parentId?: string): Promise<AssetFolder> => {
    const response = await apiClient.post<ApiResponse<AssetFolder>>('/assets/folders', {
      name,
      parent_id: parentId,
    })
    return response.data.data
  },

  /**
   * Get fatigued assets
   */
  getFatiguedAssets: async (
    minScore: number = 60,
    limit: number = 10
  ): Promise<AssetWithFatigue[]> => {
    const response = await apiClient.get<ApiResponse<AssetWithFatigue[]>>('/assets/fatigued', {
      params: { min_score: minScore, limit },
    })
    return response.data.data
  },

  /**
   * Calculate fatigue for an asset
   */
  calculateFatigue: async (id: string): Promise<AssetFatigue> => {
    const response = await apiClient.post<ApiResponse<AssetFatigue>>(`/assets/${id}/fatigue`)
    return response.data.data
  },

  /**
   * Bulk archive assets
   */
  bulkArchive: async (ids: string[]): Promise<Asset[]> => {
    const response = await apiClient.post<ApiResponse<Asset[]>>('/assets/bulk/archive', { ids })
    return response.data.data
  },
}

// React Query Hooks

export function useAssets(filters: AssetFilters = {}) {
  return useQuery({
    queryKey: ['assets', filters],
    queryFn: () => assetsApi.getAssets(filters),
    staleTime: 30 * 1000,
  })
}

export function useAsset(id: string) {
  return useQuery({
    queryKey: ['assets', id],
    queryFn: () => assetsApi.getAsset(id),
    enabled: !!id,
  })
}

export function useCreateAsset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: assetsApi.createAsset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
  })
}

export function useUploadAsset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ file, folderId }: { file: File; folderId?: string }) =>
      assetsApi.uploadAsset(file, folderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
  })
}

export function useUpdateAsset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateAssetRequest }) =>
      assetsApi.updateAsset(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
      queryClient.invalidateQueries({ queryKey: ['assets', variables.id] })
    },
  })
}

export function useDeleteAsset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: assetsApi.deleteAsset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
  })
}

export function useAssetFolders(parentId?: string) {
  return useQuery({
    queryKey: ['assets', 'folders', parentId],
    queryFn: () => assetsApi.getFolders(parentId),
  })
}

export function useCreateFolder() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, parentId }: { name: string; parentId?: string }) =>
      assetsApi.createFolder(name, parentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets', 'folders'] })
    },
  })
}

export function useFatiguedAssets(minScore: number = 60, limit: number = 10) {
  return useQuery({
    queryKey: ['assets', 'fatigued', minScore, limit],
    queryFn: () => assetsApi.getFatiguedAssets(minScore, limit),
    staleTime: 5 * 60 * 1000,
  })
}

export function useCalculateFatigue() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: assetsApi.calculateFatigue,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['assets', id] })
      queryClient.invalidateQueries({ queryKey: ['assets', 'fatigued'] })
    },
  })
}

export function useBulkArchiveAssets() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: assetsApi.bulkArchive,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] })
    },
  })
}
