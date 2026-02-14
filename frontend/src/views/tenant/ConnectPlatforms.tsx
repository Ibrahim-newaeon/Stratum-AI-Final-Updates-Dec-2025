/**
 * Stratum AI - Connect Platforms Page
 *
 * OAuth connection management for advertising platforms.
 * Supports Meta, Google, TikTok, and Snapchat ad platforms.
 */

import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  LinkIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import {
  type Platform,
  useAdAccounts,
  useConnectorStatus,
  useDisconnectPlatform,
  useRefreshToken,
  useStartConnection,
} from '@/api/campaignBuilder';

interface PlatformConnection {
  id: string;
  name: string;
  logo: string;
  status: 'connected' | 'disconnected' | 'expired' | 'error';
  connectedAt?: string;
  expiresAt?: string;
  accountCount?: number;
}

const platforms: PlatformConnection[] = [
  {
    id: 'meta',
    name: 'Meta Ads',
    logo: '/platforms/meta.svg',
    status: 'connected',
    connectedAt: '2024-01-15',
    expiresAt: '2025-01-15',
    accountCount: 3,
  },
  {
    id: 'google',
    name: 'Google Ads',
    logo: '/platforms/google.svg',
    status: 'connected',
    connectedAt: '2024-02-10',
    expiresAt: '2025-02-10',
    accountCount: 2,
  },
  {
    id: 'tiktok',
    name: 'TikTok Ads',
    logo: '/platforms/tiktok.svg',
    status: 'disconnected',
  },
  {
    id: 'snapchat',
    name: 'Snapchat Ads',
    logo: '/platforms/snapchat.svg',
    status: 'disconnected',
  },
  {
    id: 'linkedin',
    name: 'LinkedIn Ads',
    logo: '/platforms/linkedin.svg',
    status: 'disconnected',
  },
];

// Connection health based on signal reliability
type ConnectionHealth = 'healthy' | 'degraded' | 'unhealthy';
const platformHealthMock: Record<string, { health: ConnectionHealth; emqScore: number; lastSync: string; dataVolume: string }> = {
  meta: { health: 'healthy', emqScore: 92, lastSync: '2 min ago', dataVolume: '12.4k events/day' },
  google: { health: 'healthy', emqScore: 88, lastSync: '5 min ago', dataVolume: '8.2k events/day' },
  tiktok: { health: 'degraded', emqScore: 0, lastSync: 'Never', dataVolume: '0 events' },
  snapchat: { health: 'unhealthy', emqScore: 0, lastSync: 'Never', dataVolume: '0 events' },
  linkedin: { health: 'unhealthy', emqScore: 0, lastSync: 'Never', dataVolume: '0 events' },
};

const healthDotColor: Record<ConnectionHealth, string> = {
  healthy: 'bg-green-500',
  degraded: 'bg-amber-500',
  unhealthy: 'bg-gray-500',
};

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
};

