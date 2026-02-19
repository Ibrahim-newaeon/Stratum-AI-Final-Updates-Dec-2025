/**
 * Stratum AI - Profit ROAS API
 *
 * Handles products, COGS, margins, and profit calculations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiResponse, PaginatedResponse } from './client'

// =============================================================================
// Types
// =============================================================================

export type MarginType = 'percentage' | 'fixed'
export type ProductStatus = 'active' | 'inactive' | 'discontinued'
export type COGSSource = 'manual' | 'csv_upload' | 'api_sync' | 'calculated'

export interface ProductCatalog {
  id: string
  tenantId: number
  sku: string
  name: string
  description?: string
  category?: string
  subcategory?: string
  brand?: string
  status: ProductStatus
  defaultCogs: number
  defaultMarginPct: number
  currency: string
  unitOfMeasure?: string
  tags: string[]
  metadata: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

export interface ProductMargin {
  id: string
  tenantId: number
  productId: string
  product?: ProductCatalog
  effectiveDate: string
  endDate?: string
  cogs: number
  cogsSource: COGSSource
  marginType: MarginType
  marginValue: number
  marginPct: number
  sellingPrice?: number
  supplierCost?: number
  shippingCost?: number
  overheadAllocation?: number
  notes?: string
  createdAt: string
  updatedAt: string
}

export interface MarginRule {
  id: string
  tenantId: number
  name: string
  description?: string
  priority: number
  isActive: boolean
  conditions: MarginCondition[]
  marginType: MarginType
  marginValue: number
  appliesTo: 'all' | 'category' | 'product' | 'platform' | 'campaign'
  targetIds: string[]
  effectiveFrom: string
  effectiveTo?: string
  createdAt: string
  updatedAt: string
}

export interface MarginCondition {
  field: string
  operator: 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte' | 'in' | 'contains'
  value: string | number | boolean | string[]
}

export interface DailyProfitMetrics {
  id: string
  tenantId: number
  date: string
  platform?: string
  campaignId?: string
  productId?: string
  revenue: number
  cogs: number
  grossProfit: number
  adSpend: number
  netProfit: number
  grossMarginPct: number
  netMarginPct: number
  roas: number
  trueRoas: number
  profitRoas: number
  unitsSold: number
  avgOrderValue: number
  costPerAcquisition: number
}

export interface ProfitReport {
  id: string
  tenantId: number
  reportDate: string
  periodStart: string
  periodEnd: string
  groupBy: string
  totalRevenue: number
  totalCogs: number
  totalGrossProfit: number
  totalAdSpend: number
  totalNetProfit: number
  avgGrossMargin: number
  avgNetMargin: number
  overallRoas: number
  overallTrueRoas: number
  breakdown: ProfitBreakdown[]
  createdAt: string
}

export interface ProfitBreakdown {
  dimension: string
  dimensionValue: string
  revenue: number
  cogs: number
  grossProfit: number
  adSpend: number
  netProfit: number
  grossMarginPct: number
  netMarginPct: number
  roas: number
  trueRoas: number
}

export interface COGSUpload {
  id: string
  tenantId: number
  filename: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  rowCount: number
  successCount: number
  errorCount: number
  errors: COGSUploadError[]
  uploadedAt: string
  processedAt?: string
}

export interface COGSUploadError {
  row: number
  field: string
  message: string
}

export interface CreateProductRequest {
  sku: string
  name: string
  description?: string
  category?: string
  subcategory?: string
  brand?: string
  defaultCogs: number
  defaultMarginPct?: number
  currency?: string
  tags?: string[]
  metadata?: Record<string, unknown>
}

export interface CreateMarginRuleRequest {
  name: string
  description?: string
  priority?: number
  conditions: MarginCondition[]
  marginType: MarginType
  marginValue: number
  appliesTo: 'all' | 'category' | 'product' | 'platform' | 'campaign'
  targetIds?: string[]
  effectiveFrom: string
  effectiveTo?: string
}

// =============================================================================
// API Functions
// =============================================================================

export const profitApi = {
  // Products
  getProducts: async (params?: { status?: ProductStatus; category?: string; search?: string; page?: number; limit?: number }) => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<ProductCatalog>>>('/profit/products', { params })
    return response.data.data
  },

  getProduct: async (productId: string) => {
    const response = await apiClient.get<ApiResponse<ProductCatalog>>(`/profit/products/${productId}`)
    return response.data.data
  },

  createProduct: async (data: CreateProductRequest) => {
    const response = await apiClient.post<ApiResponse<ProductCatalog>>('/profit/products', data)
    return response.data.data
  },

  updateProduct: async (productId: string, data: Partial<CreateProductRequest>) => {
    const response = await apiClient.patch<ApiResponse<ProductCatalog>>(`/profit/products/${productId}`, data)
    return response.data.data
  },

  deleteProduct: async (productId: string) => {
    const response = await apiClient.delete<ApiResponse<void>>(`/profit/products/${productId}`)
    return response.data
  },

  importProducts: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post<ApiResponse<{ imported: number; errors: Array<{ row: number; field: string; message: string }> }>>('/profit/products/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data.data
  },

  // Product Margins
  getProductMargins: async (productId: string) => {
    const response = await apiClient.get<ApiResponse<ProductMargin[]>>(`/profit/products/${productId}/margins`)
    return response.data.data
  },

  setProductMargin: async (productId: string, data: Partial<ProductMargin>) => {
    const response = await apiClient.post<ApiResponse<ProductMargin>>(`/profit/products/${productId}/margins`, data)
    return response.data.data
  },

  // Margin Rules
  getMarginRules: async (params?: { isActive?: boolean }) => {
    const response = await apiClient.get<ApiResponse<MarginRule[]>>('/profit/margin-rules', { params })
    return response.data.data
  },

  getMarginRule: async (ruleId: string) => {
    const response = await apiClient.get<ApiResponse<MarginRule>>(`/profit/margin-rules/${ruleId}`)
    return response.data.data
  },

  createMarginRule: async (data: CreateMarginRuleRequest) => {
    const response = await apiClient.post<ApiResponse<MarginRule>>('/profit/margin-rules', data)
    return response.data.data
  },

  updateMarginRule: async (ruleId: string, data: Partial<CreateMarginRuleRequest>) => {
    const response = await apiClient.patch<ApiResponse<MarginRule>>(`/profit/margin-rules/${ruleId}`, data)
    return response.data.data
  },

  deleteMarginRule: async (ruleId: string) => {
    const response = await apiClient.delete<ApiResponse<void>>(`/profit/margin-rules/${ruleId}`)
    return response.data
  },

  // COGS
  uploadCOGS: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await apiClient.post<ApiResponse<COGSUpload>>('/profit/cogs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data.data
  },

  getCOGSUploads: async () => {
    const response = await apiClient.get<ApiResponse<COGSUpload[]>>('/profit/cogs/uploads')
    return response.data.data
  },

  getCOGSUpload: async (uploadId: string) => {
    const response = await apiClient.get<ApiResponse<COGSUpload>>(`/profit/cogs/uploads/${uploadId}`)
    return response.data.data
  },

  // Profit Metrics
  getDailyProfitMetrics: async (params: {
    startDate: string
    endDate: string
    platform?: string
    campaignId?: string
    productId?: string
    groupBy?: string
  }) => {
    const response = await apiClient.get<ApiResponse<DailyProfitMetrics[]>>('/profit/metrics/daily', { params })
    return response.data.data
  },

  getProfitSummary: async (params: { startDate: string; endDate: string; groupBy?: string }) => {
    const response = await apiClient.get<ApiResponse<{
      totalRevenue: number
      totalCogs: number
      grossProfit: number
      adSpend: number
      netProfit: number
      grossMarginPct: number
      netMarginPct: number
      roas: number
      trueRoas: number
      profitRoas: number
    }>>('/profit/metrics/summary', { params })
    return response.data.data
  },

  // Profit Reports
  generateProfitReport: async (params: {
    periodStart: string
    periodEnd: string
    groupBy: string
    includeProducts?: boolean
  }) => {
    const response = await apiClient.post<ApiResponse<ProfitReport>>('/profit/reports/generate', params)
    return response.data.data
  },

  getProfitReports: async () => {
    const response = await apiClient.get<ApiResponse<ProfitReport[]>>('/profit/reports')
    return response.data.data
  },

  getProfitReport: async (reportId: string) => {
    const response = await apiClient.get<ApiResponse<ProfitReport>>(`/profit/reports/${reportId}`)
    return response.data.data
  },

  // True ROAS Calculation
  calculateTrueROAS: async (params: { startDate: string; endDate: string; groupBy?: string }) => {
    const response = await apiClient.get<ApiResponse<{
      standardRoas: number
      trueRoas: number
      profitRoas: number
      breakdown: Array<{
        dimension: string
        standardRoas: number
        trueRoas: number
        profitRoas: number
      }>
    }>>('/profit/true-roas', { params })
    return response.data.data
  },
}

// =============================================================================
// React Query Hooks
// =============================================================================

// Products
export function useProducts(params?: { status?: ProductStatus; category?: string; search?: string; page?: number; limit?: number }) {
  return useQuery({
    queryKey: ['profit', 'products', params],
    queryFn: () => profitApi.getProducts(params),
  })
}

export function useProduct(productId: string) {
  return useQuery({
    queryKey: ['profit', 'products', productId],
    queryFn: () => profitApi.getProduct(productId),
    enabled: !!productId,
  })
}

export function useCreateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: profitApi.createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit', 'products'] })
    },
  })
}

export function useUpdateProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, data }: { productId: string; data: Partial<CreateProductRequest> }) =>
      profitApi.updateProduct(productId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit', 'products'] })
    },
  })
}

export function useDeleteProduct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: profitApi.deleteProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit', 'products'] })
    },
  })
}

export function useImportProducts() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: profitApi.importProducts,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit', 'products'] })
    },
  })
}

// Product Margins
export function useProductMargins(productId: string) {
  return useQuery({
    queryKey: ['profit', 'products', productId, 'margins'],
    queryFn: () => profitApi.getProductMargins(productId),
    enabled: !!productId,
  })
}

export function useSetProductMargin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ productId, data }: { productId: string; data: Partial<ProductMargin> }) =>
      profitApi.setProductMargin(productId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit', 'products'] })
    },
  })
}

// Margin Rules
export function useMarginRules(params?: { isActive?: boolean }) {
  return useQuery({
    queryKey: ['profit', 'margin-rules', params],
    queryFn: () => profitApi.getMarginRules(params),
  })
}

export function useMarginRule(ruleId: string) {
  return useQuery({
    queryKey: ['profit', 'margin-rules', ruleId],
    queryFn: () => profitApi.getMarginRule(ruleId),
    enabled: !!ruleId,
  })
}

export function useCreateMarginRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: profitApi.createMarginRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit', 'margin-rules'] })
    },
  })
}

export function useUpdateMarginRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ruleId, data }: { ruleId: string; data: Partial<CreateMarginRuleRequest> }) =>
      profitApi.updateMarginRule(ruleId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit', 'margin-rules'] })
    },
  })
}

export function useDeleteMarginRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: profitApi.deleteMarginRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit', 'margin-rules'] })
    },
  })
}

// COGS
export function useUploadCOGS() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: profitApi.uploadCOGS,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit'] })
    },
  })
}

export function useCOGSUploads() {
  return useQuery({
    queryKey: ['profit', 'cogs', 'uploads'],
    queryFn: profitApi.getCOGSUploads,
  })
}

export function useCOGSUpload(uploadId: string) {
  return useQuery({
    queryKey: ['profit', 'cogs', 'uploads', uploadId],
    queryFn: () => profitApi.getCOGSUpload(uploadId),
    enabled: !!uploadId,
  })
}

// Profit Metrics
export function useDailyProfitMetrics(params: {
  startDate: string
  endDate: string
  platform?: string
  campaignId?: string
  productId?: string
  groupBy?: string
}) {
  return useQuery({
    queryKey: ['profit', 'metrics', 'daily', params],
    queryFn: () => profitApi.getDailyProfitMetrics(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

export function useProfitSummary(params: { startDate: string; endDate: string; groupBy?: string }) {
  return useQuery({
    queryKey: ['profit', 'metrics', 'summary', params],
    queryFn: () => profitApi.getProfitSummary(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}

// Profit Reports
export function useGenerateProfitReport() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: profitApi.generateProfitReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profit', 'reports'] })
    },
  })
}

export function useProfitReports() {
  return useQuery({
    queryKey: ['profit', 'reports'],
    queryFn: profitApi.getProfitReports,
  })
}

export function useProfitReport(reportId: string) {
  return useQuery({
    queryKey: ['profit', 'reports', reportId],
    queryFn: () => profitApi.getProfitReport(reportId),
    enabled: !!reportId,
  })
}

// True ROAS
export function useTrueROAS(params: { startDate: string; endDate: string; groupBy?: string }) {
  return useQuery({
    queryKey: ['profit', 'true-roas', params],
    queryFn: () => profitApi.calculateTrueROAS(params),
    enabled: !!params.startDate && !!params.endDate,
  })
}
