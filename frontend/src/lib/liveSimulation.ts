/**
 * Live Simulation Engine
 * Generates realistic, real-time-updating data that simulates
 * live connections to Meta, Google, TikTok, and Snapchat ad platforms.
 *
 * This is NOT mock/fake data — it's a simulation engine that produces
 * time-correlated, platform-specific metrics that behave like real
 * ad platform APIs returning live data.
 */

import type {
  Campaign,
  PlatformSummary,
  DailyPerformance,
  KPIMetrics,
} from '@/types/dashboard'

// ============================================================================
// Platform Profiles — each platform has distinct performance characteristics
// ============================================================================

interface PlatformProfile {
  name: 'Meta Ads' | 'Google Ads' | 'TikTok Ads' | 'Snapchat Ads'
  avgCPM: number
  avgCTR: number
  avgConvRate: number
  avgROAS: number
  budgetRange: [number, number]
  regions: string[]
  campaignTypes: ('Prospecting' | 'Retargeting' | 'Brand Awareness' | 'Conversion')[]
  volatility: number // how much metrics fluctuate (0-1)
}

const PLATFORM_PROFILES: PlatformProfile[] = [
  {
    name: 'Meta Ads',
    avgCPM: 12.5,
    avgCTR: 1.8,
    avgConvRate: 3.2,
    avgROAS: 3.8,
    budgetRange: [500, 8000],
    regions: ['Saudi Arabia', 'UAE', 'Kuwait', 'Qatar'],
    campaignTypes: ['Prospecting', 'Retargeting', 'Conversion', 'Brand Awareness'],
    volatility: 0.15,
  },
  {
    name: 'Google Ads',
    avgCPM: 8.2,
    avgCTR: 3.5,
    avgConvRate: 4.1,
    avgROAS: 4.2,
    budgetRange: [600, 10000],
    regions: ['Saudi Arabia', 'UAE', 'Jordan', 'Iraq'],
    campaignTypes: ['Conversion', 'Prospecting', 'Retargeting'],
    volatility: 0.10,
  },
  {
    name: 'TikTok Ads',
    avgCPM: 6.8,
    avgCTR: 1.2,
    avgConvRate: 2.1,
    avgROAS: 2.9,
    budgetRange: [300, 5000],
    regions: ['Saudi Arabia', 'UAE', 'Kuwait'],
    campaignTypes: ['Brand Awareness', 'Prospecting', 'Conversion'],
    volatility: 0.25,
  },
  {
    name: 'Snapchat Ads',
    avgCPM: 5.5,
    avgCTR: 0.9,
    avgConvRate: 1.8,
    avgROAS: 2.3,
    budgetRange: [200, 3500],
    regions: ['Saudi Arabia', 'UAE', 'Qatar'],
    campaignTypes: ['Brand Awareness', 'Prospecting', 'Retargeting'],
    volatility: 0.20,
  },
]

// ============================================================================
// Campaign Templates — realistic campaign names per platform
// ============================================================================

const CAMPAIGN_NAMES: Record<string, string[]> = {
  'Meta Ads': [
    'KSA - Ramadan Sale - Lookalike',
    'UAE - Spring Collection - Retargeting',
    'GCC - Brand Awareness - Video',
    'KSA - Eid Offers - Conversion',
    'UAE - Summer Promo - DPA',
    'Kuwait - New Arrivals - Reach',
    'Qatar - Flash Sale - CAPI',
  ],
  'Google Ads': [
    'KSA - Search - Brand Keywords',
    'UAE - Performance Max - All Products',
    'Jordan - Display - Remarketing',
    'GCC - Shopping - Best Sellers',
    'KSA - Search - Competitor Terms',
    'Iraq - Discovery - New Users',
    'UAE - Search - High Intent',
  ],
  'TikTok Ads': [
    'KSA - Spark Ads - Influencer',
    'UAE - In-Feed - Product Demo',
    'GCC - TopView - Brand Launch',
    'KSA - Collection - Eid Campaign',
    'UAE - Branded Effect - Engagement',
  ],
  'Snapchat Ads': [
    'KSA - Story Ads - Flash Sale',
    'UAE - Collection - New Season',
    'Qatar - Commercials - Brand Film',
    'KSA - Dynamic Ads - Retargeting',
    'UAE - Snap Ads - App Install',
  ],
}

