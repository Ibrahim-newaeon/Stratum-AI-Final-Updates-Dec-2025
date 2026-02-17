/**
 * Stratum AI - Ad Accounts Management Page
 *
 * View and manage ad accounts from connected platforms.
 * Enable/disable accounts for campaign publishing.
 */

import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import {
  BuildingStorefrontIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import {
  useAdAccounts,
  useSyncAdAccounts,
  useUpdateAdAccount,
  type Platform,
} from '@/api/campaignBuilder'

interface AdAccount {
  id: string
  platformAccountId: string
  name: string
  platform: 'meta' | 'google' | 'tiktok' | 'snapchat'
  currency: string
  timezone: string
  enabled: boolean
  spendCap?: number
  lastSyncAt: string
}

const platformLabels = {
  meta: 'Meta Ads',
  google: 'Google Ads',
  tiktok: 'TikTok Ads',
  snapchat: 'Snapchat Ads',
}

export default function AdAccounts() {
  const { tenantId } = useParams<{ tenantId: string }>()
  const tid = parseInt(tenantId || '1', 10)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>('meta')

  // API hooks for all platforms
  const { data: metaAccounts } = useAdAccounts(tid, 'meta')
  const { data: googleAccounts } = useAdAccounts(tid, 'google')
  const { data: tiktokAccounts } = useAdAccounts(tid, 'tiktok')
  const { data: snapchatAccounts } = useAdAccounts(tid, 'snapchat')
  const syncAccounts = useSyncAdAccounts(tid)
  const updateAccount = useUpdateAdAccount(tid)

  // Combine all accounts from API (no mock fallback)
  const accounts: AdAccount[] = useMemo(() => {
    return [
      ...(metaAccounts || []),
      ...(googleAccounts || []),
      ...(tiktokAccounts || []),
      ...(snapchatAccounts || []),
    ].map((acc) => ({
      id: acc.id,
      platformAccountId: acc.platform_account_id,
      name: acc.name,
      platform: acc.platform as AdAccount['platform'],
      currency: acc.currency,
      timezone: acc.timezone,
      enabled: acc.is_enabled,
      spendCap: acc.daily_budget_cap,
      lastSyncAt: acc.last_synced_at || new Date().toISOString(),
    }))
  }, [metaAccounts, googleAccounts, tiktokAccounts, snapchatAccounts])

  const handleToggleAccount = async (account: AdAccount) => {
    try {
      await updateAccount.mutateAsync({
        platform: account.platform as Platform,
        accountId: account.id,
        data: { is_enabled: !account.enabled },
      })
    } catch (error) {
      console.error('Failed to toggle account:', error)
      // Fallback: local state update for demo mode
    }
  }

  const handleSyncAccounts = async () => {
    try {
      // Sync all platforms
      await Promise.all([
        syncAccounts.mutateAsync('meta'),
        syncAccounts.mutateAsync('google'),
        syncAccounts.mutateAsync('tiktok'),
        syncAccounts.mutateAsync('snapchat'),
      ])
    } catch (error) {
      console.error('Failed to sync accounts:', error)
    }
  }

  const filteredAccounts = accounts.filter(acc =>
    acc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    acc.platformAccountId.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const enabledCount = accounts.filter(acc => acc.enabled).length
  const syncing = syncAccounts.isPending

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Ad Accounts</h1>
          <p className="text-muted-foreground">
            {enabledCount} of {accounts.length} accounts enabled for publishing
          </p>
        </div>
        <button
          onClick={handleSyncAccounts}
          disabled={syncing}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-accent transition-colors disabled:opacity-50"
        >
          <ArrowPathIcon className={cn('h-5 w-5', syncing && 'animate-spin')} />
          Sync Accounts
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search accounts..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
      </div>

      {/* Accounts List */}
      <div className="space-y-4">
        {filteredAccounts.map((account) => (
          <div
            key={account.id}
            className={cn(
              'rounded-xl border p-6 transition-all',
              account.enabled ? 'bg-card shadow-card' : 'bg-muted/30'
            )}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-4">
                <div className={cn(
                  'h-12 w-12 rounded-lg flex items-center justify-center',
                  account.enabled ? 'bg-primary/10' : 'bg-muted'
                )}>
                  <BuildingStorefrontIcon className={cn(
                    'h-6 w-6',
                    account.enabled ? 'text-primary' : 'text-muted-foreground'
                  )} />
                </div>
                <div>
                  <h3 className="font-semibold">{account.name}</h3>
                  <p className="text-sm text-muted-foreground">
                    {platformLabels[account.platform]} - {account.platformAccountId}
                  </p>
                </div>
              </div>

              <button
                onClick={() => handleToggleAccount(account)}
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                  account.enabled
                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                )}
              >
                {account.enabled ? (
                  <>
                    <CheckCircleIcon className="h-4 w-4" />
                    Enabled
                  </>
                ) : (
                  <>
                    <XCircleIcon className="h-4 w-4" />
                    Disabled
                  </>
                )}
              </button>
            </div>

            {/* Account Details */}
            <div className="mt-4 pt-4 border-t grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Currency</p>
                <p className="font-medium">{account.currency}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Timezone</p>
                <p className="font-medium">{account.timezone}</p>
              </div>
              {account.spendCap && (
                <div>
                  <p className="text-xs text-muted-foreground">Spend Cap</p>
                  <p className="font-medium">{account.currency} {account.spendCap.toLocaleString()}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-muted-foreground">Last Synced</p>
                <p className="font-medium">
                  {new Date(account.lastSyncAt).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredAccounts.length === 0 && (
        <div className="rounded-xl border bg-muted/30 p-12 text-center">
          <BuildingStorefrontIcon className="h-12 w-12 mx-auto text-muted-foreground" />
          <h3 className="mt-4 font-semibold">No Ad Accounts Found</h3>
          <p className="text-muted-foreground mt-2">
            Connect a platform first to see available ad accounts
          </p>
        </div>
      )}

      {/* Info Box */}
      <div className="rounded-xl border bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800 p-6">
        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
          About Ad Account Management
        </h3>
        <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-200">
          <li>- Only enabled accounts can be selected for campaign publishing</li>
          <li>- Accounts are synced automatically every 6 hours</li>
          <li>- Spend caps are pulled from platform settings</li>
          <li>- Budget guardrails will respect account spend caps</li>
        </ul>
      </div>
    </div>
  )
}
