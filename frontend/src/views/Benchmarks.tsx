import { useState } from 'react'
import { useTranslation } from 'react-i18next'
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
  ScatterChart,
  Scatter,
  ZAxis,
} from 'recharts'
import {
  Trophy,
  TrendingUp,
  TrendingDown,
  Target,
  Users,
  Globe,
  Filter,
  Download,
  RefreshCw,
  Info,
} from 'lucide-react'
import { cn, formatCurrency, formatPercent, formatCompactNumber } from '@/lib/utils'
import { SmartTooltip } from '@/components/guide/SmartTooltip'
import { InfoIcon } from '@/components/ui/InfoIcon'

// Mock competitor data
const mockCompetitors = [
  { name: 'Your Brand', roas: 3.5, ctr: 2.8, cpc: 1.2, share: 18, color: '#0ea5e9', isYou: true },
  { name: 'Competitor A', roas: 3.2, ctr: 2.5, cpc: 1.4, share: 24, color: '#8b5cf6' },
  { name: 'Competitor B', roas: 2.9, ctr: 2.2, cpc: 1.6, share: 21, color: '#f59e0b' },
  { name: 'Competitor C', roas: 3.8, ctr: 3.1, cpc: 1.0, share: 15, color: '#10b981' },
  { name: 'Industry Avg', roas: 3.0, ctr: 2.4, cpc: 1.3, share: 22, color: '#6b7280', isAvg: true },
]

// Mock radar data
const mockRadarData = [
  { metric: 'ROAS', you: 85, industry: 70 },
  { metric: 'CTR', you: 78, industry: 65 },
  { metric: 'CPC', you: 72, industry: 75 },
  { metric: 'Conv Rate', you: 82, industry: 60 },
  { metric: 'Reach', you: 65, industry: 80 },
  { metric: 'Engagement', you: 90, industry: 72 },
]

// Mock market share trend
const mockMarketShareTrend = Array.from({ length: 12 }, (_, i) => ({
  month: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i],
  you: 15 + Math.random() * 5 + i * 0.3,
  compA: 22 + Math.random() * 4 - i * 0.2,
  compB: 20 + Math.random() * 3,
  compC: 14 + Math.random() * 4 + i * 0.1,
}))

// Mock demographic data for heatmap
const mockDemographics = [
  { age: '18-24', male: 2.1, female: 2.8, ctr: 2.45 },
  { age: '25-34', male: 3.5, female: 4.2, ctr: 3.85 },
  { age: '35-44', male: 2.8, female: 3.1, ctr: 2.95 },
  { age: '45-54', male: 1.9, female: 2.2, ctr: 2.05 },
  { age: '55-64', male: 1.4, female: 1.6, ctr: 1.50 },
  { age: '65+', male: 0.9, female: 1.1, ctr: 1.00 },
]

// Mock geographic data
const mockGeoData = [
  { region: 'California', impressions: 4500000, ctr: 3.2, roas: 4.1, x: 100, y: 200, z: 45 },
  { region: 'New York', impressions: 3800000, ctr: 2.9, roas: 3.8, x: 350, y: 150, z: 38 },
  { region: 'Texas', impressions: 3200000, ctr: 2.5, roas: 3.2, x: 200, y: 280, z: 32 },
  { region: 'Florida', impressions: 2900000, ctr: 2.7, roas: 3.5, x: 340, y: 320, z: 29 },
  { region: 'Illinois', impressions: 2100000, ctr: 2.3, roas: 3.0, x: 250, y: 180, z: 21 },
]