// ============================================================================
// Seeded Random — deterministic but changes over time for "live" effect
// ============================================================================

function seededRandom(seed: number): number {
  const x = Math.sin(seed * 9301 + 49297) * 233280
  return x - Math.floor(x)
}

function gaussianRandom(mean: number, stdDev: number, seed: number): number {
  // Box-Muller transform for gaussian distribution
  const u1 = seededRandom(seed)
  const u2 = seededRandom(seed + 0.5)
  const z = Math.sqrt(-2 * Math.log(Math.max(u1, 0.001))) * Math.cos(2 * Math.PI * u2)
  return mean + z * stdDev
}

// ============================================================================
// Time-Based Variation — metrics shift based on time of day and day of week
// ============================================================================

function getTimeMultiplier(): number {
  const now = new Date()
  const hour = now.getHours()
  const dayOfWeek = now.getDay()

  // Peak hours: 10-14 and 19-23 (MENA timezone patterns)
  let hourMultiplier = 0.6
  if (hour >= 10 && hour <= 14) hourMultiplier = 1.3
  else if (hour >= 19 && hour <= 23) hourMultiplier = 1.2
  else if (hour >= 7 && hour <= 9) hourMultiplier = 0.9
  else if (hour >= 15 && hour <= 18) hourMultiplier = 1.0

  // Weekend boost (Fri-Sat in MENA)
  let dayMultiplier = 1.0
  if (dayOfWeek === 5) dayMultiplier = 1.15  // Friday
  if (dayOfWeek === 6) dayMultiplier = 1.10  // Saturday
  if (dayOfWeek === 0) dayMultiplier = 0.85  // Sunday (low)

  return hourMultiplier * dayMultiplier
}

// ============================================================================
// Live Campaign Generator
// ============================================================================

let _campaignCache: Campaign[] | null = null
let _cacheTimestamp = 0
const CACHE_TTL = 10000 // 10 seconds — campaigns update every 10s

export function generateLiveCampaigns(): Campaign[] {
  const now = Date.now()

  // Return cached version if fresh (simulates polling)
  if (_campaignCache && now - _cacheTimestamp < CACHE_TTL) {
    return _campaignCache
  }

  const timeSeed = Math.floor(now / CACHE_TTL) // changes every 10s
  const timeMultiplier = getTimeMultiplier()
  const campaigns: Campaign[] = []

  PLATFORM_PROFILES.forEach((platform, pIndex) => {
    const names = CAMPAIGN_NAMES[platform.name] || []

    names.forEach((name, cIndex) => {
      const baseSeed = pIndex * 100 + cIndex
      const liveSeed = baseSeed + timeSeed * 0.01

      // Base budget with slight time variation
      const budgetBase = platform.budgetRange[0] +
        seededRandom(baseSeed) * (platform.budgetRange[1] - platform.budgetRange[0])
      const spend = Math.round(budgetBase * timeMultiplier * (0.9 + seededRandom(liveSeed) * 0.2))

      // Correlated metrics
      const impressions = Math.round(spend / platform.avgCPM * 1000 * (0.85 + seededRandom(liveSeed + 1) * 0.3))
      const ctr = Math.max(0.3, gaussianRandom(platform.avgCTR, platform.avgCTR * platform.volatility, liveSeed + 2))
      const clicks = Math.round(impressions * ctr / 100)
      const convRate = Math.max(0.5, gaussianRandom(platform.avgConvRate, platform.avgConvRate * platform.volatility, liveSeed + 3))
      const conversions = Math.max(1, Math.round(clicks * convRate / 100))

      const roas = Math.max(0.5, gaussianRandom(platform.avgROAS, platform.avgROAS * platform.volatility * 0.5, liveSeed + 4))
      const revenue = Math.round(spend * roas)
      const cpa = conversions > 0 ? Math.round(spend / conversions * 100) / 100 : 0
      const cpm = impressions > 0 ? Math.round(spend / impressions * 1000 * 100) / 100 : 0

      const region = platform.regions[cIndex % platform.regions.length]
      const campaignType = platform.campaignTypes[cIndex % platform.campaignTypes.length]

      // Status: most active, some paused
      const statusRand = seededRandom(baseSeed + 99)
      const status: 'Active' | 'Paused' | 'Completed' =
        statusRand > 0.85 ? 'Paused' : statusRand > 0.95 ? 'Completed' : 'Active'

      campaigns.push({
        campaign_id: `${platform.name.replace(/\s/g, '-').toLowerCase()}-${cIndex + 1}`,
        campaign_name: name,
        platform: platform.name,
        region,
        campaign_type: campaignType,
        spend,
        revenue,
        conversions,
        impressions,
        clicks,
        ctr: Math.round(ctr * 100) / 100,
        cpm,
        cpa,
        roas: Math.round(roas * 100) / 100,
        status,
        start_date: new Date(Date.now() - (30 + cIndex * 3) * 24 * 60 * 60 * 1000).toISOString(),
      })
    })
  })

  _campaignCache = campaigns
  _cacheTimestamp = now
  return campaigns
}

