import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  ChevronLeft,
  ChevronRight,
  Eye,
  Loader2,
  Pause,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react'
import { cn, formatCurrency, formatCompactNumber } from '@/lib/utils'
import CampaignCreateModal from '@/components/campaigns/CampaignCreateModal'
import { useCampaigns, usePauseCampaign, useActivateCampaign, useDeleteCampaign } from '@/api/hooks'
import { usePriceMetrics } from '@/hooks/usePriceMetrics'
import { PageHeader } from '@/components/primitives/PageHeader'
import { StatRow, type StatRowItem } from '@/components/primitives/StatRow'
import { StatusPill } from '@/components/primitives/StatusPill'
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable'
import { campaignStatusVariant, campaignStatusLabel } from '@/lib/statusVariant'

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
}

const PAGE_SIZE = 20

export function Campaigns() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { showPriceMetrics } = usePriceMetrics()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [platformFilter, setPlatformFilter] = useState<string>('all')
  const [selectedCampaigns, setSelectedCampaigns] = useState<number[]>([])
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)

  const { data: campaignsData, isLoading, error, refetch: refetchCampaigns } = useCampaigns()
  const pauseCampaign = usePauseCampaign()
  const activateCampaign = useActivateCampaign()
  const deleteCampaign = useDeleteCampaign()

  // Normalise the API rows. Campaign ids are integers in the database, so
  // Number() is safe here; the looser `string` in the API type is historical.
  const campaigns = useMemo((): Campaign[] => {
    const items = campaignsData?.items
    if (!items || items.length === 0) return []
    return (items as unknown as Array<Record<string, unknown>>).map((c) => ({
      id: Number(c.id) || Number(c.campaign_id) || 0,
      name: String(c.name || c.campaign_name || ''),
      platform: String(c.platform || 'google').toLowerCase(),
      status: String(c.status || 'active').toLowerCase() as Campaign['status'],
      spend: Number(c.spend) || 0,
      budget: Number(c.budget || c.daily_budget) || 0,
      revenue: Number(c.revenue) || 0,
      roas: Number(c.roas) || (Number(c.spend) > 0 ? Number(c.revenue) / Number(c.spend) : 0),
      impressions: Number(c.impressions) || 0,
      clicks: Number(c.clicks) || 0,
      conversions: Number(c.conversions) || 0,
      ctr:
        Number(c.ctr) ||
        (Number(c.impressions) > 0 ? (Number(c.clicks) / Number(c.impressions)) * 100 : 0),
    }))
  }, [campaignsData])

  const filteredCampaigns = useMemo(
    () =>
      campaigns.filter((campaign) => {
        if (searchQuery && !campaign.name.toLowerCase().includes(searchQuery.toLowerCase())) {
          return false
        }
        if (statusFilter !== 'all' && campaign.status !== statusFilter) return false
        if (platformFilter !== 'all' && campaign.platform !== platformFilter) return false
        return true
      }),
    [campaigns, searchQuery, statusFilter, platformFilter],
  )

  const totalPages = Math.max(1, Math.ceil(filteredCampaigns.length / PAGE_SIZE))
  const page = Math.min(currentPage, totalPages)
  const pageRows = filteredCampaigns.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  // The context line states the decision this screen supports, not what it is.
  const activeCount = campaigns.filter((c) => c.status === 'active').length
  const pausedCount = campaigns.filter((c) => c.status === 'paused').length
  const contextLine = campaigns.length
    ? `${activeCount} active · ${pausedCount} paused`
    : t('campaigns.subtitle')

  const stats = useMemo((): StatRowItem[] => {
    const totalSpend = campaigns.reduce((sum, c) => sum + c.spend, 0)
    const totalRevenue = campaigns.reduce((sum, c) => sum + c.revenue, 0)
    const totalBudget = campaigns.reduce((sum, c) => sum + c.budget, 0)
    const blendedRoas = totalSpend > 0 ? totalRevenue / totalSpend : 0
    const items: StatRowItem[] = [{ label: 'Active', value: String(activeCount) }]
    if (showPriceMetrics) {
      items.unshift({ label: 'Spend', value: formatCurrency(totalSpend) })
      items.push({ label: 'ROAS', value: `${blendedRoas.toFixed(2)}×` })
      items.push({ label: 'Budget', value: formatCurrency(totalBudget) })
    }
    return items
  }, [campaigns, activeCount, showPriceMetrics])

  const toggleSelectAll = () => {
    setSelectedCampaigns((prev) =>
      prev.length === pageRows.length ? [] : pageRows.map((c) => c.id),
    )
  }

  const toggleSelectCampaign = (id: number) => {
    setSelectedCampaigns((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id],
    )
  }

  const runBulk = async (fn: { mutateAsync: (id: string) => Promise<unknown> }) => {
    for (const id of selectedCampaigns) {
      await fn.mutateAsync(String(id))
    }
    setSelectedCampaigns([])
  }

  const toggleStatus = (campaign: Campaign) => {
    const action = campaign.status === 'active' ? pauseCampaign : activateCampaign
    action.mutateAsync(String(campaign.id))
  }

  const numeric = 'text-right font-mono tabular-nums'

  const columns: DataTableColumn<Campaign>[] = [
    {
      id: 'select',
      className: 'w-10',
      header: (
        <input
          type="checkbox"
          aria-label="Select all campaigns"
          checked={pageRows.length > 0 && selectedCampaigns.length === pageRows.length}
          onChange={toggleSelectAll}
          className="rounded border-muted-foreground/50"
        />
      ),
      cell: (c) => (
        <input
          type="checkbox"
          aria-label={`Select ${c.name}`}
          checked={selectedCampaigns.includes(c.id)}
          onChange={() => toggleSelectCampaign(c.id)}
          className="rounded border-muted-foreground/50"
        />
      ),
    },
    {
      id: 'name',
      header: 'Campaign',
      sortable: true,
      sortAccessor: (c) => c.name,
      cell: (c) => (
        <div className="min-w-0">
          <div className="truncate font-medium text-foreground">{c.name}</div>
          <div className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {c.platform}
          </div>
        </div>
      ),
    },
    {
      id: 'status',
      header: 'Status',
      cell: (c) => (
        <StatusPill size="sm" variant={campaignStatusVariant(c.status)}>
          {campaignStatusLabel(c.status)}
        </StatusPill>
      ),
    },
    ...(showPriceMetrics
      ? [
          {
            id: 'spend',
            header: 'Spend',
            sortable: true,
            sortAccessor: (c: Campaign) => c.spend,
            headerClassName: 'text-right',
            cellClassName: numeric,
            cell: (c: Campaign) => formatCurrency(c.spend),
          },
          {
            id: 'budget',
            header: 'Budget',
            sortable: true,
            sortAccessor: (c: Campaign) => c.budget,
            headerClassName: 'text-right',
            cellClassName: numeric,
            cell: (c: Campaign) => formatCurrency(c.budget),
          },
          {
            id: 'roas',
            header: 'ROAS',
            sortable: true,
            sortAccessor: (c: Campaign) => c.roas,
            headerClassName: 'text-right',
            cellClassName: numeric,
            cell: (c: Campaign) => `${c.roas.toFixed(2)}×`,
          },
        ]
      : []),
    {
      id: 'conversions',
      header: 'Conv.',
      sortable: true,
      sortAccessor: (c) => c.conversions,
      headerClassName: 'text-right',
      cellClassName: numeric,
      cell: (c) => formatCompactNumber(c.conversions),
    },
    {
      id: 'actions',
      header: '',
      className: 'w-32',
      cellClassName: 'text-right',
      // Hidden until hover, but always reachable by keyboard via focus-within.
      cell: (c) => (
        <div className="flex justify-end gap-1 opacity-0 transition-opacity focus-within:opacity-100 group-hover/row:opacity-100">
          <button
            type="button"
            onClick={() => navigate(`/dashboard/campaigns/${c.id}`)}
            aria-label={`View ${c.name}`}
            className="rounded-full p-2 hover:bg-muted"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => navigate(`/dashboard/campaigns/${c.id}/edit`)}
            aria-label={`Edit ${c.name}`}
            className="rounded-full p-2 hover:bg-muted"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => toggleStatus(c)}
            aria-label={c.status === 'active' ? `Pause ${c.name}` : `Activate ${c.name}`}
            className="rounded-full p-2 hover:bg-muted"
          >
            {c.status === 'active' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
        </div>
      ),
    },
  ]

  return (
    <div className="px-8 py-6">
      <PageHeader
        title={t('campaigns.title')}
        context={contextLine}
        actions={
          <>
            <button
              type="button"
              onClick={() => refetchCampaigns()}
              disabled={isLoading}
              aria-label="Refresh campaigns"
              className="rounded-full border border-border p-2 hover:bg-muted"
            >
              <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
            </button>
            <button
              type="button"
              onClick={() => setCreateModalOpen(true)}
              className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              <Plus className="h-4 w-4" />
              <span>{t('campaigns.createNew')}</span>
            </button>
          </>
        }
      />

      <StatRow items={stats} />

      <div className="flex flex-col gap-3 border-b border-border py-4 md:flex-row md:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            aria-label={t('campaigns.searchPlaceholder')}
            placeholder={t('campaigns.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-full border border-border bg-background py-2 pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
        <div className="flex gap-2">
          <select
            aria-label={t('campaigns.allStatuses')}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-full border border-border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          >
            <option value="all">{t('campaigns.allStatuses')}</option>
            <option value="active">{t('campaigns.active')}</option>
            <option value="paused">{t('campaigns.paused')}</option>
            <option value="completed">{t('campaigns.completed')}</option>
            <option value="draft">{t('campaigns.draft')}</option>
          </select>
          <select
            aria-label={t('campaigns.allPlatforms')}
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
            className="rounded-full border border-border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          >
            <option value="all">{t('campaigns.allPlatforms')}</option>
            <option value="google">Google Ads</option>
            <option value="meta">Meta Ads</option>
            <option value="tiktok">TikTok Ads</option>
          </select>
        </div>
      </div>

      {selectedCampaigns.length > 0 && (
        <div className="mt-4 flex items-center gap-4 rounded-2xl border border-border bg-card px-4 py-3">
          <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            {selectedCampaigns.length} selected
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => runBulk(pauseCampaign)}
              disabled={pauseCampaign.isPending}
              className="flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-muted disabled:opacity-50"
            >
              {pauseCampaign.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Pause className="h-4 w-4" />
              )}
              Pause
            </button>
            <button
              type="button"
              onClick={() => runBulk(activateCampaign)}
              disabled={activateCampaign.isPending}
              className="flex items-center gap-1 rounded-full border border-border px-3 py-1.5 text-sm hover:bg-muted disabled:opacity-50"
            >
              {activateCampaign.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              Activate
            </button>
            <button
              type="button"
              onClick={() => runBulk(deleteCampaign)}
              disabled={deleteCampaign.isPending}
              className="flex items-center gap-1 rounded-full border border-danger/30 px-3 py-1.5 text-sm text-danger hover:bg-danger/10 disabled:opacity-50"
            >
              {deleteCampaign.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
              Delete
            </button>
          </div>
        </div>
      )}

      <DataTable
        data={pageRows}
        columns={columns}
        rowKey={(c) => c.id}
        loading={isLoading}
        ariaLabel="Campaigns"
        className="mt-4"
        emptyMessage="No campaigns yet. Connect a platform to import them."
        // An empty table and a failed fetch must never look identical.
        error={error ? 'Could not load campaigns. Retry, or check the integration.' : undefined}
      />

      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              aria-label="Previous page"
              className="rounded-full border border-border p-2 disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              aria-label="Next page"
              className="rounded-full border border-border p-2 disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      <CampaignCreateModal
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={() => {
          setCreateModalOpen(false)
          refetchCampaigns()
        }}
      />
    </div>
  )
}

export default Campaigns