export function Benchmarks() {
  const { t } = useTranslation()
  const [selectedIndustry, setSelectedIndustry] = useState('ecommerce')
  const [selectedPlatform, setSelectedPlatform] = useState('all')

  const benchmarkMetrics = [
    {
      label: 'ROAS',
      yours: 3.5,
      industry: 3.0,
      percentile: 75,
      trend: 'up',
      tooltip: t('benchmarks.roasTooltip'),
    },
    {
      label: 'CTR',
      yours: 2.8,
      industry: 2.4,
      percentile: 68,
      trend: 'up',
      format: 'percent',
      tooltip: t('benchmarks.ctrTooltip'),
    },
    {
      label: 'CPC',
      yours: 1.2,
      industry: 1.3,
      percentile: 62,
      trend: 'down',
      format: 'currency',
      invertTrend: true,
      tooltip: t('benchmarks.cpcTooltip'),
    },
    {
      label: 'Conv. Rate',
      yours: 4.2,
      industry: 3.5,
      percentile: 82,
      trend: 'up',
      format: 'percent',
      tooltip: t('benchmarks.convRateTooltip'),
    },
  ]

  const formatValue = (value: number, format?: string) => {
    if (format === 'percent') return formatPercent(value)
    if (format === 'currency') return formatCurrency(value)
    return value.toFixed(2) + 'x'
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

          <button className="p-2 rounded-lg border hover:bg-muted transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>

          <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
            <Download className="w-4 h-4" />
            {t('common.export')}
          </button>
        </div>
      </div>

      {/* Benchmark Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {benchmarkMetrics.map((metric) => {
          const isAboveAvg = metric.invertTrend
            ? metric.yours < metric.industry
            : metric.yours > metric.industry
          const diff = ((metric.yours - metric.industry) / metric.industry) * 100

          return (
            <div key={metric.label} className="p-4 rounded-xl border bg-card">
              <div className="flex items-center justify-between mb-2">
                <SmartTooltip content={metric.tooltip} position="top">
                  <span className="text-sm text-muted-foreground flex items-center gap-1 cursor-help">
                    {metric.label}
                    <Info className="w-3 h-3" />
                  </span>
                </SmartTooltip>
                <span className="text-xs text-muted-foreground">
                  Top {100 - metric.percentile}%
                </span>
              </div>
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
                  style={{ width: `${metric.percentile}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Competitor Comparison */}
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <h3 className="font-semibold">{t('benchmarks.competitorComparison')}</h3>
            <SmartTooltip
              content="Compare your ROAS against competitors and industry average. Blue bar is your brand, gray is industry average."
              position="right"
              trigger="click"
            >
              <InfoIcon size={14} aria-label="Competitor comparison information" />
            </SmartTooltip>
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mockCompetitors} layout="vertical">
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
                  {mockCompetitors.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.isYou ? '#0ea5e9' : entry.isAvg ? '#6b7280' : '#94a3b8'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Performance Radar */}
        <div className="rounded-xl border bg-card p-5">
          <div className="flex items-center gap-2 mb-4">
            <h3 className="font-semibold">{t('benchmarks.performanceRadar')}</h3>
            <SmartTooltip
              content="Multi-metric comparison showing your performance vs industry average across key metrics. Larger area indicates better performance."
              position="right"
              trigger="click"
            >
              <InfoIcon size={14} aria-label="Performance radar information" />
            </SmartTooltip>
          </div>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={mockRadarData}>
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

      {/* Demographics Heatmap */}
      <div className="rounded-xl border bg-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold flex items-center gap-2">
                <Users className="w-5 h-5 text-primary" />
                {t('benchmarks.demographicsHeatmap')}
              </h3>
              <SmartTooltip
                content="CTR performance by age and gender segments. Darker colors indicate higher click-through rates."
                position="right"
                trigger="click"
              >
                <InfoIcon size={14} aria-label="Demographics heatmap information" />
              </SmartTooltip>
            </div>
            <p className="text-xs text-muted-foreground">{t('benchmarks.ctrBySegment')}</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b">
                <th className="p-3 text-left text-sm font-medium">Age Group</th>
                <th className="p-3 text-center text-sm font-medium">Male CTR%</th>
                <th className="p-3 text-center text-sm font-medium">Female CTR%</th>
                <th className="p-3 text-center text-sm font-medium">Average</th>
              </tr>
            </thead>
            <tbody>
              {mockDemographics.map((row) => (
                <tr key={row.age} className="border-b last:border-0">
                  <td className="p-3 font-medium">{row.age}</td>
                  <td className="p-3">
                    <div
                      className="mx-auto w-16 py-1 rounded text-center text-sm font-medium"
                      style={{
                        backgroundColor: `rgba(14, 165, 233, ${row.male / 5})`,
                        color: row.male > 2.5 ? 'white' : 'inherit',
                      }}
                    >
                      {formatPercent(row.male)}
                    </div>
                  </td>
                  <td className="p-3">
                    <div
                      className="mx-auto w-16 py-1 rounded text-center text-sm font-medium"
                      style={{
                        backgroundColor: `rgba(236, 72, 153, ${row.female / 5})`,
                        color: row.female > 2.5 ? 'white' : 'inherit',
                      }}
                    >
                      {formatPercent(row.female)}
                    </div>
                  </td>
                  <td className="p-3 text-center font-semibold">{formatPercent(row.ctr)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Geographic Performance */}
      <div className="rounded-xl border bg-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold flex items-center gap-2">
                <Globe className="w-5 h-5 text-primary" />
                {t('benchmarks.geographicPerformance')}
              </h3>
              <SmartTooltip
                content="Regional performance metrics including impressions, CTR, and ROAS. Identify top-performing geographic markets."
                position="right"
                trigger="click"
              >
                <InfoIcon size={14} aria-label="Geographic performance information" />
              </SmartTooltip>
            </div>
            <p className="text-xs text-muted-foreground">{t('benchmarks.performanceByRegion')}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {mockGeoData.map((region) => (
            <div key={region.region} className="p-4 rounded-lg border bg-background">
              <p className="font-medium text-sm mb-2">{region.region}</p>
              <div className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Impressions</span>
                  <span className="font-medium">{formatCompactNumber(region.impressions)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">CTR</span>
                  <span className="font-medium">{formatPercent(region.ctr)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">ROAS</span>
                  <span className="font-semibold text-green-500">{region.roas.toFixed(1)}x</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Benchmarks

// Cell component for BarChart (needed for recharts)
const Cell = ({ fill, ...props }: any) => <rect fill={fill} {...props} />
