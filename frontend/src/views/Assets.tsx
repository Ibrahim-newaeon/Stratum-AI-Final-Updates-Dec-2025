import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Search,
  Filter,
  Upload,
  Grid,
  List,
  MoreHorizontal,
  Image as ImageIcon,
  Video,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Eye,
  Download,
  Trash2,
  Copy,
  Tag,
  RefreshCw,
  X,
  Sparkles,
  TrendingDown,
  Calendar,
  Users,
  BarChart3,
} from 'lucide-react'
import { cn, formatCompactNumber, formatPercent } from '@/lib/utils'
import { SmartTooltip } from '@/components/guide/SmartTooltip'
import { InfoIcon } from '@/components/ui/InfoIcon'
import api from '@/lib/api'

type AssetType = 'image' | 'video' | 'copy'
type AssetStatus = 'active' | 'paused' | 'fatigued' | 'draft'

interface Asset {
  id: number
  name: string
  type: AssetType
  status: AssetStatus
  thumbnail: string
  impressions: number
  ctr: number
  fatigueScore: number
  campaigns: string[]
  createdAt: string
  dimensions?: string
  duration?: string
}

interface FatigueBreakdown {
  usage_score: number
  age_score: number
  saturation_score: number
  decay_score: number
  total_score: number
  status: string
  recommendations: string[]
}

interface FatigueSummary {
  total_assets: number
  distribution: {
    fresh: { count: number; label: string; color: string }
    healthy: { count: number; label: string; color: string }
    watch: { count: number; label: string; color: string }
    fatigued: { count: number; label: string; color: string }
    critical: { count: number; label: string; color: string }
  }
  needs_attention: number
}

const mockAssets: Asset[] = [
  {
    id: 1,
    name: 'Summer_Banner_v3',
    type: 'image',
    status: 'fatigued',
    thumbnail: 'https://placehold.co/300x250/0ea5e9/white?text=Summer+Sale',
    impressions: 2300000,
    ctr: 1.8,
    fatigueScore: 78,
    campaigns: ['Summer Sale 2024', 'Brand Awareness Q4'],
    createdAt: '2024-06-15',
    dimensions: '300x250',
  },
  {
    id: 2,
    name: 'Product_Hero_Widget',
    type: 'image',
    status: 'active',
    thumbnail: 'https://placehold.co/1200x628/10b981/white?text=Widget+Pro',
    impressions: 890000,
    ctr: 3.2,
    fatigueScore: 23,
    campaigns: ['Product Launch - Widget Pro'],
    createdAt: '2024-09-01',
    dimensions: '1200x628',
  },
  {
    id: 3,
    name: 'Brand_Video_30s',
    type: 'video',
    status: 'active',
    thumbnail: 'https://placehold.co/1920x1080/8b5cf6/white?text=Brand+Video',
    impressions: 1560000,
    ctr: 2.9,
    fatigueScore: 35,
    campaigns: ['Brand Awareness Q4', 'TikTok Influencer Collab'],
    createdAt: '2024-08-20',
    duration: '0:30',
  },
  {
    id: 4,
    name: 'Retargeting_Carousel',
    type: 'image',
    status: 'active',
    thumbnail: 'https://placehold.co/1080x1080/f59e0b/white?text=Carousel',
    impressions: 670000,
    ctr: 4.1,
    fatigueScore: 15,
    campaigns: ['Retargeting - Cart Abandoners'],
    createdAt: '2024-10-05',
    dimensions: '1080x1080',
  },
  {
    id: 5,
    name: 'Holiday_Promo_Copy',
    type: 'copy',
    status: 'draft',
    thumbnail: 'https://placehold.co/400x200/6b7280/white?text=Ad+Copy',
    impressions: 0,
    ctr: 0,
    fatigueScore: 0,
    campaigns: [],
    createdAt: '2024-11-28',
  },
  {
    id: 6,
    name: 'Flash_Sale_Banner',
    type: 'image',
    status: 'paused',
    thumbnail: 'https://placehold.co/728x90/ef4444/white?text=Flash+Sale',
    impressions: 450000,
    ctr: 2.1,
    fatigueScore: 52,
    campaigns: ['Summer Sale 2024'],
    createdAt: '2024-07-10',
    dimensions: '728x90',
  },
]

