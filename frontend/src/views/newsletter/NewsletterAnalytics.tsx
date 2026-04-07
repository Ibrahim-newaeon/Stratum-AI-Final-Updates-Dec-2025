/**
 * Newsletter Campaign Analytics - Detailed analytics view for a sent campaign
 *
 * Shows delivery funnel, event timeline, link performance, and key metrics.
 */

import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeftIcon,
  CursorArrowRaysIcon,
  EnvelopeOpenIcon,
  ExclamationCircleIcon,
  InboxIcon,
  LinkIcon,
  PaperAirplaneIcon,
  UserMinusIcon,
} from '@heroicons/react/24/outline';
import { useCampaignAnalytics } from '@/api/newsletter';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const EVENTS_LIMIT = 50;

const EVENT_BADGE_STYLES: Record<string, string> = {
  sent: 'bg-gray-500/20 text-gray-400',
  delivered: 'bg-blue-500/20 text-blue-400',
  opened: 'bg-green-500/20 text-green-400',
  clicked: 'bg-purple-500/20 text-purple-400',
  bounced: 'bg-red-500/20 text-red-400',
  unsubscribed: 'bg-orange-500/20 text-orange-400',
};

const FUNNEL_COLORS: Record<string, string> = {
  sent: '#00c7be',
  delivered: '#3b82f6',
  opened: '#22c55e',
  clicked: '#a855f7',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '\u2014';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function formatTimestamp(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function LoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header skeleton */}
      <div className="space-y-2">
        <div className="h-5 w-32 bg-white/[0.06] rounded" />
        <div className="h-8 w-64 bg-white/[0.06] rounded" />
        <div className="h-4 w-48 bg-white/[0.06] rounded" />
      </div>

      {/* Stats cards skeleton */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="bg-white/5 border border-white/[0.08] rounded-2xl p-5 space-y-3"
          >
            <div className="h-10 w-10 bg-white/[0.06] rounded-full" />
            <div className="h-7 w-16 bg-white/[0.06] rounded" />
            <div className="h-4 w-20 bg-white/[0.06] rounded" />
          </div>
        ))}
      </div>

      {/* Funnel skeleton */}
      <div className="bg-white/5 border border-white/[0.08] rounded-2xl p-6 space-y-4">
        <div className="h-6 w-40 bg-white/[0.06] rounded" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 bg-white/[0.06] rounded" />
        ))}
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  rate,
  rateColor = 'text-[rgba(245,245,247,0.6)]',
}: {
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  label: string;
  value: number;
  rate?: number;
  rateColor?: string;
}) {
  return (
    <div className="bg-white/5 border border-white/[0.08] rounded-2xl p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="h-10 w-10 rounded-full bg-[#00c7be]/15 flex items-center justify-center">
          <Icon className="h-5 w-5 text-[#00c7be]" />
        </div>
      </div>
      <div className="text-2xl font-bold text-[rgba(245,245,247,0.92)]">
        {formatNumber(value)}
      </div>
      <div className="text-sm text-[rgba(245,245,247,0.6)] mt-1">{label}</div>
      {rate !== undefined && (
        <div className={`text-sm font-medium mt-1 ${rateColor}`}>
          {formatPercent(rate)}
        </div>
      )}
    </div>
  );
}

function EventBadge({ type }: { type: string }) {
  const style = EVENT_BADGE_STYLES[type] ?? 'bg-gray-500/20 text-gray-400';
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${style}`}
    >
      {type}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function NewsletterAnalytics() {
  const { id } = useParams<{ id: string }>();
  const campaignId = Number(id);

  const { data, isLoading } = useCampaignAnalytics(campaignId);

  // Compute link performance from click events
  const linkPerformance = useMemo(() => {
    if (!data?.events) return [];

    const urlCounts: Record<string, number> = {};
    for (const event of data.events) {
      if (event.event_type === 'clicked' && event.metadata) {
        const url =
          (event.metadata.url as string) ??
          (event.metadata.link as string) ??
          null;
        if (url) {
          urlCounts[url] = (urlCounts[url] ?? 0) + 1;
        }
      }
    }

    return Object.entries(urlCounts)
      .map(([url, count]) => ({ url, count }))
      .sort((a, b) => b.count - a.count);
  }, [data?.events]);

  const maxLinkClicks = linkPerformance.length > 0 ? linkPerformance[0].count : 0;

  // Loading state
  if (isLoading || !data) {
    return <LoadingSkeleton />;
  }

  const { campaign, open_rate, click_rate, bounce_rate, unsubscribe_rate, events } =
    data;

  // Funnel stages
  const funnelStages = [
    { label: 'Sent', count: campaign.total_sent, color: FUNNEL_COLORS.sent },
    {
      label: 'Delivered',
      count: campaign.total_delivered,
      color: FUNNEL_COLORS.delivered,
    },
    { label: 'Opened', count: campaign.total_opened, color: FUNNEL_COLORS.opened },
    { label: 'Clicked', count: campaign.total_clicked, color: FUNNEL_COLORS.clicked },
  ];

  const maxCount = campaign.total_sent || 1;
  const recentEvents = events.slice(0, EVENTS_LIMIT);

  return (
    <div className="space-y-6">
      {/* ----------------------------------------------------------------- */}
      {/* Header                                                            */}
      {/* ----------------------------------------------------------------- */}
      <div>
        <Link
          to="/dashboard/newsletter/campaigns"
          className="inline-flex items-center gap-1.5 text-sm text-[rgba(245,245,247,0.6)] hover:text-[rgba(245,245,247,0.92)] transition-colors mb-3"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          Back to Campaigns
        </Link>

        <h1 className="text-2xl font-bold text-[rgba(245,245,247,0.92)]">
          {campaign.name}
        </h1>
        <p className="text-sm text-[rgba(245,245,247,0.6)] mt-1">
          {campaign.subject}
        </p>
        <p className="text-xs text-[rgba(245,245,247,0.35)] mt-1">
          {campaign.sent_at ? `Sent on ${formatDate(campaign.sent_at)}` : 'Not sent yet'}
          {campaign.completed_at && ` \u00B7 Completed ${formatDate(campaign.completed_at)}`}
        </p>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Summary Stats Cards                                               */}
      {/* ----------------------------------------------------------------- */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          icon={PaperAirplaneIcon}
          label="Total Sent"
          value={campaign.total_sent}
        />
        <StatCard
          icon={InboxIcon}
          label="Delivered"
          value={campaign.total_delivered}
        />
        <StatCard
          icon={EnvelopeOpenIcon}
          label="Opened"
          value={campaign.total_opened}
          rate={open_rate}
        />
        <StatCard
          icon={CursorArrowRaysIcon}
          label="Clicked"
          value={campaign.total_clicked}
          rate={click_rate}
        />
        <StatCard
          icon={ExclamationCircleIcon}
          label="Bounced"
          value={campaign.total_bounced}
          rate={bounce_rate}
          rateColor="text-red-400"
        />
        <StatCard
          icon={UserMinusIcon}
          label="Unsubscribed"
          value={campaign.total_unsubscribed}
          rate={unsubscribe_rate}
          rateColor="text-orange-400"
        />
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Delivery Funnel                                                   */}
      {/* ----------------------------------------------------------------- */}
      <div className="bg-white/5 border border-white/[0.08] rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-[rgba(245,245,247,0.92)] mb-5">
          Delivery Funnel
        </h2>
        <div className="space-y-4">
          {funnelStages.map((stage, idx) => {
            const widthPct = Math.max((stage.count / maxCount) * 100, 2);
            const prevCount = idx > 0 ? funnelStages[idx - 1].count : null;
            const dropPct =
              prevCount !== null && prevCount > 0
                ? (((prevCount - stage.count) / prevCount) * 100).toFixed(1)
                : null;

            return (
              <div key={stage.label}>
                {/* Drop-off indicator */}
                {dropPct !== null && (
                  <div className="flex items-center gap-2 mb-1.5 ml-2">
                    <div className="h-px w-4 bg-white/[0.15]" />
                    <span className="text-xs text-[rgba(245,245,247,0.35)]">
                      -{dropPct}% drop-off
                    </span>
                  </div>
                )}

                <div className="flex items-center gap-4">
                  {/* Label */}
                  <div className="w-24 text-sm font-medium text-[rgba(245,245,247,0.6)] shrink-0">
                    {stage.label}
                  </div>

                  {/* Bar */}
                  <div className="flex-1 h-9 bg-white/[0.04] rounded-lg overflow-hidden">
                    <div
                      className="h-full rounded-lg flex items-center px-3 transition-all duration-500"
                      style={{
                        width: `${widthPct}%`,
                        backgroundColor: stage.color,
                        opacity: 0.85,
                      }}
                    >
                      <span className="text-xs font-semibold text-black whitespace-nowrap">
                        {formatNumber(stage.count)}
                      </span>
                    </div>
                  </div>

                  {/* Percentage of total sent */}
                  <div className="w-14 text-right text-sm font-medium text-[rgba(245,245,247,0.6)] shrink-0">
                    {campaign.total_sent > 0
                      ? formatPercent((stage.count / campaign.total_sent) * 100)
                      : '\u2014'}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Event Timeline                                                    */}
      {/* ----------------------------------------------------------------- */}
      <div className="bg-white/5 border border-white/[0.08] rounded-2xl p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-[rgba(245,245,247,0.92)]">
            Recent Events
          </h2>
          <span className="text-xs text-[rgba(245,245,247,0.35)]">
            Showing {Math.min(recentEvents.length, EVENTS_LIMIT)} of {events.length}
          </span>
        </div>

        {recentEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-sm text-[rgba(245,245,247,0.6)]">
              No events recorded yet
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs font-medium text-[rgba(245,245,247,0.35)] uppercase tracking-wider">
                  <th className="px-4 py-3">Event</th>
                  <th className="px-4 py-3">Subscriber ID</th>
                  <th className="px-4 py-3">Details</th>
                  <th className="px-4 py-3 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {recentEvents.map((event) => {
                  const clickUrl =
                    event.event_type === 'clicked' && event.metadata
                      ? (event.metadata.url as string) ??
                        (event.metadata.link as string) ??
                        null
                      : null;

                  return (
                    <tr
                      key={event.id}
                      className="border-t border-white/[0.06] hover:bg-white/[0.03] transition-colors"
                    >
                      <td className="px-4 py-3">
                        <EventBadge type={event.event_type} />
                      </td>
                      <td className="px-4 py-3 text-sm text-[rgba(245,245,247,0.6)] font-mono">
                        #{event.subscriber_id}
                      </td>
                      <td className="px-4 py-3 text-sm text-[rgba(245,245,247,0.6)] max-w-xs truncate">
                        {clickUrl ? (
                          <span className="inline-flex items-center gap-1 text-[#00c7be]">
                            <LinkIcon className="h-3.5 w-3.5 shrink-0" />
                            <span className="truncate">{clickUrl}</span>
                          </span>
                        ) : (
                          <span className="text-[rgba(245,245,247,0.35)]">\u2014</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-[rgba(245,245,247,0.35)] text-right whitespace-nowrap">
                        {formatTimestamp(event.created_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ----------------------------------------------------------------- */}
      {/* Link Performance / Click Map                                      */}
      {/* ----------------------------------------------------------------- */}
      <div className="bg-white/5 border border-white/[0.08] rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-[rgba(245,245,247,0.92)] mb-5">
          Link Performance
        </h2>

        {linkPerformance.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-sm text-[rgba(245,245,247,0.6)]">
              No link clicks recorded yet
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {linkPerformance.map((link) => {
              const barPct =
                maxLinkClicks > 0
                  ? Math.max((link.count / maxLinkClicks) * 100, 4)
                  : 0;

              return (
                <div key={link.url} className="space-y-1.5">
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm text-[rgba(245,245,247,0.6)] truncate flex items-center gap-1.5 min-w-0">
                      <LinkIcon className="h-3.5 w-3.5 text-[rgba(245,245,247,0.35)] shrink-0" />
                      <span className="truncate">{link.url}</span>
                    </span>
                    <span className="text-sm font-semibold text-[rgba(245,245,247,0.92)] shrink-0">
                      {formatNumber(link.count)} {link.count === 1 ? 'click' : 'clicks'}
                    </span>
                  </div>
                  <div className="h-2.5 bg-white/[0.04] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${barPct}%`,
                        backgroundColor: '#a855f7',
                        opacity: 0.8,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