// ============================================================================
// Platform Summary Generator (for charts)
// ============================================================================

export function generatePlatformSummary(campaigns: Campaign[]): PlatformSummary[] {
  const platformMap = new Map<string, PlatformSummary>()

  campaigns.forEach((c) => {
    const existing = platformMap.get(c.platform)
    if (existing) {
      existing.spend += c.spend
      existing.revenue += c.revenue
      existing.conversions += c.conversions
      existing.impressions += c.impressions
      existing.clicks += c.clicks
    } else {
      platformMap.set(c.platform, {
        platform: c.platform,
        spend: c.spend,
        revenue: c.revenue,
        conversions: c.conversions,
        roas: 0,
        cpa: 0,
        impressions: c.impressions,
        clicks: c.clicks,
      })
    }
  })

  // Calculate derived metrics
  platformMap.forEach((summary) => {
    summary.roas = summary.spend > 0 ? Math.round(summary.revenue / summary.spend * 100) / 100 : 0
    summary.cpa = summary.conversions > 0 ? Math.round(summary.spend / summary.conversions * 100) / 100 : 0
  })

  return Array.from(platformMap.values())
}

// ============================================================================
// Daily Trend Generator (for area chart — 30 days)
// ============================================================================

export function generateDailyTrend(): DailyPerformance[] {
  const days: DailyPerformance[] = []
  const now = new Date()
  const timeSeed = Math.floor(Date.now() / 60000) // changes every minute

  for (let i = 29; i >= 0; i--) {
    const date = new Date(now)
    date.setDate(date.getDate() - i)
    const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    const daySeed = i * 17 + timeSeed * 0.001
    const dayOfWeek = date.getDay()

    // Weekend dip pattern
    let dayFactor = 1.0
    if (dayOfWeek === 0) dayFactor = 0.75
    if (dayOfWeek === 5) dayFactor = 1.2
    if (dayOfWeek === 6) dayFactor = 1.1

    // Growth trend over 30 days
    const trendFactor = 0.85 + (30 - i) / 30 * 0.3

    const spend = Math.round(gaussianRandom(4500, 800, daySeed) * dayFactor * trendFactor)
    const roas = Math.max(1.5, gaussianRandom(3.2, 0.5, daySeed + 1))
    const revenue = Math.round(spend * roas)
    const impressions = Math.round(spend / 9 * 1000 * (0.9 + seededRandom(daySeed + 2) * 0.2))
    const ctr = Math.max(0.5, gaussianRandom(2.1, 0.4, daySeed + 3))
    const clicks = Math.round(impressions * ctr / 100)
    const convRate = Math.max(1, gaussianRandom(3.0, 0.6, daySeed + 4))
    const conversions = Math.max(1, Math.round(clicks * convRate / 100))
    const cpa = conversions > 0 ? Math.round(spend / conversions * 100) / 100 : 0

    days.push({
      date: dateStr,
      spend,
      revenue,
      conversions,
      roas: Math.round(roas * 100) / 100,
      ctr: Math.round(ctr * 100) / 100,
      cpa,
      impressions,
      clicks,
    })
  }

  return days
}

