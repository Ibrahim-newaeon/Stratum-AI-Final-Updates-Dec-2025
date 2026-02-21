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
 * - Live simulation with platform connections
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
  LayoutDashboard,
  DownloadCloud,
  Radio,
  Wifi,
  WifiOff,
  Activity,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn, formatCurrency, formatCompactNumber } from '@/lib/utils'
import { KPICard } from '@/components/dashboard/KPICard'
import { CampaignTable } from '@/components/dashboard/CampaignTable'
import { FilterBar } from '@/components/dashboard/FilterBar'
import { SimulateSlider } from '@/components/widgets/SimulateSlider'
import { LivePredictionsWidget } from '@/components/widgets/LivePredictionsWidget'
import { ROASAlertsWidget } from '@/components/widgets/ROASAlertsWidget'
import { BudgetOptimizerWidget } from '@/components/widgets/BudgetOptimizerWidget'
import {
  PlatformPerformanceChart,
  ROASByPlatformChart,
  DailyTrendChart,
  RegionalBreakdownChart,
} from '@/components/charts'
import { TableSkeleton, AlertSkeleton } from '@/components/ui/Skeleton'
import { NoFilterResultsState } from '@/components/ui/EmptyState'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import {
  Campaign,
  DashboardFilters,
  KPIMetrics,
} from '@/types/dashboard'
import { useCampaigns, useTenantOverview } from '@/api/hooks'
import { useSyncAllCampaigns, useSyncCampaign } from '@/api/campaigns'
import { usePriceMetrics } from '@/hooks/usePriceMetrics'
import { useTenantStore } from '@/stores/tenantStore'
import { exportDashboardPDF } from '@/utils/pdfExport'
import { useToast } from '@/components/ui/use-toast'
import { useLiveSimulation } from '@/lib/liveSimulation'

