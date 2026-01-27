/**
 * PlatformBreakdown - Platform performance breakdown display
 */

import { AlertTriangle, BarChart3, CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PlatformSummary } from '@/api/dashboard';

// Platform icon components/colors
const platformConfigs: Record<string, { color: string; bgColor: string }> = {
  google: { color: 'text-[#4285F4]', bgColor: 'bg-[#4285F4]/10' },
  meta: { color: 'text-[#0668E1]', bgColor: 'bg-[#0668E1]/10' },
  facebook: { color: 'text-[#1877F2]', bgColor: 'bg-[#1877F2]/10' },
  tiktok: { color: 'text-[#000000] dark:text-white', bgColor: 'bg-black/10 dark:bg-white/10' },
  snapchat: { color: 'text-[#FFFC00]', bgColor: 'bg-[#FFFC00]/10' },
  default: { color: 'text-muted-foreground', bgColor: 'bg-muted' },
};

interface PlatformBreakdownProps {
  platforms: PlatformSummary[];
  loading?: boolean;
}

export function PlatformBreakdown({ platforms, loading = false }: PlatformBreakdownProps) {
  if (loading) {
    return (
      <div className="bg-card border rounded-lg p-5 flex items-center justify-center min-h-[120px]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (platforms.length === 0) {
    return (
      <div className="bg-card border rounded-lg p-5 text-center text-muted-foreground">
        <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No platforms connected</p>
      </div>
    );
  }

  const totalSpend = platforms.reduce((sum, p) => sum + p.spend, 0);
  const totalRevenue = platforms.reduce((sum, p) => sum + p.revenue, 0);

  const getStatusIcon = (status: PlatformSummary['status']) => {
    switch (status) {
      case 'connected':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'disconnected':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatRoas = (roas: number | null) => {
    if (roas === null) return '-';
    return `${roas.toFixed(2)}x`;
  };

  const getPlatformConfig = (platform: string) => {
    const key = platform.toLowerCase();
    return platformConfigs[key] || platformConfigs.default;
  };

  return (
    <div className="bg-card border rounded-lg">
      <div className="flex items-center justify-between p-4 border-b">
        <h3 className="font-semibold">Platform Performance</h3>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>Total: {formatCurrency(totalSpend)} spend</span>
          <span className="text-green-500">{formatCurrency(totalRevenue)} revenue</span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 p-4">
          {platforms.map((platform) => {
            const config = getPlatformConfig(platform.platform);
            const spendPercentage = totalSpend > 0 ? (platform.spend / totalSpend) * 100 : 0;

            return (
              <div
                key={platform.platform}
                className="bg-background border rounded-lg p-4 relative overflow-hidden"
              >
                {/* Spend bar indicator */}
                <div
                  className={cn('absolute bottom-0 left-0 h-1 transition-all', config.bgColor)}
                  style={{ width: `${spendPercentage}%`, backgroundColor: 'currentColor' }}
                />

                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div
                      className={cn(
                        'w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold',
                        config.bgColor,
                        config.color
                      )}
                    >
                      {platform.platform.charAt(0).toUpperCase()}
                    </div>
                    <span className="font-medium capitalize">{platform.platform}</span>
                  </div>
                  {getStatusIcon(platform.status)}
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Spend</span>
                    <span className="font-medium">{formatCurrency(platform.spend)}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Revenue</span>
                    <span className="font-medium text-green-500">
                      {formatCurrency(platform.revenue)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">ROAS</span>
                    <span
                      className={cn(
                        'font-medium',
                        platform.roas !== null && platform.roas >= 3
                          ? 'text-green-500'
                          : platform.roas !== null && platform.roas >= 1
                            ? 'text-yellow-500'
                            : 'text-muted-foreground'
                      )}
                    >
                      {formatRoas(platform.roas)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Campaigns</span>
                    <span className="font-medium">{platform.campaigns_count}</span>
                  </div>
                </div>

                {platform.last_synced_at && (
                  <div className="mt-3 pt-2 border-t text-xs text-muted-foreground">
                    Synced {new Date(platform.last_synced_at).toLocaleTimeString()}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
