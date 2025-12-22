/**
 * Conversion API (CAPI) Setup Page
 * No-code platform connection wizard for streaming first-party data
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Plug,
  Check,
  X,
  ChevronRight,
  AlertCircle,
  Zap,
  Shield,
  TrendingUp,
  HelpCircle,
  RefreshCw,
  Copy,
  ExternalLink,
  Settings,
  Download,
  Database,
  BarChart3,
  Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { getAccessToken } from '@/services/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Platform configurations
const PLATFORMS = [
  {
    id: 'meta',
    name: 'Meta (Facebook)',
    logo: '/platforms/meta.svg',
    color: 'bg-blue-500',
    description: 'Facebook & Instagram Conversion API',
    credentials: [
      { field: 'pixel_id', label: 'Pixel ID', placeholder: '123456789012345', help: 'Found in Events Manager > Data Sources' },
      { field: 'access_token', label: 'Access Token', placeholder: 'EAABsbCS...', help: 'System User Token from Business Settings', sensitive: true },
    ],
  },
  {
    id: 'google',
    name: 'Google Ads',
    logo: '/platforms/google.svg',
    color: 'bg-red-500',
    description: 'Enhanced Conversions for Web',
    credentials: [
      { field: 'customer_id', label: 'Customer ID', placeholder: '123-456-7890', help: 'Google Ads Customer ID' },
      { field: 'conversion_action_id', label: 'Conversion Action ID', placeholder: '123456789', help: 'From Tools > Conversions' },
      { field: 'api_key', label: 'API Key', placeholder: 'AIza...', help: 'OAuth token or Developer token', sensitive: true },
    ],
  },
  {
    id: 'tiktok',
    name: 'TikTok',
    logo: '/platforms/tiktok.svg',
    color: 'bg-black',
    description: 'TikTok Events API',
    credentials: [
      { field: 'pixel_code', label: 'Pixel Code', placeholder: 'CXXXXXXXXXX', help: 'Found in TikTok Ads Manager > Events' },
      { field: 'access_token', label: 'Access Token', placeholder: '', help: 'Long-lived access token', sensitive: true },
    ],
  },
  {
    id: 'snapchat',
    name: 'Snapchat',
    logo: '/platforms/snapchat.svg',
    color: 'bg-yellow-400',
    description: 'Snapchat Conversion API',
    credentials: [
      { field: 'pixel_id', label: 'Pixel ID', placeholder: '', help: 'Found in Snap Pixel setup' },
      { field: 'access_token', label: 'Access Token', placeholder: '', help: 'From Snapchat Business Manager', sensitive: true },
    ],
  },
  {
    id: 'linkedin',
    name: 'LinkedIn',
    logo: '/platforms/linkedin.svg',
    color: 'bg-blue-700',
    description: 'LinkedIn Conversion API',
    credentials: [
      { field: 'conversion_id', label: 'Conversion Rule ID', placeholder: '', help: 'From Campaign Manager' },
      { field: 'access_token', label: 'Access Token', placeholder: '', help: 'OAuth 2.0 access token', sensitive: true },
    ],
  },
  {
    id: 'whatsapp',
    name: 'WhatsApp Business',
    logo: '/platforms/whatsapp.svg',
    color: 'bg-green-500',
    description: 'WhatsApp Business Cloud API',
    credentials: [
      { field: 'phone_number_id', label: 'Phone Number ID', placeholder: '1234567890123456', help: 'From WhatsApp Business Manager > Phone Numbers' },
      { field: 'business_account_id', label: 'Business Account ID', placeholder: '1234567890123456', help: 'WhatsApp Business Account ID from Meta Business Suite' },
      { field: 'access_token', label: 'Access Token', placeholder: 'EAABsbCS...', help: 'Permanent token from System User in Business Settings', sensitive: true },
      { field: 'webhook_verify_token', label: 'Webhook Verify Token', placeholder: 'your_verify_token', help: 'Custom token for webhook verification' },
    ],
  },
]

interface PlatformStatus {
  connected: boolean
  lastSync?: string
  eventsToday?: number
  matchQuality?: number
  account_name?: string
  last_sync_at?: string
}

interface SyncResult {
  platforms_synced: number
  total_campaigns: number
  total_metrics: number
  platform_results: Record<string, {
    success: boolean
    campaigns_synced?: number
    metrics_synced?: number
    error?: string
  }>
}

export function CAPISetup() {
  const { t } = useTranslation()
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null)
  const [credentials, setCredentials] = useState<Record<string, string>>({})
  const [connecting, setConnecting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null)
  const [platformStatuses, setPlatformStatuses] = useState<Record<string, PlatformStatus>>({})
  const [platformDetails, setPlatformDetails] = useState<Record<string, any>>({})
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showHelp, setShowHelp] = useState<string | null>(null)

  // Fetch platform statuses
  useEffect(() => {
    fetchStatuses()
  }, [])

  const getAuthHeaders = () => {
    const token = getAccessToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  const fetchStatuses = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/capi/platforms/status`, {
        headers: getAuthHeaders(),
      })
      const data = await response.json()
      if (data.success) {
        const statuses: Record<string, PlatformStatus> = {}
        // Handle both old and new response formats
        const connectedPlatforms = data.data.connected_platforms || {}
        const details = data.data.platform_details || {}

        Object.keys(connectedPlatforms).forEach(platform => {
          if (connectedPlatforms[platform]) {
            statuses[platform] = {
              connected: true,
              account_name: details[platform]?.account_name,
              last_sync_at: details[platform]?.last_sync_at,
            }
          }
        })

        setPlatformStatuses(statuses)
        setPlatformDetails(details)
      }
    } catch (err) {
      console.error('Failed to fetch statuses:', err)
    }
  }

  const handleSyncData = async (platform?: string) => {
    setSyncing(true)
    setError(null)
    setSyncResult(null)

    try {
      const url = platform
        ? `${API_BASE_URL}/api/v1/capi/platforms/sync?platform=${platform}&days_back=90`
        : `${API_BASE_URL}/api/v1/capi/platforms/sync?days_back=90`

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
      })

      const data = await response.json()

      if (data.success) {
        setSyncResult(data.data)
        setSuccess(`Synced ${data.data.total_campaigns} campaigns with ${data.data.total_metrics} daily metrics!`)
        // Refresh statuses to get updated last_sync_at
        await fetchStatuses()
      } else {
        setError(data.message || 'Sync failed')
      }
    } catch (err) {
      setError('Failed to sync data. Please try again.')
    } finally {
      setSyncing(false)
    }
  }

  const handleConnect = async () => {
    if (!selectedPlatform) return

    setConnecting(true)
    setError(null)
    setSuccess(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/capi/platforms/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({
          platform: selectedPlatform,
          credentials,
        }),
      })

      const data = await response.json()

      if (data.success) {
        setSuccess(`Successfully connected to ${PLATFORMS.find(p => p.id === selectedPlatform)?.name}!`)
        setPlatformStatuses(prev => ({
          ...prev,
          [selectedPlatform]: { connected: true },
        }))
        setCredentials({})
        setSelectedPlatform(null)
      } else {
        setError(data.data?.message || 'Connection failed')
      }
    } catch (err) {
      setError('Failed to connect. Please check your credentials.')
    } finally {
      setConnecting(false)
    }
  }

  const handleDisconnect = async (platform: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/capi/platforms/${platform}/disconnect`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
      })
      const data = await response.json()

      if (data.success) {
        setPlatformStatuses(prev => {
          const updated = { ...prev }
          delete updated[platform]
          return updated
        })
        setSuccess(`Disconnected from ${platform}`)
      }
    } catch (err) {
      console.error('Failed to disconnect:', err)
    }
  }

  const connectedCount = Object.keys(platformStatuses).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Conversion API Setup</h1>
          <p className="text-muted-foreground mt-1">
            Connect ad platforms to stream first-party data and boost ROAS by 30-50%
          </p>
        </div>
        <button
          onClick={fetchStatuses}
          className="flex items-center gap-2 px-4 py-2 bg-muted hover:bg-muted/80 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Benefits Banner */}
      <div className="bg-gradient-to-r from-primary/10 via-purple-500/10 to-pink-500/10 rounded-xl p-6 border">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-green-500/10 rounded-lg">
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">70-90% Match Rates</h3>
              <p className="text-sm text-muted-foreground">Up from 42% with client-side tracking</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Shield className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Privacy-Compliant</h3>
              <p className="text-sm text-muted-foreground">Auto SHA256 hashing of PII data</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <Zap className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">No Code Required</h3>
              <p className="text-sm text-muted-foreground">Just paste your API tokens</p>
            </div>
          </div>
        </div>
      </div>

      {/* Success/Error Messages */}
      {success && (
        <div className="flex items-center gap-3 p-4 bg-green-500/10 border border-green-500/20 rounded-lg text-green-600">
          <Check className="w-5 h-5" />
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="ml-auto">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Platform Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {PLATFORMS.map(platform => {
          const status = platformStatuses[platform.id]
          const isSelected = selectedPlatform === platform.id

          return (
            <div
              key={platform.id}
              className={cn(
                'relative rounded-xl border p-5 transition-all cursor-pointer',
                status?.connected
                  ? 'border-green-500/50 bg-green-500/5'
                  : isSelected
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50 hover:bg-muted/50'
              )}
              onClick={() => !status?.connected && setSelectedPlatform(isSelected ? null : platform.id)}
            >
              {/* Connection Status Badge */}
              {status?.connected && (
                <div className="absolute top-3 right-3 flex items-center gap-1 px-2 py-1 bg-green-500/10 rounded-full">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs font-medium text-green-600">Connected</span>
                </div>
              )}

              <div className="flex items-start gap-4">
                <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg', platform.color)}>
                  {platform.name.charAt(0)}
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-foreground">{platform.name}</h3>
                  <p className="text-sm text-muted-foreground">{platform.description}</p>
                </div>
              </div>

              {/* Credentials Form */}
              {isSelected && !status?.connected && (
                <div className="mt-4 pt-4 border-t space-y-3" onClick={e => e.stopPropagation()}>
                  {platform.credentials.map(cred => (
                    <div key={cred.field}>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-sm font-medium text-foreground">{cred.label}</label>
                        <button
                          onClick={() => setShowHelp(showHelp === cred.field ? null : cred.field)}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <HelpCircle className="w-4 h-4" />
                        </button>
                      </div>
                      {showHelp === cred.field && (
                        <p className="text-xs text-muted-foreground mb-2 bg-muted/50 p-2 rounded">
                          {cred.help}
                        </p>
                      )}
                      <input
                        type={cred.sensitive ? 'password' : 'text'}
                        placeholder={cred.placeholder}
                        value={credentials[cred.field] || ''}
                        onChange={e => setCredentials(prev => ({ ...prev, [cred.field]: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary"
                      />
                    </div>
                  ))}

                  <button
                    onClick={handleConnect}
                    disabled={connecting || platform.credentials.some(c => !credentials[c.field])}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {connecting ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" />
                        Connecting...
                      </>
                    ) : (
                      <>
                        <Plug className="w-4 h-4" />
                        Connect Platform
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Connected Actions */}
              {status?.connected && (
                <div className="mt-4 pt-4 border-t flex items-center justify-between" onClick={e => e.stopPropagation()}>
                  <div className="text-sm">
                    <span className="text-muted-foreground">Events today:</span>
                    <span className="ml-2 font-semibold text-foreground">{status.eventsToday || 0}</span>
                  </div>
                  <button
                    onClick={() => handleDisconnect(platform.id)}
                    className="text-sm text-red-500 hover:text-red-600 hover:underline"
                  >
                    Disconnect
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Data Sync Section - Only show when platforms are connected */}
      {connectedCount > 0 && (
        <div className="rounded-xl border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-foreground">Campaign Data Sync</h2>
              <p className="text-sm text-muted-foreground">
                Pull campaign data from connected platforms for ML training
              </p>
            </div>
            <button
              onClick={() => handleSyncData()}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {syncing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Syncing...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Sync All Platforms
                </>
              )}
            </button>
          </div>

          {/* Sync Results */}
          {syncResult && (
            <div className="mt-4 p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
              <div className="flex items-center gap-2 mb-3">
                <Database className="w-5 h-5 text-green-600" />
                <span className="font-semibold text-green-600">Sync Complete</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-500/10 rounded-lg">
                    <BarChart3 className="w-4 h-4 text-blue-500" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Campaigns</p>
                    <p className="font-semibold text-foreground">{syncResult.total_campaigns}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-500/10 rounded-lg">
                    <Database className="w-4 h-4 text-purple-500" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Daily Metrics</p>
                    <p className="font-semibold text-foreground">{syncResult.total_metrics}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-500/10 rounded-lg">
                    <Check className="w-4 h-4 text-green-500" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Platforms Synced</p>
                    <p className="font-semibold text-foreground">{syncResult.platforms_synced}</p>
                  </div>
                </div>
              </div>

              {/* Per-platform results */}
              {syncResult.platform_results && Object.keys(syncResult.platform_results).length > 0 && (
                <div className="mt-4 pt-4 border-t border-green-500/20">
                  <p className="text-sm font-medium text-foreground mb-2">Platform Details:</p>
                  <div className="space-y-2">
                    {Object.entries(syncResult.platform_results).map(([platform, result]) => (
                      <div key={platform} className="flex items-center justify-between text-sm">
                        <span className="capitalize text-foreground">{platform}</span>
                        {result.success ? (
                          <span className="text-green-600">
                            {result.campaigns_synced} campaigns, {result.metrics_synced} metrics
                          </span>
                        ) : (
                          <span className="text-red-500">{result.error}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Connected Platform Sync Status */}
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(platformStatuses).map(([platformId, status]) => {
              const platform = PLATFORMS.find(p => p.id === platformId)
              if (!platform || !status.connected) return null

              const details = platformDetails[platformId]

              return (
                <div
                  key={platformId}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold', platform.color)}>
                      {platform.name.charAt(0)}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{platform.name}</p>
                      {details?.account_name && (
                        <p className="text-xs text-muted-foreground">{details.account_name}</p>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    {details?.last_sync_at ? (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        <span>
                          {new Date(details.last_sync_at).toLocaleDateString()}
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">Never synced</span>
                    )}
                    <button
                      onClick={() => handleSyncData(platformId)}
                      disabled={syncing}
                      className="text-xs text-primary hover:underline disabled:opacity-50"
                    >
                      Sync Now
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Setup Progress */}
      <div className="rounded-xl border bg-card p-6">
        <h2 className="text-lg font-semibold text-foreground mb-4">Setup Progress</h2>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="h-3 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary to-green-500 transition-all duration-500"
                style={{ width: `${(connectedCount / PLATFORMS.length) * 100}%` }}
              />
            </div>
          </div>
          <div className="text-sm font-medium">
            <span className="text-primary">{connectedCount}</span>
            <span className="text-muted-foreground"> / {PLATFORMS.length} platforms</span>
          </div>
        </div>

        {connectedCount === 0 && (
          <p className="mt-4 text-sm text-muted-foreground">
            Connect at least one platform to start streaming conversion data
          </p>
        )}

        {connectedCount > 0 && connectedCount < PLATFORMS.length && (
          <p className="mt-4 text-sm text-muted-foreground">
            Connect more platforms to maximize your cross-channel attribution
          </p>
        )}

        {connectedCount === PLATFORMS.length && (
          <div className="mt-4 flex items-center gap-2 text-green-600">
            <Check className="w-5 h-5" />
            <span className="text-sm font-medium">All platforms connected!</span>
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <a
          href="/data-quality"
          className="flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <Settings className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="font-medium text-foreground">Data Quality Dashboard</h3>
              <p className="text-sm text-muted-foreground">View match quality scores and fix data gaps</p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-muted-foreground" />
        </a>

        <a
          href="https://developers.facebook.com/docs/marketing-api/conversions-api"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between p-4 rounded-xl border bg-card hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <ExternalLink className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <h3 className="font-medium text-foreground">Documentation</h3>
              <p className="text-sm text-muted-foreground">Learn more about Conversion APIs</p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-muted-foreground" />
        </a>
      </div>
    </div>
  )
}

export default CAPISetup
