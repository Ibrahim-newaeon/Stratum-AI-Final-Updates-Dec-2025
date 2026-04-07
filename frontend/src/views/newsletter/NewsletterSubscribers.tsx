/**
 * Newsletter Subscribers - Subscriber management page for the Newsletter system
 *
 * Displays subscriber statistics, filterable subscriber table with pagination,
 * and actions to unsubscribe/resubscribe individual subscribers.
 */

import { useState, useCallback } from 'react';
import {
  UserGroupIcon,
  CheckCircleIcon,
  UserMinusIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';
import {
  useNewsletterSubscribers,
  useSubscriberStats,
  useUnsubscribe,
  useResubscribe,
  type SubscriberFilters,
  type NewsletterSubscriber,
} from '@/api/newsletter';

// ---------------------------------------------------------------------------
// Theme constants
// ---------------------------------------------------------------------------
const theme = {
  primary: '#00c7be',
  primaryLight: 'rgba(0, 199, 190, 0.15)',
  bgCard: 'rgba(255, 255, 255, 0.05)',
  border: 'rgba(255, 255, 255, 0.08)',
  textPrimary: 'rgba(245, 245, 247, 0.92)',
  textSecondary: 'rgba(245, 245, 247, 0.6)',
  textMuted: 'rgba(245, 245, 247, 0.35)',
};

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const PAGE_LIMIT = 25;

const PLATFORMS = ['All', 'Meta', 'Google', 'TikTok', 'Snapchat', 'Organic'] as const;

const STATUS_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Subscribed', value: 'subscribed' },
  { label: 'Unsubscribed', value: 'unsubscribed' },
] as const;

