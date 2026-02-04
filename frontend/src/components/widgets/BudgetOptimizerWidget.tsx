/**
 * Budget Optimizer Widget
 * Displays AI-powered budget reallocation recommendations
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronRight,
  MinusCircle,
  RefreshCw,
  Sparkles,
  TrendingUp,
  Wallet,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface BudgetReallocation {
  campaign_id: number;
  campaign_name: string;
  platform: string;
  current_roas: number;
  current_budget: number;
  recommended_budget: number;
  change_percent: number;
  action: 'increase' | 'decrease' | 'maintain';
  reason: string;
}

interface PotentialUplift {
  expected: number;
  conservative: number;
  optimistic: number;
}

interface BudgetOptimizerWidgetProps {
  className?: string;
}

export function BudgetOptimizerWidget({ className }: BudgetOptimizerWidgetProps) {
  const { t: _t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reallocations, setReallocations] = useState<BudgetReallocation[]>([]);
  const [potentialUplift, setPotentialUplift] = useState<PotentialUplift | null>(null);
  const [topPerformers, setTopPerformers] = useState<any[]>([]);
  const [bottomPerformers, setBottomPerformers] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchOptimization = async () => {
    try {
      setRefreshing(true);
      const response = await fetch('/api/v1/predictions/optimize/budget');
      const data = await response.json();

      if (data.success && data.data) {
        setReallocations(data.data.budget_reallocation || []);
        setPotentialUplift(data.data.potential_uplift || null);
        setTopPerformers(data.data.top_performers || []);
        setBottomPerformers(data.data.bottom_performers || []);
        setError(null);
      }
    } catch (err) {
      console.error('Failed to fetch optimization:', err);
      setError('Failed to load optimization data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchOptimization();
    // Refresh every 10 minutes
    const interval = setInterval(fetchOptimization, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const increaseCount = reallocations.filter((r) => r.action === 'increase').length;
  const decreaseCount = reallocations.filter((r) => r.action === 'decrease').length;

  if (loading) {
    return (
      <div className={cn('rounded-xl border bg-card p-6', className)}>
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-muted rounded w-1/3" />
          <div className="h-24 bg-muted rounded" />
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-muted rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('rounded-xl border bg-card overflow-hidden', className)}>
      {/* Header */}
      <div className="px-6 py-4 border-b bg-gradient-to-r from-violet-500/5 to-transparent">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-violet-500/10 rounded-lg">
              <Wallet className="w-5 h-5 text-violet-500" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Budget Optimizer</h3>
              <p className="text-xs text-muted-foreground">AI-powered allocation recommendations</p>
            </div>
          </div>
          <button
            onClick={fetchOptimization}
            disabled={refreshing}
            className="p-2 hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('w-4 h-4', refreshing && 'animate-spin')} />
          </button>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {error ? (
          <div className="flex items-center gap-3 p-4 bg-red-500/10 rounded-lg text-red-500 text-sm">
            {error}
          </div>
        ) : reallocations.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Wallet className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No optimization data available</p>
            <p className="text-sm mt-1">Add campaigns to see recommendations</p>
          </div>
        ) : (
          <>
            {/* Potential Impact */}
            {potentialUplift && (
              <div className="p-4 rounded-lg bg-gradient-to-r from-violet-500/10 to-purple-500/10 border border-violet-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-4 h-4 text-violet-500" />
                  <span className="font-medium text-sm">Potential Impact</span>
                </div>
                <div className="text-2xl font-bold text-violet-500 mb-1">
                  +{formatCurrency(potentialUplift.expected)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Expected revenue increase from optimization
                </div>
              </div>
            )}

            {/* Summary Stats */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-green-500/10 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <ArrowUpRight className="w-4 h-4 text-green-500" />
                  <span className="text-xs text-muted-foreground">Scale Up</span>
                </div>
                <div className="text-xl font-bold text-green-500">{increaseCount}</div>
                <div className="text-xs text-muted-foreground">campaigns</div>
              </div>
              <div className="p-3 bg-amber-500/10 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <ArrowDownRight className="w-4 h-4 text-amber-500" />
                  <span className="text-xs text-muted-foreground">Reduce</span>
                </div>
                <div className="text-xl font-bold text-amber-500">{decreaseCount}</div>
                <div className="text-xs text-muted-foreground">campaigns</div>
              </div>
            </div>

            {/* Reallocation Recommendations */}
            <div>
              <h4 className="text-sm font-medium text-foreground mb-3">Budget Recommendations</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {reallocations.slice(0, 6).map((item, index) => (
                  <div
                    key={`${item.campaign_id}-${index}`}
                    className={cn(
                      'p-3 rounded-lg transition-colors hover:shadow-md cursor-pointer',
                      item.action === 'increase'
                        ? 'bg-green-500/5 hover:bg-green-500/10'
                        : item.action === 'decrease'
                          ? 'bg-amber-500/5 hover:bg-amber-500/10'
                          : 'bg-muted/50 hover:bg-muted'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={cn(
                            'p-1.5 rounded-lg',
                            item.action === 'increase'
                              ? 'bg-green-500/10'
                              : item.action === 'decrease'
                                ? 'bg-amber-500/10'
                                : 'bg-muted'
                          )}
                        >
                          {item.action === 'increase' ? (
                            <ArrowUpRight className="w-4 h-4 text-green-500" />
                          ) : item.action === 'decrease' ? (
                            <ArrowDownRight className="w-4 h-4 text-amber-500" />
                          ) : (
                            <MinusCircle className="w-4 h-4 text-muted-foreground" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">
                            {item.campaign_name}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {item.platform} • ROAS: {item.current_roas.toFixed(2)}x
                          </p>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div
                          className={cn(
                            'text-sm font-semibold',
                            item.action === 'increase'
                              ? 'text-green-500'
                              : item.action === 'decrease'
                                ? 'text-amber-500'
                                : 'text-muted-foreground'
                          )}
                        >
                          {item.change_percent > 0 ? '+' : ''}
                          {item.change_percent.toFixed(0)}%
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatCurrency(item.current_budget)} →{' '}
                          {formatCurrency(item.recommended_budget)}
                        </div>
                      </div>
                    </div>
                    {item.reason && (
                      <p className="text-xs text-muted-foreground mt-2 pl-10">{item.reason}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Top/Bottom Performers */}
            <div className="grid grid-cols-2 gap-4">
              {topPerformers.length > 0 && (
                <div>
                  <h5 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                    <TrendingUp className="w-3 h-3 text-green-500" />
                    Top Performers
                  </h5>
                  <div className="space-y-1">
                    {topPerformers.slice(0, 3).map((c: any, i: number) => (
                      <div key={i} className="text-xs truncate text-foreground">
                        {c.name || c.campaign_name}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {bottomPerformers.length > 0 && (
                <div>
                  <h5 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                    <ArrowDownRight className="w-3 h-3 text-amber-500" />
                    Needs Work
                  </h5>
                  <div className="space-y-1">
                    {bottomPerformers.slice(0, 3).map((c: any, i: number) => (
                      <div key={i} className="text-xs truncate text-foreground">
                        {c.name || c.campaign_name}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-3 border-t bg-muted/30">
        <button className="text-sm text-primary hover:underline flex items-center gap-1">
          View detailed analysis
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default BudgetOptimizerWidget;