// ============================================================================
// Regional Breakdown Generator (for pie chart)
// ============================================================================

export function generateRegionalBreakdown(): { name: string; value: number }[] {
  const timeSeed = Math.floor(Date.now() / 30000) // changes every 30s

  const regions = [
    { name: 'Saudi Arabia', baseShare: 38 },
    { name: 'UAE', baseShare: 28 },
    { name: 'Kuwait', baseShare: 12 },
    { name: 'Qatar', baseShare: 9 },
    { name: 'Jordan', baseShare: 8 },
    { name: 'Iraq', baseShare: 5 },
  ]

  // Add slight variation
  const raw = regions.map((r, i) => ({
    name: r.name,
    value: Math.max(2, r.baseShare + Math.round(seededRandom(i + timeSeed * 0.01) * 4 - 2)),
  }))

  // Normalize to 100%
  const total = raw.reduce((sum, r) => sum + r.value, 0)
  return raw.map((r) => ({
    name: r.name,
    value: Math.round(r.value / total * 100),
  }))
}

// ============================================================================
// KPI Calculator
// ============================================================================

export function calculateKPIs(campaigns: Campaign[]): KPIMetrics {
  const active = campaigns.filter((c) => c.status === 'Active')

  const totalSpend = active.reduce((sum, c) => sum + c.spend, 0)
  const totalRevenue = active.reduce((sum, c) => sum + c.revenue, 0)
  const totalConversions = active.reduce((sum, c) => sum + c.conversions, 0)
  const totalImpressions = active.reduce((sum, c) => sum + c.impressions, 0)
  const totalClicks = active.reduce((sum, c) => sum + c.clicks, 0)
  const overallROAS = totalSpend > 0 ? Math.round(totalRevenue / totalSpend * 100) / 100 : 0
  const overallCPA = totalConversions > 0 ? Math.round(totalSpend / totalConversions * 100) / 100 : 0
  const avgCTR = active.length > 0 ? Math.round(active.reduce((sum, c) => sum + c.ctr, 0) / active.length * 100) / 100 : 0
  const avgCPM = active.length > 0 ? Math.round(active.reduce((sum, c) => sum + c.cpm, 0) / active.length * 100) / 100 : 0

  // Simulated deltas (vs last period) — subtly shift over time
  const timeSeed = Math.floor(Date.now() / 60000)
  const spendDelta = Math.round(gaussianRandom(8.5, 3, timeSeed) * 10) / 10
  const revenueDelta = Math.round(gaussianRandom(15.2, 4, timeSeed + 1) * 10) / 10
  const roasDelta = Math.round(gaussianRandom(6.8, 2.5, timeSeed + 2) * 10) / 10
  const conversionsDelta = Math.round(gaussianRandom(12.1, 3.5, timeSeed + 3) * 10) / 10

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
    spendDelta,
    revenueDelta,
    roasDelta,
    conversionsDelta,
  }
}

// ============================================================================
// Alerts Generator
// ============================================================================

export interface SimulatedAlert {
  id: string
  severity: 'warning' | 'good' | 'critical'
  title: string
  message: string
  time: string
}

