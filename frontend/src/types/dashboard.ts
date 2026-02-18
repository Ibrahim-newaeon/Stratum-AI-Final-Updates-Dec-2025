/**
 * TypeScript Type Definitions
 * Dashboard Data Structures for Stratum AI
 */

// ==================== CAMPAIGN DATA ====================

export interface Campaign {
  campaign_id: string
  campaign_name: string
  platform: 'Meta Ads' | 'Google Ads' | 'TikTok Ads' | 'Snapchat Ads' | 'LinkedIn Ads'
  region: string
  campaign_type: 'Prospecting' | 'Retargeting' | 'Brand Awareness' | 'Conversion' | 'Lead Generation'
  spend: number
  revenue: number
  conversions: number
  impressions: number
  clicks: number
  ctr: number
  cpm: number
  cpa: number
  roas: number
  status: 'Active' | 'Paused' | 'Completed'
  start_date: string
  end_date?: string
}

// ==================== AGGREGATED DATA ====================

export interface PlatformSummary {
  platform: string
  spend: number
  revenue: number
  conversions: number
  roas: number
  cpa: number
  impressions: number
  clicks: number
}

export interface RegionalSummary {
  region: string
  spend: number
  revenue: number
  conversions: number
  roas: number
}

export interface DailyPerformance {
  date: string
  spend: number
  revenue: number
  conversions: number
  roas: number
  ctr: number
  cpa: number
  impressions: number
  clicks: number
}

// ==================== KPI METRICS ====================

export interface KPIMetrics {
  totalSpend: number
  totalRevenue: number
  overallROAS: number
  totalConversions: number
  overallCPA: number
  avgCTR: number
  avgCPM: number
  totalImpressions: number
  totalClicks: number

  // Delta metrics (percentage change)
  spendDelta?: number
  revenueDelta?: number
  roasDelta?: number
  conversionsDelta?: number
}

export interface PreviousPeriodData {
  spendDelta: number
  revenueDelta: number
  roasDelta: number
  conversionsDelta: number
}

// ==================== PERFORMANCE DATA RESPONSE ====================

export interface PerformanceData {
  campaigns: Campaign[]
  topCampaigns: Campaign[]
  platformSummary: PlatformSummary[]
  regionalSummary: RegionalSummary[]
  dailyPerformance: DailyPerformance[]
  previousPeriod?: PreviousPeriodData
  metadata: {
    total_campaigns: number
    active_campaigns: number
    date_range: {
      start: string
      end: string
    }
    filters_applied: {
      platforms: string[]
      regions: string[]
      campaign_types: string[]
    }
  }
}

// ==================== FILTERS ====================

export interface DateRange {
  start: Date
  end: Date
}

export interface DashboardFilters {
  dateRange: DateRange
  platforms: string[]
  regions: string[]
  campaignTypes: string[]
}

// ==================== ALERTS ====================

export interface Alert {
  id: string
  severity: 'critical' | 'warning' | 'good'
  title: string
  message: string
  recommendation: string
  campaigns?: string[]
  created_at: string
  read: boolean
}

// ==================== USER & AUTH ====================

export interface User {
  id: string
  email: string
  name: string
  company: string
  role: 'admin' | 'user' | 'viewer'
  tenant_id: string
  avatar_url?: string
}

export interface AuthContextType {
  user: User | null
  tenantId: string
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

// ==================== API RESPONSES ====================

export interface APIResponse<T> {
  success: boolean
  data: T
  message?: string
  error?: string
}

export interface PaginatedResponse<T> {
  success: boolean
  data: T[]
  pagination: {
    page: number
    page_size: number
    total_pages: number
    total_items: number
  }
}

// ==================== BUDGET OPTIMIZATION ====================

export interface BudgetAllocation {
  platform: string
  recommended_budget: number
  budget_share_percent: number
  expected_conversions: number
  expected_revenue: number
  expected_roas: number
  current_cpa: number
}

export interface BudgetOptimizationRequest {
  total_budget: number
  optimization_goal: 'Maximize ROAS' | 'Minimize CPA' | 'Maximize Conversions' | 'Balanced Approach'
}

export interface BudgetOptimizationResponse {
  allocations: BudgetAllocation[]
  total_budget: number
  optimization_goal: string
  expected_performance: {
    total_conversions: number
    total_revenue: number
    overall_roas: number
  }
}

// ==================== EXPORT ====================

export interface ExportRequest {
  format: 'csv' | 'excel' | 'pdf'
  filters: DashboardFilters
  include_charts?: boolean
}

export interface ExportResponse {
  task_id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  download_url?: string
  created_at: string
  expires_at: string
}

// ==================== CHART DATA ====================

export interface ChartDataPoint {
  x: string | number
  y: number
  label?: string
  color?: string
}

export interface ChartSeries {
  name: string
  data: ChartDataPoint[]
  color?: string
}

// ==================== TABLE ====================

export interface TableColumn {
  key: string
  label: string
  sortable?: boolean
  format?: 'currency' | 'percent' | 'number' | 'text'
  width?: string
}

export interface TableSortConfig {
  key: string
  direction: 'asc' | 'desc'
}

// ==================== NOTIFICATIONS ====================

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  action?: {
    label: string
    onClick: () => void
  }
  dismissible: boolean
  duration?: number // ms, 0 = persistent
}