type ViewMode = 'grid' | 'list'

export function Assets() {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [selectedAssets, setSelectedAssets] = useState<number[]>([])
  const [assets, setAssets] = useState<Asset[]>(mockAssets)
  const [loading, setLoading] = useState(false)
  const [fatigueSummary, setFatigueSummary] = useState<FatigueSummary | null>(null)
  const [selectedAssetForDetail, setSelectedAssetForDetail] = useState<Asset | null>(null)
  const [fatigueBreakdown, setFatigueBreakdown] = useState<FatigueBreakdown | null>(null)
  const [recalculating, setRecalculating] = useState(false)

  // Fetch fatigue summary on mount
  useEffect(() => {
    fetchFatigueSummary()
  }, [])

  const fetchFatigueSummary = async () => {
    try {
      const response = await api.get('/api/v1/assets/fatigue-summary')
      if (response.data.success) {
        setFatigueSummary(response.data.data)
      }
    } catch (error) {
      // Use mock data fallback
      setFatigueSummary({
        total_assets: mockAssets.length,
        distribution: {
          fresh: { count: 2, label: 'Fresh (0-25%)', color: '#22c55e' },
          healthy: { count: 1, label: 'Healthy (26-50%)', color: '#84cc16' },
          watch: { count: 1, label: 'Watch (51-70%)', color: '#f59e0b' },
          fatigued: { count: 1, label: 'Fatigued (71-85%)', color: '#f97316' },
          critical: { count: 1, label: 'Critical (86-100%)', color: '#ef4444' },
        },
        needs_attention: 2,
      })
    }
  }

  const calculateAssetFatigue = async (assetId: number) => {
    setRecalculating(true)
    try {
      const response = await api.post(`/api/v1/assets/${assetId}/calculate-fatigue`)
      if (response.data.success) {
        setFatigueBreakdown(response.data.data)
        // Update asset in list
        setAssets(prev => prev.map(a =>
          a.id === assetId ? { ...a, fatigueScore: response.data.data.fatigue_score } : a
        ))
      }
    } catch (error) {
      // Generate mock breakdown for demo
      const asset = assets.find(a => a.id === assetId)
      if (asset) {
        setFatigueBreakdown({
          usage_score: Math.min(25, asset.fatigueScore * 0.3),
          age_score: Math.min(25, asset.fatigueScore * 0.25),
          saturation_score: Math.min(25, asset.fatigueScore * 0.25),
          decay_score: Math.min(25, asset.fatigueScore * 0.2),
          total_score: asset.fatigueScore,
          status: asset.fatigueScore > 70 ? 'fatigued' : asset.fatigueScore > 50 ? 'watch' : 'healthy',
          recommendations: asset.fatigueScore > 70
            ? ['Replace this creative with fresh content', 'Test new visual concepts', 'Expand to new audiences']
            : asset.fatigueScore > 50
            ? ['Monitor CTR trends closely', 'Prepare creative variations', 'Consider audience segmentation']
            : ['Creative performing well', 'Continue monitoring'],
        })
      }
    } finally {
      setRecalculating(false)
    }
  }

  const handleAssetClick = (asset: Asset) => {
    setSelectedAssetForDetail(asset)
    calculateAssetFatigue(asset.id)
  }

  const filteredAssets = mockAssets.filter((asset) => {
    if (searchQuery && !asset.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false
    }
    if (typeFilter !== 'all' && asset.type !== typeFilter) {
      return false
    }
    if (statusFilter !== 'all' && asset.status !== statusFilter) {
      return false
    }
    return true
  })

  const toggleSelectAsset = (id: number) => {
    setSelectedAssets((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    )
  }

  const getTypeIcon = (type: AssetType) => {
    switch (type) {
      case 'image':
        return <ImageIcon className="w-4 h-4" />
      case 'video':
        return <Video className="w-4 h-4" />
      case 'copy':
        return <FileText className="w-4 h-4" />
    }
  }

  const getStatusBadge = (status: AssetStatus) => {
    const config = {
      active: { color: 'bg-green-500/10 text-green-500', icon: CheckCircle2, label: 'Active' },
      paused: { color: 'bg-amber-500/10 text-amber-500', icon: Clock, label: 'Paused' },
      fatigued: { color: 'bg-red-500/10 text-red-500', icon: AlertTriangle, label: 'Fatigued' },
      draft: { color: 'bg-gray-500/10 text-gray-500', icon: FileText, label: 'Draft' },
    }
    const { color, icon: Icon, label } = config[status]
    return (
      <span className={cn('px-2 py-1 rounded-full text-xs font-medium inline-flex items-center gap-1', color)}>
        <Icon className="w-3 h-3" />
        {label}
      </span>
    )
  }

  const getFatigueColor = (score: number) => {
    if (score >= 70) return 'text-red-500 bg-red-500'
    if (score >= 40) return 'text-amber-500 bg-amber-500'
    return 'text-green-500 bg-green-500'
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{t('assets.title')}</h1>
          <p className="text-muted-foreground">{t('assets.subtitle')}</p>
        </div>

        <button className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
          <Upload className="w-4 h-4" />
          <span>{t('assets.upload')}</span>
        </button>
      </div>

      {/* Fatigue Summary Widget */}
      {fatigueSummary && (
        <div className="rounded-xl border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary" />
              <h3 className="font-semibold">{t('assets.fatigueBreakdown')}</h3>
              <SmartTooltip content="Track asset health across your library. Higher fatigue means creative needs refresh.">
                <InfoIcon size={14} />
              </SmartTooltip>
            </div>
            <div className="flex items-center gap-2">
              {fatigueSummary.needs_attention > 0 && (
                <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-amber-500/10 text-amber-500 text-xs font-medium">
                  <AlertTriangle className="w-3 h-3" />
                  {fatigueSummary.needs_attention} need attention
                </span>
              )}
              <button
                onClick={async () => {
                  setLoading(true)
                  try {
                    await api.post('/api/v1/assets/calculate-all-fatigue')
                    await fetchFatigueSummary()
                  } catch (e) {
                    // fallback handled
                  } finally {
                    setLoading(false)
                  }
                }}
                disabled={loading}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-primary/10 text-primary hover:bg-primary/20 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
                {t('assets.recalculate')}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-3">
            {Object.entries(fatigueSummary.distribution).map(([key, data]) => (
              <div
                key={key}
                className="text-center p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors cursor-pointer"
                onClick={() => setStatusFilter(key === 'fatigued' || key === 'critical' ? 'fatigued' : 'all')}
              >
                <div
                  className="w-8 h-8 mx-auto rounded-full flex items-center justify-center mb-2"
                  style={{ backgroundColor: `${data.color}20` }}
                >
                  <span className="text-sm font-bold" style={{ color: data.color }}>
                    {data.count}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground capitalize">{t(`assets.${key}`)}</p>
              </div>
            ))}
          </div>

          {/* Progress bar showing distribution */}
          <div className="mt-4 h-2 flex rounded-full overflow-hidden">
            {Object.entries(fatigueSummary.distribution).map(([key, data]) => (
              <div
                key={key}
                className="h-full transition-all"
                style={{
                  backgroundColor: data.color,
                  width: `${(data.count / fatigueSummary.total_assets) * 100}%`,
                }}
                title={`${data.label}: ${data.count}`}
              />
            ))}
          </div>
        </div>
      )}

      {/* Filters & Controls */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder={t('assets.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <div className="flex gap-3">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">{t('assets.allTypes')}</option>
            <option value="image">{t('assets.images')}</option>
            <option value="video">{t('assets.videos')}</option>
            <option value="copy">{t('assets.copy')}</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            <option value="all">{t('assets.allStatuses')}</option>
            <option value="active">{t('assets.active')}</option>
            <option value="paused">{t('assets.paused')}</option>
            <option value="fatigued">{t('assets.fatigued')}</option>
            <option value="draft">{t('assets.draft')}</option>
          </select>

          <div className="flex rounded-lg border overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                'p-2 transition-colors',
                viewMode === 'grid' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
              )}
            >
              <Grid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'p-2 transition-colors',
                viewMode === 'list' ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
              )}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedAssets.length > 0 && (
        <div className="flex items-center gap-4 p-3 rounded-lg bg-primary/10 border border-primary/20">
          <span className="text-sm font-medium">
            {selectedAssets.length} {t('assets.selected')}
          </span>
          <div className="flex gap-2">
            <button className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-background border hover:bg-muted transition-colors text-sm">
              <Tag className="w-4 h-4" />
              {t('assets.addTags')}
            </button>
            <button className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-background border hover:bg-muted transition-colors text-sm">
              <Download className="w-4 h-4" />
              {t('assets.download')}
            </button>
            <button className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors text-sm">
              <Trash2 className="w-4 h-4" />
              {t('assets.delete')}
            </button>
          </div>
        </div>
      )}

      {/* Asset Grid */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredAssets.map((asset) => (
            <div
              key={asset.id}
              onClick={() => handleAssetClick(asset)}
              className={cn(
                'rounded-xl border bg-card overflow-hidden hover:shadow-md transition-shadow cursor-pointer',
                selectedAssets.includes(asset.id) && 'ring-2 ring-primary'
              )}
            >
              {/* Thumbnail */}
              <div className="relative aspect-video bg-muted">
                <img
                  src={asset.thumbnail}
                  alt={asset.name}
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-2 left-2">
                  <input
                    type="checkbox"
                    checked={selectedAssets.includes(asset.id)}
                    onChange={() => toggleSelectAsset(asset.id)}
                    className="rounded border-white/50 bg-black/30"
                  />
                </div>
                <div className="absolute top-2 right-2">
                  {getStatusBadge(asset.status)}
                </div>
                <div className="absolute bottom-2 left-2 flex items-center gap-1 px-2 py-1 rounded bg-black/50 text-white text-xs">
                  {getTypeIcon(asset.type)}
                  <span>{asset.dimensions || asset.duration || 'Copy'}</span>
                </div>
              </div>

              {/* Details */}
              <div className="p-4">
                <h4 className="font-medium text-sm truncate mb-2">{asset.name}</h4>

                <div className="flex items-center justify-between text-sm mb-3">
                  <div className="flex items-center gap-1 text-muted-foreground">
                    <Eye className="w-3 h-3" />
                    <span>{formatCompactNumber(asset.impressions)}</span>
                  </div>
                  <div className="text-muted-foreground">
                    CTR: <span className="font-medium">{formatPercent(asset.ctr)}</span>
                  </div>
                </div>

                {/* Fatigue Score */}
                {asset.status !== 'draft' && (
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">{t('assets.fatigueScore')}</span>
                      <span className={cn('font-medium', getFatigueColor(asset.fatigueScore).split(' ')[0])}>
                        {asset.fatigueScore}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn('h-full rounded-full', getFatigueColor(asset.fatigueScore).split(' ')[1])}
                        style={{ width: `${asset.fatigueScore}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center justify-between mt-4 pt-3 border-t">
                  <div className="flex gap-1">
                    <button className="p-1.5 rounded hover:bg-muted transition-colors">
                      <Eye className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 rounded hover:bg-muted transition-colors">
                      <Copy className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 rounded hover:bg-muted transition-colors">
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                  <button className="p-1.5 rounded hover:bg-muted transition-colors">
                    <MoreHorizontal className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* List View */
        <div className="rounded-xl border bg-card overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="p-4 text-left">
                  <input
                    type="checkbox"
                    onChange={() => {
                      if (selectedAssets.length === filteredAssets.length) {
                        setSelectedAssets([])
                      } else {
                        setSelectedAssets(filteredAssets.map((a) => a.id))
                      }
                    }}
                    checked={selectedAssets.length === filteredAssets.length && filteredAssets.length > 0}
                    className="rounded"
                  />
                </th>
                <th className="p-4 text-left text-sm font-medium">{t('assets.name')}</th>
                <th className="p-4 text-left text-sm font-medium">{t('assets.type')}</th>
                <th className="p-4 text-left text-sm font-medium">{t('assets.status')}</th>
                <th className="p-4 text-right text-sm font-medium">{t('assets.impressions')}</th>
                <th className="p-4 text-right text-sm font-medium">CTR</th>
                <th className="p-4 text-center text-sm font-medium">{t('assets.fatigue')}</th>
                <th className="p-4 text-right text-sm font-medium">{t('assets.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filteredAssets.map((asset) => (
                <tr key={asset.id} onClick={() => handleAssetClick(asset)} className="hover:bg-muted/30 transition-colors cursor-pointer">
                  <td className="p-4">
                    <input
                      type="checkbox"
                      checked={selectedAssets.includes(asset.id)}
                      onChange={() => toggleSelectAsset(asset.id)}
                      className="rounded"
                    />
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      <img
                        src={asset.thumbnail}
                        alt={asset.name}
                        className="w-12 h-12 rounded object-cover"
                      />
                      <div>
                        <p className="font-medium text-sm">{asset.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {asset.campaigns.length > 0
                            ? `${asset.campaigns.length} campaigns`
                            : 'Not assigned'}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2 text-sm">
                      {getTypeIcon(asset.type)}
                      <span className="capitalize">{asset.type}</span>
                    </div>
                  </td>
                  <td className="p-4">{getStatusBadge(asset.status)}</td>
                  <td className="p-4 text-right font-medium">
                    {formatCompactNumber(asset.impressions)}
                  </td>
                  <td className="p-4 text-right font-medium">{formatPercent(asset.ctr)}</td>
                  <td className="p-4">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={cn('h-full rounded-full', getFatigueColor(asset.fatigueScore).split(' ')[1])}
                          style={{ width: `${asset.fatigueScore}%` }}
                        />
                      </div>
                      <span className={cn('text-sm font-medium', getFatigueColor(asset.fatigueScore).split(' ')[0])}>
                        {asset.fatigueScore}%
                      </span>
                    </div>
                  </td>
                  <td className="p-4 text-right">
                    <button className="p-2 rounded hover:bg-muted transition-colors">
                      <MoreHorizontal className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {filteredAssets.length === 0 && (
        <div className="text-center py-12">
          <ImageIcon className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <p className="text-muted-foreground">{t('assets.noResults')}</p>
        </div>
      )}

      {/* Asset Detail Modal with Fatigue Breakdown */}
      {selectedAssetForDetail && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => {
            setSelectedAssetForDetail(null)
            setFatigueBreakdown(null)
          }}
        >
          <div
            className="bg-card rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <div className="flex items-center gap-3">
                {getTypeIcon(selectedAssetForDetail.type)}
                <div>
                  <h3 className="font-semibold">{selectedAssetForDetail.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    Created {selectedAssetForDetail.createdAt}
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setSelectedAssetForDetail(null)
                  setFatigueBreakdown(null)
                }}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-4 space-y-6">
              {/* Asset Preview */}
              <div className="aspect-video rounded-lg overflow-hidden bg-muted">
                <img
                  src={selectedAssetForDetail.thumbnail}
                  alt={selectedAssetForDetail.name}
                  className="w-full h-full object-cover"
                />
              </div>

              {/* Performance Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-3 rounded-lg bg-muted/50">
                  <Eye className="w-5 h-5 mx-auto mb-1 text-muted-foreground" />
                  <p className="text-lg font-bold">{formatCompactNumber(selectedAssetForDetail.impressions)}</p>
                  <p className="text-xs text-muted-foreground">{t('assets.impressions')}</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted/50">
                  <TrendingDown className="w-5 h-5 mx-auto mb-1 text-muted-foreground" />
                  <p className="text-lg font-bold">{formatPercent(selectedAssetForDetail.ctr)}</p>
                  <p className="text-xs text-muted-foreground">CTR</p>
                </div>
                <div className="text-center p-3 rounded-lg bg-muted/50">
                  <Users className="w-5 h-5 mx-auto mb-1 text-muted-foreground" />
                  <p className="text-lg font-bold">{selectedAssetForDetail.campaigns.length}</p>
                  <p className="text-xs text-muted-foreground">Campaigns</p>
                </div>
              </div>

              {/* Fatigue Breakdown */}
              <div className="rounded-lg border p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-primary" />
                    <h4 className="font-semibold">{t('assets.fatigueBreakdown')}</h4>
                  </div>
                  <button
                    onClick={() => calculateAssetFatigue(selectedAssetForDetail.id)}
                    disabled={recalculating}
                    className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-primary/10 text-primary hover:bg-primary/20 transition-colors disabled:opacity-50"
                  >
                    <RefreshCw className={cn("w-3 h-3", recalculating && "animate-spin")} />
                    {t('assets.recalculate')}
                  </button>
                </div>

                {fatigueBreakdown ? (
                  <div className="space-y-4">
                    {/* Overall Score */}
                    <div className="text-center p-4 rounded-lg bg-muted/50">
                      <div
                        className="text-4xl font-bold mb-1"
                        style={{
                          color: fatigueBreakdown.total_score > 70 ? '#ef4444' :
                            fatigueBreakdown.total_score > 50 ? '#f59e0b' : '#22c55e'
                        }}
                      >
                        {fatigueBreakdown.total_score}%
                      </div>
                      <p className="text-sm text-muted-foreground capitalize">
                        Status: <span className="font-medium">{fatigueBreakdown.status}</span>
                      </p>
                    </div>

                    {/* Component Breakdown */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-3 rounded-lg bg-muted/30">
                        <div className="flex items-center gap-2 mb-2">
                          <RefreshCw className="w-4 h-4 text-blue-500" />
                          <span className="text-sm font-medium">{t('assets.usageScore')}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500 rounded-full"
                              style={{ width: `${(fatigueBreakdown.usage_score / 25) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">{fatigueBreakdown.usage_score.toFixed(1)}/25</span>
                        </div>
                      </div>

                      <div className="p-3 rounded-lg bg-muted/30">
                        <div className="flex items-center gap-2 mb-2">
                          <Calendar className="w-4 h-4 text-purple-500" />
                          <span className="text-sm font-medium">{t('assets.ageScore')}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-purple-500 rounded-full"
                              style={{ width: `${(fatigueBreakdown.age_score / 25) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">{fatigueBreakdown.age_score.toFixed(1)}/25</span>
                        </div>
                      </div>

                      <div className="p-3 rounded-lg bg-muted/30">
                        <div className="flex items-center gap-2 mb-2">
                          <Eye className="w-4 h-4 text-amber-500" />
                          <span className="text-sm font-medium">{t('assets.saturationScore')}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-amber-500 rounded-full"
                              style={{ width: `${(fatigueBreakdown.saturation_score / 25) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">{fatigueBreakdown.saturation_score.toFixed(1)}/25</span>
                        </div>
                      </div>

                      <div className="p-3 rounded-lg bg-muted/30">
                        <div className="flex items-center gap-2 mb-2">
                          <TrendingDown className="w-4 h-4 text-red-500" />
                          <span className="text-sm font-medium">{t('assets.decayScore')}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-red-500 rounded-full"
                              style={{ width: `${(fatigueBreakdown.decay_score / 25) * 100}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">{fatigueBreakdown.decay_score.toFixed(1)}/25</span>
                        </div>
                      </div>
                    </div>

                    {/* Recommendations */}
                    {fatigueBreakdown.recommendations.length > 0 && (
                      <div className="mt-4">
                        <h5 className="text-sm font-medium mb-2">{t('assets.recommendations')}</h5>
                        <ul className="space-y-2">
                          {fatigueBreakdown.recommendations.map((rec, i) => (
                            <li
                              key={i}
                              className="flex items-start gap-2 text-sm text-muted-foreground"
                            >
                              <span className="text-primary mt-0.5">•</span>
                              {rec}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-8">
                    <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
                  </div>
                )}
              </div>

              {/* Campaigns Using This Asset */}
              {selectedAssetForDetail.campaigns.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Active in Campaigns</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedAssetForDetail.campaigns.map((campaign, i) => (
                      <span
                        key={i}
                        className="px-3 py-1 rounded-full bg-muted text-sm"
                      >
                        {campaign}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Assets
