/**
 * CampaignPerformanceTable - Top campaigns performance display
 */

import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BarChart3,
  Loader2,
  Minus,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { usePriceMetrics } from '@/hooks/usePriceMetrics';
import type { CampaignSummaryItem, TrendDirection } from '@/api/dashboard';

interface CampaignPerformanceTableProps {
  campaigns: CampaignSummaryItem[];
  loading?: boolean;
  onViewAll?: () => void;
}

export function CampaignPerformanceTable({
  campaigns,
  loading = false,
  onViewAll,
}: CampaignPerformanceTableProps) {
  const { showPriceMetrics } = usePriceMetrics();
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

  const getTrendIcon = (trend: TrendDirection) => {
    switch (trend) {
      case 'up':
        return <ArrowUp className="w-3 h-3 text-green-500" />;
      case 'down':
        return <ArrowDown className="w-3 h-3 text-red-500" />;
      case 'stable':
        return <Minus className="w-3 h-3 text-muted-foreground" />;
      default:
        return null;
    }
  };

  const getScalingScoreColor = (score: number | null) => {
    if (score === null) return 'text-muted-foreground';
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getStatusBadge = (status: string) => {
    const statusLower = status.toLowerCase();
    if (statusLower === 'active' || statusLower === 'enabled') {
      return (
        <span className="text-xs px-2 py-0.5 bg-green-500/10 text-green-500 rounded-full font-medium">
          Active
        </span>
      );
    }
    if (statusLower === 'paused') {
      return (
        <span className="text-xs px-2 py-0.5 bg-yellow-500/10 text-yellow-500 rounded-full font-medium">
          Paused
        </span>
      );
    }
    return (
      <span className="text-xs px-2 py-0.5 bg-muted text-muted-foreground rounded-full font-medium">
        {status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="bg-card border rounded-lg p-5 flex items-center justify-center min-h-[300px]">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="bg-card border rounded-lg">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Top Campaigns</h3>
        </div>
        {onViewAll && (
          <button
            onClick={onViewAll}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          >
            View all
            <ArrowRight className="w-3 h-3" />
          </button>
        )}
      </div>

      {campaigns.length === 0 ? (
        <div className="p-8 text-center text-muted-foreground">
          <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No campaigns to display</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="p-3 font-medium">Campaign</th>
                <th className="p-3 font-medium">Platform</th>
                <th className="p-3 font-medium">Status</th>
                {showPriceMetrics && <th className="p-3 font-medium text-right">Spend</th>}
                {showPriceMetrics && <th className="p-3 font-medium text-right">Revenue</th>}
                {showPriceMetrics && <th className="p-3 font-medium text-right">ROAS</th>}
                <th className="p-3 font-medium text-right">Conv.</th>
                <th className="p-3 font-medium text-center">Score</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {campaigns.map((campaign) => (
                <tr key={campaign.id} className="hover:bg-muted/50 transition-colors">
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      {getTrendIcon(campaign.trend)}
                      <div className="min-w-0">
                        <div className="font-medium truncate max-w-[200px]" title={campaign.name}>
                          {campaign.name}
                        </div>
                        {campaign.recommendation && (
                          <div className="text-xs text-primary truncate max-w-[200px]">
                            {campaign.recommendation}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="p-3">
                    <span className="text-sm capitalize">{campaign.platform}</span>
                  </td>
                  <td className="p-3">{getStatusBadge(campaign.status)}</td>
                  {showPriceMetrics && (
                    <td className="p-3 text-right text-sm font-medium">
                      {formatCurrency(campaign.spend)}
                    </td>
                  )}
                  {showPriceMetrics && (
                    <td className="p-3 text-right text-sm font-medium text-green-500">
                      {formatCurrency(campaign.revenue)}
                    </td>
                  )}
                  {showPriceMetrics && (
                    <td className="p-3 text-right">
                      <span
                        className={cn(
                          'text-sm font-medium',
                          campaign.roas !== null && campaign.roas >= 3
                            ? 'text-green-500'
                            : campaign.roas !== null && campaign.roas >= 1
                              ? 'text-yellow-500'
                              : 'text-muted-foreground'
                        )}
                      >
                        {formatRoas(campaign.roas)}
                      </span>
                    </td>
                  )}
                  <td className="p-3 text-right text-sm font-medium">
                    {campaign.conversions.toLocaleString()}
                  </td>
                  <td className="p-3 text-center">
                    <span
                      className={cn(
                        'text-sm font-bold',
                        getScalingScoreColor(campaign.scaling_score)
                      )}
                    >
                      {campaign.scaling_score !== null ? campaign.scaling_score : '-'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