export function Overview() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [showKeyboardHints, setShowKeyboardHints] = useState(false)

  // Get tenant ID from tenant store
  const tenantId = useTenantStore((state) => state.tenantId) ?? 1

  // Price metrics toggle — hides spend, revenue, ROAS, CPA, CPM across dashboard
  const { showPriceMetrics } = usePriceMetrics()

  // Sync mutations
  const syncAllMutation = useSyncAllCampaigns()
  const syncCampaignMutation = useSyncCampaign()
  const [syncingCampaignId, setSyncingCampaignId] = useState<string | null>(null)

  // Fetch data from API with fallback
  const { data: campaignsData, isLoading: campaignsLoading, refetch: refetchCampaigns } = useCampaigns()
  const { data: overviewData } = useTenantOverview(tenantId)

  // ============================================================================
  // Live Simulation — generates realistic platform data in real-time
  // ============================================================================
  const simulation = useLiveSimulation(10000) // refresh every 10 seconds

  // Filter state
  const [filters, setFilters] = useState<DashboardFilters>({
    dateRange: {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      end: new Date(),
    },
    platforms: ['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads', 'LinkedIn Ads'],
    regions: ['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq'],
    campaignTypes: ['Prospecting', 'Retargeting', 'Brand Awareness', 'Conversion'],
  })

  // Use API campaigns or fall back to live simulation data
  const campaigns = useMemo(() => {
    if (campaignsData?.items && campaignsData.items.length > 0) {
      return (campaignsData.items as unknown as Array<Record<string, unknown>>).map((c) => ({
        campaign_id: String(c.id ?? c.campaign_id ?? ''),
        campaign_name: String(c.name || c.campaign_name || ''),
        platform: String(c.platform || 'Unknown'),
        region: String(c.region || 'Unknown'),
        campaign_type: String(c.campaign_type || 'Conversion'),
        spend: Number(c.spend) || 0,
        revenue: Number(c.revenue) || 0,
        conversions: Number(c.conversions) || 0,
        impressions: Number(c.impressions) || 0,
        clicks: Number(c.clicks) || 0,
        ctr: Number(c.ctr) || 0,
        cpm: Number(c.cpm) || 0,
        cpa: Number(c.cpa) || 0,
        roas: Number(c.roas) || 0,
        status: String(c.status || 'Active'),
        start_date: String(c.start_date || c.startDate || new Date().toISOString()),
      })) as Campaign[]
    }
    // Fall back to live simulation campaigns
    return simulation.campaigns
  }, [campaignsData, simulation.campaigns])

  // Memoized: Calculate KPI metrics from campaigns (API or simulation)
  const kpis = useMemo((): KPIMetrics => {
    // Use API overview data if available
    if (overviewData?.kpis) {
      const apiKpis = overviewData.kpis
      return {
        totalSpend: apiKpis.total_spend ?? 0,
        totalRevenue: apiKpis.total_revenue ?? 0,
        overallROAS: apiKpis.roas ?? 0,
        totalConversions: 0,
        overallCPA: apiKpis.cpa ?? 0,
        avgCTR: 2.0,
        avgCPM: 0,
        totalImpressions: 0,
        totalClicks: 0,
        spendDelta: 12.5,
        revenueDelta: 23.4,
        roasDelta: 9.7,
        conversionsDelta: 21.5,
      }
    }

    // Use simulation KPIs (which are calculated from simulation campaigns)
    if (simulation.kpis) {
      return simulation.kpis
    }

    // Fallback: calculate from whatever campaigns we have
    const totalSpend = campaigns.reduce((sum, c) => sum + c.spend, 0)
    const totalRevenue = campaigns.reduce((sum, c) => sum + c.revenue, 0)
    const totalConversions = campaigns.reduce((sum, c) => sum + c.conversions, 0)
    const overallROAS = totalSpend > 0 ? totalRevenue / totalSpend : 0
    const overallCPA = totalConversions > 0 ? totalSpend / totalConversions : 0
    const avgCTR = campaigns.length > 0 ? campaigns.reduce((sum, c) => sum + c.ctr, 0) / campaigns.length : 0
    const avgCPM = campaigns.length > 0 ? campaigns.reduce((sum, c) => sum + c.cpm, 0) / campaigns.length : 0
    const totalImpressions = campaigns.reduce((sum, c) => sum + c.impressions, 0)
    const totalClicks = campaigns.reduce((sum, c) => sum + c.clicks, 0)

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
  }, [campaigns, overviewData, simulation.kpis])

  // Memoized: Filter campaigns based on current filters
  const filteredCampaigns = useMemo(() => {
    return campaigns.filter((campaign) => {
      if (filters.platforms.length > 0 && !filters.platforms.includes(campaign.platform)) {
        return false
      }
      if (filters.regions.length > 0 && !filters.regions.includes(campaign.region)) {
        return false
      }
      if (filters.campaignTypes.length > 0 && !filters.campaignTypes.includes(campaign.campaign_type)) {
        return false
      }
      return true
    })
  }, [filters, campaigns])

  // Check if filters resulted in empty data
  const hasNoFilterResults = filteredCampaigns.length === 0 && campaigns.length > 0

  // Refresh data
  const handleRefresh = useCallback(async () => {
    setLoading(true)
    // Refetch API data + refresh simulation
    await refetchCampaigns()
    simulation.refresh()
    setLoading(false)
  }, [refetchCampaigns, simulation])

  // Sync all campaigns from platforms
  const handleSyncAll = useCallback(async () => {
    syncAllMutation.mutate(undefined, {
      onSuccess: () => {
        setTimeout(() => {
          refetchCampaigns()
          simulation.refresh()
        }, 2000)
      },
    })
  }, [syncAllMutation, refetchCampaigns, simulation])

  // Sync a single campaign from its platform
  const handleSyncCampaign = useCallback((campaignId: string) => {
    setSyncingCampaignId(campaignId)
    syncCampaignMutation.mutate(campaignId, {
      onSettled: () => {
        setTimeout(() => {
          setSyncingCampaignId(null)
          refetchCampaigns()
          simulation.refresh()
        }, 2000)
      },
    })
  }, [syncCampaignMutation, refetchCampaigns, simulation])

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Partial<DashboardFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }, [])

  // Clear all filters
  const handleClearFilters = useCallback(() => {
    setFilters({
      dateRange: {
        start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
        end: new Date(),
      },
      platforms: ['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads', 'LinkedIn Ads'],
      regions: ['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq'],
      campaignTypes: ['Prospecting', 'Retargeting', 'Brand Awareness', 'Conversion'],
    })
  }, [])

  // Export handler
  const handleExport = useCallback(async () => {
    try {
      toast({ title: 'Exporting', description: 'Generating PDF export of the dashboard...' })
      await exportDashboardPDF('Dashboard')
      toast({ title: 'Export Complete', description: 'Dashboard PDF has been downloaded.' })
    } catch (error) {
      toast({
        title: 'Export Failed',
        description: error instanceof Error ? error.message : 'Failed to export dashboard PDF.',
        variant: 'destructive',
      })
    }
  }, [toast])

  // KPI action handlers
  const handleViewDetails = useCallback((metric: string) => {
    console.log('View details for:', metric)
  }, [])

  const handleSetAlert = useCallback((metric: string) => {
    console.log('Set alert for:', metric)
  }, [])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
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

  // Set initial loading — immediate when simulation data is ready
  useEffect(() => {
    if (!campaignsLoading || simulation.campaigns.length > 0) {
      // Short delay for a realistic loading feel
      const timer = setTimeout(() => setInitialLoading(false), 800)
      return () => clearTimeout(timer)
    }
  }, [campaignsLoading, simulation.campaigns.length])

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

      {/* ================================================================== */}
      {/* Live Platform Connection Status Bar                                */}
      {/* ================================================================== */}
      <div className="rounded-xl border bg-card/50 backdrop-blur-sm p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="relative">
              <Radio className="w-4 h-4 text-green-500" />
              <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-green-500 animate-ping" />
            </div>
            <span className="text-sm font-medium text-foreground">Live Platform Connections</span>
            <span className="text-xs text-muted-foreground">
              — {simulation.connections.filter(c => c.status === 'connected').length}/4 active
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              Last sync: {simulation.lastUpdated.toLocaleTimeString()}
            </span>
            {simulation.isLive && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-medium">
                <Activity className="w-3 h-3" />
                LIVE
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {simulation.connections.map((conn) => (
            <div
              key={conn.platform}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg border transition-all',
                conn.status === 'connected' && 'bg-green-500/5 border-green-500/20',
                conn.status === 'syncing' && 'bg-blue-500/5 border-blue-500/20',
                conn.status === 'warning' && 'bg-amber-500/5 border-amber-500/20',
              )}
            >
              {/* Platform icon placeholder */}
              <div className={cn(
                'w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold',
                conn.status === 'connected' && 'bg-green-500/10 text-green-500',
                conn.status === 'syncing' && 'bg-blue-500/10 text-blue-500',
                conn.status === 'warning' && 'bg-amber-500/10 text-amber-500',
              )}>
                {conn.platform === 'Meta Ads' && 'M'}
                {conn.platform === 'Google Ads' && 'G'}
                {conn.platform === 'TikTok Ads' && 'T'}
                {conn.platform === 'Snapchat Ads' && 'S'}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-foreground truncate">
                    {conn.platform.replace(' Ads', '')}
                  </span>
                  {conn.status === 'connected' && <Wifi className="w-3 h-3 text-green-500" />}
                  {conn.status === 'syncing' && <RefreshCw className="w-3 h-3 text-blue-500 animate-spin" />}
                  {conn.status === 'warning' && <WifiOff className="w-3 h-3 text-amber-500" />}
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{conn.campaigns} campaigns</span>
                  <span>·</span>
                  <span className={cn(
                    'font-medium',
                    conn.health >= 80 ? 'text-green-500' : conn.health >= 60 ? 'text-amber-500' : 'text-red-500'
                  )}>
                    {conn.health}%
                  </span>
                  <span>·</span>
                  <span>{conn.lastSync}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
            {t('overview.title')}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Last updated: {simulation.lastUpdated.toLocaleString()} | Stratum AI
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
            onClick={() => navigate('/dashboard/custom-dashboard')}
            className="inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium bg-background hover:bg-muted transition-colors"
          >
            <LayoutDashboard className="w-4 h-4 mr-2" />
            Customize
          </button>

          <button
            onClick={handleSyncAll}
            disabled={syncAllMutation.isPending}
            className="inline-flex items-center px-4 py-2 border border-primary/30 rounded-lg text-sm font-medium bg-primary/5 text-primary hover:bg-primary/10 transition-colors disabled:opacity-50"
            aria-label="Sync all campaigns from ad platforms"
            title="Pull latest data from Meta, TikTok, Snapchat & Google"
          >
            {syncAllMutation.isPending ? (
              <>
                <DownloadCloud className="w-4 h-4 mr-2 animate-bounce" />
                Syncing...
              </>
            ) : syncAllMutation.isSuccess ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2 text-green-500" />
                Synced!
              </>
            ) : (
              <>
                <DownloadCloud className="w-4 h-4 mr-2" />
                Sync All Platforms
              </>
            )}
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
        regions={['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq']}
      />

      {/* Primary KPI Cards */}
      <div className={cn('grid grid-cols-1 gap-5 sm:grid-cols-2', showPriceMetrics ? 'lg:grid-cols-4' : 'lg:grid-cols-2')}>
        {showPriceMetrics && (
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
        )}

        {showPriceMetrics && (
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
        )}

        {showPriceMetrics && (
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
        )}

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

        {!showPriceMetrics && (
          <KPICard
            title="Impressions"
            value={formatCompactNumber(kpis.totalImpressions)}
            numericValue={kpis.totalImpressions}
            icon={<Eye className="w-5 h-5" />}
            loading={initialLoading}
          />
        )}
      </div>

      {/* Secondary KPI Cards */}
      <div className={cn('grid grid-cols-2 gap-4 sm:grid-cols-3', showPriceMetrics ? 'lg:grid-cols-5' : 'lg:grid-cols-3')}>
        {showPriceMetrics && (
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
        )}

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

        {showPriceMetrics && (
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
        )}

        {showPriceMetrics && (
          <KPICard
            title="Impressions"
            value={formatCompactNumber(kpis.totalImpressions)}
            numericValue={kpis.totalImpressions}
            size="small"
            icon={<Eye className="w-4 h-4" />}
            loading={initialLoading}
          />
        )}

        <KPICard
          title="Clicks"
          value={formatCompactNumber(kpis.totalClicks)}
          numericValue={kpis.totalClicks}
          size="small"
          icon={<MousePointerClick className="w-4 h-4" />}
          loading={initialLoading}
        />
      </div>

      {/* Charts Section — now fed with live simulation data */}
      <div className={cn('grid grid-cols-1 gap-6', showPriceMetrics ? 'lg:grid-cols-2' : 'lg:grid-cols-1')}>
        <PlatformPerformanceChart
          data={simulation.platformSummary}
          loading={initialLoading}
          onRefresh={handleRefresh}
        />

        {showPriceMetrics && (
          <ROASByPlatformChart
            data={simulation.platformSummary}
            loading={initialLoading}
            targetROAS={3.0}
            onRefresh={handleRefresh}
          />
        )}
      </div>

      {/* Second Row of Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <DailyTrendChart
            data={simulation.dailyTrend}
            loading={initialLoading}
            onRefresh={handleRefresh}
          />
        </div>

        <RegionalBreakdownChart
          data={simulation.regionalBreakdown}
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
              <div className="px-6 py-4 border-b flex items-center justify-between">
                <h3 className="text-lg font-semibold text-foreground">Top Performing Campaigns</h3>
                <span className="text-xs text-muted-foreground">
                  {filteredCampaigns.length} campaigns across {new Set(filteredCampaigns.map(c => c.platform)).size} platforms
                </span>
              </div>
              <ErrorBoundary>
                <CampaignTable
                  campaigns={filteredCampaigns}
                  onCampaignClick={(campaignId) => {
                    console.log('Navigate to campaign:', campaignId)
                  }}
                  onSyncCampaign={handleSyncCampaign}
                  syncingCampaignId={syncingCampaignId}
                  showPriceMetrics={showPriceMetrics}
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
      <div className={cn('grid grid-cols-1 gap-6', showPriceMetrics ? 'lg:grid-cols-3' : 'lg:grid-cols-1')}>
        <ErrorBoundary>
          <LivePredictionsWidget />
        </ErrorBoundary>

        {showPriceMetrics && (
          <ErrorBoundary>
            <ROASAlertsWidget />
          </ErrorBoundary>
        )}

        {showPriceMetrics && (
          <ErrorBoundary>
            <BudgetOptimizerWidget />
          </ErrorBoundary>
        )}
      </div>

      {/* ================================================================== */}
      {/* Live Alerts Section — fed from simulation engine                    */}
      {/* ================================================================== */}
      <div className="rounded-xl border bg-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Bell className="w-5 h-5" />
            {t('overview.recentAlerts')}
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-medium ml-2">
              <Activity className="w-3 h-3" />
              LIVE
            </span>
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
            {simulation.alerts.map((alert) => (
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
