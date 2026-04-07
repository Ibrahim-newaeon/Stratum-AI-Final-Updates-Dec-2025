/**
 * ConnectorStatusCard - Platform connector with health indicators
 *
 * Displays platform connection status with health dot,
 * sync timestamp, data volume, and refresh action.
 * Used in ConnectPlatforms enhancement.
 */

import { cn } from '@/lib/utils';
import { ArrowPathIcon, LinkIcon, SignalIcon } from '@heroicons/react/24/outline';

type ConnectionHealth = 'healthy' | 'degraded' | 'unhealthy' | 'disconnected';

interface ConnectorStatusCardProps {
  platform: string;
  platformIcon?: React.ReactNode;
  status: 'connected' | 'disconnected' | 'expired' | 'error';
  health: ConnectionHealth;
  lastSync?: string;
  dataVolume?: string;
  emqScore?: number;
  onRefresh?: () => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

const healthConfig: Record<ConnectionHealth, { color: string; bg: string; label: string }> = {
  healthy: { color: 'bg-green-500', bg: 'bg-green-500/10', label: 'Healthy' },
  degraded: { color: 'bg-amber-500', bg: 'bg-amber-500/10', label: 'Degraded' },
  unhealthy: { color: 'bg-red-500', bg: 'bg-red-500/10', label: 'Unhealthy' },
  disconnected: { color: 'bg-gray-500', bg: 'bg-gray-500/10', label: 'Disconnected' },
};

export function ConnectorStatusCard({
  platform,
  platformIcon,
  status,
  health,
  lastSync,
  dataVolume,
  emqScore,
  onRefresh,
  onConnect,
  onDisconnect,
}: ConnectorStatusCardProps) {
  const hc = healthConfig[health];
  const isConnected = status === 'connected';

  return (
    <div
      className={cn(
        'rounded-xl border p-5 transition-all',
        isConnected ? 'bg-card shadow-card' : 'bg-muted/30'
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 flex items-center justify-center">
            {platformIcon || (
              <span className="text-sm font-bold text-gray-600 dark:text-gray-300">
                {platform.charAt(0)}
              </span>
            )}
          </div>
          <div>
            <h3 className="font-semibold">{platform}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={cn('h-2 w-2 rounded-full', hc.color)} />
              <span className="text-xs text-muted-foreground">{hc.label}</span>
            </div>
          </div>
        </div>
        {isConnected && emqScore !== undefined && (
          <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-white/5">
            <SignalIcon className="h-3.5 w-3.5 text-primary" />
            <span className="text-xs font-medium">EMQ {emqScore}%</span>
          </div>
        )}
      </div>

      {/* Stats */}
      {isConnected && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="p-2.5 rounded-lg bg-white/5">
            <p className="text-xs text-muted-foreground">Last Sync</p>
            <p className="text-sm font-medium">{lastSync || 'Never'}</p>
          </div>
          <div className="p-2.5 rounded-lg bg-white/5">
            <p className="text-xs text-muted-foreground">Data Volume</p>
            <p className="text-sm font-medium">{dataVolume || '0 events'}</p>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {isConnected ? (
          <>
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-white/10 hover:bg-white/5 transition-colors"
              >
                <ArrowPathIcon className="h-4 w-4" />
                Sync Now
              </button>
            )}
            {onDisconnect && (
              <button
                onClick={onDisconnect}
                className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
              >
                Disconnect
              </button>
            )}
          </>
        ) : (
          onConnect && (
            <button
              onClick={onConnect}
              className="flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
            >
              <LinkIcon className="h-4 w-4" />
              Connect {platform}
            </button>
          )
        )}
      </div>
    </div>
  );
}

export default ConnectorStatusCard;