const PLATFORM_COLORS: Record<string, { bg: string; text: string }> = {
  meta: { bg: 'rgba(59, 130, 246, 0.15)', text: '#60a5fa' },
  google: { bg: 'rgba(239, 68, 68, 0.15)', text: '#f87171' },
  tiktok: { bg: 'rgba(236, 72, 153, 0.15)', text: '#f472b6' },
  snapchat: { bg: 'rgba(234, 179, 8, 0.15)', text: '#facc15' },
  organic: { bg: 'rgba(34, 197, 94, 0.15)', text: '#4ade80' },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatRelativeDate(dateString: string | null): string {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#4ade80';
  if (score >= 50) return '#fbbf24';
  return '#f87171';
}

// ---------------------------------------------------------------------------
// StatCard
// ---------------------------------------------------------------------------
function StatCard({
  title,
  value,
  icon: Icon,
  accentColor,
  loading,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  accentColor?: string;
  loading?: boolean;
}) {
  const iconColor = accentColor || theme.primary;

  return (
    <div className="bg-white/5 border border-white/[0.08] rounded-2xl p-4 backdrop-blur-xl">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p
            className="text-sm font-medium mb-1"
            style={{ color: theme.textSecondary }}
          >
            {title}
          </p>
          {loading ? (
            <div className="h-8 w-20 bg-white/[0.08] rounded-md animate-pulse mt-1" />
          ) : (
            <p
              className="text-2xl font-bold tracking-tight"
              style={{ color: theme.textPrimary }}
            >
              {value.toLocaleString()}
            </p>
          )}
        </div>
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: `${iconColor}20` }}
        >
          <Icon className="w-5 h-5" style={{ color: iconColor }} />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PlatformBadge
// ---------------------------------------------------------------------------
function PlatformBadge({ platform }: { platform: string | null }) {
  if (!platform) {
    return (
      <span
        className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium"
        style={{
          background: 'rgba(255, 255, 255, 0.06)',
          color: theme.textMuted,
        }}
      >
        Unknown
      </span>
    );
  }

  const key = platform.toLowerCase();
  const colors = PLATFORM_COLORS[key] || {
    bg: 'rgba(255, 255, 255, 0.06)',
    text: theme.textSecondary,
  };

  return (
    <span
      className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium capitalize"
      style={{ background: colors.bg, color: colors.text }}
    >
      {platform}
    </span>
  );
}

// ---------------------------------------------------------------------------
// SubscriberRow
// ---------------------------------------------------------------------------
function SubscriberRow({
  subscriber,
  onUnsubscribe,
  onResubscribe,
}: {
  subscriber: NewsletterSubscriber;
  onUnsubscribe: (id: number) => void;
  onResubscribe: (id: number) => void;
}) {
  const [confirming, setConfirming] = useState<'unsubscribe' | 'resubscribe' | null>(null);

  const handleAction = useCallback(() => {
    if (subscriber.subscribed_to_newsletter) {
      if (confirming === 'unsubscribe') {
        onUnsubscribe(subscriber.id);
        setConfirming(null);
      } else {
        setConfirming('unsubscribe');
      }
    } else {
      if (confirming === 'resubscribe') {
        onResubscribe(subscriber.id);
        setConfirming(null);
      } else {
        setConfirming('resubscribe');
      }
    }
  }, [subscriber, confirming, onUnsubscribe, onResubscribe]);

  const scoreColor = getScoreColor(subscriber.lead_score);

  return (
    <tr className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
      {/* Name + Company */}
      <td className="p-4">
        <div>
          <p className="font-medium" style={{ color: theme.textPrimary }}>
            {subscriber.full_name || '\u2014'}
          </p>
          {subscriber.company_name && (
            <p className="text-xs mt-0.5" style={{ color: theme.textMuted }}>
              {subscriber.company_name}
            </p>
          )}
        </div>
      </td>

      {/* Email */}
      <td className="p-4">
        <span className="text-sm" style={{ color: theme.textSecondary }}>
          {subscriber.email}
        </span>
      </td>

      {/* Platform */}
      <td className="p-4">
        <PlatformBadge platform={subscriber.attributed_platform} />
      </td>

      {/* Lead Score */}
      <td className="p-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold" style={{ color: scoreColor }}>
            {subscriber.lead_score}
          </span>
          <div className="w-12 h-1.5 rounded-full bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(subscriber.lead_score, 100)}%`,
                background: scoreColor,
              }}
            />
          </div>
        </div>
      </td>

      {/* Newsletter Status */}
      <td className="p-4">
        {subscriber.subscribed_to_newsletter ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-400">
            <CheckCircleIcon className="w-3.5 h-3.5" />
            Subscribed
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400">
            <UserMinusIcon className="w-3.5 h-3.5" />
            Unsubscribed
          </span>
        )}
      </td>

      {/* Emails Sent */}
      <td className="p-4">
        <span className="text-sm" style={{ color: theme.textSecondary }}>
          {subscriber.email_send_count}
        </span>
      </td>

      {/* Opens */}
      <td className="p-4">
        <span className="text-sm" style={{ color: theme.textSecondary }}>
          {subscriber.email_open_count}
        </span>
      </td>

      {/* Last Sent */}
      <td className="p-4">
        <span className="text-sm" style={{ color: theme.textMuted }}>
          {formatRelativeDate(subscriber.last_email_sent_at)}
        </span>
      </td>

      {/* Actions */}
      <td className="p-4 text-right">
        {confirming ? (
          <div className="inline-flex items-center gap-2">
            <span className="text-xs" style={{ color: theme.textMuted }}>
              Confirm?
            </span>
            <button
              onClick={handleAction}
              className="px-3 py-1 text-xs font-medium rounded-lg transition-colors"
              style={{
                background: subscriber.subscribed_to_newsletter
                  ? 'rgba(239, 68, 68, 0.15)'
                  : 'rgba(34, 197, 94, 0.15)',
                color: subscriber.subscribed_to_newsletter ? '#f87171' : '#4ade80',
              }}
            >
              Yes
            </button>
            <button
              onClick={() => setConfirming(null)}
              className="px-3 py-1 text-xs font-medium rounded-lg bg-white/5 transition-colors hover:bg-white/10"
              style={{ color: theme.textSecondary }}
            >
              No
            </button>
          </div>
        ) : (
          <button
            onClick={handleAction}
            className="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
            style={{
              background: subscriber.subscribed_to_newsletter
                ? 'rgba(239, 68, 68, 0.1)'
                : 'rgba(34, 197, 94, 0.1)',
              color: subscriber.subscribed_to_newsletter ? '#f87171' : '#4ade80',
            }}
          >
            {subscriber.subscribed_to_newsletter ? 'Unsubscribe' : 'Resubscribe'}
          </button>
        )}
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// SkeletonRows
// ---------------------------------------------------------------------------
function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <tr key={i} className="border-b border-white/5">
          <td className="p-4">
            <div className="h-4 w-28 bg-white/[0.08] rounded animate-pulse" />
            <div className="h-3 w-20 bg-white/[0.06] rounded animate-pulse mt-1.5" />
          </td>
          <td className="p-4">
            <div className="h-4 w-40 bg-white/[0.08] rounded animate-pulse" />
          </td>
          <td className="p-4">
            <div className="h-6 w-16 bg-white/[0.08] rounded-full animate-pulse" />
          </td>
          <td className="p-4">
            <div className="h-4 w-10 bg-white/[0.08] rounded animate-pulse" />
          </td>
          <td className="p-4">
            <div className="h-6 w-20 bg-white/[0.08] rounded-full animate-pulse" />
          </td>
          <td className="p-4">
            <div className="h-4 w-8 bg-white/[0.08] rounded animate-pulse" />
          </td>
          <td className="p-4">
            <div className="h-4 w-8 bg-white/[0.08] rounded animate-pulse" />
          </td>
          <td className="p-4">
            <div className="h-4 w-20 bg-white/[0.08] rounded animate-pulse" />
          </td>
          <td className="p-4">
            <div className="h-7 w-20 bg-white/[0.08] rounded-lg animate-pulse ml-auto" />
          </td>
        </tr>
      ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
