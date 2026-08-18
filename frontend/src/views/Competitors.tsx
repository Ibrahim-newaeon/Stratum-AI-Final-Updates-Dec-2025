/**
 * Competitor Intelligence Page
 *
 * Shows what the scanner can actually source about a competitor: their site
 * metadata and social links, and their Meta Ad Library activity.
 *
 * Estimated ad spend, share of voice and keyword overlap are NOT shown. They
 * need a paid ad-intelligence provider that is not wired, so the API does not
 * serve them. This page used to render all three from `?? 0` fallbacks over
 * camelCase keys the API has never sent — every card read "$0/mo, 0% share of
 * voice, 0% keyword overlap" and presented it as measurement. Add the panels
 * back in the same change that wires a provider.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { useCompetitors, useCreateCompetitor, useDeleteCompetitor } from '@/api/hooks'
import type { Competitor as ApiCompetitor } from '@/api/competitors'
import {
  MagnifyingGlassIcon,
  PlusIcon,
  EyeIcon,
  GlobeAltIcon,
  ArrowPathIcon,
  EllipsisHorizontalIcon,
  XMarkIcon,
  CheckIcon,
  TrashIcon,
  ArrowTopRightOnSquareIcon,
} from '@heroicons/react/24/outline'

interface Competitor {
  id: number
  name: string
  domain: string
  /** null = the Ad Library lookup could not run. Not the same as zero ads. */
  activeAds: number | null
  platforms: string[]
  lastScanned: Date | null
  source: ApiCompetitor['data_source']
  fetchError: string | null
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
]

export function Competitors() {
  const { t: _t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCompetitor, setSelectedCompetitor] = useState<number | null>(null)
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
      // no-op
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle delete competitor
  const handleDeleteCompetitor = async (id: number) => {
    if (!confirm('Are you sure you want to delete this competitor?')) return
    try {
      await deleteCompetitor.mutateAsync(id)
      refetchCompetitors()
    } catch (error) {
      // no-op
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

  // Map API competitors to view model.
  //
  // Reads snake_case because that is what the API returns. The previous
  // version read `c.estimatedSpend`, `c.shareOfVoice`, `c.activeCreatives` and
  // `c.lastUpdated` — camelCase keys the backend has never sent — so every
  // Number(... ?? 0) produced 0 and every card showed a confident zero.
  const rawCompetitors: ApiCompetitor[] = Array.isArray(competitorsData)
    ? competitorsData
    : (competitorsData as unknown as { items?: ApiCompetitor[] })?.items ?? []

  const competitors: Competitor[] = rawCompetitors.map((c) => ({
    id: c.id,
    name: c.name || c.domain,
    domain: c.domain,
    // Preserved as null when the Ad Library could not answer. Rendering this
    // as 0 would claim the competitor runs no ads.
    activeAds: c.ad_creatives_count,
    platforms: c.detected_ad_platforms ?? [],
    lastScanned: c.last_fetched_at ? new Date(c.last_fetched_at) : null,
    source: c.data_source,
    fetchError: c.fetch_error,
  }))

  const filteredCompetitors = competitors.filter((c) =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.domain.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const formatLastRefresh = (date: Date | null) => {
    if (!date) return 'Never'
    const hours = Math.floor((Date.now() - date.getTime()) / (60 * 60 * 1000))
    if (hours < 1) return 'Just now'
    if (hours < 24) return `${hours}h ago`
    return `${Math.floor(hours / 24)}d ago`
  }

  // Stats — counts of things we observed, not estimates of things we did not.
  // avgKeywordOverlap used to divide by competitors.length, so an empty list
  // rendered NaN%.
  const withKnownAdCount = competitors.filter((c) => c.activeAds !== null)
  const stats = {
    totalCompetitors: competitors.length,
    scanned: competitors.filter((c) => c.source !== 'unavailable').length,
    runningAds: withKnownAdCount.filter((c) => (c.activeAds ?? 0) > 0).length,
    totalActiveAds: withKnownAdCount.reduce((sum, c) => sum + (c.activeAds ?? 0), 0),
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

      {/* Stats — observed counts only. "Avg Keyword Overlap" and "Creatives
          Tracked" used to sit here reading columns nothing writes; the first
          also divided by competitors.length, rendering NaN% on an empty list. */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground mb-1">Tracked Competitors</div>
          <div className="text-2xl font-bold">{stats.totalCompetitors}</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground mb-1">Successfully Scanned</div>
          <div className="text-2xl font-bold">{stats.scanned}</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground mb-1">Running Ads</div>
          <div className="text-2xl font-bold text-green-500">{stats.runningAds}</div>
        </div>
        <div className="p-4 rounded-xl border bg-card">
          <div className="text-sm text-muted-foreground mb-1">Active Ads Seen</div>
          <div className="text-2xl font-bold">{stats.totalActiveAds}</div>
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
              'p-4 rounded-xl border bg-card hover:shadow-md transition-colors cursor-pointer',
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
                  competitor.activeAds === null
                    ? 'bg-muted text-muted-foreground'
                    : competitor.activeAds > 0
                      ? 'bg-green-500/10 text-green-500'
                      : 'bg-muted text-muted-foreground'
                )}>
                  {competitor.activeAds === null
                    ? 'Ad activity unknown'
                    : competitor.activeAds > 0
                      ? 'Active on Meta'
                      : 'No ads detected'}
                </span>
                <button aria-label="More options" className="p-1 rounded hover:bg-muted transition-colors">
                  <EllipsisHorizontalIcon className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <div className="text-sm text-muted-foreground">Active ads</div>
                <div className="font-semibold">
                  {competitor.activeAds === null ? (
                    <span className="text-muted-foreground">Unknown</span>
                  ) : (
                    competitor.activeAds
                  )}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Platforms</div>
                <div className="font-semibold">
                  {competitor.platforms.length > 0 ? (
                    competitor.platforms.join(', ')
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                {competitor.source === 'meta_ad_library'
                  ? 'Meta Ad Library'
                  : competitor.source === 'website_scrape'
                    ? 'Website scrape'
                    : 'Not reachable'}
              </span>
              <span className="text-muted-foreground">
                Scanned {formatLastRefresh(competitor.lastScanned)}
              </span>
            </div>

            {competitor.fetchError && (
              <p className="mt-2 text-xs text-amber-600">{competitor.fetchError}</p>
            )}

            {/* Quick Links to Ad Libraries */}
            {/* Quick Links - Search by competitor name */}
            <div className="flex items-center gap-2 mt-3 pt-3 border-t">
              <a
                href={getMetaAdsLibraryUrl(competitor.name, 'SA')}
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
                        'flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors',
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
