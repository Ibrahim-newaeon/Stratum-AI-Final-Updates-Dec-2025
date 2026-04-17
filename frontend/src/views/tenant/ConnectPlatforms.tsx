/**
 * Stratum AI - Connect Platforms Page
 *
 * Integration hub for all platform connections.
 * Click any platform to see required tokens, IDs, and credentials.
 * Supports OAuth connect/disconnect for ad platforms.
 */

import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import {
  LinkIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import {
  useConnectorStatus,
  useStartConnection,
  useRefreshToken,
  useDisconnectPlatform,
  useAdAccounts,
  type Platform,
} from '@/api/campaignBuilder'
import {
  PlatformSetupModal,
  platformCredentials,
  categoryLabels,
  categoryOrder,
  type PlatformCredentialConfig,
} from '@/components/integrations/PlatformSetupModal'

// ─── Status Config ────────────────────────────────────────────────────────

const statusConfig = {
  connected: {
    icon: CheckCircleIcon,
    color: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-500/15',
    borderColor: 'border-emerald-500/30',
    label: 'Connected',
  },
  disconnected: {
    icon: XCircleIcon,
    color: 'text-white/40',
    bgColor: 'bg-white/5',
    borderColor: 'border-white/10',
    label: 'Not Connected',
  },
  expired: {
    icon: ExclamationTriangleIcon,
    color: 'text-amber-600 dark:text-amber-400',
    bgColor: 'bg-amber-500/15',
    borderColor: 'border-amber-500/30',
    label: 'Token Expired',
  },
  error: {
    icon: XCircleIcon,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-500/15',
    borderColor: 'border-red-500/30',
    label: 'Connection Error',
  },
}

type ConnectionStatus = keyof typeof statusConfig

// ─── OAuth-enabled platforms ──────────────────────────────────────────────

const oauthPlatforms = new Set(['meta', 'google', 'tiktok', 'snapchat'])

// ─── Main Component ──────────────────────────────────────────────────────

export default function ConnectPlatforms() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const tid = parseInt(tenantId || '1', 10)
  const [connecting, setConnecting] = useState<string | null>(null)
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformCredentialConfig | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  // API hooks for connector status (ad platforms only)
  const { data: metaStatus } = useConnectorStatus(tid, 'meta')
  const { data: googleStatus } = useConnectorStatus(tid, 'google')
  const { data: tiktokStatus } = useConnectorStatus(tid, 'tiktok')
  const { data: snapchatStatus } = useConnectorStatus(tid, 'snapchat')

  // API hooks for ad account counts
  const { data: metaAccounts } = useAdAccounts(tid, 'meta')
  const { data: googleAccounts } = useAdAccounts(tid, 'google')
  const { data: tiktokAccounts } = useAdAccounts(tid, 'tiktok')
  const { data: snapchatAccounts } = useAdAccounts(tid, 'snapchat')

  // Mutation hooks
  const startConnection = useStartConnection(tid)
  const refreshToken = useRefreshToken(tid)
  const disconnectPlatform = useDisconnectPlatform(tid)

  // Build status map
  const statusMap: Record<string, { status: ConnectionStatus; connectedAt?: string; accountCount: number }> = useMemo(() => {
    const apiStatusMap: Record<string, typeof metaStatus> = {
      meta: metaStatus,
      google: googleStatus,
      tiktok: tiktokStatus,
      snapchat: snapchatStatus,
    }
    const accountsMap: Record<string, typeof metaAccounts> = {
      meta: metaAccounts,
      google: googleAccounts,
      tiktok: tiktokAccounts,
      snapchat: snapchatAccounts,
    }

    const result: Record<string, { status: ConnectionStatus; connectedAt?: string; accountCount: number }> = {}
    for (const id of Object.keys(apiStatusMap)) {
      const apiStatus = apiStatusMap[id]
      const accounts = accountsMap[id]
      result[id] = {
        status: (apiStatus?.status as ConnectionStatus) || 'disconnected',
        connectedAt: apiStatus?.connected_at?.split('T')[0],
        accountCount: accounts?.length ?? 0,
      }
    }
    return result
  }, [metaStatus, googleStatus, tiktokStatus, snapchatStatus, metaAccounts, googleAccounts, tiktokAccounts, snapchatAccounts])

  // Filter platforms
  const filteredPlatforms = useMemo(() => {
    let platforms = platformCredentials
    if (selectedCategory !== 'all') {
      platforms = platforms.filter((p) => p.category === selectedCategory)
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      platforms = platforms.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.subtitle.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.category.toLowerCase().includes(q)
      )
    }
    return platforms
  }, [selectedCategory, searchQuery])

  // Group by category
  const groupedPlatforms = useMemo(() => {
    const grouped: Record<string, PlatformCredentialConfig[]> = {}
    for (const p of filteredPlatforms) {
      if (!grouped[p.category]) grouped[p.category] = []
      grouped[p.category].push(p)
    }
    return grouped
  }, [filteredPlatforms])

  const handleConnect = async (platformId: string) => {
    if (!oauthPlatforms.has(platformId)) return
    setConnecting(platformId)
    try {
      const result = await startConnection.mutateAsync(platformId as Platform)
      if (result.oauth_url) {
        window.location.href = result.oauth_url
      }
    } catch (error) {
      console.error('Failed to start connection:', error)
    } finally {
      setConnecting(null)
    }
  }

  const handleDisconnect = async (platformId: string) => {
    if (confirm('Are you sure you want to disconnect this platform?')) {
      try {
        await disconnectPlatform.mutateAsync(platformId as Platform)
      } catch (error) {
        console.error('Failed to disconnect:', error)
      }
    }
  }

  const handleRefresh = async (platformId: string) => {
    try {
      await refreshToken.mutateAsync(platformId as Platform)
    } catch (error) {
      console.error('Failed to refresh token:', error)
    }
  }

  const getStatus = (platformId: string): ConnectionStatus => {
    return statusMap[platformId]?.status || 'disconnected'
  }

  const connectedCount = Object.values(statusMap).filter((s) => s.status === 'connected').length
  const totalPlatforms = platformCredentials.length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Integrations</h1>
          <p className="text-muted-foreground">
            Connect your platforms to Stratum AI. Click any integration to view required credentials.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-sm">
            <span className="text-emerald-400 font-semibold">{connectedCount}</span>
            <span className="text-white/40">/{totalPlatforms} connected</span>
          </div>
        </div>
      </div>

      {/* Search + Category Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search integrations..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-white/10 bg-white/[0.02] text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/30 transition-all"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setSelectedCategory('all')}
            className={cn(
              'px-3 py-2 rounded-lg text-xs font-medium transition-all',
              selectedCategory === 'all'
                ? 'bg-primary text-primary-foreground'
                : 'bg-white/5 text-white/50 hover:text-white/80 hover:bg-white/10 border border-white/10'
            )}
          >
            All
          </button>
          {categoryOrder.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={cn(
                'px-3 py-2 rounded-lg text-xs font-medium transition-all',
                selectedCategory === cat
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-white/5 text-white/50 hover:text-white/80 hover:bg-white/10 border border-white/10'
              )}
            >
              {categoryLabels[cat]}
            </button>
          ))}
        </div>
      </div>

      {/* Platform Grid by Category */}
      {categoryOrder.map((cat) => {
        const platforms = groupedPlatforms[cat]
        if (!platforms || platforms.length === 0) return null

        return (
          <div key={cat}>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-white/50 mb-3">
              {categoryLabels[cat]}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {platforms.map((platform) => {
                const isOAuth = oauthPlatforms.has(platform.id)
                const status = getStatus(platform.id)
                const statusCfg = statusConfig[status]
                const StatusIcon = statusCfg.icon
                const connInfo = statusMap[platform.id]

                return (
                  <div
                    key={platform.id}
                    className={cn(
                      'group relative rounded-xl border transition-all cursor-pointer hover:border-white/20',
                      status === 'connected'
                        ? 'border-emerald-500/20 bg-emerald-500/[0.03]'
                        : 'border-white/8 bg-white/[0.02] hover:bg-white/[0.04]'
                    )}
                    onClick={() => setSelectedPlatform(platform)}
                  >
                    <div className="p-5">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={cn('h-11 w-11 rounded-lg bg-gradient-to-br flex items-center justify-center shrink-0', platform.color)}>
                            <span className="text-sm font-bold text-white">{platform.icon}</span>
                          </div>
                          <div>
                            <h3 className="font-semibold text-sm">{platform.name}</h3>
                            <p className="text-xs text-white/40">{platform.subtitle}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {isOAuth && (
                            <div className={cn('flex items-center gap-1 text-xs', statusCfg.color)}>
                              <StatusIcon className="h-3.5 w-3.5" />
                              <span>{statusCfg.label}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Credential count + auth method */}
                      <div className="flex items-center gap-3 mt-3">
                        <span className="text-[11px] px-2 py-0.5 rounded-md bg-white/5 text-white/40 border border-white/8">
                          {platform.credentials.filter((c) => c.required).length} required fields
                        </span>
                        <span className="text-[11px] px-2 py-0.5 rounded-md bg-white/5 text-white/40 border border-white/8">
                          {platform.authMethod === 'oauth' ? 'OAuth' : platform.authMethod === 'oauth+api-key' ? 'OAuth + API' : platform.authMethod === 'webhook' ? 'Webhook' : 'API Key'}
                        </span>
                        {platform.capiEvents && platform.capiEvents.length > 0 && (
                          <span className="text-[11px] px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            CAPI
                          </span>
                        )}
                      </div>

                      {/* Connected info for OAuth platforms */}
                      {isOAuth && status === 'connected' && connInfo && (
                        <div className="flex items-center gap-4 mt-3 pt-3 border-t border-white/5 text-xs text-white/40">
                          <span>Accounts: <span className="text-white/70 font-medium">{connInfo.accountCount}</span></span>
                          <span>Since: <span className="text-white/70 font-medium">{connInfo.connectedAt || '—'}</span></span>
                        </div>
                      )}

                      {/* Action buttons for OAuth platforms */}
                      {isOAuth && (
                        <div className="flex items-center gap-2 mt-3" onClick={(e) => e.stopPropagation()}>
                          {status === 'connected' ? (
                            <>
                              <button
                                onClick={() => handleRefresh(platform.id)}
                                className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-white/10 hover:bg-white/5 transition-colors"
                              >
                                <ArrowPathIcon className="h-3.5 w-3.5" />
                                Refresh
                              </button>
                              <button
                                onClick={() => handleDisconnect(platform.id)}
                                className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
                              >
                                Disconnect
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => handleConnect(platform.id)}
                              disabled={connecting === platform.id}
                              className="flex items-center gap-1.5 px-4 py-1.5 text-xs rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-all"
                            >
                              {connecting === platform.id ? (
                                <ArrowPathIcon className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <LinkIcon className="h-3.5 w-3.5" />
                              )}
                              Connect via OAuth
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}

      {/* Empty state */}
      {filteredPlatforms.length === 0 && (
        <div className="text-center py-12 text-white/40">
          <MagnifyingGlassIcon className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No integrations match your search.</p>
        </div>
      )}

      {/* Feature Support Matrix */}
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-6">
        <h3 className="font-semibold mb-4">Ad Platform Feature Matrix</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left">
                <th className="pb-3 font-medium text-white/50">Feature</th>
                <th className="pb-3 font-medium text-white/50 text-center">Meta</th>
                <th className="pb-3 font-medium text-white/50 text-center">Google</th>
                <th className="pb-3 font-medium text-white/50 text-center">TikTok</th>
                <th className="pb-3 font-medium text-white/50 text-center">Snapchat</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {[
                ['OAuth Flow',          true, true, true, true],
                ['Token Auto-Refresh',  true, true, true, true],
                ['Ad Account Fetching', true, true, true, true],
                ['CAPI Events',         true, 'planned', 'planned', 'planned'],
                ['Custom Audiences',    true, true, true, true],
                ['Audience Add/Remove', true, true, true, true],
                ['Audience Replace',    true, true, true, true],
                ['Webhook Support',     true, true, true, true],
              ].map(([feature, ...platforms], i) => (
                <tr key={i}>
                  <td className="py-2.5 font-medium text-white/70">{feature as string}</td>
                  {(platforms as (boolean | string)[]).map((v, j) => (
                    <td key={j} className="py-2.5 text-center">
                      {v === true ? (
                        <span className="text-emerald-400 font-bold">&#10003;</span>
                      ) : (
                        <span className="text-amber-400/70 text-xs font-medium">Planned</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Security info */}
      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-6">
        <h3 className="font-semibold mb-2">Security & Data Handling</h3>
        <ul className="space-y-2 text-sm text-white/50">
          <li>&#8226; OAuth tokens are AES-256 encrypted at rest and auto-refreshed before expiry</li>
          <li>&#8226; All PII data (emails, phone numbers) is SHA-256 hashed before sending to any platform</li>
          <li>&#8226; API keys and secrets are encrypted with Fernet symmetric encryption</li>
          <li>&#8226; Webhook signatures are verified using HMAC for Stripe, WhatsApp, and Slack</li>
          <li>&#8226; You can disconnect any platform at any time — this revokes access immediately</li>
          <li>&#8226; Campaign Builder requires at least one connected ad platform to launch campaigns</li>
        </ul>
      </div>

      {/* Platform Setup Modal */}
      <PlatformSetupModal
        platform={selectedPlatform}
        onClose={() => setSelectedPlatform(null)}
        onConnect={oauthPlatforms.has(selectedPlatform?.id || '') ? handleConnect : undefined}
      />
    </div>
  )
}