export default function NewsletterSubscribers() {
  // Filter state
  const [statusFilter, setStatusFilter] = useState<'all' | 'subscribed' | 'unsubscribed'>('all');
  const [platformFilter, setPlatformFilter] = useState<string>('All');
  const [minScore, setMinScore] = useState<string>('');
  const [offset, setOffset] = useState(0);

  // Build filters for the API
  const filters: SubscriberFilters = {
    limit: PAGE_LIMIT,
    offset,
    ...(statusFilter === 'subscribed' ? { subscribed: true } : {}),
    ...(statusFilter === 'unsubscribed' ? { subscribed: false } : {}),
    ...(platformFilter !== 'All' ? { platform: platformFilter.toLowerCase() } : {}),
    ...(minScore !== '' && !isNaN(Number(minScore)) ? { min_score: Number(minScore) } : {}),
  };

  // Queries
  const { data: subscribers, isLoading: subscribersLoading } = useNewsletterSubscribers(filters);
  const { data: stats, isLoading: statsLoading } = useSubscriberStats();

  // Mutations
  const unsubscribeMutation = useUnsubscribe();
  const resubscribeMutation = useResubscribe();

  const handleUnsubscribe = useCallback(
    async (id: number) => {
      await unsubscribeMutation.mutateAsync(id);
    },
    [unsubscribeMutation]
  );

  const handleResubscribe = useCallback(
    async (id: number) => {
      await resubscribeMutation.mutateAsync(id);
    },
    [resubscribeMutation]
  );

  // Pagination helpers
  const hasMore = (subscribers?.length ?? 0) === PAGE_LIMIT;
  const hasPrev = offset > 0;
  const currentPage = Math.floor(offset / PAGE_LIMIT) + 1;

  const handlePrev = () => setOffset((prev) => Math.max(0, prev - PAGE_LIMIT));
  const handleNext = () => setOffset((prev) => prev + PAGE_LIMIT);

  // Reset offset when filters change
  const handleStatusChange = (value: 'all' | 'subscribed' | 'unsubscribed') => {
    setStatusFilter(value);
    setOffset(0);
  };

  const handlePlatformChange = (value: string) => {
    setPlatformFilter(value);
    setOffset(0);
  };

  const handleMinScoreChange = (value: string) => {
    setMinScore(value);
    setOffset(0);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1
          className="text-2xl font-bold tracking-tight"
          style={{ color: theme.textPrimary }}
        >
          Newsletter Subscribers
        </h1>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Total Subscribers"
          value={stats?.total ?? 0}
          icon={UserGroupIcon}
          loading={statsLoading}
        />
        <StatCard
          title="Active"
          value={stats?.active ?? 0}
          icon={CheckCircleIcon}
          accentColor="#4ade80"
          loading={statsLoading}
        />
        <StatCard
          title="Unsubscribed"
          value={stats?.unsubscribed ?? 0}
          icon={UserMinusIcon}
          accentColor="#f87171"
          loading={statsLoading}
        />
      </div>

      {/* Filter Bar */}
      <div
        className="rounded-2xl p-4 backdrop-blur-xl"
        style={{
          background: theme.bgCard,
          border: `1px solid ${theme.border}`,
        }}
      >
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          {/* Status filter (radio-style buttons) */}
          <div className="flex items-center gap-1 bg-white/[0.04] rounded-xl p-1">
            {STATUS_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => handleStatusChange(opt.value as typeof statusFilter)}
                className="px-4 py-2 rounded-lg text-sm font-medium transition-all"
                style={{
                  background:
                    statusFilter === opt.value ? theme.primary : 'transparent',
                  color:
                    statusFilter === opt.value ? '#000' : theme.textSecondary,
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Platform dropdown */}
          <div className="flex items-center gap-2">
            <label
              className="text-sm font-medium whitespace-nowrap"
              style={{ color: theme.textMuted }}
            >
              Platform:
            </label>
            <select
              value={platformFilter}
              onChange={(e) => handlePlatformChange(e.target.value)}
              className="px-3 py-2 rounded-xl text-sm bg-white/[0.05] border border-white/[0.08] focus:border-[#00c7be]/50 focus:outline-none transition-colors appearance-none cursor-pointer"
              style={{ color: theme.textPrimary }}
            >
              {PLATFORMS.map((p) => (
                <option key={p} value={p} className="bg-[#12131a]">
                  {p}
                </option>
              ))}
            </select>
          </div>

          {/* Min Lead Score */}
          <div className="flex items-center gap-2">
            <label
              className="text-sm font-medium whitespace-nowrap"
              style={{ color: theme.textMuted }}
            >
              Min Score:
            </label>
            <input
              type="number"
              min={0}
              max={100}
              placeholder="0"
              value={minScore}
              onChange={(e) => handleMinScoreChange(e.target.value)}
              className="w-20 px-3 py-2 rounded-xl text-sm bg-white/[0.05] border border-white/[0.08] focus:border-[#00c7be]/50 focus:outline-none transition-colors"
              style={{ color: theme.textPrimary }}
            />
          </div>
        </div>
      </div>

      {/* Subscribers Table */}
      <div
        className="rounded-2xl overflow-hidden backdrop-blur-xl"
        style={{
          background: theme.bgCard,
          border: `1px solid ${theme.border}`,
        }}
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/[0.08]">
                {[
                  'Name',
                  'Email',
                  'Platform',
                  'Lead Score',
                  'Newsletter Status',
                  'Emails Sent',
                  'Opens',
                  'Last Sent',
                  'Actions',
                ].map((header) => (
                  <th
                    key={header}
                    className={`p-4 text-sm font-medium ${
                      header === 'Actions' ? 'text-right' : 'text-left'
                    }`}
                    style={{ color: theme.textMuted }}
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {subscribersLoading ? (
                <SkeletonRows count={8} />
              ) : subscribers && subscribers.length > 0 ? (
                subscribers.map((subscriber) => (
                  <SubscriberRow
                    key={subscriber.id}
                    subscriber={subscriber}
                    onUnsubscribe={handleUnsubscribe}
                    onResubscribe={handleResubscribe}
                  />
                ))
              ) : (
                <tr>
                  <td colSpan={9} className="p-12">
                    <div className="flex flex-col items-center justify-center text-center">
                      <div
                        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
                        style={{ background: 'rgba(255, 255, 255, 0.04)' }}
                      >
                        <UserGroupIcon
                          className="w-8 h-8"
                          style={{ color: theme.textMuted }}
                        />
                      </div>
                      <p
                        className="text-lg font-medium mb-1"
                        style={{ color: theme.textSecondary }}
                      >
                        No subscribers found
                      </p>
                      <p className="text-sm" style={{ color: theme.textMuted }}>
                        Try adjusting your filters to see more results.
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!subscribersLoading && subscribers && subscribers.length > 0 && (
          <div className="flex items-center justify-between p-4 border-t border-white/[0.06]">
            <span className="text-sm" style={{ color: theme.textMuted }}>
              Showing {offset + 1}&ndash;{offset + (subscribers?.length ?? 0)} &middot; Page{' '}
              {currentPage}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={handlePrev}
                disabled={!hasPrev}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/[0.06]"
                style={{ color: theme.textSecondary }}
              >
                <ChevronLeftIcon className="w-4 h-4" />
                Previous
              </button>
              <button
                onClick={handleNext}
                disabled={!hasMore}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/[0.06]"
                style={{ color: theme.textSecondary }}
              >
                Next
                <ChevronRightIcon className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
