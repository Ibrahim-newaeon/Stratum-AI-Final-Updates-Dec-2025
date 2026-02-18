import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts'
import {
  Trophy,
  TrendingUp,
  TrendingDown,
  Target,
  Globe,
  Download,
  RefreshCw,
  Info,
  ExternalLink,
  Plus,
  Smartphone,
  Monitor,
  Laptop,
  Tablet,
  Loader2,
} from 'lucide-react'
import { cn, formatCurrency, formatPercent, formatCompactNumber } from '@/lib/utils'
import { SmartTooltip } from '@/components/guide/SmartTooltip'
import { useCompetitors } from '@/api/hooks'
import apiClient from '@/api/client'

// Colors for competitors in charts
const COMPETITOR_COLORS = ['#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#6366f1', '#ec4899']

export function Benchmarks() {
  const { t } = useTranslation()
  const [selectedIndustry, setSelectedIndustry] = useState('ecommerce')
  const [selectedPlatform, setSelectedPlatform] = useState('all')
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Fetch competitors from API
  const { data: competitorsData, isLoading: isLoadingCompetitors, refetch: refetchCompetitors } = useCompetitors()

  // Benchmark data state (loaded from API when available)
  const [benchmarkData, setBenchmarkData] = useState<{
    metrics: any[] | null
    radarData: any[] | null
    geoData: any[] | null
    languageData: any[] | null
    deviceData: any[] | null
    osData: any[] | null
  }>({
    metrics: null,
    radarData: null,
    geoData: null,
    languageData: null,
    deviceData: null,
    osData: null,
  })

  // Refresh handler — fetches latest data from API
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    try {
      const params: Record<string, string> = {}
      if (selectedPlatform !== 'all') params.platform = selectedPlatform
      if (selectedIndustry) params.industry = selectedIndustry

      const [metricsRes, geoRes, audienceRes] = await Promise.allSettled([
        apiClient.get('/benchmarks/metrics', { params }),
        apiClient.get('/benchmarks/geographic', { params }),
        apiClient.get('/benchmarks/audience', { params }),
      ])

      setBenchmarkData((prev) => ({
        ...prev,
        metrics: metricsRes.status === 'fulfilled' ? (metricsRes.value.data?.data || metricsRes.value.data) : prev.metrics,
        geoData: geoRes.status === 'fulfilled' ? (geoRes.value.data?.data || geoRes.value.data) : prev.geoData,
        languageData: audienceRes.status === 'fulfilled' ? (audienceRes.value.data?.data?.languages || null) : prev.languageData,
        deviceData: audienceRes.status === 'fulfilled' ? (audienceRes.value.data?.data?.devices || null) : prev.deviceData,
        osData: audienceRes.status === 'fulfilled' ? (audienceRes.value.data?.data?.operating_systems || null) : prev.osData,
      }))
      refetchCompetitors()
    } catch {
      // Silently handle errors — empty states will show
    } finally {
      setIsRefreshing(false)
    }
  }, [selectedPlatform, selectedIndustry, refetchCompetitors])

  // Generate Meta Ads Library URL
  const getMetaAdsLibraryUrl = (name: string, country: string = 'SA') => {
    return `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=${country}&q=${encodeURIComponent(name)}&search_type=keyword_unordered`
  }

  // Generate Google Ads Transparency URL
  const getGoogleTransparencyUrl = (name: string) => {
    return `https://adstransparency.google.com/?query=${encodeURIComponent(name)}`
  }

  // Build competitor data for charts
  const chartCompetitors = [
    { name: 'Your Brand', roas: 3.5, ctr: 2.8, cpc: 1.2, share: 18, color: '#0ea5e9', isYou: true },
    ...(competitorsData?.items || []).slice(0, 5).map((comp: any, index: number) => ({
      name: comp.name,
      domain: comp.domain,
      country: comp.country || 'SA',
      roas: comp.estimatedRoas ?? (2.5 + (index * 0.4)),
      ctr: comp.estimatedCtr ?? (1.8 + (index * 0.3)),
      cpc: comp.estimatedCpc ?? (0.8 + (index * 0.2)),
      share: comp.shareOfVoice ?? (10 + (index * 5)),
      color: COMPETITOR_COLORS[index % COMPETITOR_COLORS.length],
    })),
    { name: 'Industry Avg', roas: 3.0, ctr: 2.4, cpc: 1.3, share: 22, color: '#6b7280', isAvg: true },
  ]

  // Check if user has competitors
  const hasCompetitors = (competitorsData?.items?.length || 0) > 0

  // Radar chart data — from API or default "awaiting data" values
  const radarData = benchmarkData.radarData || [
    { metric: 'ROAS', you: 0, industry: 0 },
    { metric: 'CTR', you: 0, industry: 0 },
    { metric: 'CPC', you: 0, industry: 0 },
    { metric: 'Conv Rate', you: 0, industry: 0 },
    { metric: 'Reach', you: 0, industry: 0 },
    { metric: 'Engagement', you: 0, industry: 0 },
  ]

  // Benchmark summary metric cards — from API or defaults indicating no data
  const benchmarkMetrics = benchmarkData.metrics || [
    {
      label: 'ROAS',
      yours: 0,
      industry: 0,
      percentile: 0,
      trend: 'up',
      tooltip: t('benchmarks.roasTooltip'),
    },
    {
      label: 'CTR',
      yours: 0,
      industry: 0,
      percentile: 0,
      trend: 'up',
      format: 'percent',
      tooltip: t('benchmarks.ctrTooltip'),
    },
    {
      label: 'CPC',
      yours: 0,
      industry: 0,
      percentile: 0,
      trend: 'down',
      format: 'currency',
      invertTrend: true,
      tooltip: t('benchmarks.cpcTooltip'),
    },
    {
      label: 'Conv. Rate',
      yours: 0,
      industry: 0,
      percentile: 0,
      trend: 'up',
      format: 'percent',
      tooltip: t('benchmarks.convRateTooltip'),
    },
  ]

  const formatValue = (value: number, format?: string) => {
    if (value === 0) return '—'
    if (format === 'percent') return formatPercent(value)
    if (format === 'currency') return formatCurrency(value)
    return value.toFixed(2) + 'x'
  }

  // Device icon helper
  const getDeviceIcon = (device: string) => {
    const d = device.toLowerCase()
    if (d.includes('mobile') || d.includes('phone')) return <Smartphone className="w-4 h-4" />
    if (d.includes('tablet') || d.includes('ipad')) return <Tablet className="w-4 h-4" />
    if (d.includes('desktop') || d.includes('pc')) return <Monitor className="w-4 h-4" />
    return <Laptop className="w-4 h-4" />
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Trophy className="w-7 h-7 text-primary" />
            {t('benchmarks.title')}
          </h1>
          <p className="text-muted-foreground">{t('benchmarks.subtitle')}</p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedIndustry}
            onChange={(e) => setSelectedIndustry(e.target.value)}
            className="px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="ecommerce">E-commerce</option>
            <option value="saas">SaaS</option>
            <option value="finance">Finance</option>
            <option value="retail">Retail</option>
          </select>

          <select
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            className="px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">All Platforms</option>
            <option value="google">Google Ads</option>
            <option value="meta">Meta Ads</option>
            <option value="tiktok">TikTok Ads</option>
          </select>

          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-2 rounded-lg border hover:bg-muted transition-colors disabled:opacity-50"
            title="Refresh benchmark data"
          >
            <RefreshCw className={cn('w-4 h-4', isRefreshing && 'animate-spin')} />
          </button>

          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
            <Download className="w-4 h-4" />
            {t('common.export')}
          </button>
        </div>
      </div>

      {/* Benchmark Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {benchmarkMetrics.map((metric: any) => {
          const hasData = metric.yours > 0 || metric.industry > 0
          const isAboveAvg = metric.invertTrend
            ? metric.yours < metric.industry
            : metric.yours > metric.industry
          const diff = metric.industry > 0 ? ((metric.yours - metric.industry) / metric.industry) * 100 : 0

          return (
            <div key={metric.label} className="p-4 rounded-xl border bg-card">
              <div className="flex items-center justify-between mb-2">
                <SmartTooltip content={metric.tooltip} position="top">
                  <span className="text-sm text-muted-foreground flex items-center gap-1 cursor-help">
                    {metric.label}
                    <Info className="w-3 h-3" />
                  </span>
                </SmartTooltip>
                {hasData && (
                  <span className="text-xs text-muted-foreground">
                    Top {100 - (metric.percentile || 0)}%
                  </span>
                )}
              </div>
              {hasData ? (
                <>
                  <div className="flex items-end justify-between">
                    <div>
                      <p className="text-2xl font-bold">
                        {formatValue(metric.yours, metric.format)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Industry: {formatValue(metric.industry, metric.format)}
                      </p>
                    </div>
                    <div
                      className={cn(
                        'flex items-center gap-1 text-sm font-medium',
                        isAboveAvg ? 'text-green-500' : 'text-red-500'
                      )}
                    >
                      {isAboveAvg ? (
                        <TrendingUp className="w-4 h-4" />
                      ) : (
                        <TrendingDown className="w-4 h-4" />
                      )}
                      {Math.abs(diff).toFixed(0)}%
                    </div>
                  </div>
                  <div className="mt-3 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn(
                        'h-full rounded-full transition-all',
                        isAboveAvg ? 'bg-green-500' : 'bg-red-500'
                      )}
                      style={{ width: `${metric.percentile || 0}%` }}
                    />
                  </div>
                </>
              ) : (
                <div className="flex items-center justify-center py-3">
                  <p className="text-sm text-muted-foreground">
                    Click refresh to load data
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Your Competitors Section */}
      <div className="rounded-xl border bg-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              Your Tracked Competitors
            </h3>
            <p className="text-xs text-muted-foreground">
              Click to view their ads in Meta Ads Library or Google Transparency
            </p>
          </div>
          <Link
            to="/dashboard/competitors"
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Competitor
          </Link>
        </div>

        {isLoadingCompetitors ? (
          <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading competitors...
          </div>
        ) : !hasCompetitors ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground mb-3">No competitors tracked yet</p>
            <Link
              to="/dashboard/competitors"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Your First Competitor
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {(competitorsData?.items || []).slice(0, 6).map((competitor: any) => (
              <div key={competitor.id} className="p-3 rounded-lg border bg-background">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="font-medium text-sm">{competitor.name}</p>
                    <p className="text-xs text-muted-foreground">{competitor.domain}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <a
                    href={getMetaAdsLibraryUrl(competitor.name, competitor.country || 'SA')}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-blue-500/10 text-blue-600 hover:bg-blue-500/20 transition-colors"
                  >
                    <span className="font-bold">M</span>
                    Meta
                    <ExternalLink className="w-3 h-3" />
                  </a>
                  <a
                    href={getGoogleTransparencyUrl(competitor.name)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-green-500/10 text-green-600 hover:bg-green-500/20 transition-colors"
                  >
                    <span className="font-bold">G</span>
                    Google
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Competitor Comparison */}
        <div className="rounded-xl border bg-card p-5">
          <h3 className="font-semibold mb-4">{t('benchmarks.competitorComparison')}</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartCompetitors} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis
                  dataKey="name"
                  type="category"
                  tick={{ fontSize: 12 }}
                  width={100}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                />
                <Bar dataKey="roas" name="ROAS" radius={[0, 4, 4, 0]}>
                  {chartCompetitors.map((entry: any, index: number) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.isYou ? '#0ea5e9' : entry.isAvg ? '#6b7280' : entry.color || '#94a3b8'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Performance Radar */}
        <div className="rounded-xl border bg-card p-5">
          <h3 className="font-semibold mb-4">{t('benchmarks.performanceRadar')}</h3>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid className="stroke-muted" />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} />
                <PolarRadiusAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
                <Radar
                  name="You"
                  dataKey="you"
                  stroke="#0ea5e9"
                  fill="#0ea5e9"
                  fillOpacity={0.3}
                />
                <Radar
                  name="Industry"
                  dataKey="industry"
                  stroke="#6b7280"
                  fill="#6b7280"
                  fillOpacity={0.1}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '0.5rem',
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center gap-6 mt-2">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-primary" />
              <span className="text-sm text-muted-foreground">Your Performance</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gray-400" />
              <span className="text-sm text-muted-foreground">Industry Average</span>
            </div>
          </div>
        </div>
      </div>

      {/* Language & Device Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Language Breakdown */}
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold flex items-center gap-2">
                <Globe className="w-5 h-5 text-primary" />
                Language Breakdown
              </h3>
              <p className="text-xs text-muted-foreground">Performance by audience language</p>
            </div>
          </div>

          {benchmarkData.languageData && benchmarkData.languageData.length > 0 ? (
            <div className="space-y-3">
              {benchmarkData.languageData.map((lang: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg border bg-background">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{lang.flag || '🌐'}</span>
                    <div>
                      <p className="font-medium text-sm">{lang.name || lang.language}</p>
                      <p className="text-xs text-muted-foreground">{formatCompactNumber(lang.impressions || 0)} impressions</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-sm">{formatPercent(lang.ctr || 0)} CTR</p>
                    <p className="text-xs text-muted-foreground">{lang.share ? `${lang.share}% of traffic` : ''}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Globe className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground mb-1">No language data available yet</p>
              <p className="text-xs text-muted-foreground">Click refresh to load audience insights from your connected platforms.</p>
            </div>
          )}
        </div>

        {/* Device Breakdown */}
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold flex items-center gap-2">
                <Smartphone className="w-5 h-5 text-primary" />
                Device Breakdown
              </h3>
              <p className="text-xs text-muted-foreground">Performance by device type</p>
            </div>
          </div>

          {benchmarkData.deviceData && benchmarkData.deviceData.length > 0 ? (
            <div className="space-y-3">
              {benchmarkData.deviceData.map((device: any, i: number) => {
                const pct = device.share || 0
                return (
                  <div key={i} className="p-3 rounded-lg border bg-background">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {getDeviceIcon(device.name || device.device)}
                        <span className="font-medium text-sm">{device.name || device.device}</span>
                      </div>
                      <span className="text-sm font-semibold">{pct}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="flex justify-between mt-1 text-xs text-muted-foreground">
                      <span>CTR: {formatPercent(device.ctr || 0)}</span>
                      <span>ROAS: {device.roas ? `${device.roas.toFixed(1)}x` : '—'}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <Smartphone className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground mb-1">No device data available yet</p>
              <p className="text-xs text-muted-foreground">Click refresh to load device breakdown from your connected platforms.</p>
            </div>
          )}
        </div>
      </div>

      {/* Operating System Breakdown */}
      <div className="rounded-xl border bg-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold flex items-center gap-2">
              <Monitor className="w-5 h-5 text-primary" />
              Operating System
            </h3>
            <p className="text-xs text-muted-foreground">Performance breakdown by OS</p>
          </div>
        </div>

        {benchmarkData.osData && benchmarkData.osData.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {benchmarkData.osData.map((os: any, i: number) => (
              <div key={i} className="p-4 rounded-lg border bg-background text-center">
                <div className="w-12 h-12 mx-auto mb-2 rounded-xl bg-muted flex items-center justify-center">
                  <span className="text-lg font-bold text-muted-foreground">
                    {(os.name || os.os || '?').charAt(0).toUpperCase()}
                  </span>
                </div>
                <p className="font-medium text-sm mb-1">{os.name || os.os}</p>
                <p className="text-2xl font-bold">{os.share || 0}%</p>
                <div className="flex justify-center gap-3 mt-2 text-xs text-muted-foreground">
                  <span>CTR {formatPercent(os.ctr || 0)}</span>
                  <span>ROAS {os.roas ? `${os.roas.toFixed(1)}x` : '—'}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Monitor className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground mb-1">No operating system data available yet</p>
            <p className="text-xs text-muted-foreground">Click refresh to load OS breakdown from your connected platforms.</p>
          </div>
        )}
      </div>

      {/* Geographic Performance */}
      <div className="rounded-xl border bg-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold flex items-center gap-2">
              <Globe className="w-5 h-5 text-primary" />
              {t('benchmarks.geographicPerformance')}
            </h3>
            <p className="text-xs text-muted-foreground">{t('benchmarks.performanceByRegion')}</p>
          </div>
        </div>

        {benchmarkData.geoData && benchmarkData.geoData.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {benchmarkData.geoData.map((region: any, i: number) => (
              <div key={i} className="p-4 rounded-lg border bg-background">
                <p className="font-medium text-sm mb-2">{region.region || region.name}</p>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Impressions</span>
                    <span className="font-medium">{formatCompactNumber(region.impressions || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">CTR</span>
                    <span className="font-medium">{formatPercent(region.ctr || 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">ROAS</span>
                    <span className="font-semibold text-green-500">{region.roas ? `${region.roas.toFixed(1)}x` : '—'}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <Globe className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground mb-1">No geographic data available yet</p>
            <p className="text-xs text-muted-foreground">Click refresh to load regional performance from your connected platforms.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default Benchmarks

// Cell component for BarChart (needed for recharts)
const Cell = ({ fill, ...props }: any) => <rect fill={fill} {...props} />
