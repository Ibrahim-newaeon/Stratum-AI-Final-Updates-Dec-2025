/**
 * PlatformBreakdown - Platform performance breakdown display
 */

import { AlertTriangle, BarChart3, CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PlatformSummary } from '@/api/dashboard';

// Platform icon components/colors with brand-dominant styling
const platformConfigs: Record<string, {
  color: string;
  bgColor: string;
  brandHex: string;
  borderColor: string;
  gradientBg: string;
}> = {
  google: {
    color: 'text-[#4285F4]', bgColor: 'bg-[#4285F4]/10',
    brandHex: '#4285F4',
    borderColor: 'border-[#4285F4]/25',
    gradientBg: 'linear-gradient(135deg, rgba(66,133,244,0.08), rgba(66,133,244,0.02))',
  },
  meta: {
    color: 'text-[#0866FF]', bgColor: 'bg-[#0866FF]/10',
    brandHex: '#0866FF',
    borderColor: 'border-[#0866FF]/25',
    gradientBg: 'linear-gradient(135deg, rgba(8,102,255,0.08), rgba(8,102,255,0.02))',
  },
  facebook: {
    color: 'text-[#1877F2]', bgColor: 'bg-[#1877F2]/10',
    brandHex: '#1877F2',
    borderColor: 'border-[#1877F2]/25',
    gradientBg: 'linear-gradient(135deg, rgba(24,119,242,0.08), rgba(24,119,242,0.02))',
  },
  tiktok: {
    color: 'text-[#00F2EA]', bgColor: 'bg-[#00F2EA]/10',
    brandHex: '#00F2EA',
    borderColor: 'border-[#00F2EA]/25',
    gradientBg: 'linear-gradient(135deg, rgba(0,242,234,0.08), rgba(0,242,234,0.02))',
  },
  snapchat: {
    color: 'text-[#FFFC00]', bgColor: 'bg-[#FFFC00]/10',
    brandHex: '#FFFC00',
    borderColor: 'border-[#FFFC00]/25',
    gradientBg: 'linear-gradient(135deg, rgba(255,252,0,0.08), rgba(255,252,0,0.02))',
  },
  mercedes: {
    color: 'text-[#A0A0A0]', bgColor: 'bg-[#A0A0A0]/10',
    brandHex: '#A0A0A0',
    borderColor: 'border-[#A0A0A0]/25',
    gradientBg: 'linear-gradient(135deg, rgba(160,160,160,0.08), rgba(160,160,160,0.02))',
  },
  default: {
    color: 'text-muted-foreground', bgColor: 'bg-muted',
    brandHex: '#6B7280',
    borderColor: 'border-white/10',
    gradientBg: 'linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))',
  },
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
        return <CheckCircle2 className="w-4 h-4 text-[#00c7be]" />;
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'disconnected':
        return <XCircle className="w-4 h-4 text-[#ff6b6b]" />;
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
          <span className="text-[#00c7be]">{formatCurrency(totalRevenue)} revenue</span>
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
                className={cn(
                  'rounded-lg p-4 relative overflow-hidden backdrop-blur-md',
                  'border transition-all duration-200',
                  config.borderColor
                )}
                style={{
                  background: config.gradientBg,
                  boxShadow: 'inset 0 1px 1px rgba(255,255,255,0.08), 0 2px 12px rgba(0,0,0,0.15)',
                }}
              >
                {/* Brand accent top bar */}
                <div
                  className="absolute top-0 left-0 right-0 h-[3px] rounded-t-lg"
                  style={{ background: config.brandHex }}
                />
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
                    <span className="font-medium text-[#00c7be]">
                      {formatCurrency(platform.revenue)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">ROAS</span>
                    <span
                      className={cn(
                        'font-medium',
                        platform.roas !== null && platform.roas >= 3
                          ? 'text-[#00c7be]'
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
