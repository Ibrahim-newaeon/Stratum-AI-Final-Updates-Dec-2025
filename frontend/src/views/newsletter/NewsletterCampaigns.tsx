/**
 * Newsletter Campaigns - Campaign list page with filtering, pagination, and actions
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ChartBarIcon,
  DocumentDuplicateIcon,
  EnvelopeIcon,
  PaperAirplaneIcon,
  PencilIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import {
  type CampaignStatus,
  type NewsletterCampaign,
  useCampaigns,
  useDeleteCampaign,
  useDuplicateCampaign,
  useSendCampaign,
} from '@/api/newsletter';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PAGE_SIZE = 10;

const STATUS_OPTIONS: { value: CampaignStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'draft', label: 'Draft' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'sending', label: 'Sending' },
  { value: 'sent', label: 'Sent' },
  { value: 'paused', label: 'Paused' },
  { value: 'cancelled', label: 'Cancelled' },
];

const STATUS_BADGE_STYLES: Record<CampaignStatus, string> = {
  draft: 'bg-gray-500/20 text-gray-400',
  scheduled: 'bg-blue-500/20 text-blue-400',
  sending: 'bg-amber-500/20 text-amber-400',
  sent: 'bg-green-500/20 text-green-400',
  paused: 'bg-orange-500/20 text-orange-400',
  cancelled: 'bg-red-500/20 text-red-400',
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: CampaignStatus }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize',
        STATUS_BADGE_STYLES[status],
      )}
    >
      {status}
    </span>
  );
}

function SkeletonRow() {
  return (
    <tr className="border-t border-white/[0.06]">
      {Array.from({ length: 6 }).map((_, i) => (
        <td key={i} className="px-6 py-4">
          <div className="h-4 bg-white/[0.06] rounded animate-pulse" />
        </td>
      ))}
    </tr>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="rounded-2xl bg-white/5 p-4 mb-4">
        <EnvelopeIcon className="h-10 w-10 text-[rgba(245,245,247,0.35)]" />
      </div>
      <h3 className="text-lg font-semibold text-[rgba(245,245,247,0.92)] mb-1">
        No campaigns yet
      </h3>
      <p className="text-sm text-[rgba(245,245,247,0.6)] mb-6 max-w-sm">
        Create your first email campaign to start reaching your audience.
      </p>
      <Link
        to="/dashboard/newsletter/campaigns/new"
        className="inline-flex items-center gap-2 bg-[#00c7be] hover:bg-[#00b5ad] text-black font-semibold rounded-xl px-4 py-2 transition-colors"
      >
        <PlusIcon className="h-5 w-5" />
        New Campaign
      </Link>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRate(opened: number, sent: number): string {
  if (sent === 0) return '\u2014';
  return `${((opened / sent) * 100).toFixed(1)}%`;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value);
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function NewsletterCampaigns() {
  const navigate = useNavigate();

  // Filter & pagination state
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | undefined>(undefined);
  const [offset, setOffset] = useState(0);

  // Data fetching
  const { data, isLoading } = useCampaigns({
    status: statusFilter,
    limit: PAGE_SIZE,
    offset,
  });

  const campaigns = data?.campaigns ?? [];
  const total = data?.total ?? 0;
  const hasNextPage = offset + PAGE_SIZE < total;
  const hasPrevPage = offset > 0;

  // Mutations
  const deleteCampaign = useDeleteCampaign();
  const duplicateCampaign = useDuplicateCampaign();
  const sendCampaign = useSendCampaign();

  // Handlers
  const handleDelete = (campaign: NewsletterCampaign) => {
    if (!window.confirm(`Delete campaign "${campaign.name}"? This action cannot be undone.`)) {
      return;
    }
    deleteCampaign.mutate(campaign.id);
  };

  const handleDuplicate = (campaign: NewsletterCampaign) => {
    duplicateCampaign.mutate(campaign.id);
  };

  const handleSend = (campaign: NewsletterCampaign) => {
    if (
      !window.confirm(
        `Send campaign "${campaign.name}" to ${formatNumber(campaign.total_recipients)} recipients? This cannot be undone.`,
      )
    ) {
      return;
    }
    sendCampaign.mutate(campaign.id);
  };

  const handleStatusChange = (value: string) => {
    setStatusFilter(value === '' ? undefined : (value as CampaignStatus));
    setOffset(0);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[rgba(245,245,247,0.92)]">Campaigns</h1>
        <Link
          to="/dashboard/newsletter/campaigns/new"
          className="inline-flex items-center gap-2 bg-[#00c7be] hover:bg-[#00b5ad] text-black font-semibold rounded-xl px-4 py-2 transition-colors"
        >
          <PlusIcon className="h-5 w-5" />
          New Campaign
        </Link>
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-4">
        <select
          value={statusFilter ?? ''}
          onChange={(e) => handleStatusChange(e.target.value)}
          className={cn(
            'bg-white/5 border border-white/[0.08] rounded-xl',
            'px-4 py-2 text-sm text-[rgba(245,245,247,0.92)]',
            'focus:outline-none focus:ring-1 focus:ring-[#00c7be]/50 focus:border-[#00c7be]/50',
            'appearance-none cursor-pointer',
          )}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-[#1a1a2e] text-white">
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Campaign Table */}
      <div className="bg-white/5 border border-white/[0.08] rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs font-medium text-[rgba(245,245,247,0.35)] uppercase tracking-wider">
                <th className="px-6 py-4">Campaign</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Recipients</th>
                <th className="px-6 py-4">Open Rate</th>
                <th className="px-6 py-4">Click Rate</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {/* Loading skeleton */}
              {isLoading &&
                Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)}

              {/* Empty state */}
              {!isLoading && campaigns.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <EmptyState />
                  </td>
                </tr>
              )}

              {/* Campaign rows */}
              {!isLoading &&
                campaigns.map((campaign) => (
                  <tr
                    key={campaign.id}
                    className="border-t border-white/[0.06] hover:bg-white/[0.03] transition-colors"
                  >
                    {/* Campaign name + subject */}
                    <td className="px-6 py-4 max-w-xs">
                      <div className="font-semibold text-[rgba(245,245,247,0.92)] truncate">
                        {campaign.name}
                      </div>
                      <div className="text-sm text-[rgba(245,245,247,0.35)] truncate mt-0.5">
                        {campaign.subject}
                      </div>
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4">
                      <StatusBadge status={campaign.status} />
                    </td>

                    {/* Recipients */}
                    <td className="px-6 py-4 text-sm text-[rgba(245,245,247,0.6)]">
                      {formatNumber(campaign.total_recipients)}
                    </td>

                    {/* Open Rate */}
                    <td className="px-6 py-4 text-sm text-[rgba(245,245,247,0.6)]">
                      {formatRate(campaign.total_opened, campaign.total_sent)}
                    </td>

                    {/* Click Rate */}
                    <td className="px-6 py-4 text-sm text-[rgba(245,245,247,0.6)]">
                      {formatRate(campaign.total_clicked, campaign.total_sent)}
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-1">
                        {/* Edit - only drafts */}
                        {campaign.status === 'draft' && (
                          <Link
                            to={`/dashboard/newsletter/campaigns/${campaign.id}/edit`}
                            className="p-2 rounded-lg text-[rgba(245,245,247,0.6)] hover:text-[rgba(245,245,247,0.92)] hover:bg-white/[0.06] transition-colors"
                            title="Edit"
                          >
                            <PencilIcon className="h-4 w-4" />
                          </Link>
                        )}

                        {/* Duplicate */}
                        <button
                          onClick={() => handleDuplicate(campaign)}
                          disabled={duplicateCampaign.isPending}
                          className="p-2 rounded-lg text-[rgba(245,245,247,0.6)] hover:text-[rgba(245,245,247,0.92)] hover:bg-white/[0.06] transition-colors disabled:opacity-40"
                          title="Duplicate"
                        >
                          <DocumentDuplicateIcon className="h-4 w-4" />
                        </button>

                        {/* Analytics - only sent */}
                        {campaign.status === 'sent' && (
                          <Link
                            to={`/dashboard/newsletter/campaigns/${campaign.id}/analytics`}
                            className="p-2 rounded-lg text-[rgba(245,245,247,0.6)] hover:text-[rgba(245,245,247,0.92)] hover:bg-white/[0.06] transition-colors"
                            title="Analytics"
                          >
                            <ChartBarIcon className="h-4 w-4" />
                          </Link>
                        )}

                        {/* Send - only drafts */}
                        {campaign.status === 'draft' && (
                          <button
                            onClick={() => handleSend(campaign)}
                            disabled={sendCampaign.isPending}
                            className="p-2 rounded-lg text-[#00c7be] hover:text-[#00b5ad] hover:bg-[#00c7be]/10 transition-colors disabled:opacity-40"
                            title="Send"
                          >
                            <PaperAirplaneIcon className="h-4 w-4" />
                          </button>
                        )}

                        {/* Delete - only drafts */}
                        {campaign.status === 'draft' && (
                          <button
                            onClick={() => handleDelete(campaign)}
                            disabled={deleteCampaign.isPending}
                            className="p-2 rounded-lg text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors disabled:opacity-40"
                            title="Delete"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!isLoading && total > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-white/[0.06] px-6 py-3">
            <span className="text-sm text-[rgba(245,245,247,0.35)]">
              Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of{' '}
              {formatNumber(total)} campaigns
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setOffset((prev) => Math.max(0, prev - PAGE_SIZE))}
                disabled={!hasPrevPage}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-lg border transition-colors',
                  hasPrevPage
                    ? 'border-white/[0.08] text-[rgba(245,245,247,0.92)] hover:bg-white/[0.06] cursor-pointer'
                    : 'border-white/[0.04] text-[rgba(245,245,247,0.2)] cursor-not-allowed',
                )}
              >
                Previous
              </button>
              <button
                onClick={() => setOffset((prev) => prev + PAGE_SIZE)}
                disabled={!hasNextPage}
                className={cn(
                  'px-3 py-1.5 text-sm rounded-lg border transition-colors',
                  hasNextPage
                    ? 'border-white/[0.08] text-[rgba(245,245,247,0.92)] hover:bg-white/[0.06] cursor-pointer'
                    : 'border-white/[0.04] text-[rgba(245,245,247,0.2)] cursor-not-allowed',
                )}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
