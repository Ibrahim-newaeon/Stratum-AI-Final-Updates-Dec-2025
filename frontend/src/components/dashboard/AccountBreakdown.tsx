/**
 * Account Breakdown Component
 *
 * Displays performance metrics grouped by ad account.
 * Supports filtering by platform and shows account-level KPIs,
 * signal health status, and pacing indicators.
 */

import React, { useState, useMemo } from 'react';
import { useAccountBreakdown, useAccountSignalHealth } from '@/api/dashboard';
import { cn } from '@/lib/utils';
import {
  ChevronDown,
  ChevronUp,
  Activity,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Layers,
} from 'lucide-react';

// Platform icon/color mapping
const PLATFORM_CONFIG: Record<string, { color: string; label: string }> = {
  meta: { color: 'text-blue-400', label: 'Meta' },
  google: { color: 'text-yellow-400', label: 'Google' },
  tiktok: { color: 'text-pink-400', label: 'TikTok' },
  snapchat: { color: 'text-amber-300', label: 'Snapchat' },
};

const STATUS_CONFIG: Record<string, { color: string; bgColor: string; icon: React.ReactNode }> = {
  ok: { color: 'text-emerald-400', bgColor: 'bg-emerald-400/10', icon: <CheckCircle className="w-4 h-4" /> },
  risk: { color: 'text-yellow-400', bgColor: 'bg-yellow-400/10', icon: <AlertTriangle className="w-4 h-4" /> },
  degraded: { color: 'text-orange-400', bgColor: 'bg-orange-400/10', icon: <AlertTriangle className="w-4 h-4" /> },
  critical: { color: 'text-red-400', bgColor: 'bg-red-400/10', icon: <XCircle className="w-4 h-4" /> },
};

type SortField = 'spend' | 'revenue' | 'roas' | 'conversions' | 'campaign_count';
type SortDir = 'asc' | 'desc';

interface AccountBreakdownProps {
  tenantId: number;
  className?: string;
}

