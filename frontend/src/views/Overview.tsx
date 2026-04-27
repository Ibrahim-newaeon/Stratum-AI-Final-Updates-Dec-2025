/**
 * Overview — COMMAND CENTER DESIGN SYSTEM
 * Premium dashboard overview for Stratum AI
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import {
  RefreshCw,
  Download,
  Bell,
  AlertTriangle,
  CheckCircle,
  Info,
    DollarSign,
  Target,
      ShoppingCart,
  BarChart3,
  Keyboard,
  LayoutDashboard,
  DownloadCloud,
  Radio,
        ArrowUpRight,
  ArrowDownRight,
    Brain,
  Sparkles,
  ChevronRight,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn, formatCurrency } from '@/lib/utils'
import { CampaignTable } from '@/components/dashboard/CampaignTable'
import { AccountBreakdown } from '@/components/dashboard/AccountBreakdown'
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
import { TableSkeleton } from '@/components/ui/Skeleton'
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
import { MorningBriefingCard } from '@/components/dashboard/MorningBriefingCard'
import { AnomalyNarrativesCard } from '@/components/dashboard/AnomalyNarrativesCard'
import { SignalRecoveryCard } from '@/components/dashboard/SignalRecoveryCard'
import { PredictiveBudgetCard } from '@/components/dashboard/PredictiveBudgetCard'
import { AIReportCard } from '@/components/dashboard/AIReportCard'
import { ChurnPreventionCard } from '@/components/dashboard/ChurnPreventionCard'
import { UnifiedNotificationsCard } from '@/components/dashboard/UnifiedNotificationsCard'
import { CrossPlatformOptimizerCard } from '@/components/dashboard/CrossPlatformOptimizerCard'
import { AudienceLifecycleCard } from '@/components/dashboard/AudienceLifecycleCard'
import { GoalTrackingCard } from '@/components/dashboard/GoalTrackingCard'
import { AttributionConfidenceCard } from '@/components/dashboard/AttributionConfidenceCard'
import { LTVForecastCard } from '@/components/dashboard/LTVForecastCard'
import { CreativeScoringCard } from '@/components/dashboard/CreativeScoringCard'
import { CompetitorIntelCard } from '@/components/dashboard/CompetitorIntelCard'
import { ABTestAnalysisCard } from '@/components/dashboard/ABTestAnalysisCard'
import { CollaborativeAnnotationsCard } from '@/components/dashboard/CollaborativeAnnotationsCard'
import { KnowledgeGraphCard } from '@/components/dashboard/KnowledgeGraphCard'
import { JourneyMapCard } from '@/components/dashboard/JourneyMapCard'
import { NLFilterCard } from '@/components/dashboard/NLFilterCard'

/* ═══════════════════════════════════════════════════════════════
   SPARKLINE COMPONENT — gradient area simulation
   ═══════════════════════════════════════════════════════════════ */
