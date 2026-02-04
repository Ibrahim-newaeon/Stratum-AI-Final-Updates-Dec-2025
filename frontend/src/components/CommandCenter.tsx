/**
 * Stratum AI - Command Center Table Component
 *
 * Displays campaigns with scaling scores and recommended actions (scale/watch/fix).
 * Supports filtering by action type and platform.
 */

import React, { useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  ChevronDown,
  ChevronUp,
  Eye,
  Filter,
  Minus,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { type CommandCenterItem, useCommandCenter } from '@/api/hooks/useTenantDashboard';

interface CommandCenterProps {
  tenantId: number;
  className?: string;
  onApply?: (item: CommandCenterItem) => void;
  onDismiss?: (item: CommandCenterItem) => void;
}

type ActionFilter = 'all' | 'scale' | 'watch' | 'fix';
type SortField = 'scaling_score' | 'roas' | 'spend' | 'conversions';
type SortDirection = 'asc' | 'desc';

const ActionBadge: React.FC<{ action: string }> = ({ action }) => {
  const styles = {
    scale: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
    watch: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
    fix: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  };

  const icons = {
    scale: TrendingUp,
    watch: Eye,
    fix: AlertTriangle,
  };

  const Icon = icons[action as keyof typeof icons] || Eye;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
        styles[action as keyof typeof styles] || styles.watch
      }`}
    >
      <Icon className="h-3 w-3" />
      {action.charAt(0).toUpperCase() + action.slice(1)}
    </span>
  );
};

const ScoreBar: React.FC<{ score: number }> = ({ score }) => {
  // Score ranges from -1 to +1
  const percentage = ((score + 1) / 2) * 100;
  const isPositive = score >= 0;

  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${
            isPositive ? 'bg-emerald-500' : 'bg-red-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span
        className={`text-sm font-medium ${
          isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
        }`}
      >
        {score >= 0 ? '+' : ''}
        {score.toFixed(2)}
      </span>
    </div>
  );
};

const SignalIndicator: React.FC<{ value: number; label: string }> = ({ value, label }) => {
  const Icon = value > 0 ? ArrowUpRight : value < 0 ? ArrowDownRight : Minus;
  const color = value > 0 ? 'text-emerald-500' : value < 0 ? 'text-red-500' : 'text-gray-400';

  return (
    <div className="flex items-center gap-1 text-xs">
      <Icon className={`h-3 w-3 ${color}`} />
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
    </div>
  );
};

export const CommandCenter: React.FC<CommandCenterProps> = ({
  tenantId,
  className = '',
  onApply,
  onDismiss,
}) => {
  const [actionFilter, setActionFilter] = useState<ActionFilter>('all');
  const [sortField, setSortField] = useState<SortField>('scaling_score');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const { data, isLoading, error } = useCommandCenter(
    tenantId,
    actionFilter !== 'all' ? { action: actionFilter } : undefined
  );

  const sortedItems = useMemo(() => {
    if (!data?.items) return [];

    return [...data.items].sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];
      const multiplier = sortDirection === 'desc' ? -1 : 1;
      return (aValue - bValue) * multiplier;
    });
  }, [data?.items, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const SortHeader: React.FC<{ field: SortField; label: string }> = ({ field, label }) => (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortField === field &&
          (sortDirection === 'desc' ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronUp className="h-4 w-4" />
          ))}
      </div>
    </th>
  );

  if (isLoading) {
    return (
      <div className={`rounded-xl border bg-card shadow-card p-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-xl border bg-card shadow-card p-6 ${className}`}>
        <p className="text-red-500">Failed to load command center data</p>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border bg-card shadow-card overflow-hidden ${className}`}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Command Center</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Campaign actions based on scaling scores
            </p>
          </div>

          {/* Summary badges */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
              <TrendingUp className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
                {data?.summary?.scale || 0} Scale
              </span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/20">
              <Eye className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
                {data?.summary?.watch || 0} Watch
              </span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-50 dark:bg-red-900/20">
              <TrendingDown className="h-4 w-4 text-red-600 dark:text-red-400" />
              <span className="text-sm font-medium text-red-700 dark:text-red-300">
                {data?.summary?.fix || 0} Fix
              </span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="mt-4 flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-400" />
          <div className="flex gap-1">
            {(['all', 'scale', 'watch', 'fix'] as ActionFilter[]).map((filter) => (
              <button
                key={filter}
                onClick={() => setActionFilter(filter)}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  actionFilter === filter
                    ? 'bg-primary text-primary-foreground'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-800/50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Campaign
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Action
              </th>
              <SortHeader field="scaling_score" label="Score" />
              <SortHeader field="roas" label="ROAS" />
              <SortHeader field="spend" label="Spend" />
              <SortHeader field="conversions" label="Conv." />
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Signals
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {sortedItems.map((item) => (
              <React.Fragment key={item.campaign_id}>
                <tr
                  className="hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer transition-colors"
                  onClick={() =>
                    setExpandedRow(expandedRow === item.campaign_id ? null : item.campaign_id)
                  }
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {item.campaign_name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {item.platform} | {item.status}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <ActionBadge action={item.action} />
                  </td>
                  <td className="px-4 py-3">
                    <ScoreBar score={item.scaling_score} />
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`font-medium ${
                        item.roas >= 2
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : item.roas < 1
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-gray-900 dark:text-white'
                      }`}
                    >
                      {item.roas.toFixed(2)}x
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-900 dark:text-white">
                    ${item.spend.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-gray-900 dark:text-white">
                    {item.conversions.toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-3">
                      <SignalIndicator value={item.signals.roas_momentum} label="ROAS" />
                      <SignalIndicator value={item.signals.spend_efficiency} label="Eff." />
                      <SignalIndicator value={item.signals.conversion_trend} label="Conv." />
                    </div>
                  </td>
                </tr>

                {/* Expanded row with recommendation */}
                {expandedRow === item.campaign_id && (
                  <tr className="bg-gray-50 dark:bg-gray-800/30">
                    <td colSpan={7} className="px-6 py-4">
                      <div className="flex items-start gap-4">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Recommendation
                          </p>
                          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                            {item.recommendation}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            className={`px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg transition-opacity ${
                              onApply
                                ? 'hover:opacity-90 cursor-pointer'
                                : 'opacity-50 cursor-not-allowed'
                            }`}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (onApply) {
                                onApply(item);
                              }
                            }}
                            disabled={!onApply}
                            title={onApply ? 'Apply this action' : 'Action handler not configured'}
                          >
                            Apply Action
                          </button>
                          <button
                            className={`px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg transition-colors ${
                              onDismiss
                                ? 'hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer'
                                : 'opacity-50 cursor-not-allowed'
                            }`}
                            onClick={(e) => {
                              e.stopPropagation();
                              if (onDismiss) {
                                onDismiss(item);
                              }
                            }}
                            disabled={!onDismiss}
                            title={
                              onDismiss
                                ? 'Dismiss this recommendation'
                                : 'Dismiss handler not configured'
                            }
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>

        {sortedItems.length === 0 && (
          <div className="px-6 py-12 text-center">
            <p className="text-gray-500 dark:text-gray-400">No campaigns found</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CommandCenter;
