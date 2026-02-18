/**
 * EMQ Benchmarks (Super Admin View)
 *
 * Cross-tenant EMQ benchmarks by platform and industry
 * Shows P25/P50/P75 percentiles and trends
 */

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { useEmqBenchmarks } from '@/api/hooks'
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CalendarIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'

type Platform = 'all' | 'meta' | 'google' | 'tiktok' | 'snapchat' | 'linkedin'
type TimeRange = '7d' | '30d' | '90d'
type Metric = 'emq' | 'freshness' | 'dataLoss' | 'variance' | 'errors'

interface BenchmarkData {
  platform: string
  p25: number
  p50: number
  p75: number
  trend: number // percentage change from previous period
  sampleSize: number
}

interface DriverBenchmark {
  driver: string
  label: string
  p25: number
  p50: number
  p75: number
  yourValue?: number
}

export default function Benchmarks() {
  const [platform, _setPlatform] = useState<Platform>('all')
  const [timeRange, setTimeRange] = useState<TimeRange>('30d')
  const [selectedMetric, setSelectedMetric] = useState<Metric>('emq')

  const { data: _benchmarksData } = useEmqBenchmarks(new Date().toISOString().split('T')[0], platform === 'all' ? undefined : platform)

  // Sample benchmark data
  const platformBenchmarks: BenchmarkData[] = [
    { platform: 'Meta', p25: 72, p50: 82, p75: 91, trend: 2.3, sampleSize: 245 },
    { platform: 'Google', p25: 78, p50: 86, p75: 93, trend: 1.8, sampleSize: 312 },
    { platform: 'TikTok', p25: 65, p50: 76, p75: 85, trend: -1.2, sampleSize: 156 },
    { platform: 'Snapchat', p25: 58, p50: 71, p75: 82, trend: 0.5, sampleSize: 89 },
    { platform: 'LinkedIn', p25: 75, p50: 84, p75: 92, trend: 3.1, sampleSize: 67 },
  ]

  const driverBenchmarks: DriverBenchmark[] = [
    { driver: 'freshness', label: 'Data Freshness', p25: 85, p50: 92, p75: 98 },
    { driver: 'dataLoss', label: 'Data Completeness', p25: 78, p50: 88, p75: 95 },
    { driver: 'variance', label: 'Attribution Variance', p25: 70, p50: 82, p75: 91 },
    { driver: 'errors', label: 'Error Rate (inverted)', p25: 88, p50: 94, p75: 99 },
  ]

  // Industry benchmarks
  const industryBenchmarks = [
    { industry: 'E-commerce', p50: 84, trend: 2.1, count: 156 },
    { industry: 'SaaS', p50: 86, trend: 1.5, count: 89 },
    { industry: 'Retail', p50: 79, trend: -0.8, count: 124 },
    { industry: 'Healthcare', p50: 81, trend: 1.2, count: 45 },
    { industry: 'Finance', p50: 88, trend: 2.8, count: 67 },
    { industry: 'Education', p50: 77, trend: 0.3, count: 34 },
  ]

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-success'
    if (score >= 60) return 'text-warning'
    return 'text-danger'
  }

  const getTrendIcon = (trend: number) => {
    if (trend > 0) return <ArrowTrendingUpIcon className="w-4 h-4 text-success" />
    if (trend < 0) return <ArrowTrendingDownIcon className="w-4 h-4 text-danger" />
    return null
  }

  const renderPercentileBar = (p25: number, p50: number, p75: number) => {
    return (
      <div className="relative h-8 bg-surface-tertiary rounded-lg overflow-hidden">
        {/* P25-P75 range */}
        <div
          className="absolute h-full bg-stratum-500/20"
          style={{ left: `${p25}%`, width: `${p75 - p25}%` }}
        />
        {/* P25 marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-stratum-400/50"
          style={{ left: `${p25}%` }}
        />
        {/* P50 marker (median) */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-stratum-500"
          style={{ left: `${p50}%` }}
        />
        {/* P75 marker */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-stratum-400/50"
          style={{ left: `${p75}%` }}
        />
        {/* Labels */}
        <div className="absolute inset-0 flex items-center justify-between px-2 text-xs text-text-muted">
          <span>0</span>
          <span>100</span>
        </div>
      </div>
    )
  }

  const metrics = [
    { id: 'emq' as Metric, label: 'Overall EMQ' },
    { id: 'freshness' as Metric, label: 'Freshness' },
    { id: 'dataLoss' as Metric, label: 'Completeness' },
    { id: 'variance' as Metric, label: 'Variance' },
    { id: 'errors' as Metric, label: 'Error Rate' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">EMQ Benchmarks</h1>
          <p className="text-text-muted">Cross-tenant performance benchmarks</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Time Range */}
          <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-surface-secondary border border-white/10">
            <CalendarIcon className="w-5 h-5 text-text-muted" />
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as TimeRange)}
              className="bg-transparent text-white focus:outline-none"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
            </select>
          </div>
        </div>
      </div>

      {/* Metric Selector */}
      <div className="flex items-center gap-2 flex-wrap">
        {metrics.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelectedMetric(m.id)}
            className={cn(
              'px-4 py-2 rounded-lg transition-colors',
              selectedMetric === m.id
                ? 'bg-stratum-500/10 text-stratum-400 border border-stratum-500/30'
                : 'bg-surface-secondary border border-white/10 text-text-muted hover:text-white'
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">Platform Average</div>
          <div className="text-3xl font-bold text-white">82</div>
          <div className="flex items-center gap-1 text-success text-sm mt-1">
            <ArrowTrendingUpIcon className="w-4 h-4" />
            +1.8% vs last period
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">P25 (Bottom Quartile)</div>
          <div className="text-3xl font-bold text-warning">68</div>
          <div className="text-sm text-text-muted mt-1">Needs improvement</div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">P50 (Median)</div>
          <div className="text-3xl font-bold text-stratum-400">82</div>
          <div className="text-sm text-text-muted mt-1">Typical performance</div>
        </div>

        <div className="p-4 rounded-xl bg-surface-secondary border border-white/10">
          <div className="text-text-muted text-sm mb-1">P75 (Top Quartile)</div>
          <div className="text-3xl font-bold text-success">91</div>
          <div className="text-sm text-text-muted mt-1">Best performers</div>
        </div>
      </div>

      {/* Platform Benchmarks */}
      <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <ChartBarIcon className="w-5 h-5 text-stratum-400" />
            <h2 className="font-semibold text-white">Platform Benchmarks</h2>
          </div>
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <InformationCircleIcon className="w-4 h-4" />
            Based on {platformBenchmarks.reduce((sum, p) => sum + p.sampleSize, 0)} tenants
          </div>
        </div>

        <div className="p-4">
          <div className="grid gap-6">
            {platformBenchmarks.map((benchmark) => (
              <div key={benchmark.platform}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <span className="font-medium text-white">{benchmark.platform}</span>
                    <span className="text-xs text-text-muted">
                      ({benchmark.sampleSize} tenants)
                    </span>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1 text-sm">
                      {getTrendIcon(benchmark.trend)}
                      <span className={benchmark.trend >= 0 ? 'text-success' : 'text-danger'}>
                        {benchmark.trend >= 0 ? '+' : ''}{benchmark.trend}%
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-text-muted">P25:</span>
                      <span className={getScoreColor(benchmark.p25)}>{benchmark.p25}</span>
                      <span className="text-text-muted ml-2">P50:</span>
                      <span className={getScoreColor(benchmark.p50)}>{benchmark.p50}</span>
                      <span className="text-text-muted ml-2">P75:</span>
                      <span className={getScoreColor(benchmark.p75)}>{benchmark.p75}</span>
                    </div>
                  </div>
                </div>
                {renderPercentileBar(benchmark.p25, benchmark.p50, benchmark.p75)}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Driver Benchmarks */}
      <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
        <div className="flex items-center gap-3 p-4 border-b border-white/10">
          <ChartBarIcon className="w-5 h-5 text-stratum-400" />
          <h2 className="font-semibold text-white">Driver Benchmarks</h2>
        </div>

        <div className="p-4">
          <div className="grid gap-6">
            {driverBenchmarks.map((benchmark) => (
              <div key={benchmark.driver}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-white">{benchmark.label}</span>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-text-muted">P25:</span>
                    <span className={getScoreColor(benchmark.p25)}>{benchmark.p25}</span>
                    <span className="text-text-muted ml-2">P50:</span>
                    <span className={getScoreColor(benchmark.p50)}>{benchmark.p50}</span>
                    <span className="text-text-muted ml-2">P75:</span>
                    <span className={getScoreColor(benchmark.p75)}>{benchmark.p75}</span>
                  </div>
                </div>
                {renderPercentileBar(benchmark.p25, benchmark.p50, benchmark.p75)}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Industry Benchmarks */}
      <div className="rounded-2xl bg-surface-secondary border border-white/10 overflow-hidden">
        <div className="flex items-center gap-3 p-4 border-b border-white/10">
          <ChartBarIcon className="w-5 h-5 text-stratum-400" />
          <h2 className="font-semibold text-white">Industry Benchmarks</h2>
        </div>

        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {industryBenchmarks.map((benchmark) => (
              <div
                key={benchmark.industry}
                className="p-4 rounded-xl bg-surface-tertiary border border-white/5"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-white">{benchmark.industry}</span>
                  <span className="text-xs text-text-muted">
                    {benchmark.count} tenants
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className={cn('text-3xl font-bold', getScoreColor(benchmark.p50))}>
                    {benchmark.p50}
                  </span>
                  <div className="flex items-center gap-1 text-sm">
                    {getTrendIcon(benchmark.trend)}
                    <span className={benchmark.trend >= 0 ? 'text-success' : 'text-danger'}>
                      {benchmark.trend >= 0 ? '+' : ''}{benchmark.trend}%
                    </span>
                  </div>
                </div>
                <div className="text-xs text-text-muted mt-2">Median EMQ</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-8 py-4 text-sm text-text-muted">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded bg-stratum-500/20 border-l-2 border-stratum-400/50" />
          <span>P25-P75 Range</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1 h-3 rounded bg-stratum-500" />
          <span>Median (P50)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-success">80+</span>
          <span>Healthy</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-warning">60-79</span>
          <span>At Risk</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-danger">&lt;60</span>
          <span>Critical</span>
        </div>
      </div>
    </div>
  )
}