export default function ConnectPlatforms() {
  const { tenantId } = useParams<{ tenantId: string }>();
  const tid = parseInt(tenantId || '1', 10);
  const [connecting, setConnecting] = useState<string | null>(null);

  // API hooks for connector status
  const { data: metaStatus } = useConnectorStatus(tid, 'meta');
  const { data: googleStatus } = useConnectorStatus(tid, 'google');
  const { data: tiktokStatus } = useConnectorStatus(tid, 'tiktok');
  const { data: snapchatStatus } = useConnectorStatus(tid, 'snapchat');

  // API hooks for ad account counts
  const { data: metaAccounts } = useAdAccounts(tid, 'meta');
  const { data: googleAccounts } = useAdAccounts(tid, 'google');
  const { data: tiktokAccounts } = useAdAccounts(tid, 'tiktok');
  const { data: snapchatAccounts } = useAdAccounts(tid, 'snapchat');

  // Mutation hooks
  const startConnection = useStartConnection(tid);
  const refreshToken = useRefreshToken(tid);
  const disconnectPlatform = useDisconnectPlatform(tid);

  // Build platforms with API data or fallback to mock
  const platformsWithStatus: PlatformConnection[] = useMemo(() => {
    const statusMap: Record<string, typeof metaStatus> = {
      meta: metaStatus,
      google: googleStatus,
      tiktok: tiktokStatus,
      snapchat: snapchatStatus,
    };
    const accountsMap: Record<string, typeof metaAccounts> = {
      meta: metaAccounts,
      google: googleAccounts,
      tiktok: tiktokAccounts,
      snapchat: snapchatAccounts,
    };

    return platforms.map((p) => {
      const apiStatus = statusMap[p.id];
      const accounts = accountsMap[p.id];

      if (apiStatus) {
        return {
          ...p,
          status: apiStatus.status as PlatformConnection['status'],
          connectedAt: apiStatus.connected_at?.split('T')[0],
          accountCount: accounts?.length ?? 0,
        };
      }
      return p;
    });
  }, [
    metaStatus,
    googleStatus,
    tiktokStatus,
    snapchatStatus,
    metaAccounts,
    googleAccounts,
    tiktokAccounts,
    snapchatAccounts,
  ]);

  const handleConnect = async (platformId: string) => {
    setConnecting(platformId);
    try {
      const result = await startConnection.mutateAsync(platformId as Platform);
      // Redirect to OAuth URL
      if (result.oauth_url) {
        window.location.href = result.oauth_url;
      }
    } catch (error) {
      // Error - falling back to demo mode
      // Fallback for demo mode
      alert(`OAuth flow would start for ${platformId}`);
    } finally {
      setConnecting(null);
    }
  };

  const handleDisconnect = async (platformId: string) => {
    if (confirm('Are you sure you want to disconnect this platform?')) {
      try {
        await disconnectPlatform.mutateAsync(platformId as Platform);
      } catch (error) {
        // Error - falling back to demo mode
        alert(`Disconnected ${platformId} (demo mode)`);
      }
    }
  };

  const handleRefresh = async (platformId: string) => {
    try {
      await refreshToken.mutateAsync(platformId as Platform);
      alert('Token refreshed successfully');
    } catch (error) {
      // Error - falling back to demo mode
      alert(`Refreshing token for ${platformId} (demo mode)`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Connect Platforms</h1>
        <p className="text-muted-foreground">
          Connect your advertising accounts via OAuth to manage campaigns and access ad accounts
        </p>
        <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
          <ExclamationTriangleIcon className="w-3 h-3" />
          <span>
            This grants access to <strong>ad accounts & campaigns</strong>. For server-side
            conversion tracking (CAPI), go to{' '}
            <a href="/dashboard/capi-setup" className="text-primary hover:underline">
              CAPI Setup
            </a>
          </span>
        </p>
      </div>

      {/* Platform Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {platformsWithStatus.map((platform) => {
          const status = statusConfig[platform.status];
          const StatusIcon = status.icon;

          return (
            <div
              key={platform.id}
              className={cn(
                'rounded-xl border p-6 transition-all',
                platform.status === 'connected' ? 'bg-card shadow-card' : 'bg-muted/30'
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  {/* Platform logo placeholder */}
                  <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 flex items-center justify-center">
                    <span className="text-lg font-bold text-gray-600 dark:text-gray-300">
                      {platform.name.charAt(0)}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-semibold">{platform.name}</h3>
                    <div className={cn('flex items-center gap-1 text-sm', status.color)}>
                      <StatusIcon className="h-4 w-4" />
                      <span>{status.label}</span>
                    </div>
                  </div>
                </div>
                {/* Health indicator */}
                {platform.status === 'connected' && platformHealthMock[platform.id] && (
                  <div className="flex items-center gap-2">
                    <span className={cn('h-2.5 w-2.5 rounded-full', healthDotColor[platformHealthMock[platform.id].health])} />
                    <span className="text-xs text-muted-foreground capitalize">{platformHealthMock[platform.id].health}</span>
                    {platformHealthMock[platform.id].emqScore > 0 && (
                      <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                        EMQ {platformHealthMock[platform.id].emqScore}%
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Connection details */}
              {platform.status === 'connected' && (
                <div className="mt-4 pt-4 border-t space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Connected Accounts</span>
                    <span className="font-medium">{platform.accountCount}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Connected On</span>
                    <span className="font-medium">{platform.connectedAt}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Token Expires</span>
                    <span className="font-medium">{platform.expiresAt}</span>
                  </div>
                  {platformHealthMock[platform.id] && (
                    <>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Last Sync</span>
                        <span className="font-medium">{platformHealthMock[platform.id].lastSync}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground">Data Volume</span>
                        <span className="font-medium">{platformHealthMock[platform.id].dataVolume}</span>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="mt-4 flex gap-2">
                {platform.status === 'connected' ? (
                  <>
                    <button
                      onClick={() => handleRefresh(platform.id)}
                      className="flex items-center gap-2 px-3 py-2 text-sm rounded-lg border hover:bg-accent transition-colors"
                    >
                      <ArrowPathIcon className="h-4 w-4" />
                      Refresh Token
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
                    Connect {platform.name}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* OAuth Information */}
      <div className="rounded-xl border bg-muted/30 p-6">
        <h3 className="font-semibold mb-2">About Platform Connections</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>- OAuth tokens are securely stored and automatically refreshed</li>
          <li>- Connections grant access to view and manage ad accounts</li>
          <li>- You can disconnect at any time from platform settings</li>
          <li>- Campaign Builder requires at least one connected platform</li>
        </ul>
      </div>
    </div>
  );
}
