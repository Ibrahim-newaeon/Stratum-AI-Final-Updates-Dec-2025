/**
 * Dashboard Overview Page
 * Stratum AI Marketing Intelligence Platform
 *
 * Features:
 * - Real-time KPI cards with animations
 * - Interactive charts with error boundaries
 * - Campaign performance table
 * - Advanced filtering with empty states
 * - Keyboard shortcuts
 * - Responsive design
 * - Full accessibility support
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RefreshCw,
  Download,
  Bell,
  AlertTriangle,
  CheckCircle,
  Info,
  TrendingUp,
  DollarSign,
  Target,
  MousePointerClick,
  Eye,
  ShoppingCart,
  BarChart3,
  Keyboard,
} from 'lucide-react'
import { cn, formatCurrency, formatCompactNumber } from '@/lib/utils'
import { KPICard } from '@/components/dashboard/KPICard'
import { CampaignTable } from '@/components/dashboard/CampaignTable'
import { FilterBar } from '@/components/dashboard/FilterBar'
import { SimulateSlider } from '@/components/widgets/SimulateSlider'
import { LivePredictionsWidget } from '@/components/widgets/LivePredictionsWidget'
import { ROASAlertsWidget } from '@/components/widgets/ROASAlertsWidget'
import { BudgetOptimizerWidget } from '@/components/widgets/BudgetOptimizerWidget'
import { EMQWidget } from '@/components/widgets/EMQWidget'
import { EMQAlertsWidget } from '@/components/widgets/EMQAlertsWidget'
import {
  PlatformPerformanceChart,
  ROASByPlatformChart,
  DailyTrendChart,
  RegionalBreakdownChart,
} from '@/components/charts'
import { ALL_REGIONS } from '@/components/dashboard/FilterBar'
import { KPICardSkeleton, TableSkeleton, AlertSkeleton } from '@/components/ui/Skeleton'
import { NoFilterResultsState } from '@/components/ui/EmptyState'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import {
  Campaign,
  DashboardFilters,
  KPIMetrics,
  PlatformSummary,
  DailyPerformance,
} from '@/types/dashboard'
import { campaignsApi, analyticsApi } from '@/services/api'

// Platform name mapping from API to display names
const PLATFORM_DISPLAY_NAMES: Record<string, string> = {
  meta: 'Meta Ads',
  google: 'Google Ads',
  tiktok: 'TikTok Ads',
  snapchat: 'Snapchat Ads',
  linkedin: 'LinkedIn Ads',
}

// Reverse mapping for filtering
const PLATFORM_API_NAMES: Record<string, string> = {
  'Meta Ads': 'meta',
  'Google Ads': 'google',
  'TikTok Ads': 'tiktok',
  'Snapchat Ads': 'snapchat',
  'LinkedIn Ads': 'linkedin',
}

// Status mapping
const STATUS_DISPLAY_NAMES: Record<string, 'Active' | 'Paused' | 'Completed'> = {
  active: 'Active',
  paused: 'Paused',
  completed: 'Completed',
  deleted: 'Completed',
}

// Map Meta objectives to campaign types
const OBJECTIVE_TO_CAMPAIGN_TYPE: Record<string, Campaign['campaign_type']> = {
  OUTCOME_ENGAGEMENT: 'Retargeting',
  OUTCOME_AWARENESS: 'Brand Awareness',
  OUTCOME_TRAFFIC: 'Prospecting',
  OUTCOME_LEADS: 'Conversion',
  OUTCOME_SALES: 'Conversion',
  OUTCOME_APP_PROMOTION: 'Prospecting',
  CONVERSIONS: 'Conversion',
  REACH: 'Brand Awareness',
  BRAND_AWARENESS: 'Brand Awareness',
  LINK_CLICKS: 'Prospecting',
  POST_ENGAGEMENT: 'Retargeting',
  VIDEO_VIEWS: 'Brand Awareness',
}

// Infer region from campaign name
const inferRegionFromName = (name: string): string => {
  const nameUpper = name.toUpperCase()
  if (nameUpper.includes('KSA') || nameUpper.includes('SAUDI') || nameUpper.includes('السعودية')) {
    return 'Saudi Arabia'
  }
  if (nameUpper.includes('KUWAIT') || nameUpper.includes('الكويت')) {
    return 'Kuwait'
  }
  if (nameUpper.includes('UAE') || nameUpper.includes('EMIRATES') || nameUpper.includes('DUBAI') || nameUpper.includes('ABU DHABI')) {
    return 'UAE'
  }
  if (nameUpper.includes('QATAR') || nameUpper.includes('قطر')) {
    return 'Qatar'
  }
  if (nameUpper.includes('BAHRAIN') || nameUpper.includes('البحرين')) {
    return 'Bahrain'
  }
  if (nameUpper.includes('OMAN') || nameUpper.includes('عمان')) {
    return 'Oman'
  }
  if (nameUpper.includes('JORDAN') || nameUpper.includes('الأردن')) {
    return 'Jordan'
  }
  if (nameUpper.includes('EGYPT') || nameUpper.includes('مصر')) {
    return 'Egypt'
  }
  if (nameUpper.includes('IRAQ') || nameUpper.includes('العراق')) {
    return 'Iraq'
  }
  // Default to Saudi Arabia if no region found
  return 'Saudi Arabia'
}

// Map API campaign response to frontend Campaign type
interface APICampaign {
  id: number
  name: string
  platform: string
  status: string
  objective: string | null
  account_id: string | null
  total_spend_cents: number
  impressions: number
  clicks: number
  conversions: number
  roas: number | null
  labels: string[]
  last_synced_at: string | null
}

const mapAPICampaignToFrontend = (apiCampaign: APICampaign): Campaign => {
  const spend = (apiCampaign.total_spend_cents || 0) / 100
  const conversions = apiCampaign.conversions || 0
  const impressions = apiCampaign.impressions || 0
  const clicks = apiCampaign.clicks || 0

  // Calculate derived metrics
  const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0
  const cpm = impressions > 0 ? (spend / impressions) * 1000 : 0
  const cpa = conversions > 0 ? spend / conversions : 0
  const roas = apiCampaign.roas || 0
  // Estimate revenue from ROAS (revenue = spend * roas)
  const revenue = spend * roas

  // Map objective to campaign type
  const campaignType = apiCampaign.objective
    ? OBJECTIVE_TO_CAMPAIGN_TYPE[apiCampaign.objective] || 'Conversion'
    : 'Conversion'

  return {
    campaign_id: String(apiCampaign.id),
    campaign_name: apiCampaign.name,
    platform: (PLATFORM_DISPLAY_NAMES[apiCampaign.platform] || apiCampaign.platform) as Campaign['platform'],
    region: inferRegionFromName(apiCampaign.name),
    campaign_type: campaignType,
    account_id: apiCampaign.account_id || undefined,
    spend,
    revenue,
    conversions,
    impressions,
    clicks,
    ctr,
    cpm,
    cpa,
    roas,
    status: STATUS_DISPLAY_NAMES[apiCampaign.status] || 'Active',
    start_date: apiCampaign.last_synced_at?.split('T')[0] || new Date().toISOString().split('T')[0],
  }
}

// Mock data for demonstration
const mockCampaigns: Campaign[] = [
  {
    campaign_id: '1',
    campaign_name: 'Summer Sale 2024',
    platform: 'Meta Ads',
    region: 'Saudi Arabia',
    campaign_type: 'Conversion',
    spend: 12500,
    revenue: 45000,
    conversions: 450,
    impressions: 1250000,
    clicks: 25000,
    ctr: 2.0,
    cpm: 10.0,
    cpa: 27.78,
    roas: 3.6,
    status: 'Active',
    start_date: '2024-06-01',
  },
  {
    campaign_id: '2',
    campaign_name: 'Brand Awareness Q4',
    platform: 'Google Ads',
    region: 'UAE',
    campaign_type: 'Brand Awareness',
    spend: 8200,
    revenue: 28700,
    conversions: 287,
    impressions: 980000,
    clicks: 19600,
    ctr: 2.0,
    cpm: 8.37,
    cpa: 28.57,
    roas: 3.5,
    status: 'Active',
    start_date: '2024-09-15',
  },
  {
    campaign_id: '3',
    campaign_name: 'Retargeting - Cart Abandoners',
    platform: 'Meta Ads',
    region: 'Saudi Arabia',
    campaign_type: 'Retargeting',
    spend: 5600,
    revenue: 22400,
    conversions: 320,
    impressions: 560000,
    clicks: 11200,
    ctr: 2.0,
    cpm: 10.0,
    cpa: 17.5,
    roas: 4.0,
    status: 'Active',
    start_date: '2024-10-01',
  },
  {
    campaign_id: '4',
    campaign_name: 'TikTok Influencer Campaign',
    platform: 'TikTok Ads',
    region: 'UAE',
    campaign_type: 'Prospecting',
    spend: 15000,
    revenue: 37500,
    conversions: 500,
    impressions: 2500000,
    clicks: 50000,
    ctr: 2.0,
    cpm: 6.0,
    cpa: 30.0,
    roas: 2.5,
    status: 'Active',
    start_date: '2024-11-01',
  },
  {
    campaign_id: '5',
    campaign_name: 'Snapchat Gen-Z Reach',
    platform: 'Snapchat Ads',
    region: 'Qatar',
    campaign_type: 'Prospecting',
    spend: 4500,
    revenue: 11250,
    conversions: 150,
    impressions: 750000,
    clicks: 15000,
    ctr: 2.0,
    cpm: 6.0,
    cpa: 30.0,
    roas: 2.5,
    status: 'Active',
    start_date: '2024-11-15',
  },
  {
    campaign_id: '6',
    campaign_name: 'LinkedIn B2B Lead Gen',
    platform: 'LinkedIn Ads',
    region: 'United States',
    campaign_type: 'Lead Generation',
    spend: 9800,
    revenue: 39200,
    conversions: 196,
    impressions: 420000,
    clicks: 8400,
    ctr: 2.0,
    cpm: 23.33,
    cpa: 50.0,
    roas: 4.0,
    status: 'Active',
    start_date: '2024-10-20',
  },
]

const mockPlatformSummary: PlatformSummary[] = [
  { platform: 'Meta Ads', spend: 18100, revenue: 67400, conversions: 770, roas: 3.72, cpa: 23.51, impressions: 1810000, clicks: 36200 },
  { platform: 'Google Ads', spend: 8200, revenue: 28700, conversions: 287, roas: 3.5, cpa: 28.57, impressions: 980000, clicks: 19600 },
  { platform: 'TikTok Ads', spend: 15000, revenue: 37500, conversions: 500, roas: 2.5, cpa: 30.0, impressions: 2500000, clicks: 50000 },
  { platform: 'Snapchat Ads', spend: 4500, revenue: 11250, conversions: 150, roas: 2.5, cpa: 30.0, impressions: 750000, clicks: 15000 },
  { platform: 'LinkedIn Ads', spend: 9800, revenue: 39200, conversions: 196, roas: 4.0, cpa: 50.0, impressions: 420000, clicks: 8400 },
]

const mockDailyPerformance: DailyPerformance[] = Array.from({ length: 30 }, (_, i) => {
  const date = new Date()
  date.setDate(date.getDate() - (29 - i))
  return {
    date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    spend: 1200 + Math.random() * 800 + i * 20,
    revenue: 4000 + Math.random() * 2000 + i * 60,
    conversions: 40 + Math.floor(Math.random() * 20) + Math.floor(i * 0.5),
    roas: 2.5 + Math.random() * 1.5 + i * 0.03,
    ctr: 1.5 + Math.random() * 1.5,
    cpa: 25 + Math.random() * 15,
    impressions: 120000 + Math.random() * 50000 + i * 2000,
    clicks: 2400 + Math.floor(Math.random() * 1000) + i * 40,
  }
})

const mockAlerts = [
  {
    id: '1',
    severity: 'warning' as const,
    title: 'Campaign budget depleted',
    message: '"Summer Sale 2024" has reached 95% of daily budget',
    time: '10 minutes ago',
  },
  {
    id: '2',
    severity: 'good' as const,
    title: 'ROAS target achieved',
    message: '"Brand Awareness Q4" exceeded 4.0x ROAS target',
    time: '1 hour ago',
  },
  {
    id: '3',
    severity: 'critical' as const,
    title: 'New optimization suggestion',
    message: 'AI detected underperforming keywords in 3 campaigns',
    time: '3 hours ago',
  },
]

// Regional data for pie chart
const regionalData = [
  { name: 'Saudi Arabia', value: 45 },
  { name: 'UAE', value: 30 },
  { name: 'Qatar', value: 10 },
  { name: 'Kuwait', value: 8 },
  { name: 'Other', value: 7 },
]

export function Overview() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())
  const [showKeyboardHints, setShowKeyboardHints] = useState(false)

  // Real campaign data from API
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [dailyPerformance, setDailyPerformance] = useState<DailyPerformance[]>([])
  const [fetchError, setFetchError] = useState<string | null>(null)

  // Filter state - start with all options selected (no filtering)
  const [filters, setFilters] = useState<DashboardFilters>({
    dateRange: {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      end: new Date(),
    },
    platforms: ['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads', 'LinkedIn Ads'],
    regions: ALL_REGIONS, // Include all global regions by default
    campaignTypes: ['Prospecting', 'Retargeting', 'Brand Awareness', 'Conversion', 'Lead Generation'],
  })

  // Fetch campaigns from API
  const fetchCampaigns = useCallback(async () => {
    try {
      setFetchError(null)
      const response = await campaignsApi.list({ page: 1, page_size: 100 })

      if (response.success && response.data?.items) {
        const mappedCampaigns = response.data.items.map(mapAPICampaignToFrontend)
        setCampaigns(mappedCampaigns)
      } else {
        setCampaigns([])
      }
    } catch (error: any) {
      console.error('Failed to fetch campaigns:', error)
      setFetchError(error.message || 'Failed to load campaigns')
      // Keep existing campaigns on error
    }
  }, [])

  // Fetch daily performance data from API
  const fetchDailyPerformance = useCallback(async (dateRange?: { start: Date; end: Date }) => {
    try {
      // Calculate days from date range or default to 30
      const range = dateRange || filters.dateRange
      const days = Math.ceil((range.end.getTime() - range.start.getTime()) / (1000 * 60 * 60 * 24))
      const response = await analyticsApi.getDailyPerformance({ days: Math.max(7, Math.min(90, days)) })

      if (response.success && response.data) {
        setDailyPerformance(response.data)
      }
    } catch (error: any) {
      console.error('Failed to fetch daily performance:', error)
      // Keep mock data on error
    }
  }, [filters.dateRange])

  // Memoized: Calculate KPI metrics from campaigns (use filtered campaigns)
  const kpis = useMemo((): KPIMetrics => {
    // Use real campaigns data or fallback to empty calculations
    const campaignsToUse = campaigns.length > 0 ? campaigns : []

    const totalSpend = campaignsToUse.reduce((sum, c) => sum + c.spend, 0)
    const totalRevenue = campaignsToUse.reduce((sum, c) => sum + c.revenue, 0)
    const totalConversions = campaignsToUse.reduce((sum, c) => sum + c.conversions, 0)
    const overallROAS = totalSpend > 0 ? totalRevenue / totalSpend : 0
    const overallCPA = totalConversions > 0 ? totalSpend / totalConversions : 0
    const avgCTR = campaignsToUse.length > 0 ? campaignsToUse.reduce((sum, c) => sum + c.ctr, 0) / campaignsToUse.length : 0
    const avgCPM = campaignsToUse.length > 0 ? campaignsToUse.reduce((sum, c) => sum + c.cpm, 0) / campaignsToUse.length : 0
    const totalImpressions = campaignsToUse.reduce((sum, c) => sum + c.impressions, 0)
    const totalClicks = campaignsToUse.reduce((sum, c) => sum + c.clicks, 0)

    return {
      totalSpend,
      totalRevenue,
      overallROAS,
      totalConversions,
      overallCPA,
      avgCTR,
      avgCPM,
      totalImpressions,
      totalClicks,
      spendDelta: 12.5,
      revenueDelta: 23.4,
      roasDelta: 9.7,
      conversionsDelta: 21.5,
    }
  }, [campaigns])

  // Memoized: Filter campaigns based on current filters
  const filteredCampaigns = useMemo(() => {
    return campaigns.filter((campaign) => {
      // Filter by date range - only if we have a valid date
      if (campaign.start_date) {
        const campaignDate = new Date(campaign.start_date)
        // Only filter by date if the date is valid
        if (!isNaN(campaignDate.getTime())) {
          if (campaignDate < filters.dateRange.start || campaignDate > filters.dateRange.end) {
            return false
          }
        }
      }

      // Filter by platform - empty array means no filter (show all)
      if (filters.platforms.length > 0 && !filters.platforms.includes(campaign.platform)) {
        return false
      }

      // Filter by region - empty array means no filter (show all)
      if (filters.regions.length > 0 && !filters.regions.includes(campaign.region)) {
        return false
      }

      // Filter by campaign type - empty array means no filter (show all)
      if (filters.campaignTypes.length > 0 && !filters.campaignTypes.includes(campaign.campaign_type)) {
        return false
      }

      return true
    })
  }, [filters, campaigns])

  // Check if filters resulted in empty data
  const hasNoFilterResults = filteredCampaigns.length === 0 && campaigns.length > 0

  // Calculate platform summary from real campaigns
  const platformSummary = useMemo((): PlatformSummary[] => {
    const platformMap = new Map<string, PlatformSummary>()

    filteredCampaigns.forEach((campaign) => {
      const existing = platformMap.get(campaign.platform)
      if (existing) {
        existing.spend += campaign.spend
        existing.revenue += campaign.revenue
        existing.conversions += campaign.conversions
        existing.impressions += campaign.impressions
        existing.clicks += campaign.clicks
      } else {
        platformMap.set(campaign.platform, {
          platform: campaign.platform,
          spend: campaign.spend,
          revenue: campaign.revenue,
          conversions: campaign.conversions,
          roas: 0, // Will calculate below
          cpa: 0, // Will calculate below
          impressions: campaign.impressions,
          clicks: campaign.clicks,
        })
      }
    })

    // Calculate derived metrics
    return Array.from(platformMap.values()).map((p) => ({
      ...p,
      roas: p.spend > 0 ? p.revenue / p.spend : 0,
      cpa: p.conversions > 0 ? p.spend / p.conversions : 0,
    }))
  }, [filteredCampaigns])

  // Calculate regional breakdown from real campaigns
  const regionalBreakdown = useMemo(() => {
    const regionMap = new Map<string, number>()
    let totalSpend = 0

    filteredCampaigns.forEach((campaign) => {
      const spend = campaign.spend || 0
      totalSpend += spend
      const existing = regionMap.get(campaign.region) || 0
      regionMap.set(campaign.region, existing + spend)
    })

    // Convert to percentage-based data for pie chart
    if (totalSpend === 0) return []

    return Array.from(regionMap.entries())
      .map(([name, spend]) => ({
        name,
        value: Math.round((spend / totalSpend) * 100),
      }))
      .sort((a, b) => b.value - a.value)
  }, [filteredCampaigns])

  // Refresh data
  const handleRefresh = useCallback(async () => {
    setLoading(true)
    await Promise.all([fetchCampaigns(), fetchDailyPerformance()])
    setLastUpdated(new Date())
    setLoading(false)
  }, [fetchCampaigns, fetchDailyPerformance])

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Partial<DashboardFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }, [])

  // Clear all filters - reset to show everything
  const handleClearFilters = useCallback(() => {
    setFilters({
      dateRange: {
        start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        end: new Date(),
      },
      platforms: ['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads', 'LinkedIn Ads'],
      regions: ALL_REGIONS,
      campaignTypes: ['Prospecting', 'Retargeting', 'Brand Awareness', 'Conversion', 'Lead Generation'],
    })
  }, [])

  // Export handler
  const handleExport = useCallback(() => {
    // Prepare export data
    const exportData = {
      exportedAt: new Date().toISOString(),
      dateRange: {
        start: filters.dateRange.start.toISOString(),
        end: filters.dateRange.end.toISOString(),
      },
      summary: {
        totalSpend: kpis.totalSpend,
        totalRevenue: kpis.totalRevenue,
        overallROAS: kpis.overallROAS,
        totalConversions: kpis.totalConversions,
        overallCPA: kpis.overallCPA,
        avgCTR: kpis.avgCTR,
        avgCPM: kpis.avgCPM,
        totalImpressions: kpis.totalImpressions,
        totalClicks: kpis.totalClicks,
      },
      platformSummary: mockPlatformSummary,
      campaigns: filteredCampaigns.map((c) => ({
        id: c.campaign_id,
        name: c.campaign_name,
        platform: c.platform,
        region: c.region,
        type: c.campaign_type,
        status: c.status,
        spend: c.spend,
        revenue: c.revenue,
        conversions: c.conversions,
        impressions: c.impressions,
        clicks: c.clicks,
        ctr: c.ctr,
        cpm: c.cpm,
        cpa: c.cpa,
        roas: c.roas,
        startDate: c.start_date,
      })),
      dailyPerformance: mockDailyPerformance,
    }

    // Create and download JSON file
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `stratum-dashboard-export-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }, [filters, kpis, filteredCampaigns])

  // KPI action handlers
  const handleViewDetails = useCallback((metric: string) => {
    // Navigate to detailed view for this metric
  }, [])

  const handleSetAlert = useCallback((metric: string) => {
    // Open alert configuration modal for this metric
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      switch (e.key.toLowerCase()) {
        case 'r':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault()
            handleRefresh()
          }
          break
        case 'e':
          if (!e.ctrlKey && !e.metaKey) {
            e.preventDefault()
            handleExport()
          }
          break
        case '?':
          e.preventDefault()
          setShowKeyboardHints((prev) => !prev)
          break
        case 'escape':
          setShowKeyboardHints(false)
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleRefresh, handleExport])

  // Initial data loading - fetch campaigns and daily performance from API
  useEffect(() => {
    const loadInitialData = async () => {
      setInitialLoading(true)
      await Promise.all([fetchCampaigns(), fetchDailyPerformance()])
      setInitialLoading(false)
    }
    loadInitialData()
  }, [fetchCampaigns, fetchDailyPerformance])

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(handleRefresh, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [handleRefresh])

  // Refetch daily performance when date range changes
  useEffect(() => {
    if (!initialLoading) {
      fetchDailyPerformance(filters.dateRange)
    }
  }, [filters.dateRange, initialLoading])

  // Calculate active filter count
  const activeFilterCount =
    (filters.platforms.length < 4 ? 4 - filters.platforms.length : 0) +
    (filters.regions.length < 6 ? 6 - filters.regions.length : 0)

  return (
    <div className="space-y-6">
      {/* Keyboard Shortcuts Modal */}
      {showKeyboardHints && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={() => setShowKeyboardHints(false)}
        >
          <div
            className="bg-card border rounded-xl p-6 shadow-xl max-w-sm w-full mx-4 animate-in fade-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-4">
              <Keyboard className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold">Keyboard Shortcuts</h3>
            </div>
            <div className="space-y-3">
              {[
                { key: 'R', action: 'Refresh data' },
                { key: 'E', action: 'Export dashboard' },
                { key: '?', action: 'Toggle shortcuts' },
                { key: 'Esc', action: 'Close modal' },
              ].map((shortcut) => (
                <div key={shortcut.key} className="flex items-center justify-between">
                  <span className="text-muted-foreground">{shortcut.action}</span>
                  <kbd className="px-2 py-1 text-xs font-mono bg-muted rounded border">
                    {shortcut.key}
                  </kbd>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {fetchError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-red-500">Failed to load campaigns</p>
            <p className="text-xs text-red-400">{fetchError}</p>
          </div>
          <button
            onClick={handleRefresh}
            className="px-3 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
            {t('overview.title')}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Last updated: {lastUpdated.toLocaleString()} | {campaigns.length} campaigns loaded
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Keyboard shortcut hint */}
          <button
            onClick={() => setShowKeyboardHints(true)}
            className="hidden lg:flex items-center px-3 py-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
            title="Keyboard shortcuts (?)"
          >
            <Keyboard className="w-4 h-4 mr-1" />
            <kbd className="px-1.5 py-0.5 text-xs bg-muted rounded">?</kbd>
          </button>

          <button
            onClick={handleRefresh}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium bg-background hover:bg-muted transition-colors disabled:opacity-50"
            aria-label="Refresh data (R)"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Refreshing...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </>
            )}
          </button>

          <button
            onClick={handleExport}
            className="inline-flex items-center px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            aria-label="Export dashboard (E)"
          >
            <Download className="w-4 h-4 mr-2" />
            {t('common.export')}
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        platforms={['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads', 'LinkedIn Ads']}
        useGlobalRegions={true}
      />

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Spend"
          value={formatCurrency(kpis.totalSpend)}
          numericValue={kpis.totalSpend}
          prefix="$"
          delta={kpis.spendDelta}
          deltaText="vs last period"
          trend={kpis.spendDelta && kpis.spendDelta > 0 ? 'up' : 'down'}
          icon={<DollarSign className="w-5 h-5" />}
          loading={initialLoading}
          onViewDetails={() => handleViewDetails('spend')}
          onSetAlert={() => handleSetAlert('spend')}
        />

        <KPICard
          title="Total Revenue"
          value={formatCurrency(kpis.totalRevenue)}
          numericValue={kpis.totalRevenue}
          prefix="$"
          delta={kpis.revenueDelta}
          deltaText="vs last period"
          trend={kpis.revenueDelta && kpis.revenueDelta > 0 ? 'up' : 'down'}
          trendIsGood={true}
          icon={<TrendingUp className="w-5 h-5" />}
          loading={initialLoading}
          onViewDetails={() => handleViewDetails('revenue')}
          onSetAlert={() => handleSetAlert('revenue')}
        />

        <KPICard
          title="ROAS"
          value={`${kpis.overallROAS.toFixed(2)}x`}
          numericValue={kpis.overallROAS}
          suffix="x"
          decimals={2}
          delta={kpis.roasDelta}
          deltaText="vs target"
          trend={kpis.roasDelta && kpis.roasDelta > 0 ? 'up' : 'down'}
          trendIsGood={true}
          highlight={kpis.overallROAS >= 3.0}
          icon={<Target className="w-5 h-5" />}
          loading={initialLoading}
          onViewDetails={() => handleViewDetails('roas')}
          onSetAlert={() => handleSetAlert('roas')}
        />

        <KPICard
          title="Total Conversions"
          value={kpis.totalConversions.toLocaleString('en-US')}
          numericValue={kpis.totalConversions}
          delta={kpis.conversionsDelta}
          deltaText="vs last period"
          trend={kpis.conversionsDelta && kpis.conversionsDelta > 0 ? 'up' : 'down'}
          trendIsGood={true}
          icon={<ShoppingCart className="w-5 h-5" />}
          loading={initialLoading}
          onViewDetails={() => handleViewDetails('conversions')}
          onSetAlert={() => handleSetAlert('conversions')}
        />
      </div>

      {/* Secondary KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <KPICard
          title="CPA"
          value={formatCurrency(kpis.overallCPA)}
          numericValue={kpis.overallCPA}
          prefix="$"
          decimals={2}
          size="small"
          icon={<DollarSign className="w-4 h-4" />}
          loading={initialLoading}
        />

        <KPICard
          title="CTR"
          value={`${kpis.avgCTR.toFixed(2)}%`}
          numericValue={kpis.avgCTR}
          suffix="%"
          decimals={2}
          size="small"
          icon={<MousePointerClick className="w-4 h-4" />}
          loading={initialLoading}
        />

        <KPICard
          title="CPM"
          value={formatCurrency(kpis.avgCPM)}
          numericValue={kpis.avgCPM}
          prefix="$"
          decimals={2}
          size="small"
          icon={<BarChart3 className="w-4 h-4" />}
          loading={initialLoading}
        />

        <KPICard
          title="Impressions"
          value={formatCompactNumber(kpis.totalImpressions)}
          numericValue={kpis.totalImpressions}
          size="small"
          icon={<Eye className="w-4 h-4" />}
          loading={initialLoading}
        />

        <KPICard
          title="Clicks"
          value={formatCompactNumber(kpis.totalClicks)}
          numericValue={kpis.totalClicks}
          size="small"
          icon={<MousePointerClick className="w-4 h-4" />}
          loading={initialLoading}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PlatformPerformanceChart
          data={platformSummary.length > 0 ? platformSummary : mockPlatformSummary}
          loading={initialLoading}
          onRefresh={handleRefresh}
        />

        <ROASByPlatformChart
          data={platformSummary.length > 0 ? platformSummary : mockPlatformSummary}
          loading={initialLoading}
          targetROAS={3.0}
          onRefresh={handleRefresh}
        />
      </div>

      {/* Second Row of Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <DailyTrendChart
            data={dailyPerformance.length > 0 ? dailyPerformance : mockDailyPerformance}
            loading={initialLoading}
            onRefresh={handleRefresh}
          />
        </div>

        <RegionalBreakdownChart
          data={regionalBreakdown.length > 0 ? regionalBreakdown : regionalData}
          loading={initialLoading}
          onRefresh={handleRefresh}
        />
      </div>

      {/* Third Row - Table and Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Campaign Performance Table */}
        <div className="lg:col-span-2">
          {initialLoading ? (
            <TableSkeleton rows={5} columns={7} />
          ) : hasNoFilterResults ? (
            <div className="rounded-xl border bg-card overflow-hidden">
              <div className="px-6 py-4 border-b">
                <h3 className="text-lg font-semibold text-foreground">Top Performing Campaigns</h3>
              </div>
              <NoFilterResultsState
                onClearFilters={handleClearFilters}
                filterCount={activeFilterCount}
              />
            </div>
          ) : (
            <div className="rounded-xl border bg-card overflow-hidden">
              <div className="px-6 py-4 border-b">
                <h3 className="text-lg font-semibold text-foreground">Top Performing Campaigns</h3>
              </div>
              <ErrorBoundary>
                <CampaignTable
                  campaigns={filteredCampaigns}
                  onCampaignClick={(campaignId) => {
                    // TODO: Navigate to campaign detail page
                    window.location.href = `/campaigns/${campaignId}`
                  }}
                />
              </ErrorBoundary>
            </div>
          )}
        </div>

        {/* Simulator Widget */}
        <ErrorBoundary>
          <SimulateSlider />
        </ErrorBoundary>
      </div>

      {/* AI Predictions Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ErrorBoundary>
          <LivePredictionsWidget />
        </ErrorBoundary>

        <ErrorBoundary>
          <ROASAlertsWidget />
        </ErrorBoundary>

        <ErrorBoundary>
          <BudgetOptimizerWidget />
        </ErrorBoundary>
      </div>

      {/* EMQ Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ErrorBoundary>
          <EMQWidget />
        </ErrorBoundary>

        <ErrorBoundary>
          <EMQAlertsWidget />
        </ErrorBoundary>
      </div>

      {/* Alerts Section */}
      <div className="rounded-xl border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Bell className="w-5 h-5" />
            {t('overview.recentAlerts')}
          </h3>
          <button className="text-sm text-primary hover:underline">{t('common.viewAll')}</button>
        </div>

        {initialLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <AlertSkeleton key={i} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {mockAlerts.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  'p-4 rounded-lg border-l-4 transition-all hover:shadow-md cursor-pointer',
                  alert.severity === 'warning' && 'bg-amber-500/10 border-amber-500 hover:bg-amber-500/15',
                  alert.severity === 'good' && 'bg-green-500/10 border-green-500 hover:bg-green-500/15',
                  alert.severity === 'critical' && 'bg-red-500/10 border-red-500 hover:bg-red-500/15'
                )}
                role="button"
                tabIndex={0}
                aria-label={`${alert.severity} alert: ${alert.title}`}
              >
                <div className="flex items-start gap-3">
                  {alert.severity === 'warning' && <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" aria-hidden="true" />}
                  {alert.severity === 'good' && <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" aria-hidden="true" />}
                  {alert.severity === 'critical' && <Info className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" aria-hidden="true" />}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm text-foreground">{alert.title}</p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{alert.message}</p>
                    <p className="text-xs text-muted-foreground mt-2">{alert.time}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Overview