function Sparkline({ positive = true }: { positive?: boolean }) {
  return (
    <div className="h-10 w-full relative overflow-hidden">
      <svg viewBox="0 0 120 40" className="w-full h-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`spark-${positive}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={positive ? '#FF1F6D' : '#E85D5D'} stopOpacity="0.3" />
            <stop offset="100%" stopColor={positive ? '#FF1F6D' : '#E85D5D'} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path
          d={positive
            ? 'M0,35 C10,32 20,28 30,30 C40,25 50,20 60,22 C70,15 80,18 90,12 C100,8 110,5 120,2 L120,40 L0,40 Z'
            : 'M0,5 C10,8 20,12 30,10 C40,18 50,22 60,20 C70,28 80,25 90,32 C100,35 110,38 120,40 L120,40 L0,40 Z'
          }
          fill={`url(#spark-${positive})`}
        />
        <path
          d={positive
            ? 'M0,35 C10,32 20,28 30,30 C40,25 50,20 60,22 C70,15 80,18 90,12 C100,8 110,5 120,2'
            : 'M0,5 C10,8 20,12 30,10 C40,18 50,22 60,20 C70,28 80,25 90,32 C100,35 110,38 120,40'
          }
          fill="none"
          stroke={positive ? '#FF8C00' : '#E85D5D'}
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   KPI CARD V2 — Command Center style
   ═══════════════════════════════════════════════════════════════ */
function CommandKPI({
  title,
  value,
  delta,
  deltaLabel,
  positive = true,
  icon: Icon,
}: {
  title: string
  value: string
  delta?: number
  deltaLabel?: string
  positive?: boolean
  icon: React.ElementType
}) {
  return (
    <div className="surface-card p-5 hover:shadow-lg transition-shadow duration-200">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-[#FF8C00]/10">
            <Icon className="h-4 w-4 text-[#FF8C00]" />
          </div>
          <span className="text-xs font-medium uppercase tracking-wider text-[#5A6278]">{title}</span>
        </div>
        {delta !== undefined && (
          <div className={cn('flex items-center gap-1 text-xs font-medium', positive ? 'text-[#27C39D]' : 'text-[#E85D5D]')}>
            {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {Math.abs(delta).toFixed(1)}%
          </div>
        )}
      </div>
      <div className="text-2xl font-semibold text-[#F0EDE5] tracking-tight mb-3">{value}</div>
      <Sparkline positive={positive} />
      {deltaLabel && (
        <p className="mt-2 text-xs text-[#5A6278]">{deltaLabel}</p>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   PLATFORM HEALTH ITEM
   ═══════════════════════════════════════════════════════════════ */
function PlatformHealthItem({
  platform,
  status,
  syncTime,
  campaigns,
}: {
  platform: string
  status: 'connected' | 'syncing' | 'warning' | 'error'
  syncTime: string
  campaigns: number
}) {
  const statusConfig = {
    connected: { dot: 'bg-[#27C39D]', text: 'text-[#27C39D]', label: 'Connected' },
    syncing: { dot: 'bg-[#FF1F6D]', text: 'text-[#FF8C00]', label: 'Syncing' },
    warning: { dot: 'bg-[#F5A623]', text: 'text-[#F5A623]', label: 'Warning' },
    error: { dot: 'bg-[#E85D5D]', text: 'text-[#E85D5D]', label: 'Error' },
  }
  const cfg = statusConfig[status]

  return (
    <div className="flex items-center justify-between py-3 border-b border-[#1E2740]/50 last:border-0">
      <div className="flex items-center gap-3">
        <div className={cn('h-2.5 w-2.5 rounded-full', cfg.dot)} />
        <div>
          <p className="text-sm font-medium text-[#F0EDE5]">{platform}</p>
          <p className="text-xs text-[#5A6278]">{campaigns} campaigns · {syncTime}</p>
        </div>
      </div>
      <span className={cn('text-xs font-medium', cfg.text)}>{cfg.label}</span>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   AI RECOMMENDATION CARD
   ═══════════════════════════════════════════════════════════════ */
function AIRecommendationCard({
  title,
  description,
  impact,
  action,
}: {
  title: string
  description: string
  impact: string
  action: string
}) {
  return (
    <div className="surface-card p-4 border-l-2 border-l-[#FF1F6D] hover:shadow-lg transition-shadow duration-200">
      <div className="flex items-start gap-3 mb-3">
        <div className="p-1.5 rounded-md bg-[#FF8C00]/10 flex-shrink-0">
          <Brain className="h-4 w-4 text-[#FF8C00]" />
        </div>
        <div>
          <h4 className="text-sm font-medium text-[#F0EDE5]">{title}</h4>
          <p className="text-xs text-[#8B92A8] mt-1 leading-relaxed">{description}</p>
        </div>
      </div>
      <div className="flex items-center justify-between mt-3">
        <span className="text-xs text-[#27C39D] font-medium">{impact}</span>
        <button className="text-xs font-medium text-[#FF8C00] hover:text-[#FF4D8F] transition-colors duration-200 flex items-center gap-1">
          {action} <ChevronRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════ */
export function Overview() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { toast } = useToast()
  const timeoutsRef = useRef<Set<ReturnType<typeof setTimeout>>>(new Set())

  useEffect(() => {
    return () => {
      timeoutsRef.current.forEach(clearTimeout)
      timeoutsRef.current.clear()
    }
  }, [])

  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [showKeyboardHints, setShowKeyboardHints] = useState(false)
  const [timeRange, setTimeRange] = useState<'7D' | '30D' | '90D'>('30D')

  const tenantId = useTenantStore((state) => state.tenantId)
  const { showPriceMetrics } = usePriceMetrics()

  const syncAllMutation = useSyncAllCampaigns()
  const syncCampaignMutation = useSyncCampaign()
  const [syncingCampaignId, setSyncingCampaignId] = useState<string | null>(null)

  const { data: campaignsData, isLoading: campaignsLoading, refetch: refetchCampaigns } = useCampaigns()
  const { data: overviewData } = useTenantOverview(tenantId ?? 0)

  const simulation = useLiveSimulation(10000)

  const [filters, setFilters] = useState<DashboardFilters>({
    dateRange: {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      end: new Date(),
    },
    platforms: ['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads', 'LinkedIn Ads'],
    regions: ['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq'],
    campaignTypes: ['Prospecting', 'Retargeting', 'Brand Awareness', 'Conversion'],
  })

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
    return simulation.campaigns
  }, [campaignsData, simulation.campaigns])

  const kpis = useMemo((): KPIMetrics => {
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
    if (simulation.kpis) return simulation.kpis

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
      totalSpend, totalRevenue, overallROAS, totalConversions, overallCPA,
      avgCTR, avgCPM, totalImpressions, totalClicks,
      spendDelta: 12.5, revenueDelta: 23.4, roasDelta: 9.7, conversionsDelta: 21.5,
    }
  }, [campaigns, overviewData, simulation.kpis])

  const filteredCampaigns = useMemo(() => {
    return campaigns.filter((campaign) => {
      if (filters.platforms.length > 0 && !filters.platforms.includes(campaign.platform)) return false
      if (filters.regions.length > 0 && !filters.regions.includes(campaign.region)) return false
      if (filters.campaignTypes.length > 0 && !filters.campaignTypes.includes(campaign.campaign_type)) return false
      return true
    })
  }, [filters, campaigns])

  const hasNoFilterResults = filteredCampaigns.length === 0 && campaigns.length > 0

  const handleRefresh = useCallback(async () => {
    setLoading(true)
    await refetchCampaigns()
    simulation.refresh()
    setLoading(false)
  }, [refetchCampaigns, simulation])

  const handleSyncAll = useCallback(async () => {
    syncAllMutation.mutate(undefined, {
      onSuccess: () => {
        const id = setTimeout(() => { refetchCampaigns(); simulation.refresh() }, 2000)
        timeoutsRef.current.add(id)
      },
    })
  }, [syncAllMutation, refetchCampaigns, simulation])

  const handleSyncCampaign = useCallback((campaignId: string) => {
    setSyncingCampaignId(campaignId)
    syncCampaignMutation.mutate(campaignId, {
      onSettled: () => {
        const id = setTimeout(() => { setSyncingCampaignId(null); refetchCampaigns(); simulation.refresh() }, 2000)
        timeoutsRef.current.add(id)
      },
    })
  }, [syncCampaignMutation, refetchCampaigns, simulation])

  const handleFilterChange = useCallback((newFilters: Partial<DashboardFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }, [])

  const handleClearFilters = useCallback(() => {
    setFilters({
      dateRange: { start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), end: new Date() },
      platforms: ['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads', 'LinkedIn Ads'],
      regions: ['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq'],
      campaignTypes: ['Prospecting', 'Retargeting', 'Brand Awareness', 'Conversion'],
    })
  }, [])

  const handleExport = useCallback(async () => {
    try {
      toast({ title: 'Exporting', description: 'Generating PDF export of the dashboard...' })
      await exportDashboardPDF('Dashboard')
      toast({ title: 'Export Complete', description: 'Dashboard PDF has been downloaded.' })
    } catch (error) {
      toast({ title: 'Export Failed', description: error instanceof Error ? error.message : 'Failed to export dashboard PDF.', variant: 'destructive' })
    }
  }, [toast])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      switch (e.key.toLowerCase()) {
        case 'r':
          if (!e.ctrlKey && !e.metaKey) { e.preventDefault(); handleRefresh() }
          break
        case 'e':
          if (!e.ctrlKey && !e.metaKey) { e.preventDefault(); handleExport() }
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

  useEffect(() => {
    if (!campaignsLoading || simulation.campaigns.length > 0) setInitialLoading(false)
  }, [campaignsLoading, simulation.campaigns.length])

  const activeFilterCount =
    (filters.platforms.length < 4 ? 4 - filters.platforms.length : 0) +
    (filters.regions.length < 6 ? 6 - filters.regions.length : 0)

  return (
    <div className="space-y-8">
      {/* ── AI CARDS (kept from original) ────────────────────── */}
      <MorningBriefingCard />
      <SignalRecoveryCard />
      <AnomalyNarrativesCard />
      <PredictiveBudgetCard />
      <AIReportCard />
      <ChurnPreventionCard />
      <CrossPlatformOptimizerCard />
      <GoalTrackingCard />
      <AttributionConfidenceCard />
      <LTVForecastCard />
      <CreativeScoringCard />
      <CompetitorIntelCard />
      <ABTestAnalysisCard />
      <CollaborativeAnnotationsCard />
      <KnowledgeGraphCard />
      <JourneyMapCard />
      <NLFilterCard />
      <AudienceLifecycleCard />
      <UnifiedNotificationsCard />

      {/* ── KEYBOARD SHORTCUTS MODAL ─────────────────────────── */}
      {showKeyboardHints && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowKeyboardHints(false)}>
          <div className="bg-[#0F1320] border border-[#1E2740] rounded-xl p-6 shadow-xl max-w-sm w-full mx-4 animate-in fade-in zoom-in-95 duration-200" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2 mb-4">
              <Keyboard className="w-5 h-5 text-[#FF8C00]" />
              <h3 className="text-lg font-semibold text-[#F0EDE5]">Keyboard Shortcuts</h3>
            </div>
            <div className="space-y-3">
              {[{ key: 'R', action: 'Refresh data' }, { key: 'E', action: 'Export dashboard' }, { key: '?', action: 'Toggle shortcuts' }, { key: 'Esc', action: 'Close modal' }].map((shortcut) => (
                <div key={shortcut.key} className="flex items-center justify-between">
                  <span className="text-[#8B92A8]">{shortcut.action}</span>
                  <kbd className="px-2 py-1 text-xs font-mono bg-[#1E2740] rounded border border-[#1E2740]">{shortcut.key}</kbd>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── PAGE HEADER ──────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-[#F0EDE5]">{t('overview.title')}</h1>
          <p className="mt-1 text-sm text-[#5A6278]">
            Last updated: {simulation.lastUpdated.toLocaleString()} · <span className="text-[#27C39D]">Stratum AI</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setShowKeyboardHints(true)} className="hidden lg:flex items-center px-3 py-2 text-xs text-[#5A6278] hover:text-[#F0EDE5] transition-colors duration-200" title="Keyboard shortcuts (?)" aria-label="Keyboard shortcuts">
            <Keyboard className="w-4 h-4 mr-1" />
            <kbd className="px-1.5 py-0.5 text-xs bg-[#1E2740] rounded">?</kbd>
          </button>
          <button onClick={() => navigate('/dashboard/custom-dashboard')} className="inline-flex items-center px-4 py-2 border border-[#1E2740] rounded-lg text-sm font-medium bg-[#0F1320] text-[#F0EDE5] hover:bg-[#1E2740] transition-colors duration-200">
            <LayoutDashboard className="w-4 h-4 mr-2" />
            Customize
          </button>
          <button onClick={handleSyncAll} disabled={syncAllMutation.isPending} className="inline-flex items-center px-4 py-2 border border-[#FF1F6D]/30 rounded-lg text-sm font-medium bg-[#FF1F6D]/5 text-[#FF8C00] hover:bg-[#FF8C00]/10 transition-colors duration-200 disabled:opacity-50" aria-label="Sync all campaigns from ad platforms" title="Pull latest data from Meta, TikTok, Snapchat & Google">
            {syncAllMutation.isPending ? (<><DownloadCloud className="w-4 h-4 mr-2 animate-pulse" /> Syncing...</>) : syncAllMutation.isSuccess ? (<><CheckCircle className="w-4 h-4 mr-2 text-[#27C39D]" /> Synced!</>) : (<><DownloadCloud className="w-4 h-4 mr-2" /> Sync All Platforms</>)}
          </button>
          <button onClick={handleRefresh} disabled={loading} className="inline-flex items-center px-4 py-2 border border-[#1E2740] rounded-lg text-sm font-medium bg-[#0F1320] text-[#F0EDE5] hover:bg-[#1E2740] transition-colors duration-200 disabled:opacity-50" aria-label="Refresh data (R)">
            {loading ? (<><RefreshCw className="w-4 h-4 mr-2 animate-spin" /> Refreshing...</>) : (<><RefreshCw className="w-4 h-4 mr-2" /> Refresh</>)}
          </button>
          <button onClick={handleExport} className="inline-flex items-center px-4 py-2 rounded-lg bg-[#FF1F6D] text-[#080C14] hover:bg-[#FF4D8F] transition-colors duration-200 font-medium" aria-label="Export dashboard (E)">
            <Download className="w-4 h-4 mr-2" />
            {t('common.export')}
          </button>
        </div>
      </div>

      {/* ── FILTER BAR ───────────────────────────────────────── */}
      <FilterBar filters={filters} onChange={handleFilterChange} platforms={['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads', 'LinkedIn Ads']} regions={['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq']} />

      {/* ═══════════════════════════════════════════════════════
          TOP ROW — 4 KPI CARDS
         ═══════════════════════════════════════════════════════ */}
      <div className={cn('grid grid-cols-1 gap-5 sm:grid-cols-2', showPriceMetrics ? 'lg:grid-cols-4' : 'lg:grid-cols-2')}>
        {showPriceMetrics && (
          <CommandKPI title="Total Spend" value={formatCurrency(kpis.totalSpend)} delta={kpis.spendDelta} deltaLabel="vs last period" positive={(kpis.spendDelta ?? 0) > 0} icon={DollarSign} />
        )}
        {showPriceMetrics && (
          <CommandKPI title="ROAS" value={`${kpis.overallROAS.toFixed(2)}x`} delta={kpis.roasDelta} deltaLabel="vs target" positive={(kpis.roasDelta ?? 0) > 0} icon={Target} />
        )}
        <CommandKPI title="Conversions" value={kpis.totalConversions.toLocaleString('en-US')} delta={kpis.conversionsDelta} deltaLabel="vs last period" positive={(kpis.conversionsDelta ?? 0) > 0} icon={ShoppingCart} />
        <CommandKPI title="Active Campaigns" value={String(filteredCampaigns.length)} delta={undefined} deltaLabel="Across all platforms" positive icon={BarChart3} />
      </div>

      {/* ═══════════════════════════════════════════════════════
          SECOND ROW — PERFORMANCE + PLATFORM HEALTH
         ═══════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Performance Over Time */}
        <div className="lg:col-span-2 surface-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-semibold text-[#F0EDE5]">Performance Over Time</h3>
              <p className="text-xs text-[#5A6278] mt-0.5">Revenue and spend trends</p>
            </div>
            <div className="flex items-center gap-1 p-1 rounded-lg bg-[#1E2740]/30 border border-[#1E2740]">
              {(['7D', '30D', '90D'] as const).map((range) => (
                <button
                  key={range}
                  onClick={() => setTimeRange(range)}
                  className={cn(
                    'px-3 py-1 text-xs font-medium rounded-md transition-colors duration-200',
                    timeRange === range ? 'bg-gradient-to-r from-[#FF1F6D]/10 to-[#FF8C00]/10 text-[#FF8C00]' : 'text-[#5A6278] hover:text-[#F0EDE5]'
                  )}
                >
                  {range}
                </button>
              ))}
            </div>
          </div>
          {/* Chart placeholder with gradient fill */}
          <div className="h-64 w-full relative rounded-lg overflow-hidden bg-[#080C14] border border-[#1E2740]">
            <div className="absolute inset-0 opacity-30">
              <svg viewBox="0 0 600 200" className="w-full h-full" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="perf-grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#FF8C00" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#FF8C00" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d="M0,180 C50,170 100,140 150,150 C200,120 250,80 300,90 C350,50 400,60 450,30 C500,20 550,10 600,5 L600,200 L0,200 Z" fill="url(#perf-grad)" />
                <path d="M0,180 C50,170 100,140 150,150 C200,120 250,80 300,90 C350,50 400,60 450,30 C500,20 550,10 600,5" fill="none" stroke="#FF8C00" strokeWidth="2" />
                <path d="M0,190 C60,185 120,175 180,180 C240,170 300,160 360,165 C420,155 480,150 540,145 C580,140 600,138" fill="none" stroke="#27C39D" strokeWidth="2" strokeDasharray="4 4" />
              </svg>
            </div>
            <div className="absolute bottom-4 left-4 flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-[#FF1F6D]" />
                <span className="text-xs text-[#8B92A8]">Revenue</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-[#27C39D]" />
                <span className="text-xs text-[#8B92A8]">Spend</span>
              </div>
            </div>
          </div>
        </div>

        {/* Platform Health */}
        <div className="surface-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-[#F0EDE5]">Platform Health</h3>
            <div className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-[#27C39D]" />
              <span className="text-xs text-[#27C39D] font-medium">Live</span>
            </div>
          </div>
          <div>
            <PlatformHealthItem platform="Meta Ads" status="connected" syncTime="2m ago" campaigns={12} />
            <PlatformHealthItem platform="Google Ads" status="connected" syncTime="5m ago" campaigns={8} />
            <PlatformHealthItem platform="TikTok Ads" status="syncing" syncTime="Now" campaigns={4} />
            <PlatformHealthItem platform="Snapchat Ads" status="warning" syncTime="15m ago" campaigns={3} />
          </div>
          <button className="mt-4 w-full py-2 text-xs font-medium text-[#FF8C00] hover:text-[#FF4D8F] transition-colors duration-200 border border-[#1E2740] rounded-lg hover:border-[#FF1F6D]/30">
            View All Connections
          </button>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════
          THIRD ROW — ALERTS + AI RECOMMENDATIONS
         ═══════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <div className="surface-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-base font-semibold text-[#F0EDE5] flex items-center gap-2">
              <Bell className="w-4 h-4 text-[#FF8C00]" />
              Recent Alerts
            </h3>
            <button className="text-xs text-[#FF8C00] hover:text-[#FF4D8F] transition-colors duration-200">View all</button>
          </div>
          {initialLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-[#1E2740]/30 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {simulation.alerts.slice(0, 4).map((alert) => (
                <div
                  key={alert.id}
                  className={cn(
                    'flex items-start gap-3 p-3 rounded-lg border transition-colors duration-200 hover:shadow-md cursor-pointer',
                    alert.severity === 'warning' && 'bg-[#F5A623]/5 border-[#F5A623]/20 hover:bg-[#F5A623]/10',
                    alert.severity === 'good' && 'bg-[#27C39D]/5 border-[#27C39D]/20 hover:bg-[#27C39D]/10',
                    alert.severity === 'critical' && 'bg-[#E85D5D]/5 border-[#E85D5D]/20 hover:bg-[#E85D5D]/10'
                  )}
                  role="button"
                  tabIndex={0}
                  aria-label={`${alert.severity} alert: ${alert.title}`}
                >
                  {alert.severity === 'warning' && <AlertTriangle className="w-4 h-4 text-[#F5A623] mt-0.5 flex-shrink-0" aria-hidden="true" />}
                  {alert.severity === 'good' && <CheckCircle className="w-4 h-4 text-[#27C39D] mt-0.5 flex-shrink-0" aria-hidden="true" />}
                  {alert.severity === 'critical' && <Info className="w-4 h-4 text-[#E85D5D] mt-0.5 flex-shrink-0" aria-hidden="true" />}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#F0EDE5]">{alert.title}</p>
                    <p className="text-xs text-[#5A6278] mt-0.5 line-clamp-2">{alert.message}</p>
                  </div>
                  <span className="text-[10px] text-[#5A6278] flex-shrink-0">{alert.time}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Recommendations */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-[#F0EDE5] flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#FF8C00]" />
              AI Recommendations
            </h3>
            <span className="text-xs text-[#5A6278]">3 new today</span>
          </div>
          <AIRecommendationCard
            title="Increase Meta Budget"
            description="ROAS is 3.2x on Meta prospecting campaigns. Consider shifting 15% from underperforming Google search."
            impact="+$12,400/mo"
            action="Apply"
          />
          <AIRecommendationCard
            title="Refresh Creative Assets"
            description="CTR on TikTok assets older than 14 days has dropped 18%. New batch recommended."
            impact="+8.5% CTR"
            action="Review"
          />
          <AIRecommendationCard
            title="Optimal Bid Adjustment"
            description="AI model predicts 12% lower CPA if you decrease Google max CPC by $0.40 at peak hours."
            impact="-$3,200/mo"
            action="Simulate"
          />
        </div>
      </div>

      {/* ── ORIGINAL FEATURE CARDS (preserved data/logic) ────── */}
      <div className={cn('grid grid-cols-1 gap-6', showPriceMetrics ? 'lg:grid-cols-2' : 'lg:grid-cols-1')}>
        <PlatformPerformanceChart data={simulation.platformSummary} loading={initialLoading} onRefresh={handleRefresh} />
        {showPriceMetrics && <ROASByPlatformChart data={simulation.platformSummary} loading={initialLoading} targetROAS={3.0} onRefresh={handleRefresh} />}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <DailyTrendChart data={simulation.dailyTrend} loading={initialLoading} onRefresh={handleRefresh} />
        </div>
        <RegionalBreakdownChart data={simulation.regionalBreakdown} loading={initialLoading} onRefresh={handleRefresh} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {initialLoading ? (
            <TableSkeleton rows={5} columns={7} />
          ) : hasNoFilterResults ? (
            <div className="surface-card overflow-hidden">
              <div className="px-6 py-4 border-b border-[#1E2740]">
                <h3 className="text-lg font-semibold text-[#F0EDE5]">Top Performing Campaigns</h3>
              </div>
              <NoFilterResultsState onClearFilters={handleClearFilters} filterCount={activeFilterCount} />
            </div>
          ) : (
            <div className="surface-card overflow-hidden">
              <div className="px-6 py-4 border-b border-[#1E2740] flex items-center justify-between">
                <h3 className="text-lg font-semibold text-[#F0EDE5]">Top Performing Campaigns</h3>
                <span className="text-xs text-[#5A6278]">{filteredCampaigns.length} campaigns across {new Set(filteredCampaigns.map(c => c.platform)).size} platforms</span>
              </div>
              <ErrorBoundary>
                <CampaignTable campaigns={filteredCampaigns} onCampaignClick={(campaignId) => { window.location.href = `/dashboard/campaigns/${campaignId}` }} onSyncCampaign={handleSyncCampaign} syncingCampaignId={syncingCampaignId} showPriceMetrics={showPriceMetrics} />
              </ErrorBoundary>
            </div>
          )}
        </div>
        <ErrorBoundary><AccountBreakdown tenantId={tenantId ?? 0} /></ErrorBoundary>
        <ErrorBoundary><SimulateSlider /></ErrorBoundary>
      </div>

      <div className={cn('grid grid-cols-1 gap-6', showPriceMetrics ? 'lg:grid-cols-3' : 'lg:grid-cols-1')}>
        <ErrorBoundary><LivePredictionsWidget /></ErrorBoundary>
        {showPriceMetrics && <ErrorBoundary><ROASAlertsWidget /></ErrorBoundary>}
        {showPriceMetrics && <ErrorBoundary><BudgetOptimizerWidget /></ErrorBoundary>}
      </div>
    </div>
  )
}

export default Overview
