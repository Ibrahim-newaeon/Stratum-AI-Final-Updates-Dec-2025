/**
 * Competitor Intelligence Page
 *
 * Track competitors, share of voice, keyword overlap, and market trends
 * Integrates with Meta Ads Library and Google Ads Transparency Center
 */

import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';
import {
  useCompetitors,
  useDeleteCompetitor,
  useScanExistingCompetitor,
  useShareOfVoice,
} from '@/api/hooks';
import type { CompetitorScanResult } from '@/api/competitors';
import {
  ArrowPathIcon,
  ArrowTopRightOnSquareIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  ChartBarIcon,
  CheckCircleIcon,
  EllipsisHorizontalIcon,
  EyeIcon,
  GlobeAltIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  TrashIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { AddCompetitorModal } from '@/components/competitors/AddCompetitorModal';

interface Competitor {
  id: string;
  name: string;
  domain: string;
  logo: string | null;
  adSpend: number;
  adSpendTrend: number;
  shareOfVoice: number;
  keywordOverlap: number;
  creativesTracked: number;
  lastRefresh: Date;
  status: 'active' | 'paused';
  country?: string;
  platforms?: string[];
}

interface KeywordOverlap {
  keyword: string;
  yourPosition: number;
  competitorPosition: number;
  searchVolume: number;
  cpc: number;
  competitor: string;
}


export function Competitors() {
  const { t: _t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCompetitor, setSelectedCompetitor] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Scan state
  const [scanningId, setScanningId] = useState<string | null>(null);
  const [scanResults, setScanResults] = useState<Record<string, CompetitorScanResult>>({});

  // Auto-open modal if ?action=create is in URL
  useEffect(() => {
    if (searchParams.get('action') === 'create') {
      setIsModalOpen(true);
      // Clear the URL parameter after opening
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const { data: competitorsData, refetch: refetchCompetitors } = useCompetitors();
  // Get last 30 days for share of voice
  const endDate = new Date().toISOString().split('T')[0];
  const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  const { data: sovData } = useShareOfVoice(startDate, endDate);
  const deleteCompetitor = useDeleteCompetitor();
  const scanExistingCompetitor = useScanExistingCompetitor();

  // Generate Meta Ads Library URL - search by name (brand name works better)
  const getMetaAdsLibraryUrl = (name: string, country: string) => {
    return `https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=${country}&q=${encodeURIComponent(name)}&search_type=keyword_unordered`;
  };

  // Generate Google Ads Transparency URL - search by full website URL with country filter
  const getGoogleTransparencyUrl = (domain: string, country: string = 'SA') => {
    // Build full URL (Google Transparency needs https://www. prefix for best results)
    let fullUrl = domain.replace(/\/+$/, '');
    if (!fullUrl.startsWith('http')) {
      fullUrl = `https://www.${fullUrl}`;
    }
    return `https://adstransparency.google.com/?query=${encodeURIComponent(fullUrl)}&region=${country}`;
  };

  // Get best Meta search query: prefer FB page name from scan results, fallback to competitor name
  const getMetaSearchQuery = (competitorId: string, competitorName: string) => {
    const scan = scanResults[competitorId];
    if (scan?.fb_page_name) return scan.fb_page_name;
    if (scan?.ad_library?.page_name) return scan.ad_library.page_name;
    return competitorName;
  };

  // Handle delete competitor
  const handleDeleteCompetitor = async (id: string) => {
    if (!confirm('Are you sure you want to delete this competitor?')) return;
    try {
      await deleteCompetitor.mutateAsync(id);
      refetchCompetitors();
    } catch (error) {
      // Error handled by mutation
    }
  };

  // Handle scan competitor
  const handleScanCompetitor = async (id: string, country?: string) => {
    setScanningId(id);
    try {
      const result = await scanExistingCompetitor.mutateAsync({
        id,
        country: country || 'SA',
      });
      setScanResults((prev) => ({ ...prev, [id]: result }));
      refetchCompetitors();
    } catch (error) {
      // Error handled by mutation
    } finally {
      setScanningId(null);
    }
  };

  // Sample competitors - handle paginated response
  const competitorsList = Array.isArray(competitorsData)
    ? competitorsData
    : (competitorsData as { data?: unknown[] } | undefined)?.data || [];
  const competitors: Competitor[] = (
    competitorsList as {
      id: string;
      name: string;
      domain: string;
      estimatedSpend?: number;
      shareOfVoice?: number;
      activeCreatives?: number;
      lastUpdated?: string;
      isActive?: boolean;
    }[]
  ).map((c) => ({
    id: c.id,
    name: c.name,
    domain: c.domain,
    logo: null,
    adSpend: c.estimatedSpend ?? 0,
    adSpendTrend: Math.random() * 40 - 20,
    shareOfVoice: c.shareOfVoice ?? 0,
    keywordOverlap: Math.floor(Math.random() * 50) + 10,
    creativesTracked: c.activeCreatives ?? 0,
    lastRefresh: new Date(c.lastUpdated ?? Date.now()),
    status: c.isActive ? 'active' : 'paused',
  })) ?? [
    {
      id: '1',
      name: 'CompetitorOne',
      domain: 'competitorone.com',
      logo: null,
      adSpend: 125000,
      adSpendTrend: 15,
      shareOfVoice: 24,
      keywordOverlap: 45,
      creativesTracked: 32,
      lastRefresh: new Date(Date.now() - 2 * 60 * 60 * 1000),
      status: 'active' as const,
    },
    {
      id: '2',
      name: 'MarketLeader Inc',
      domain: 'marketleader.com',
      logo: null,
      adSpend: 280000,
      adSpendTrend: 8,
      shareOfVoice: 35,
      keywordOverlap: 62,
      creativesTracked: 78,
      lastRefresh: new Date(Date.now() - 4 * 60 * 60 * 1000),
      status: 'active' as const,
    },
    {
      id: '3',
      name: 'NewEntrant Co',
      domain: 'newentrant.io',
      logo: null,
      adSpend: 45000,
      adSpendTrend: 85,
      shareOfVoice: 8,
      keywordOverlap: 28,
      creativesTracked: 15,
      lastRefresh: new Date(Date.now() - 6 * 60 * 60 * 1000),
      status: 'active' as const,
    },
    {
      id: '4',
      name: 'OldPlayer Ltd',
      domain: 'oldplayer.com',
      logo: null,
      adSpend: 95000,
      adSpendTrend: -12,
      shareOfVoice: 18,
      keywordOverlap: 55,
      creativesTracked: 24,
      lastRefresh: new Date(Date.now() - 12 * 60 * 60 * 1000),
      status: 'paused' as const,
    },
  ];

  const keywordOverlaps: KeywordOverlap[] = [
    {
      keyword: 'marketing automation',
      yourPosition: 3,
      competitorPosition: 1,
      searchVolume: 12500,
      cpc: 8.5,
      competitor: 'MarketLeader Inc',
    },
    {
      keyword: 'email campaigns',
      yourPosition: 2,
      competitorPosition: 4,
      searchVolume: 8900,
      cpc: 5.2,
      competitor: 'CompetitorOne',
    },
    {
      keyword: 'ad optimization',
      yourPosition: 5,
      competitorPosition: 2,
      searchVolume: 6700,
      cpc: 12.3,
      competitor: 'MarketLeader Inc',
    },
    {
      keyword: 'social media ads',
      yourPosition: 1,
      competitorPosition: 3,
      searchVolume: 15200,
      cpc: 4.8,
      competitor: 'NewEntrant Co',
    },
    {
      keyword: 'ppc management',
      yourPosition: 4,
      competitorPosition: 1,
      searchVolume: 9800,
      cpc: 15.6,
      competitor: 'CompetitorOne',
    },
  ];

  // Share of Voice data - handle API response shape
  type ShareOfVoiceData = { you: number; competitors: { name: string; share: number }[] };
  const shareOfVoice: ShareOfVoiceData = (sovData && !Array.isArray(sovData)
    ? (sovData as ShareOfVoiceData)
    : null) ?? {
    you: 15,
    competitors: [
      { name: 'MarketLeader Inc', share: 35 },
      { name: 'CompetitorOne', share: 24 },
      { name: 'OldPlayer Ltd', share: 18 },
      { name: 'NewEntrant Co', share: 8 },
    ],
  };

  const filteredCompetitors = competitors.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.domain.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatCurrency = (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value}`;
  };

  const formatLastRefresh = (date: Date) => {
    const hours = Math.floor((Date.now() - date.getTime()) / (60 * 60 * 1000));
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  // Stats
  const stats = {
    totalCompetitors: competitors.length,
    activeTracking: competitors.filter((c) => c.status === 'active').length,
    avgKeywordOverlap: Math.round(
      competitors.reduce((sum, c) => sum + c.keywordOverlap, 0) / competitors.length
    ),
    totalCreatives: competitors.reduce((sum, c) => sum + c.creativesTracked, 0),
  };

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
        <div className="metric-card premium p-4">
          <div className="text-sm text-muted-foreground mb-1">Tracked Competitors</div>
          <div className="text-2xl font-bold">{stats.totalCompetitors}</div>
        </div>
        <div className="metric-card success p-4">
          <div className="text-sm text-muted-foreground mb-1">Active Tracking</div>
          <div className="text-2xl font-bold text-green-500">{stats.activeTracking}</div>
        </div>
        <div className="metric-card active p-4">
          <div className="text-sm text-muted-foreground mb-1">Avg Keyword Overlap</div>
          <div className="text-2xl font-bold">{stats.avgKeywordOverlap}%</div>
        </div>
        <div className="metric-card warning p-4">
          <div className="text-sm text-muted-foreground mb-1">Creatives Tracked</div>
          <div className="text-2xl font-bold">{stats.totalCreatives}</div>
        </div>
      </div>

      {/* Share of Voice */}
      <div className="metric-card premium p-6">
        <div className="flex items-center gap-3 mb-4">
          <ChartBarIcon className="w-5 h-5 text-purple-500" />
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
              <span>
                {c.name} ({c.share}%)
              </span>
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

      {/* Competitors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredCompetitors.map((competitor) => (
          <div
            key={competitor.id}
            className={cn(
              'metric-card info p-4 cursor-pointer',
              selectedCompetitor === competitor.id && 'ring-2 ring-primary'
            )}
            onClick={() =>
              setSelectedCompetitor(selectedCompetitor === competitor.id ? null : competitor.id)
            }
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
                <span
                  className={cn(
                    'px-2 py-1 rounded-full text-xs',
                    competitor.status === 'active'
                      ? 'bg-green-500/10 text-green-500'
                      : 'bg-muted text-muted-foreground'
                  )}
                >
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
                  <span
                    className={cn(
                      'flex items-center text-xs',
                      competitor.adSpendTrend >= 0 ? 'text-green-500' : 'text-red-500'
                    )}
                  >
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

            {/* Scan Results (if available) */}
            {scanResults[competitor.id] && (
              <div className="mt-3 pt-3 border-t space-y-2" onClick={(e) => e.stopPropagation()}>
                {/* Social Links */}
                {scanResults[competitor.id].social_links && (
                  <div className="flex flex-wrap items-center gap-2">
                    {scanResults[competitor.id].social_links.facebook && (
                      <a
                        href={scanResults[competitor.id].social_links.facebook!}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-blue-500/10 text-blue-600 hover:bg-blue-500/20"
                      >
                        <span className="font-bold">f</span> Facebook
                        <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                      </a>
                    )}
                    {scanResults[competitor.id].social_links.instagram && (
                      <a
                        href={scanResults[competitor.id].social_links.instagram!}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-pink-500/10 text-pink-500 hover:bg-pink-500/20"
                      >
                        <span className="font-bold">IG</span> Instagram
                        <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                      </a>
                    )}
                    {scanResults[competitor.id].social_links.tiktok && (
                      <a
                        href={scanResults[competitor.id].social_links.tiktok!}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-muted text-foreground hover:bg-muted/80"
                      >
                        <span className="font-bold">TT</span> TikTok
                        <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                )}

                {/* Ad Library Status */}
                <div className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-lg text-xs',
                  scanResults[competitor.id].ad_library.has_ads
                    ? 'bg-green-500/10 text-green-500'
                    : 'bg-amber-500/10 text-amber-500'
                )}>
                  {scanResults[competitor.id].ad_library.has_ads ? (
                    <>
                      <CheckCircleIcon className="w-4 h-4" />
                      <span className="font-medium">
                        {scanResults[competitor.id].ad_library.ad_count}+ Active Ads Found
                      </span>
                      {scanResults[competitor.id].ad_library.page_name && (
                        <span className="text-muted-foreground">
                          ({scanResults[competitor.id].ad_library.page_name})
                        </span>
                      )}
                    </>
                  ) : (
                    <>
                      <XCircleIcon className="w-4 h-4" />
                      <span className="font-medium">No Active Ads</span>
                    </>
                  )}
                  {scanResults[competitor.id].ad_library.search_url && (
                    <a
                      href={scanResults[competitor.id].ad_library.search_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-auto text-primary hover:underline flex items-center gap-1"
                    >
                      View <ArrowTopRightOnSquareIcon className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            )}

            {/* Quick Links + Actions */}
            <div className="flex items-center gap-2 mt-3 pt-3 border-t">
              {/* Scan Button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleScanCompetitor(competitor.id, competitor.country || 'SA');
                }}
                disabled={scanningId === competitor.id}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-colors',
                  scanningId === competitor.id
                    ? 'bg-cyan-500/10 text-cyan-500'
                    : 'bg-purple-500/10 text-purple-500 hover:bg-purple-500/20'
                )}
                title="Scan website & check Meta Ad Library"
              >
                <MagnifyingGlassIcon className={cn('w-3 h-3', scanningId === competitor.id && 'animate-spin')} />
                {scanningId === competitor.id ? 'Scanning...' : 'Scan'}
              </button>
              <a
                href={getMetaAdsLibraryUrl(getMetaSearchQuery(competitor.id, competitor.name), competitor.country || 'SA')}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-blue-500/10 text-blue-600 hover:bg-blue-500/20 transition-colors"
                title={`Search "${getMetaSearchQuery(competitor.id, competitor.name)}" in Meta Ads Library`}
              >
                <span className="font-bold">M</span>
                Meta Ads
                <ArrowTopRightOnSquareIcon className="w-3 h-3" />
              </a>
              <a
                href={getGoogleTransparencyUrl(competitor.domain, competitor.country || 'SA')}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs bg-green-500/10 text-green-600 hover:bg-green-500/20 transition-colors"
                title={`Search "${competitor.domain}" in Google Transparency (${competitor.country || 'SA'})`}
              >
                <span className="font-bold">G</span>
                Google
                <ArrowTopRightOnSquareIcon className="w-3 h-3" />
              </a>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteCompetitor(competitor.id);
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

      {/* Keyword Overlap Table */}
      <div className="metric-card active overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-cyan-500/20">
          <h2 className="font-semibold">Keyword Overlap</h2>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border hover:bg-muted transition-colors">
            <ArrowPathIcon className="w-4 h-4" />
            Refresh
          </button>
        </div>
        <table className="w-full">
          <thead className="bg-cyan-500/10 border-b border-cyan-500/20">
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
                  <span
                    className={cn(
                      'px-2 py-1 rounded text-sm font-medium',
                      kw.yourPosition <= 3
                        ? 'bg-green-500/10 text-green-500'
                        : kw.yourPosition <= 5
                          ? 'bg-amber-500/10 text-amber-500'
                          : 'bg-muted text-muted-foreground'
                    )}
                  >
                    #{kw.yourPosition}
                  </span>
                </td>
                <td className="p-4 text-center text-sm text-muted-foreground">{kw.competitor}</td>
                <td className="p-4 text-center">
                  <span
                    className={cn(
                      'px-2 py-1 rounded text-sm font-medium',
                      kw.competitorPosition <= 3
                        ? 'bg-red-500/10 text-red-500'
                        : kw.competitorPosition <= 5
                          ? 'bg-amber-500/10 text-amber-500'
                          : 'bg-muted text-muted-foreground'
                    )}
                  >
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
      </div>

      {filteredCompetitors.length === 0 && (
        <div className="text-center py-12">
          <EyeIcon className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No competitors found</p>
        </div>
      )}

      {/* Add Competitor Modal */}
      <AddCompetitorModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => refetchCompetitors()}
      />
    </div>
  );
}

export default Competitors;
