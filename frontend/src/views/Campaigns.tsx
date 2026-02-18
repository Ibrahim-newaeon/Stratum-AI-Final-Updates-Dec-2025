import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Search,
  Filter,
  Plus,
  MoreHorizontal,
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Pause,
  Play,
  Edit,
  Trash2,
  ExternalLink,
  Loader2,
  Target,
} from 'lucide-react'
import { cn, formatCurrency, formatPercent, formatCompactNumber, getPlatformColor } from '@/lib/utils'
import CampaignCreateModal from '@/components/campaigns/CampaignCreateModal'
import { useCampaigns, usePauseCampaign, useActivateCampaign, useDeleteCampaign } from '@/api/hooks'

interface Campaign {
  id: number
  name: string
  platform: string
  status: 'active' | 'paused' | 'completed' | 'draft'
  spend: number
  budget: number
  revenue: number
  roas: number
  impressions: number
  clicks: number
  conversions: number
  ctr: number
  trend: 'up' | 'down' | 'stable'
}

type SortField = 'name' | 'spend' | 'revenue' | 'roas' | 'conversions'
type SortDirection = 'asc' | 'desc'

export function Campaigns() {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [platformFilter, setPlatformFilter] = useState<string>('all')
  const [sortField, setSortField] = useState<SortField>('spend')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [selectedCampaigns, setSelectedCampaigns] = useState<number[]>([])
  const [createModalOpen, setCreateModalOpen] = useState(false)

  // Fetch campaigns from API
  const { data: campaignsData, isLoading } = useCampaigns()
  const pauseCampaign = usePauseCampaign()
  const activateCampaign = useActivateCampaign()
  const deleteCampaign = useDeleteCampaign()

  // Transform API data or fall back to mock
  const campaigns = useMemo((): Campaign[] => {
    if (campaignsData?.items && campaignsData.items.length > 0) {
      return campaignsData.items.map((c: any) => ({
        id: Number(c.id) || Number(c.campaign_id) || 0,
        name: c.name || c.campaign_name || '',
        platform: c.platform?.toLowerCase() || 'google',
        status: c.status?.toLowerCase() || 'active',
        spend: c.spend || 0,
        budget: c.budget || c.daily_budget || 10000,
        revenue: c.revenue || 0,
        roas: c.roas || (c.spend > 0 ? c.revenue / c.spend : 0),
        impressions: c.impressions || 0,
        clicks: c.clicks || 0,
        conversions: c.conversions || 0,
        ctr: c.ctr || (c.impressions > 0 ? (c.clicks / c.impressions) * 100 : 0),
        trend: c.trend || (c.roas >= 3.5 ? 'up' : c.roas < 2.5 ? 'down' : 'stable'),
      }))
    }
    return []
  }, [campaignsData])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const filteredCampaigns = campaigns
    .filter((campaign) => {
      if (searchQuery && !campaign.name.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false
      }
      if (statusFilter !== 'all' && campaign.status !== statusFilter) {
        return false
      }
      if (platformFilter !== 'all' && campaign.platform !== platformFilter) {
        return false
      }
      return true
    })
    .sort((a, b) => {
      const aValue = a[sortField]
      const bValue = b[sortField]
      const direction = sortDirection === 'asc' ? 1 : -1
      if (typeof aValue === 'string') {
        return aValue.localeCompare(bValue as string) * direction
      }
      return ((aValue as number) - (bValue as number)) * direction
    })

  // Handle bulk pause
  const handleBulkPause = async () => {
    for (const id of selectedCampaigns) {
      await pauseCampaign.mutateAsync(id.toString())
    }
    setSelectedCampaigns([])
  }

  // Handle bulk activate
  const handleBulkActivate = async () => {
    for (const id of selectedCampaigns) {
      await activateCampaign.mutateAsync(id.toString())
    }
    setSelectedCampaigns([])
  }

  // Handle bulk delete
  const handleBulkDelete = async () => {
    for (const id of selectedCampaigns) {
      await deleteCampaign.mutateAsync(id.toString())
    }
    setSelectedCampaigns([])
  }

  const toggleSelectAll = () => {
    if (selectedCampaigns.length === filteredCampaigns.length) {
      setSelectedCampaigns([])
    } else {
      setSelectedCampaigns(filteredCampaigns.map((c) => c.id))
    }
  }

  const toggleSelectCampaign = (id: number) => {
    setSelectedCampaigns((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null
    return sortDirection === 'asc' ? (
      <ChevronUp className="w-4 h-4" />
    ) : (
      <ChevronDown className="w-4 h-4" />
    )
  }

  const getStatusBadge = (status: Campaign['status']) => {
    const styles = {
      active: 'bg-green-500/10 text-green-500',
      paused: 'bg-amber-500/10 text-amber-500',
      completed: 'bg-blue-500/10 text-blue-500',
      draft: 'bg-gray-500/10 text-gray-500',
    }

    return (
      <span className={cn('px-2 py-1 rounded-full text-xs font-medium', styles[status])}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getPlatformBadge = (platform: string) => {
    const logoMap: Record<string, string> = {
      meta: '/icons/meta.svg',
      google: '/icons/google.svg',
      tiktok: '/icons/tiktok.svg',
      snapchat: '/icons/snapchat.svg',
    }
    const logo = logoMap[platform.toLowerCase()]
    if (logo) {
      return (
        <img
          src={logo}
          alt={platform}
          className="w-6 h-6 rounded-full"
          title={platform.charAt(0).toUpperCase() + platform.slice(1)}
        />
      )
    }
    return (
      <div
        className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold"
        style={{ backgroundColor: getPlatformColor(platform) }}
        title={platform.charAt(0).toUpperCase() + platform.slice(1)}
      >
        {platform.charAt(0).toUpperCase()}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{t('campaigns.title')}</h1>
          <p className="text-muted-foreground">{t('campaigns.subtitle')}</p>
        </div>

        <button
          onClick={() => setCreateModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>{t('campaigns.createNew')}</span>
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={t('campaigns.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <div className="flex gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">{t('campaigns.allStatuses')}</option>
            <option value="active">{t('campaigns.active')}</option>
            <option value="paused">{t('campaigns.paused')}</option>
            <option value="completed">{t('campaigns.completed')}</option>
            <option value="draft">{t('campaigns.draft')}</option>
          </select>

          <select
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
            className="px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">{t('campaigns.allPlatforms')}</option>
            <option value="google">Google Ads</option>
            <option value="meta">Meta Ads</option>
            <option value="tiktok">TikTok Ads</option>
            <option value="linkedin">LinkedIn Ads</option>
          </select>

          <button className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors">
            <Filter className="w-4 h-4" />
            <span>{t('common.moreFilters')}</span>
          </button>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedCampaigns.length > 0 && (
        <div className="flex items-center gap-4 p-3 rounded-lg bg-primary/10 border border-primary/20">
          <span className="text-sm font-medium">
            {selectedCampaigns.length} {t('campaigns.selected')}
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleBulkPause}
              disabled={pauseCampaign.isPending}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-background border hover:bg-muted transition-colors text-sm disabled:opacity-50"
            >
              {pauseCampaign.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Pause className="w-4 h-4" />}
              {t('campaigns.pauseSelected')}
            </button>
            <button
              onClick={handleBulkActivate}
              disabled={activateCampaign.isPending}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-background border hover:bg-muted transition-colors text-sm disabled:opacity-50"
            >
              {activateCampaign.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              {t('campaigns.activateSelected')}
            </button>
            <button
              onClick={handleBulkDelete}
              disabled={deleteCampaign.isPending}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors text-sm disabled:opacity-50"
            >
              {deleteCampaign.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              {t('campaigns.deleteSelected')}
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && campaigns.length === 0 && (
        <div className="flex flex-col items-center justify-center p-12 rounded-xl border bg-card">
          <Target className="w-12 h-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No campaigns yet</h3>
          <p className="text-muted-foreground text-center max-w-md">
            Create your first campaign to start tracking performance across platforms.
          </p>
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="p-4 text-left">
                  <input
                    type="checkbox"
                    checked={selectedCampaigns.length === filteredCampaigns.length && filteredCampaigns.length > 0}
                    onChange={toggleSelectAll}
                    className="rounded border-muted-foreground/50"
                  />
                </th>
                <th className="p-4 text-left">
                  <button
                    onClick={() => handleSort('name')}
                    className="flex items-center gap-1 text-sm font-medium hover:text-primary"
                  >
                    {t('campaigns.name')}
                    <SortIcon field="name" />
                  </button>
                </th>
                <th className="p-4 text-left text-sm font-medium">{t('campaigns.status')}</th>
                <th className="p-4 text-right">
                  <button
                    onClick={() => handleSort('spend')}
                    className="flex items-center gap-1 text-sm font-medium hover:text-primary ml-auto"
                  >
                    {t('campaigns.spend')}
                    <SortIcon field="spend" />
                  </button>
                </th>
                <th className="p-4 text-right">
                  <button
                    onClick={() => handleSort('revenue')}
                    className="flex items-center gap-1 text-sm font-medium hover:text-primary ml-auto"
                  >
                    {t('campaigns.revenue')}
                    <SortIcon field="revenue" />
                  </button>
                </th>
                <th className="p-4 text-right">
                  <button
                    onClick={() => handleSort('roas')}
                    className="flex items-center gap-1 text-sm font-medium hover:text-primary ml-auto"
                  >
                    ROAS
                    <SortIcon field="roas" />
                  </button>
                </th>
                <th className="p-4 text-right">
                  <button
                    onClick={() => handleSort('conversions')}
                    className="flex items-center gap-1 text-sm font-medium hover:text-primary ml-auto"
                  >
                    {t('campaigns.conversions')}
                    <SortIcon field="conversions" />
                  </button>
                </th>
                <th className="p-4 text-right text-sm font-medium">CTR</th>
                <th className="p-4 text-center text-sm font-medium">{t('campaigns.trend')}</th>
                <th className="p-4 text-right text-sm font-medium">{t('campaigns.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredCampaigns.map((campaign) => (
                <tr key={campaign.id} className="hover:bg-muted/30 transition-colors">
                  <td className="p-4">
                    <input
                      type="checkbox"
                      checked={selectedCampaigns.includes(campaign.id)}
                      onChange={() => toggleSelectCampaign(campaign.id)}
                      className="rounded border-muted-foreground/50"
                    />
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      {getPlatformBadge(campaign.platform)}
                      <div>
                        <p className="font-medium">{campaign.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatCurrency(campaign.spend)} / {formatCurrency(campaign.budget)}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">{getStatusBadge(campaign.status)}</td>
                  <td className="p-4 text-right font-medium">{formatCurrency(campaign.spend)}</td>
                  <td className="p-4 text-right font-medium text-green-500">
                    {formatCurrency(campaign.revenue)}
                  </td>
                  <td className="p-4 text-right">
                    <span
                      className={cn(
                        'font-semibold',
                        campaign.roas >= 4 && 'text-green-500',
                        campaign.roas >= 3 && campaign.roas < 4 && 'text-primary',
                        campaign.roas < 3 && 'text-amber-500'
                      )}
                    >
                      {campaign.roas.toFixed(2)}x
                    </span>
                  </td>
                  <td className="p-4 text-right">{formatCompactNumber(campaign.conversions)}</td>
                  <td className="p-4 text-right">{formatPercent(campaign.ctr)}</td>
                  <td className="p-4 text-center">
                    {campaign.trend === 'up' && (
                      <TrendingUp className="w-5 h-5 text-green-500 mx-auto" />
                    )}
                    {campaign.trend === 'down' && (
                      <TrendingDown className="w-5 h-5 text-red-500 mx-auto" />
                    )}
                    {campaign.trend === 'stable' && (
                      <div className="w-5 h-0.5 bg-muted-foreground mx-auto" />
                    )}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button className="p-2 rounded-lg hover:bg-muted transition-colors">
                        <ExternalLink className="w-4 h-4" />
                      </button>
                      <button className="p-2 rounded-lg hover:bg-muted transition-colors">
                        <Edit className="w-4 h-4" />
                      </button>
                      <button className="p-2 rounded-lg hover:bg-muted transition-colors">
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredCampaigns.length === 0 && (
          <div className="p-12 text-center">
            <p className="text-muted-foreground">{t('campaigns.noResults')}</p>
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {isLoading ? (
            <span className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading campaigns...
            </span>
          ) : (
            t('campaigns.showing', {
              count: filteredCampaigns.length,
              total: campaigns.length,
            })
          )}
        </p>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 rounded-lg border hover:bg-muted transition-colors text-sm disabled:opacity-50" disabled>
            {t('common.previous')}
          </button>
          <button className="px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-sm">
            1
          </button>
          <button className="px-3 py-1.5 rounded-lg border hover:bg-muted transition-colors text-sm">
            2
          </button>
          <button className="px-3 py-1.5 rounded-lg border hover:bg-muted transition-colors text-sm">
            {t('common.next')}
          </button>
        </div>
      </div>

      {/* Campaign Create Modal */}
      <CampaignCreateModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={(campaign) => {
          console.log('Campaign created:', campaign)
          // In a real app, you'd refetch the campaigns list here
        }}
      />
    </div>
  )
}

export default Campaigns
