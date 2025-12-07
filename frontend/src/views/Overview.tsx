/**
 * Dashboard Overview Page
 * Stratum AI Marketing Intelligence Platform
 *
 * Features:
 * - Real-time KPI cards
 * - Interactive charts
 * - Campaign performance table
 * - Advanced filtering
 * - Responsive design
 */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
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
} from 'lucide-react'
import { cn, formatCurrency, formatCompactNumber } from '@/lib/utils'
import { KPICard } from '@/components/dashboard/KPICard'
import { CampaignTable } from '@/components/dashboard/CampaignTable'
import { FilterBar } from '@/components/dashboard/FilterBar'
import { SimulateSlider } from '@/components/widgets/SimulateSlider'
import {
  Campaign,
  DashboardFilters,
  KPIMetrics,
  PlatformSummary,
  DailyPerformance,
} from '@/types/dashboard'

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
]

const mockPlatformSummary: PlatformSummary[] = [
  { platform: 'Meta Ads', spend: 18100, revenue: 67400, conversions: 770, roas: 3.72, cpa: 23.51, impressions: 1810000, clicks: 36200 },
  { platform: 'Google Ads', spend: 8200, revenue: 28700, conversions: 287, roas: 3.5, cpa: 28.57, impressions: 980000, clicks: 19600 },
  { platform: 'TikTok Ads', spend: 15000, revenue: 37500, conversions: 500, roas: 2.5, cpa: 30.0, impressions: 2500000, clicks: 50000 },
  { platform: 'Snapchat Ads', spend: 4500, revenue: 11250, conversions: 150, roas: 2.5, cpa: 30.0, impressions: 750000, clicks: 15000 },
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

const REGION_COLORS = ['#6366f1', '#ec4899', '#f97316', '#14b8a6', '#8b5cf6', '#f43f5e']

export function Overview() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  // Filter state
  const [filters, setFilters] = useState<DashboardFilters>({
    dateRange: {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
      end: new Date(),
    },
    platforms: ['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads'],
    regions: ['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq'],
    campaignTypes: ['Prospecting', 'Retargeting', 'Brand Awareness', 'Conversion'],
  })

  // Calculate KPI metrics from campaigns
  const calculateKPIs = useCallback((): KPIMetrics => {
    const totalSpend = mockCampaigns.reduce((sum, c) => sum + c.spend, 0)
    const totalRevenue = mockCampaigns.reduce((sum, c) => sum + c.revenue, 0)
    const totalConversions = mockCampaigns.reduce((sum, c) => sum + c.conversions, 0)
    const overallROAS = totalSpend > 0 ? totalRevenue / totalSpend : 0
    const overallCPA = totalConversions > 0 ? totalSpend / totalConversions : 0
    const avgCTR = mockCampaigns.reduce((sum, c) => sum + c.ctr, 0) / mockCampaigns.length
    const avgCPM = mockCampaigns.reduce((sum, c) => sum + c.cpm, 0) / mockCampaigns.length
    const totalImpressions = mockCampaigns.reduce((sum, c) => sum + c.impressions, 0)
    const totalClicks = mockCampaigns.reduce((sum, c) => sum + c.clicks, 0)

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
  }, [])

  const kpis = calculateKPIs()

  // Refresh data
  const handleRefresh = useCallback(async () => {
    setLoading(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setLastUpdated(new Date())
    setLoading(false)
  }, [])

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Partial<DashboardFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }, [])

  // Auto-refresh every 5 minutes
  useEffect(() => {
    const interval = setInterval(handleRefresh, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [handleRefresh])

  // Regional data for pie chart
  const regionalData = [
    { name: 'Saudi Arabia', value: 45, color: REGION_COLORS[0] },
    { name: 'UAE', value: 30, color: REGION_COLORS[1] },
    { name: 'Qatar', value: 10, color: REGION_COLORS[2] },
    { name: 'Kuwait', value: 8, color: REGION_COLORS[3] },
    { name: 'Other', value: 7, color: REGION_COLORS[4] },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-foreground">
            {t('overview.title')}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Last updated: {lastUpdated.toLocaleString()} | Stratum AI
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium bg-background hover:bg-muted transition-colors disabled:opacity-50"
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

          <button className="inline-flex items-center px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
            <Download className="w-4 h-4 mr-2" />
            {t('common.export')}
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        platforms={['Meta Ads', 'Google Ads', 'TikTok Ads', 'Snapchat Ads']}
        regions={['Saudi Arabia', 'UAE', 'Qatar', 'Kuwait', 'Jordan', 'Iraq']}
      />

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Spend"
          value={formatCurrency(kpis.totalSpend)}
          delta={kpis.spendDelta}
          deltaText="vs last period"
          trend={kpis.spendDelta && kpis.spendDelta > 0 ? 'up' : 'down'}
          icon={<DollarSign className="w-5 h-5" />}
        />

        <KPICard
          title="Total Revenue"
          value={formatCurrency(kpis.totalRevenue)}
          delta={kpis.revenueDelta}
          deltaText="vs last period"
          trend={kpis.revenueDelta && kpis.revenueDelta > 0 ? 'up' : 'down'}
          trendIsGood={true}
          icon={<TrendingUp className="w-5 h-5" />}
        />

        <KPICard
          title="ROAS"
          value={`${kpis.overallROAS.toFixed(2)}x`}
          delta={kpis.roasDelta}
          deltaText="vs target"
          trend={kpis.roasDelta && kpis.roasDelta > 0 ? 'up' : 'down'}
          trendIsGood={true}
          highlight={kpis.overallROAS >= 3.0}
          icon={<Target className="w-5 h-5" />}
        />

        <KPICard
          title="Total Conversions"
          value={kpis.totalConversions.toLocaleString('en-US')}
          delta={kpis.conversionsDelta}
          deltaText="vs last period"
          trend={kpis.conversionsDelta && kpis.conversionsDelta > 0 ? 'up' : 'down'}
          trendIsGood={true}
          icon={<ShoppingCart className="w-5 h-5" />}
        />
      </div>

      {/* Secondary KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <KPICard
          title="CPA"
          value={formatCurrency(kpis.overallCPA)}
          size="small"
          icon={<DollarSign className="w-4 h-4" />}
        />

        <KPICard
          title="CTR"
          value={`${kpis.avgCTR.toFixed(2)}%`}
          size="small"
          icon={<MousePointerClick className="w-4 h-4" />}
        />

        <KPICard
          title="CPM"
          value={formatCurrency(kpis.avgCPM)}
          size="small"
          icon={<BarChart3 className="w-4 h-4" />}
        />

        <KPICard
          title="Impressions"
          value={formatCompactNumber(kpis.totalImpressions)}
          size="small"
          icon={<Eye className="w-4 h-4" />}
        />

        <KPICard
          title="Clicks"
          value={formatCompactNumber(kpis.totalClicks)}
          size="small"
          icon={<MousePointerClick className="w-4 h-4" />}
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Platform Performance Chart */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">
            Platform Performance Comparison
          </h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mockPlatformSummary}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="platform" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 12 }} tickLine={false} axisLine={false} tickFormatter={(value) => formatCompactNumber(value)} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                  formatter={(value: number, name: string) => [
                    name === 'spend' || name === 'revenue' ? formatCurrency(value) : value,
                    name.charAt(0).toUpperCase() + name.slice(1),
                  ]}
                />
                <Legend />
                <Bar dataKey="spend" name="Spend" fill="#f97316" radius={[4, 4, 0, 0]} />
                <Bar dataKey="revenue" name="Revenue" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* ROAS by Platform */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">ROAS by Platform</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mockPlatformSummary} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis type="number" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} domain={[0, 5]} tickFormatter={(value) => `${value}x`} />
                <YAxis dataKey="platform" type="category" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} width={100} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                  formatter={(value: number) => [`${value.toFixed(2)}x`, 'ROAS']}
                />
                <Bar dataKey="roas" name="ROAS" fill="#10b981" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Second Row of Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Daily Performance Trend */}
        <div className="lg:col-span-2 rounded-xl border bg-card p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Daily Performance Trend</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockDailyPerformance}>
                <defs>
                  <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorSpend" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 12 }} tickLine={false} axisLine={false} tickFormatter={(value) => formatCompactNumber(value)} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                  formatter={(value: number) => [formatCurrency(value), '']}
                />
                <Legend />
                <Area type="monotone" dataKey="revenue" name="Revenue" stroke="#0ea5e9" strokeWidth={2} fillOpacity={1} fill="url(#colorRevenue)" />
                <Area type="monotone" dataKey="spend" name="Spend" stroke="#f97316" strokeWidth={2} fillOpacity={1} fill="url(#colorSpend)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Regional Breakdown */}
        <div className="rounded-xl border bg-card p-6">
          <h3 className="text-lg font-semibold text-foreground mb-4">Performance by Region</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={regionalData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {regionalData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                  formatter={(value: number) => [`${value}%`, 'Share']}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Third Row - Table and Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Campaign Performance Table */}
        <div className="lg:col-span-2 rounded-xl border bg-card overflow-hidden">
          <div className="px-6 py-4 border-b">
            <h3 className="text-lg font-semibold text-foreground">Top Performing Campaigns</h3>
          </div>
          <CampaignTable
            campaigns={mockCampaigns}
            onCampaignClick={(campaignId) => {
              console.log('Navigate to campaign:', campaignId)
            }}
          />
        </div>

        {/* Simulator Widget */}
        <SimulateSlider />
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

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {mockAlerts.map((alert) => (
            <div
              key={alert.id}
              className={cn(
                'p-4 rounded-lg border-l-4',
                alert.severity === 'warning' && 'bg-amber-500/10 border-amber-500',
                alert.severity === 'good' && 'bg-green-500/10 border-green-500',
                alert.severity === 'critical' && 'bg-red-500/10 border-red-500'
              )}
            >
              <div className="flex items-start gap-3">
                {alert.severity === 'warning' && <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5" />}
                {alert.severity === 'good' && <CheckCircle className="w-5 h-5 text-green-500 mt-0.5" />}
                {alert.severity === 'critical' && <Info className="w-5 h-5 text-red-500 mt-0.5" />}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-foreground">{alert.title}</p>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{alert.message}</p>
                  <p className="text-xs text-muted-foreground mt-2">{alert.time}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Overview