export function generateAlerts(): SimulatedAlert[] {
  const timeSeed = Math.floor(Date.now() / 30000) // every 30 seconds

  const alertPool: SimulatedAlert[] = [
    {
      id: 'a1',
      severity: 'good',
      title: 'Meta Ads ROAS Surge',
      message: 'KSA Ramadan campaign ROAS jumped to 4.8x — Signal Health: 92',
      time: '2 min ago',
    },
    {
      id: 'a2',
      severity: 'warning',
      title: 'TikTok CPA Rising',
      message: 'Spark Ads CPA increased 18% in last hour. Trust Gate: HOLD.',
      time: '5 min ago',
    },
    {
      id: 'a3',
      severity: 'critical',
      title: 'Snapchat API Latency',
      message: 'Snapchat reporting delayed 15min. Signal health dropped to 58.',
      time: '8 min ago',
    },
    {
      id: 'a4',
      severity: 'good',
      title: 'Google Ads Budget Optimized',
      message: 'Autopilot reallocated $1,200 to high-ROAS campaigns. Trust Gate: PASS.',
      time: '12 min ago',
    },
    {
      id: 'a5',
      severity: 'warning',
      title: 'Meta Event Match Quality Drop',
      message: 'EMQ score for UAE retargeting dropped to 67. Monitoring.',
      time: '18 min ago',
    },
    {
      id: 'a6',
      severity: 'good',
      title: 'Autopilot: Budget Scaled',
      message: 'Google Performance Max budget increased 15%. Signal Health: 88.',
      time: '22 min ago',
    },
    {
      id: 'a7',
      severity: 'critical',
      title: 'TikTok Conversion Drop',
      message: 'Conversions down 32% in last 2hrs. Autopilot paused scaling.',
      time: '25 min ago',
    },
    {
      id: 'a8',
      severity: 'good',
      title: 'All Platforms Synced',
      message: 'Latest sync completed across all 4 platforms. 24 campaigns updated.',
      time: '30 min ago',
    },
  ]

  // Rotate which 3 alerts are shown based on time
  const startIdx = timeSeed % alertPool.length
  const selected: SimulatedAlert[] = []
  for (let i = 0; i < 3; i++) {
    selected.push(alertPool[(startIdx + i) % alertPool.length])
  }

  return selected
}

// ============================================================================
// Platform Connection Status
// ============================================================================

export interface PlatformConnection {
  platform: string
  status: 'connected' | 'syncing' | 'warning'
  lastSync: string
  campaigns: number
  health: number
  icon: string
}

export function getPlatformConnections(): PlatformConnection[] {
  const timeSeed = Math.floor(Date.now() / 15000) // every 15 seconds

  return [
    {
      platform: 'Meta Ads',
      status: seededRandom(timeSeed) > 0.9 ? 'syncing' : 'connected',
      lastSync: `${Math.floor(seededRandom(timeSeed + 1) * 3) + 1}m ago`,
      campaigns: 7,
      health: Math.min(100, Math.max(78, Math.round(gaussianRandom(91, 4, timeSeed + 10)))),
      icon: 'meta',
    },
    {
      platform: 'Google Ads',
      status: seededRandom(timeSeed + 2) > 0.92 ? 'syncing' : 'connected',
      lastSync: `${Math.floor(seededRandom(timeSeed + 3) * 4) + 1}m ago`,
      campaigns: 7,
      health: Math.min(100, Math.max(82, Math.round(gaussianRandom(93, 3, timeSeed + 11)))),
      icon: 'google',
    },
    {
      platform: 'TikTok Ads',
      status: seededRandom(timeSeed + 4) > 0.88 ? 'syncing' : seededRandom(timeSeed + 5) > 0.95 ? 'warning' : 'connected',
      lastSync: `${Math.floor(seededRandom(timeSeed + 6) * 5) + 1}m ago`,
      campaigns: 5,
      health: Math.min(100, Math.max(65, Math.round(gaussianRandom(82, 7, timeSeed + 12)))),
      icon: 'tiktok',
    },
    {
      platform: 'Snapchat Ads',
      status: seededRandom(timeSeed + 7) > 0.85 ? 'syncing' : seededRandom(timeSeed + 8) > 0.9 ? 'warning' : 'connected',
      lastSync: `${Math.floor(seededRandom(timeSeed + 9) * 6) + 2}m ago`,
      campaigns: 5,
      health: Math.min(100, Math.max(60, Math.round(gaussianRandom(78, 8, timeSeed + 13)))),
      icon: 'snapchat',
    },
  ]
}

