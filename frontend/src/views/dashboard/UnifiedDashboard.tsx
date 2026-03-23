/**
 * Stratum AI - Unified Dashboard
 *
 * Main dashboard overview with widget layout:
 * - Onboarding checklist (when incomplete)
 * - Quick actions bar
 * - Signal score trend + Budget pacing (side-by-side)
 * - Autopilot actions log
 * - Anomaly feed
 */

import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  Calendar,
  ChevronDown,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  TimePeriod,
  useDashboardOverview,
  useDashboardQuickActions,
  useDashboardSignalHealth,
} from '@/api/dashboard';

// Widgets
import { OnboardingChecklist } from '@/components/onboarding/OnboardingChecklist';
import { QuickActionsBar } from './widgets/QuickActionsBar';
import { SignalScoreTrend } from './widgets/SignalScoreTrend';
import { BudgetPacingCard } from './widgets/BudgetPacingCard';
import { AutopilotActionsCard } from './widgets/AutopilotActionsCard';
import { AnomalyFeedCard } from './widgets/AnomalyFeedCard';

// Period options
const periodOptions: { value: TimePeriod; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' },
  { value: '90d', label: 'Last 90 Days' },
  { value: 'this_month', label: 'This Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: 'custom', label: 'Custom Range' },
];

function formatDateLabel(start: string, end: string): string {
  const s = new Date(start + 'T00:00:00');
  const e = new Date(end + 'T00:00:00');
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
  const endOpts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric', year: 'numeric' };
  return `${s.toLocaleDateString('en-US', opts)} – ${e.toLocaleDateString('en-US', endOpts)}`;
}

export default function UnifiedDashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [period, setPeriod] = useState<TimePeriod>('7d');
  const [showPeriodDropdown, setShowPeriodDropdown] = useState(false);
  const [showCustomPicker, setShowCustomPicker] = useState(false);
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [appliedStartDate, setAppliedStartDate] = useState<string | undefined>();
  const [appliedEndDate, setAppliedEndDate] = useState<string | undefined>();

  // Fetch dashboard data
  const {
    data: overview,
    isLoading: overviewLoading,
    isError: overviewError,
    error: overviewErrorData,
  } = useDashboardOverview(period, true, appliedStartDate, appliedEndDate);

  const { data: signalHealth, isLoading: signalHealthLoading, isError: signalHealthError } =
    useDashboardSignalHealth();

  const { data: quickActions } = useDashboardQuickActions();

  // Handlers
  const handleRefresh = useCallback(() => {
    queryClient.refetchQueries({ queryKey: ['dashboard'] });
  }, [queryClient]);

  const handlePeriodChange = useCallback((newPeriod: TimePeriod) => {
    if (newPeriod === 'custom') {
      setShowCustomPicker(true);
      return;
    }
    setPeriod(newPeriod);
    setAppliedStartDate(undefined);
    setAppliedEndDate(undefined);
    setShowCustomPicker(false);
    setShowPeriodDropdown(false);
  }, []);

  const handleApplyCustomRange = useCallback(() => {
    if (customStartDate && customEndDate) {
      setPeriod('custom');
      setAppliedStartDate(customStartDate);
      setAppliedEndDate(customEndDate);
      setShowCustomPicker(false);
      setShowPeriodDropdown(false);
    }
  }, [customStartDate, customEndDate]);

  const isLoading = overviewLoading || signalHealthLoading;
  const hasError = overviewError || signalHealthError;

  // Show loading state when data is still being fetched for the first time
  if (isLoading && !overview && !signalHealth) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  // Show error state when critical API calls fail (but not while still loading)
  if (hasError && !isLoading && !overview && !signalHealth) {
    const errorStatus = (overviewErrorData as Error & { response?: { status?: number } })?.response
      ?.status;
    const isAuthError = errorStatus === 401 || errorStatus === 403;

    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="w-8 h-8 text-red-500" />
          </div>
          <h2 className="text-2xl font-bold mb-3">
            {isAuthError ? 'Authentication Required' : 'Unable to Load Dashboard'}
          </h2>
          <p className="text-muted-foreground mb-6">
            {isAuthError
              ? 'Your session may have expired. Please sign in again to access the dashboard.'
              : "We couldn't connect to the server. Please check your connection and try again."}
          </p>
          <div className="flex gap-3 justify-center">
            {isAuthError ? (
              <button
                onClick={() => navigate('/login')}
                className="inline-flex items-center px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
              >
                Sign In
                <ArrowRight className="w-4 h-4 ml-2" />
              </button>
            ) : (
              <button
                onClick={handleRefresh}
                className="inline-flex items-center px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Onboarding Checklist (when incomplete) */}
      {overview && !overview.onboarding_complete && <OnboardingChecklist variant="inline" />}

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            {overview?.period_label || 'Last 7 Days'} Overview
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Period Selector */}
          <div className="relative">
            <button
              onClick={() => {
                setShowPeriodDropdown(!showPeriodDropdown);
                setShowCustomPicker(false);
              }}
              className="inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium bg-background hover:bg-muted transition-colors"
            >
              {period === 'custom' && appliedStartDate && appliedEndDate
                ? formatDateLabel(appliedStartDate, appliedEndDate)
                : periodOptions.find((p) => p.value === period)?.label || 'Last 7 Days'}
              <ChevronDown className="w-4 h-4 ml-2" />
            </button>

            {showPeriodDropdown && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => {
                    setShowPeriodDropdown(false);
                    setShowCustomPicker(false);
                  }}
                />
                <div className="absolute right-0 mt-2 w-64 bg-card border rounded-lg shadow-lg z-20 py-1">
                  {periodOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => handlePeriodChange(option.value)}
                      className={cn(
                        'w-full px-4 py-2 text-left text-sm hover:bg-muted transition-colors flex items-center gap-2',
                        period === option.value && !showCustomPicker && 'bg-muted font-medium'
                      )}
                    >
                      {option.value === 'custom' && <Calendar className="w-4 h-4" />}
                      {option.label}
                    </button>
                  ))}

                  {/* Custom Date Range Picker */}
                  {showCustomPicker && (
                    <div className="border-t px-4 py-3 space-y-3">
                      <div className="space-y-2">
                        <label className="block text-xs font-medium text-muted-foreground">
                          Start Date
                        </label>
                        <input
                          type="date"
                          value={customStartDate}
                          onChange={(e) => setCustomStartDate(e.target.value)}
                          max={customEndDate || undefined}
                          className="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="block text-xs font-medium text-muted-foreground">
                          End Date
                        </label>
                        <input
                          type="date"
                          value={customEndDate}
                          onChange={(e) => setCustomEndDate(e.target.value)}
                          min={customStartDate || undefined}
                          max={new Date().toISOString().split('T')[0]}
                          className="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                        />
                      </div>
                      <button
                        onClick={handleApplyCustomRange}
                        disabled={!customStartDate || !customEndDate}
                        className="w-full px-3 py-1.5 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                      >
                        Apply
                      </button>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="inline-flex items-center px-4 py-2 border rounded-lg text-sm font-medium bg-background hover:bg-muted transition-colors disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Refresh
          </button>
        </div>
      </div>

      {/* Quick Actions Bar */}
      {quickActions && <QuickActionsBar actions={quickActions.actions} />}

      {/* Signal Score Trend + Budget Pacing (side by side) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SignalScoreTrend signalHealth={signalHealth} loading={signalHealthLoading} />
        <BudgetPacingCard />
      </div>

      {/* Autopilot Actions (full width) */}
      <AutopilotActionsCard />

      {/* Anomaly Feed (full width) */}
      <AnomalyFeedCard />
    </div>
  );
}
