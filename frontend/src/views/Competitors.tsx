/**
 * Competitor Intelligence Page
 *
 * Track competitors, share of voice, keyword overlap, and market trends
 * Integrates with Meta Ads Library and Google Ads Transparency Center
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { useCompetitors, useShareOfVoice, useCreateCompetitor, useDeleteCompetitor } from '@/api/hooks'
import apiClient from '@/api/client'
import {
  MagnifyingGlassIcon,
  PlusIcon,
  EyeIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  GlobeAltIcon,
  ChartBarIcon,
  ArrowPathIcon,
  EllipsisHorizontalIcon,
  XMarkIcon,
  CheckIcon,
  TrashIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline'

interface Competitor {
  id: string
  name: string
  domain: string
  logo: string | null
  adSpend: number
  adSpendTrend: number
  shareOfVoice: number
  keywordOverlap: number
  creativesTracked: number
  lastRefresh: Date
  status: 'active' | 'paused'
  country?: string
  platforms?: string[]
}

interface KeywordOverlap {
  keyword: string
  yourPosition: number
  competitorPosition: number
  searchVolume: number
  cpc: number
  competitor: string
}

// Countries for Meta Ads Library and Google Transparency
const COUNTRIES = [
  { code: 'SA', name: 'Saudi Arabia', flag: '🇸🇦' },
  { code: 'AE', name: 'United Arab Emirates', flag: '🇦🇪' },
  { code: 'EG', name: 'Egypt', flag: '🇪🇬' },
  { code: 'KW', name: 'Kuwait', flag: '🇰🇼' },
  { code: 'QA', name: 'Qatar', flag: '🇶🇦' },
  { code: 'BH', name: 'Bahrain', flag: '🇧🇭' },
  { code: 'OM', name: 'Oman', flag: '🇴🇲' },
  { code: 'JO', name: 'Jordan', flag: '🇯🇴' },
  { code: 'LB', name: 'Lebanon', flag: '🇱🇧' },
  { code: 'US', name: 'United States', flag: '🇺🇸' },
  { code: 'GB', name: 'United Kingdom', flag: '🇬🇧' },
  { code: 'DE', name: 'Germany', flag: '🇩🇪' },
  { code: 'FR', name: 'France', flag: '🇫🇷' },
  { code: 'IN', name: 'India', flag: '🇮🇳' },
  { code: 'PK', name: 'Pakistan', flag: '🇵🇰' },
  { code: 'TR', name: 'Turkey', flag: '🇹🇷' },
]

const PLATFORMS = [
  { id: 'meta', name: 'Meta (Facebook/Instagram)', icon: 'M' },
  { id: 'google', name: 'Google Ads', icon: 'G' },
  { id: 'tiktok', name: 'TikTok', icon: 'T' },
  { id: 'snapchat', name: 'Snapchat', icon: 'S' },
  { id: 'linkedin', name: 'LinkedIn', icon: 'L' },
]

export function Competitors() {
  const { t: _t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCompetitor, setSelectedCompetitor] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form state for new competitor
  const [newCompetitor, setNewCompetitor] = useState({
    name: '',
    domain: '',
    country: 'SA',
    platforms: ['meta', 'google'] as string[],
  })

  const { data: competitorsData, isLoading: isLoadingCompetitors, refetch: refetchCompetitors } = useCompetitors()
  // Get last 30 days for share of voice
  const endDate = new Date().toISOString().split('T')[0]
  const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  const { data: sovData } = useShareOfVoice(startDate, endDate)
  const createCompetitor = useCreateCompetitor()
  const deleteCompetitor = useDeleteCompetitor()

  // Generate Meta Ads Library URL - search by name (brand name works better)
  const getMetaAdsLibraryUrl = (name: string, country: string) => {
    return `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=${country}&q=${encodeURIComponent(name)}&search_type=keyword_unordered`
  }

  // Generate Google Ads Transparency URL - search by name
  const getGoogleTransparencyUrl = (name: string) => {
    return `https://adstransparency.google.com/?query=${encodeURIComponent(name)}`
  }

  // Handle form submission
  const handleAddCompetitor = async () => {
    if (!newCompetitor.name || !newCompetitor.domain) return

    setIsSubmitting(true)
    try {
      await createCompetitor.mutateAsync({
        name: newCompetitor.name,
        domain: newCompetitor.domain,
        country: newCompetitor.country,
        platforms: newCompetitor.platforms,
      })
      setIsModalOpen(false)
      setNewCompetitor({ name: '', domain: '', country: 'SA', platforms: ['meta', 'google'] })
      refetchCompetitors()
    } catch (error) {
      console.error('Failed to add competitor:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle delete competitor
  const handleDeleteCompetitor = async (id: string) => {
    if (!confirm('Are you sure you want to delete this competitor?')) return
    try {
      await deleteCompetitor.mutateAsync(id)
      refetchCompetitors()
    } catch (error) {
      console.error('Failed to delete competitor:', error)
    }
  }

  // Toggle platform selection
  const togglePlatform = (platformId: string) => {
    setNewCompetitor(prev => ({
      ...prev,
      platforms: prev.platforms.includes(platformId)
        ? prev.platforms.filter(p => p !== platformId)
        : [...prev.platforms, platformId]
    }))
  }

  // Map API competitors to view model
  const competitors: Competitor[] = (competitorsData?.items || competitorsData || []).map((c: any) => ({
    id: c.id,
    name: c.name,
    domain: c.domain,
    logo: null,
    adSpend: c.estimatedSpend ?? 0,
    adSpendTrend: c.spendTrend ?? 0,
    shareOfVoice: c.shareOfVoice ?? 0,
    keywordOverlap: c.keywordOverlap ?? 0,
    creativesTracked: c.activeCreatives ?? 0,
    lastRefresh: new Date(c.lastUpdated ?? c.lastRefreshedAt ?? Date.now()),
    status: c.isActive !== false ? 'active' : 'paused',
    country: c.country,
    platforms: c.platforms,
  }))

  // Keyword overlaps — fetched from API
  const [keywordOverlaps, setKeywordOverlaps] = useState<KeywordOverlap[]>([])
  const [isLoadingKeywords, setIsLoadingKeywords] = useState(false)

  // Fetch keyword overlaps when competitors change
  useEffect(() => {
    if (competitors.length === 0) {
      setKeywordOverlaps([])
      return
    }
    setIsLoadingKeywords(true)
    apiClient.get('/competitors/keywords/overlap')
      .then((res) => {
        const data = res.data?.data || res.data || []
        if (Array.isArray(data)) {
          setKeywordOverlaps(data.map((kw: any) => ({
            keyword: kw.keyword,
            yourPosition: kw.yourPosition ?? kw.your_position ?? 0,
            competitorPosition: kw.competitorPosition ?? kw.competitor_position ?? 0,
            searchVolume: kw.searchVolume ?? kw.search_volume ?? 0,
            cpc: kw.cpc ?? 0,
            competitor: kw.competitor ?? kw.competitorName ?? kw.competitor_name ?? '',
          })))
        }
      })
      .catch(() => {
        setKeywordOverlaps([])
      })
      .finally(() => setIsLoadingKeywords(false))
  }, [competitors.length])

  // Share of Voice data — from API or empty defaults
  const shareOfVoice = sovData ?? {
    you: 0,
    competitors: competitors.map((c) => ({ name: c.name, share: c.shareOfVoice })),
  }

  const filteredCompetitors = competitors.filter((c) =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.domain.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`
    return `$${value}`
  }

  const formatLastRefresh = (date: Date) => {
    const hours = Math.floor((Date.now() - date.getTime()) / (60 * 60 * 1000))
    if (hours < 1) return 'Just now'
    if (hours < 24) return `${hours}h ago`
    return `${Math.floor(hours / 24)}d ago`
  }

  // Stats
  const stats = {
    totalCompetitors: competitors.length,
    activeTracking: competitors.filter((c) => c.status === 'active').length,
    avgKeywordOverlap: Math.round(competitors.reduce((sum, c) => sum + c.keywordOverlap, 0) / competitors.length),
    totalCreatives: competitors.reduce((sum, c) => sum + c.creativesTracked, 0),
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Competitor Intelligence</h1>
          <p className="text-muted-foreground">Track competitor activity and market share</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <PlusIcon className="w-4 h-4" />
          Add Competitor
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground mb-1">Tracked Competitors</div>
          <div className="text-2xl font-bold">{stats.totalCompetitors}</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground mb-1">Active Tracking</div>
          <div className="text-2xl font-bold text-green-500">{stats.activeTracking}</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground mb-1">Avg Keyword Overlap</div>
          <div className="text-2xl font-bold">{stats.avgKeywordOverlap}%</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground mb-1">Creatives Tracked</div>
          <div className="text-2xl font-bold">{stats.totalCreatives}</div>
        </div>
      </div>

      {/* Share of Voice */}
      <div className="rounded-xl border bg-card p-6">
        <div className="flex items-center gap-3 mb-4">
          <ChartBarIcon className="w-5 h-5 text-primary" />
          <h2 className="font-semibold">Share of Voice</h2>
        </div>
        <div className="flex items-center gap-2 mb-4">
          <div className="flex-1 h-8 rounded-full overflow-hidden flex bg-muted">
            <div
              className="h-full bg-primary"
              style={{ width: `${shareOfVoice.you}%` }}
              title={`You: ${shareOfVoice.you}%`}
            />
            {shareOfVoice.competitors.map((c, i) => (
              <div
                key={c.name}
                className="h-full"
                style={{
                  width: `${c.share}%`,
                  backgroundColor: ['#ef4444', '#f59e0b', '#10b981', '#6366f1'][i % 4],
                }}
                title={`${c.name}: ${c.share}%`}
              />
            ))}
          </div>
        </div>
        <div className="flex flex-wrap gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-primary" />
            <span>You ({shareOfVoice.you}%)</span>
          </div>
          {shareOfVoice.competitors.map((c, i) => (
            <div key={c.name} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: ['#ef4444', '#f59e0b', '#10b981', '#6366f1'][i % 4] }}
              />
              <span>{c.name} ({c.share}%)</span>
            </div>
          ))}
        </div>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search competitors..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {/* Loading State */}
      {isLoadingCompetitors && (
        <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
          <ArrowPathIcon className="w-5 h-5 animate-spin" />
          Loading competitors...
        </div>
      )}

      {/* Empty State */}
      {!isLoadingCompetitors && competitors.length === 0 && (
        <div className="text-center py-12 rounded-xl border bg-card">
          <EyeIcon className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No competitors tracked yet</h3>
          <p className="text-muted-foreground mb-4 max-w-md mx-auto">
            Start tracking your competitors to monitor their ad spend, keyword overlap, and share of voice.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <PlusIcon className="w-4 h-4" />
            Add Your First Competitor
          </button>
        </div>
      )}

      {/* Competitors Grid */}
      {!isLoadingCompetitors && competitors.length > 0 && (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredCompetitors.map((competitor) => (
          <div
            key={competitor.id}
            className={cn(
              'p-4 rounded-xl border bg-card hover:shadow-md transition-all cursor-pointer',
              selectedCompetitor === competitor.id && 'ring-2 ring-primary'
            )}
            onClick={() => setSelectedCompetitor(
              selectedCompetitor === competitor.id ? null : competitor.id
            )}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                  <GlobeAltIcon className="w-5 h-5 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="font-semibold">{competitor.name}</h3>
                  <p className="text-sm text-muted-foreground">{competitor.domain}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn(
                  'px-2 py-1 rounded-full text-xs',
                  competitor.status === 'active'
                    ? 'bg-green-500/10 text-green-500'
                    : 'bg-muted text-muted-foreground'
                )}>
                  {competitor.status}
                </span>
                <button className="p-1 rounded hover:bg-muted transition-colors">
                  <EllipsisHorizontalIcon className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <div className="text-sm text-muted-foreground">Est. Ad Spend</div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{formatCurrency(competitor.adSpend)}/mo</span>
                  <span className={cn(
                    'flex items-center text-xs',
                    competitor.adSpendTrend >= 0 ? 'text-green-500' : 'text-red-500'
                  )}>
                    {competitor.adSpendTrend >= 0 ? (
                      <ArrowTrendingUpIcon className="w-3 h-3" />
                    ) : (
                      <ArrowTrendingDownIcon className="w-3 h-3" />
                    )}
                    {Math.abs(competitor.adSpendTrend)}%
                  </span>
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Share of Voice</div>
                <div className="font-semibold">{competitor.shareOfVoice}%</div>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-4">
                <span className="text-muted-foreground">
                  {competitor.keywordOverlap}% keyword overlap
                </span>
                <span className="text-muted-foreground">
                  {competitor.creativesTracked} creatives
                </span>
              </div>
              <span className="text-muted-foreground">
                Updated {formatLastRefresh(competitor.lastRefresh)}
              </span>
            </div>

            {/* Quick Links to Ad Libraries */}
            {/* Quick Links - Search by competitor name */}
            <div className="flex items-center gap-2 mt-3 pt-3 border-t">
              <a
                href={getMetaAdsLibraryUrl(competitor.name, competitor.country || 'SA')}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-blue-500/10 text-blue-600 hover:bg-blue-500/20 transition-colors"
                title={`Search "${competitor.name}" in Meta Ads Library`}
              >
                <span className="font-bold">M</span>
                Meta Ads Library
                <ArrowTopRightOnSquareIcon className="w-3 h-3" />
              </a>
              <a
                href={getGoogleTransparencyUrl(competitor.name)}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-green-500/10 text-green-600 hover:bg-green-500/20 transition-colors"
                title={`Search "${competitor.name}" in Google Transparency`}
              >
                <span className="font-bold">G</span>
                Google Transparency
                <ArrowTopRightOnSquareIcon className="w-3 h-3" />
              </a>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteCompetitor(competitor.id)
                }}
                className="ml-auto p-1.5 rounded-md text-red-500 hover:bg-red-500/10 transition-colors"
                title="Delete competitor"
              >
                <TrashIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
      )}

      {/* Keyword Overlap Table */}
      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <div>
            <h2 className="font-semibold">Keyword Overlap</h2>
            <p className="text-xs text-muted-foreground mt-1">
              Keywords where you and your competitors both appear in search results.
              Lower position numbers mean higher ranking. Use this to identify opportunities
              where you can outbid or outrank competitors on high-value keywords.
            </p>
          </div>
          <button
            onClick={() => {
              setIsLoadingKeywords(true)
              apiClient.get('/competitors/keywords/overlap')
                .then((res) => {
                  const data = res.data?.data || res.data || []
                  if (Array.isArray(data)) {
                    setKeywordOverlaps(data.map((kw: any) => ({
                      keyword: kw.keyword,
                      yourPosition: kw.yourPosition ?? kw.your_position ?? 0,
                      competitorPosition: kw.competitorPosition ?? kw.competitor_position ?? 0,
                      searchVolume: kw.searchVolume ?? kw.search_volume ?? 0,
                      cpc: kw.cpc ?? 0,
                      competitor: kw.competitor ?? kw.competitorName ?? kw.competitor_name ?? '',
                    })))
                  }
                })
                .catch(() => setKeywordOverlaps([]))
                .finally(() => setIsLoadingKeywords(false))
            }}
            disabled={isLoadingKeywords}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border hover:bg-muted transition-colors disabled:opacity-50 flex-shrink-0"
          >
            <ArrowPathIcon className={cn('w-4 h-4', isLoadingKeywords && 'animate-spin')} />
            Refresh
          </button>
        </div>

        {isLoadingKeywords ? (
          <div className="flex items-center justify-center gap-2 py-8 text-muted-foreground">
            <ArrowPathIcon className="w-4 h-4 animate-spin" />
            Loading keyword data...
          </div>
        ) : keywordOverlaps.length > 0 ? (
          <table className="w-full">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="p-4 text-left text-sm font-medium">Keyword</th>
                <th className="p-4 text-center text-sm font-medium">Your Position</th>
                <th className="p-4 text-center text-sm font-medium">Competitor</th>
                <th className="p-4 text-center text-sm font-medium">Their Position</th>
                <th className="p-4 text-right text-sm font-medium">Search Volume</th>
                <th className="p-4 text-right text-sm font-medium">CPC</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {keywordOverlaps.map((kw, i) => (
                <tr key={i} className="hover:bg-muted/30 transition-colors">
                  <td className="p-4 font-medium">{kw.keyword}</td>
                  <td className="p-4 text-center">
                    <span className={cn(
                      'px-2 py-1 rounded text-sm font-medium',
                      kw.yourPosition <= 3 ? 'bg-green-500/10 text-green-500' :
                      kw.yourPosition <= 5 ? 'bg-amber-500/10 text-amber-500' :
                      'bg-muted text-muted-foreground'
                    )}>
                      #{kw.yourPosition}
                    </span>
                  </td>
                  <td className="p-4 text-center text-sm text-muted-foreground">
                    {kw.competitor}
                  </td>
                  <td className="p-4 text-center">
                    <span className={cn(
                      'px-2 py-1 rounded text-sm font-medium',
                      kw.competitorPosition <= 3 ? 'bg-red-500/10 text-red-500' :
                      kw.competitorPosition <= 5 ? 'bg-amber-500/10 text-amber-500' :
                      'bg-muted text-muted-foreground'
                    )}>
                      #{kw.competitorPosition}
                    </span>
                  </td>
                  <td className="p-4 text-right text-muted-foreground">
                    {kw.searchVolume.toLocaleString()}
                  </td>
                  <td className="p-4 text-right font-medium">${kw.cpc.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center py-8">
            <MagnifyingGlassIcon className="w-10 h-10 mx-auto text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground mb-1">No keyword overlap data available</p>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Add competitors and connect your ad platforms to see which keywords you both target.
              This helps you identify opportunities to outrank competitors on high-value searches.
            </p>
          </div>
        )}
      </div>

      {/* No search results */}
      {!isLoadingCompetitors && competitors.length > 0 && filteredCompetitors.length === 0 && (
        <div className="text-center py-12">
          <MagnifyingGlassIcon className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No competitors match your search</p>
        </div>
      )}

      {/* Add Competitor Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setIsModalOpen(false)}
          />

          {/* Modal */}
          <div className="relative w-full max-w-lg mx-4 bg-card rounded-2xl shadow-2xl border overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b">
              <div>
                <h2 className="text-xl font-semibold">Add Competitor</h2>
                <p className="text-sm text-muted-foreground">
                  Track competitor ads via Meta Ads Library & Google Transparency
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            {/* Form */}
            <div className="p-6 space-y-5">
              {/* Competitor Name */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Competitor Name *
                </label>
                <input
                  type="text"
                  value={newCompetitor.name}
                  onChange={(e) => setNewCompetitor(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., Competitor Inc"
                  className="w-full px-4 py-2.5 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>

              {/* Domain/Website */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Website / Domain *
                </label>
                <input
                  type="text"
                  value={newCompetitor.domain}
                  onChange={(e) => setNewCompetitor(prev => ({ ...prev, domain: e.target.value }))}
                  placeholder="e.g., competitor.com"
                  className="w-full px-4 py-2.5 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Used to search ads in Meta Ads Library and Google Transparency
                </p>
              </div>

              {/* Country Selection */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Competitor's Country *
                </label>
                <select
                  value={newCompetitor.country}
                  onChange={(e) => setNewCompetitor(prev => ({ ...prev, country: e.target.value }))}
                  className="w-full px-4 py-2.5 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  {COUNTRIES.map((country) => (
                    <option key={country.code} value={country.code}>
                      {country.flag} {country.name}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  Select the country where competitor runs ads (for Meta Ads Library filter)
                </p>
              </div>

              {/* Platform Selection */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Platforms to Track
                </label>
                <div className="flex flex-wrap gap-2">
                  {PLATFORMS.map((platform) => (
                    <button
                      key={platform.id}
                      type="button"
                      onClick={() => togglePlatform(platform.id)}
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all',
                        newCompetitor.platforms.includes(platform.id)
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border hover:border-primary/50'
                      )}
                    >
                      <span className="w-5 h-5 rounded bg-muted flex items-center justify-center text-xs font-bold">
                        {platform.icon}
                      </span>
                      <span className="text-sm">{platform.name}</span>
                      {newCompetitor.platforms.includes(platform.id) && (
                        <CheckIcon className="w-4 h-4" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Quick Links Preview - shows when name is entered */}
              {newCompetitor.name && (
                <div className="p-4 rounded-lg bg-muted/50 space-y-3">
                  <p className="text-sm font-medium">Preview Ad Library Links for "{newCompetitor.name}":</p>
                  <div className="space-y-2">
                    <a
                      href={getMetaAdsLibraryUrl(newCompetitor.name, newCompetitor.country)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-primary hover:underline"
                    >
                      <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                      Search "{newCompetitor.name}" in Meta Ads Library ({COUNTRIES.find(c => c.code === newCompetitor.country)?.name})
                    </a>
                    <a
                      href={getGoogleTransparencyUrl(newCompetitor.name)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-sm text-primary hover:underline"
                    >
                      <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                      Search "{newCompetitor.name}" in Google Ads Transparency
                    </a>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-6 border-t bg-muted/30">
              <button
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddCompetitor}
                disabled={!newCompetitor.name || !newCompetitor.domain || isSubmitting}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting ? (
                  <>
                    <ArrowPathIcon className="w-4 h-4 animate-spin" />
                    Adding...
                  </>
                ) : (
                  <>
                    <PlusIcon className="w-4 h-4" />
                    Add Competitor
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Competitors