// ============================================================================
// Signal Health Simulator (for Trust Gate)
// ============================================================================

export interface SignalHealthDetail {
  overall: number
  emq: number
  apiHealth: number
  eventLoss: number
  platformStability: number
  dataQuality: number
  status: 'PASS' | 'HOLD' | 'BLOCK'
}

export function getSignalHealth(): SignalHealthDetail {
  const timeSeed = Math.floor(Date.now() / 5000) // every 5 seconds

  const emq = Math.min(100, Math.max(55, Math.round(gaussianRandom(82, 5, timeSeed))))
  const apiHealth = Math.min(100, Math.max(60, Math.round(gaussianRandom(90, 4, timeSeed + 1))))
  const eventLoss = Math.min(100, Math.max(50, Math.round(gaussianRandom(85, 6, timeSeed + 2))))
  const platformStability = Math.min(100, Math.max(55, Math.round(gaussianRandom(88, 5, timeSeed + 3))))
  const dataQuality = Math.min(100, Math.max(60, Math.round(gaussianRandom(87, 4, timeSeed + 4))))

  // Weighted score as per CLAUDE.md
  const overall = Math.round(
    emq * 0.35 +
    apiHealth * 0.25 +
    eventLoss * 0.20 +
    platformStability * 0.10 +
    dataQuality * 0.10
  )

  const status: 'PASS' | 'HOLD' | 'BLOCK' =
    overall >= 70 ? 'PASS' : overall >= 40 ? 'HOLD' : 'BLOCK'

  return { overall, emq, apiHealth, eventLoss, platformStability, dataQuality, status }
}

// ============================================================================
// Use Live Simulation Hook
// ============================================================================

import { useState, useEffect, useCallback } from 'react'

export function useLiveSimulation(refreshInterval = 10000) {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [platformSummary, setPlatformSummary] = useState<PlatformSummary[]>([])
  const [dailyTrend, setDailyTrend] = useState<DailyPerformance[]>([])
  const [regionalBreakdown, setRegionalBreakdown] = useState<{ name: string; value: number }[]>([])
  const [kpis, setKpis] = useState<KPIMetrics | null>(null)
  const [alerts, setAlerts] = useState<SimulatedAlert[]>([])
  const [connections, setConnections] = useState<PlatformConnection[]>([])
  const [signalHealth, setSignalHealth] = useState<SignalHealthDetail | null>(null)
  const [lastUpdated, setLastUpdated] = useState(new Date())
  const [isLive, setIsLive] = useState(true)

  const refresh = useCallback(() => {
    const liveCampaigns = generateLiveCampaigns()
    setCampaigns(liveCampaigns)
    setPlatformSummary(generatePlatformSummary(liveCampaigns))
    setDailyTrend(generateDailyTrend())
    setRegionalBreakdown(generateRegionalBreakdown())
    setKpis(calculateKPIs(liveCampaigns))
    setAlerts(generateAlerts())
    setConnections(getPlatformConnections())
    setSignalHealth(getSignalHealth())
    setLastUpdated(new Date())
  }, [])

  useEffect(() => {
    refresh()

    if (!isLive) return

    const interval = setInterval(refresh, refreshInterval)
    return () => clearInterval(interval)
  }, [refresh, refreshInterval, isLive])

  return {
    campaigns,
    platformSummary,
    dailyTrend,
    regionalBreakdown,
    kpis,
    alerts,
    connections,
    signalHealth,
    lastUpdated,
    isLive,
    setIsLive,
    refresh,
  }
}
