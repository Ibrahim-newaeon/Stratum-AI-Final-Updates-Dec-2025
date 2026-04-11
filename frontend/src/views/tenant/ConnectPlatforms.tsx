/**
 * Stratum AI - Connect Platforms Page
 *
 * OAuth connection management for advertising platforms.
 * Supports Meta, Google, TikTok, and Snapchat ad platforms.
 */

import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import {
  LinkIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  ChevronDownIcon,
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

interface PlatformConnection {
  id: string
  name: string
  logo: string
  status: 'connected' | 'disconnected' | 'expired' | 'error'
  connectedAt?: string
  expiresAt?: string
  accountCount?: number
}

// Platform definitions with client-facing requirements
const platformDefs = [
  {
    id: 'meta',
    name: 'Meta Ads',
    logo: '/platforms/meta.svg',
    subtitle: 'Facebook & Instagram Ads, CAPI, Custom Audiences',
    whatYouNeed: [
      'A Meta Business Suite account with admin access',
      'A Meta Pixel configured in Events Manager',
      'A System User access token (generated from Business Settings)',
    ],
    features: ['Campaign management', 'CAPI event streaming', 'Custom Audience sync (up to 10K users/batch)', 'Webhook notifications'],
    tokenInfo: 'Tokens are exchanged for a 60-day long-lived token and auto-refreshed before expiry.',
    capiEvents: 'Purchase, Lead, AddToCart, InitiateCheckout, Subscribe, CompleteRegistration, Contact, ViewContent',
    audienceFormat: 'Email, Phone, MADID — all SHA256 hashed automatically',
  },
  {
    id: 'google',
    name: 'Google Ads',
    logo: '/platforms/google.svg',
    subtitle: 'Ads API, Enhanced Conversions, Customer Match',
    whatYouNeed: [
      'A Google Ads account (Customer ID, e.g. 123-456-7890)',
      'Admin or Standard access to the Google Ads account',
    ],
    features: ['Campaign management', 'Enhanced Conversions', 'Customer Match audiences (up to 100K users/batch)', 'Webhook notifications'],
    tokenInfo: 'After connecting, a persistent refresh token keeps the connection alive — no re-authentication needed.',
    capiEvents: 'Enhanced Conversions for Web (planned)',
    audienceFormat: 'Hashed email, phone, first name, last name, country, postal code — retention 1–540 days',
  },
  {
    id: 'tiktok',
    name: 'TikTok Ads',
    logo: '/platforms/tiktok.svg',
    subtitle: 'Business API, Events API, DMP Custom Audiences',
    whatYouNeed: [
      'A TikTok for Business account',
      'An Advertiser ID from TikTok Ads Manager',
      'A TikTok Pixel (found in Ads Manager → Events)',
    ],
    features: ['Campaign management', 'Events API streaming', 'DMP Custom Audiences (up to 50K users/batch)', 'Webhook notifications'],
    tokenInfo: 'Access tokens last 24 hours and are auto-refreshed. Refresh tokens are valid for 365 days.',
    capiEvents: 'Events API (planned)',
    audienceFormat: 'Separate uploads per type: EMAIL_SHA256, PHONE_SHA256, IDFA_SHA256, GAID_SHA256',
  },
  {
    id: 'snapchat',
    name: 'Snapchat Ads',
    logo: '/platforms/snapchat.svg',
    subtitle: 'Marketing API, Snap Audience Match (SAM)',
    whatYouNeed: [
      'A Snapchat Business Manager account',
      'An Ad Account ID from Snapchat Ads Manager',
      'A Snap Pixel configured in your account',
    ],
    features: ['Campaign management', 'Snap Audience Match (up to 100K users/batch)', 'Conversion tracking', 'Webhook notifications'],
    tokenInfo: 'Access tokens last 30 minutes and are auto-refreshed. Refresh tokens are valid for 1 year.',
    capiEvents: 'Conversion API (planned)',
    audienceFormat: 'Hashed email, phone, MADID — default 180-day retention',
  },
]

const statusConfig = {
  connected: {
    icon: CheckCircleIcon,
    color: 'text-emerald-600 dark:text-emerald-400',
    bgColor: 'bg-emerald-50 dark:bg-emerald-950/30',
    label: 'Connected',
  },
  disconnected: {
    icon: XCircleIcon,
    color: 'text-gray-400',
    bgColor: 'bg-gray-50 dark:bg-gray-900/30',
    label: 'Not Connected',
  },
  expired: {
    icon: ExclamationTriangleIcon,
    color: 'text-amber-600 dark:text-amber-400',
    bgColor: 'bg-amber-50 dark:bg-amber-950/30',
    label: 'Token Expired',
  },
  error: {
    icon: XCircleIcon,
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
    label: 'Connection Error',
  },
}

export default function ConnectPlatforms() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const tid = parseInt(tenantId || '1', 10)
  const [connecting, setConnecting] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  // API hooks for connector status
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

  // Build platforms with API status only (no mock fallback)
  const platformsWithStatus: PlatformConnection[] = useMemo(() => {
    const statusMap: Record<string, typeof metaStatus> = {
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

    return platformDefs.map((p) => {
      const apiStatus = statusMap[p.id]
      const accounts = accountsMap[p.id]

      return {
        ...p,
        status: (apiStatus?.status as PlatformConnection['status']) || 'disconnected',
        connectedAt: apiStatus?.connected_at?.split('T')[0],
        accountCount: accounts?.length ?? 0,
      }
    })
  }, [metaStatus, googleStatus, tiktokStatus, snapchatStatus, metaAccounts, googleAccounts, tiktokAccounts, snapchatAccounts])

  const handleConnect = async (platformId: string) => {
    setConnecting(platformId)
    try {
      const result = await startConnection.mutateAsync(platformId as Platform)
      // Redirect to OAuth URL
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Connect Platforms</h1>
        <p className="text-muted-foreground">
          Connect your advertising accounts to start building campaigns
        </p>
      </div>

      {/* Platform Cards */}
      <div className="grid grid-cols-1 gap-6">
        {platformsWithStatus.map((platform) => {
          const status = statusConfig[platform.status]
          const StatusIcon = status.icon
          const def = platformDefs.find((d) => d.id === platform.id)!
          const isExpanded = expanded === platform.id

          return (
            <div
              key={platform.id}
              className={cn(
                'rounded-xl border transition-all',
                platform.status === 'connected' ? 'bg-card shadow-card' : 'bg-muted/30'
              )}
            >
              {/* Card Header */}
              <div className="flex items-start justify-between p-6">
                <div className="flex items-center gap-4">
                  <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 flex items-center justify-center">
                    <span className="text-lg font-bold text-gray-600 dark:text-gray-300">
                      {platform.name.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-semibold">{platform.name}</h3>
                    <p className="text-xs text-muted-foreground">{def.subtitle}</p>
                    <div className={cn('flex items-center gap-1 text-sm mt-1', status.color)}>
                      <StatusIcon className="h-4 w-4" />
                      <span>{status.label}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {platform.status === 'connected' ? (
                    <>
                      <button
                        onClick={() => handleRefresh(platform.id)}
                        className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border hover:bg-accent transition-colors"
                      >
                        <ArrowPathIcon className="h-4 w-4" />
                        Refresh
                      </button>
                      <button
                        onClick={() => handleDisconnect(platform.id)}
                        className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                      >
                        Disconnect
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => handleConnect(platform.id)}
                      disabled={connecting === platform.id}
                      className="flex items-center gap-2 px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
                    >
                      {connecting === platform.id ? (
                        <ArrowPathIcon className="h-4 w-4 animate-spin" />
                      ) : (
                        <LinkIcon className="h-4 w-4" />
                      )}
                      Connect
                    </button>
                  )}
                </div>
              </div>

              {/* Connection details (when connected) */}
              {platform.status === 'connected' && (
                <div className="px-6 pb-4 grid grid-cols-3 gap-4 text-sm">
                  <div className="bg-muted/50 rounded-lg p-3">
                    <span className="text-muted-foreground block text-xs">Accounts</span>
                    <span className="font-semibold">{platform.accountCount}</span>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3">
                    <span className="text-muted-foreground block text-xs">Connected</span>
                    <span className="font-semibold">{platform.connectedAt || '—'}</span>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3">
                    <span className="text-muted-foreground block text-xs">Token Expires</span>
                    <span className="font-semibold">{platform.expiresAt || 'Auto-refresh'}</span>
                  </div>
                </div>
              )}

              {/* Expand/Collapse Requirements */}
              <button
                onClick={() => setExpanded(isExpanded ? null : platform.id)}
                className="w-full flex items-center justify-center gap-2 px-6 py-3 text-xs font-medium text-muted-foreground hover:text-foreground border-t transition-colors"
              >
                <InformationCircleIcon className="h-4 w-4" />
                {isExpanded ? 'Hide' : 'View'} Requirements & Features
                <ChevronDownIcon className={cn('h-4 w-4 transition-transform', isExpanded && 'rotate-180')} />
              </button>

              {/* Requirements Panel */}
              {isExpanded && (
                <div className="px-6 pb-6 space-y-4 border-t bg-muted/20">
                  {/* What You Need */}
                  <div className="pt-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-primary mb-2">What You Need</h4>
                    <ul className="space-y-1.5">
                      {def.whatYouNeed.map((item, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <span className="text-primary mt-0.5">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Features Enabled */}
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-primary mb-2">Features Enabled</h4>
                    <div className="flex flex-wrap gap-2">
                      {def.features.map((feat, i) => (
                        <span key={i} className="inline-block px-3 py-1 text-xs rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                          {feat}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Token & Refresh Info */}
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-primary mb-2">Token & Refresh</h4>
                    <p className="text-sm text-muted-foreground">{def.tokenInfo}</p>
                  </div>

                  {/* Audience Sync */}
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-primary mb-2">Audience Sync Format</h4>
                    <p className="text-sm text-muted-foreground">{def.audienceFormat}</p>
                  </div>

                  {/* Supported Events */}
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-primary mb-2">CAPI Events</h4>
                    <p className="text-sm text-muted-foreground">{def.capiEvents}</p>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Feature Support Matrix */}
      <div className="rounded-xl border bg-card p-6">
        <h3 className="font-semibold mb-4">Feature Support Matrix</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="pb-3 font-medium text-muted-foreground">Feature</th>
                <th className="pb-3 font-medium text-muted-foreground text-center">Meta</th>
                <th className="pb-3 font-medium text-muted-foreground text-center">Google</th>
                <th className="pb-3 font-medium text-muted-foreground text-center">TikTok</th>
                <th className="pb-3 font-medium text-muted-foreground text-center">Snapchat</th>
              </tr>
            </thead>
            <tbody className="divide-y">
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
                  <td className="py-2.5 font-medium">{feature as string}</td>
                  {(platforms as (boolean | string)[]).map((v, j) => (
                    <td key={j} className="py-2.5 text-center">
                      {v === true ? (
                        <span className="text-emerald-500 font-bold">✓</span>
                      ) : (
                        <span className="text-amber-500 text-xs font-medium">Planned</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* OAuth Information */}
      <div className="rounded-xl border bg-muted/30 p-6">
        <h3 className="font-semibold mb-2">About Platform Connections</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>• OAuth tokens are securely encrypted and automatically refreshed before expiry</li>
          <li>• Connections grant access to view and manage ad accounts within Stratum</li>
          <li>• All PII data (emails, phone numbers) is SHA256 hashed before sending to platforms</li>
          <li>• You can disconnect at any time — this revokes Stratum's access immediately</li>
          <li>• Campaign Builder requires at least one connected platform to launch campaigns</li>
        </ul>
      </div>
    </div>
  )
}