const formatCurrency = (value: number): string => {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toFixed(2)}`;
};

const formatNumber = (value: number): string => {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString();
};

export const AccountBreakdown: React.FC<AccountBreakdownProps> = ({
  tenantId,
  className,
}) => {
  const [platformFilter, setPlatformFilter] = useState<string | undefined>();
  const [sortField, setSortField] = useState<SortField>('spend');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [expandedAccount, setExpandedAccount] = useState<string | null>(null);

  const { data: accounts, isLoading, error } = useAccountBreakdown(platformFilter);
  const { data: signalHealth } = useAccountSignalHealth(tenantId, platformFilter);

  // Build signal health lookup
  const healthLookup = useMemo(() => {
    if (!signalHealth?.accounts) return {};
    const map: Record<string, (typeof signalHealth.accounts)[0]> = {};
    for (const account of signalHealth.accounts) {
      map[account.account_id] = account;
    }
    return map;
  }, [signalHealth]);

  // Sort accounts
  const sortedAccounts = useMemo(() => {
    if (!accounts) return [];
    return [...accounts].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      return sortDir === 'desc' ? (bVal as number) - (aVal as number) : (aVal as number) - (bVal as number);
    });
  }, [accounts, sortField, sortDir]);

  // Aggregate totals
  const totals = useMemo(() => {
    if (!accounts) return null;
    return accounts.reduce(
      (acc, item) => ({
        spend: acc.spend + item.spend,
        revenue: acc.revenue + item.revenue,
        impressions: acc.impressions + item.impressions,
        clicks: acc.clicks + item.clicks,
        conversions: acc.conversions + item.conversions,
        campaigns: acc.campaigns + item.campaign_count,
      }),
      { spend: 0, revenue: 0, impressions: 0, clicks: 0, conversions: 0, campaigns: 0 },
    );
  }, [accounts]);

  // Get unique platforms
  const platforms = useMemo(() => {
    if (!accounts) return [];
    return [...new Set(accounts.map((a) => a.platform))];
  }, [accounts]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortDir === 'desc' ? (
      <ChevronDown className="w-3 h-3 inline ml-1" />
    ) : (
      <ChevronUp className="w-3 h-3 inline ml-1" />
    );
  };

  if (error) {
    return (
      <div className={cn('rounded-xl border border-red-500/20 bg-card p-6', className)}>
        <p className="text-red-400 text-sm">Failed to load account breakdown</p>
      </div>
    );
  }

  return (
    <div className={cn('rounded-xl border bg-card overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10">
            <Layers className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-foreground">Account Breakdown</h3>
            <p className="text-sm text-muted-foreground">
              Performance by ad account
              {totals && ` \u2022 ${sortedAccounts.length} accounts, ${totals.campaigns} campaigns`}
            </p>
          </div>
        </div>

        {/* Platform filter */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPlatformFilter(undefined)}
            className={cn(
              'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
              !platformFilter
                ? 'bg-primary/20 text-primary border border-primary/30'
                : 'bg-muted/50 text-muted-foreground hover:bg-muted',
            )}
          >
            All
          </button>
          {platforms.map((p) => {
            const config = PLATFORM_CONFIG[p] || { color: 'text-gray-400', label: p };
            return (
              <button
                key={p}
                onClick={() => setPlatformFilter(platformFilter === p ? undefined : p)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                  platformFilter === p
                    ? 'bg-primary/20 text-primary border border-primary/30'
                    : 'bg-muted/50 text-muted-foreground hover:bg-muted',
                )}
              >
                {config.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Summary tiles */}
      {totals && (
        <div className="grid grid-cols-4 gap-px bg-border/30">
          <div className="bg-card p-4 text-center">
            <p className="text-xs text-muted-foreground mb-1">Total Spend</p>
            <p className="text-lg font-bold text-foreground">{formatCurrency(totals.spend)}</p>
          </div>
          <div className="bg-card p-4 text-center">
            <p className="text-xs text-muted-foreground mb-1">Total Revenue</p>
            <p className="text-lg font-bold text-foreground">{formatCurrency(totals.revenue)}</p>
          </div>
          <div className="bg-card p-4 text-center">
            <p className="text-xs text-muted-foreground mb-1">Blended ROAS</p>
            <p className="text-lg font-bold text-foreground">
              {totals.spend > 0 ? (totals.revenue / totals.spend).toFixed(2) : '0.00'}x
            </p>
          </div>
          <div className="bg-card p-4 text-center">
            <p className="text-xs text-muted-foreground mb-1">Total Conversions</p>
            <p className="text-lg font-bold text-foreground">{formatNumber(totals.conversions)}</p>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-muted-foreground mt-2">Loading accounts...</p>
          </div>
        ) : sortedAccounts.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-muted-foreground">No account data available</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-border/50 text-xs text-muted-foreground">
                <th className="text-left p-3 pl-6 font-medium">Account</th>
                <th className="text-left p-3 font-medium">Platform</th>
                <th className="text-left p-3 font-medium">Signal</th>
                <th
                  className="text-right p-3 font-medium cursor-pointer hover:text-foreground"
                  onClick={() => handleSort('spend')}
                >
                  Spend <SortIcon field="spend" />
                </th>
                <th
                  className="text-right p-3 font-medium cursor-pointer hover:text-foreground"
                  onClick={() => handleSort('revenue')}
                >
                  Revenue <SortIcon field="revenue" />
                </th>
                <th
                  className="text-right p-3 font-medium cursor-pointer hover:text-foreground"
                  onClick={() => handleSort('roas')}
                >
                  ROAS <SortIcon field="roas" />
                </th>
                <th
                  className="text-right p-3 font-medium cursor-pointer hover:text-foreground"
                  onClick={() => handleSort('conversions')}
                >
                  Conv. <SortIcon field="conversions" />
                </th>
                <th
                  className="text-right p-3 pr-6 font-medium cursor-pointer hover:text-foreground"
                  onClick={() => handleSort('campaign_count')}
                >
                  Campaigns <SortIcon field="campaign_count" />
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedAccounts.map((account) => {
                const platformCfg = PLATFORM_CONFIG[account.platform] || {
                  color: 'text-gray-400',
                  label: account.platform,
                };
                const health = healthLookup[account.account_id];
                const statusCfg = health ? STATUS_CONFIG[health.status] || STATUS_CONFIG.ok : null;
                const isExpanded = expandedAccount === account.account_id;

                return (
                  <React.Fragment key={`${account.platform}-${account.account_id}`}>
                    <tr
                      className={cn(
                        'border-b border-border/30 hover:bg-muted/30 transition-colors cursor-pointer',
                        isExpanded && 'bg-muted/20',
                      )}
                      onClick={() =>
                        setExpandedAccount(isExpanded ? null : account.account_id)
                      }
                    >
                      <td className="p-3 pl-6">
                        <div>
                          <p className="text-sm font-medium text-foreground">
                            {account.account_name}
                          </p>
                          {account.business_name && (
                            <p className="text-xs text-muted-foreground">
                              {account.business_name}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="p-3">
                        <span className={cn('text-sm font-medium', platformCfg.color)}>
                          {platformCfg.label}
                        </span>
                      </td>
                      <td className="p-3">
                        {statusCfg ? (
                          <span
                            className={cn(
                              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                              statusCfg.color,
                              statusCfg.bgColor,
                            )}
                          >
                            {statusCfg.icon}
                            {health?.status || 'ok'}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">--</span>
                        )}
                      </td>
                      <td className="p-3 text-right text-sm tabular-nums text-foreground">
                        {formatCurrency(account.spend)}
                      </td>
                      <td className="p-3 text-right text-sm tabular-nums text-foreground">
                        {formatCurrency(account.revenue)}
                      </td>
                      <td className="p-3 text-right text-sm tabular-nums">
                        <span
                          className={cn(
                            'font-medium',
                            account.roas >= 3
                              ? 'text-emerald-400'
                              : account.roas >= 1.5
                              ? 'text-yellow-400'
                              : 'text-red-400',
                          )}
                        >
                          {account.roas.toFixed(2)}x
                        </span>
                      </td>
                      <td className="p-3 text-right text-sm tabular-nums text-foreground">
                        {formatNumber(account.conversions)}
                      </td>
                      <td className="p-3 pr-6 text-right text-sm tabular-nums text-muted-foreground">
                        {account.campaign_count}
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {isExpanded && (
                      <tr className="bg-muted/10">
                        <td colSpan={8} className="p-4 pl-6 pr-6">
                          <div className="grid grid-cols-4 gap-4">
                            <div className="flex items-center gap-2">
                              <DollarSign className="w-4 h-4 text-muted-foreground" />
                              <div>
                                <p className="text-xs text-muted-foreground">CTR</p>
                                <p className="text-sm font-medium">{account.ctr.toFixed(2)}%</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <TrendingUp className="w-4 h-4 text-muted-foreground" />
                              <div>
                                <p className="text-xs text-muted-foreground">Impressions</p>
                                <p className="text-sm font-medium">{formatNumber(account.impressions)}</p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Activity className="w-4 h-4 text-muted-foreground" />
                              <div>
                                <p className="text-xs text-muted-foreground">Clicks</p>
                                <p className="text-sm font-medium">{formatNumber(account.clicks)}</p>
                              </div>
                            </div>
                            {health && (
                              <div className="flex items-center gap-2">
                                <Activity className="w-4 h-4 text-muted-foreground" />
                                <div>
                                  <p className="text-xs text-muted-foreground">EMQ Score</p>
                                  <p className="text-sm font-medium">
                                    {health.emq_score != null ? `${health.emq_score.toFixed(0)}/100` : '--'}
                                  </p>
                                </div>
                              </div>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground mt-2">
                            Account ID: {account.account_id}
                            {!account.is_enabled && (
                              <span className="ml-2 text-red-400">(Disabled)</span>
                            )}
                          </p>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AccountBreakdown;
