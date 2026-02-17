/**
 * Portal Dashboard - Read-only client/viewer dashboard
 *
 * Shows campaign performance metrics and recent campaigns for portal (VIEWER)
 * users. Includes a "Request Changes" modal for submitting client requests.
 * Uses placeholder data until connected to real APIs.
 */

import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  CursorArrowRaysIcon,
  MegaphoneIcon,
  XMarkIcon,
  PaperAirplaneIcon,
  CheckCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';

// ── Theme ──────────────────────────────────────────────────────────────────
const theme = {
  bgBase: '#0b1215',
  bgCard: 'rgba(255, 255, 255, 0.04)',
  bgCardHover: 'rgba(255, 255, 255, 0.06)',
  bgSurface: 'rgba(255, 255, 255, 0.03)',
  bgInput: 'rgba(255, 255, 255, 0.05)',
  primary: '#00c7be',
  primaryLight: 'rgba(0, 199, 190, 0.15)',
  textPrimary: 'rgba(245, 245, 247, 0.92)',
  textSecondary: 'rgba(245, 245, 247, 0.6)',
  textMuted: 'rgba(245, 245, 247, 0.4)',
  border: 'rgba(255, 255, 255, 0.08)',
  success: '#34c759',
  danger: '#ef4444',
  warning: '#f59e0b',
};

// ── Types ──────────────────────────────────────────────────────────────────
interface MetricCard {
  title: string;
  value: string;
  change: string;
  changeType: 'positive' | 'negative' | 'neutral';
  icon: React.ComponentType<{ className?: string }>;
}

interface Campaign {
  id: string;
  name: string;
  platform: string;
  status: 'active' | 'paused' | 'completed';
  spend: string;
  roas: string;
  conversions: number;
  lastUpdated: string;
}

interface ClientRequest {
  type: 'budget_change' | 'creative_update' | 'targeting_change' | 'pause_campaign' | 'general';
  campaignName: string;
  description: string;
}

// ── Placeholder Data ───────────────────────────────────────────────────────
const MOCK_METRICS: MetricCard[] = [
  {
    title: 'ROAS',
    value: '4.2x',
    change: '+0.3x vs last month',
    changeType: 'positive',
    icon: ArrowTrendingUpIcon,
  },
  {
    title: 'Total Spend',
    value: '$24,580',
    change: '+12% vs last month',
    changeType: 'neutral',
    icon: CurrencyDollarIcon,
  },
  {
    title: 'Conversions',
    value: '1,847',
    change: '+18% vs last month',
    changeType: 'positive',
    icon: ChartBarIcon,
  },
  {
    title: 'CTR',
    value: '3.24%',
    change: '-0.1% vs last month',
    changeType: 'negative',
    icon: CursorArrowRaysIcon,
  },
];

const MOCK_CAMPAIGNS: Campaign[] = [
  {
    id: 'c1',
    name: 'Summer Sale - Search',
    platform: 'Google Ads',
    status: 'active',
    spend: '$8,420',
    roas: '5.1x',
    conversions: 642,
    lastUpdated: '2 hours ago',
  },
  {
    id: 'c2',
    name: 'Brand Awareness - Social',
    platform: 'Meta Ads',
    status: 'active',
    spend: '$6,230',
    roas: '3.8x',
    conversions: 489,
    lastUpdated: '4 hours ago',
  },
  {
    id: 'c3',
    name: 'Retargeting - Display',
    platform: 'Google Ads',
    status: 'active',
    spend: '$4,150',
    roas: '4.5x',
    conversions: 384,
    lastUpdated: '6 hours ago',
  },
  {
    id: 'c4',
    name: 'Product Launch - Video',
    platform: 'TikTok Ads',
    status: 'paused',
    spend: '$3,280',
    roas: '2.9x',
    conversions: 198,
    lastUpdated: '1 day ago',
  },
  {
    id: 'c5',
    name: 'Holiday Promo - Shopping',
    platform: 'Google Ads',
    status: 'completed',
    spend: '$2,500',
    roas: '6.2x',
    conversions: 134,
    lastUpdated: '3 days ago',
  },
];

const REQUEST_TYPES: { value: ClientRequest['type']; label: string }[] = [
  { value: 'budget_change', label: 'Budget Change' },
  { value: 'creative_update', label: 'Creative Update' },
  { value: 'targeting_change', label: 'Targeting Change' },
  { value: 'pause_campaign', label: 'Pause / Resume Campaign' },
  { value: 'general', label: 'General Request' },
];

// ── Helpers ────────────────────────────────────────────────────────────────
function statusBadge(status: Campaign['status']): { bg: string; text: string; label: string } {
  switch (status) {
    case 'active':
      return { bg: 'rgba(52, 199, 89, 0.15)', text: theme.success, label: 'Active' };
    case 'paused':
      return { bg: 'rgba(245, 158, 11, 0.15)', text: theme.warning, label: 'Paused' };
    case 'completed':
      return { bg: 'rgba(245, 245, 247, 0.08)', text: theme.textSecondary, label: 'Completed' };
  }
}

// ── Component ──────────────────────────────────────────────────────────────
export default function PortalDashboard() {
  const { user } = useAuth();
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [requestSubmitted, setRequestSubmitted] = useState(false);
  const [requestForm, setRequestForm] = useState<ClientRequest>({
    type: 'general',
    campaignName: '',
    description: '',
  });

  const clientName = user?.name || user?.organization || 'Client';

  const handleSubmitRequest = () => {
    // Placeholder: will connect to real API later
    console.log('Client request submitted:', requestForm);
    setRequestSubmitted(true);
    setTimeout(() => {
      setShowRequestModal(false);
      setRequestSubmitted(false);
      setRequestForm({ type: 'general', campaignName: '', description: '' });
    }, 2000);
  };

  return (
    <div className="min-h-screen p-6 md:p-8" style={{ background: theme.bgBase }}>
      {/* ── Welcome Header ─────────────────────────────────────────────── */}
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ color: theme.textPrimary }}>
          Welcome back, {clientName}
        </h1>
        <p className="text-sm" style={{ color: theme.textSecondary }}>
          Here is an overview of your campaign performance. Data refreshes automatically.
        </p>
      </div>

      {/* ── Metric Cards ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {MOCK_METRICS.map((metric) => {
          const Icon = metric.icon;
          return (
            <div
              key={metric.title}
              className="rounded-xl p-5 transition-colors duration-200"
              style={{
                background: theme.bgCard,
                border: `1px solid ${theme.border}`,
              }}
            >
              <div className="flex items-center gap-3 mb-3">
                <div
                  className="p-2 rounded-lg"
                  style={{ background: theme.primaryLight }}
                >
                  <span style={{ color: theme.primary }}><Icon className="h-5 w-5" /></span>
                </div>
                <span className="text-sm font-medium" style={{ color: theme.textSecondary }}>
                  {metric.title}
                </span>
              </div>
              <p className="text-2xl font-bold mb-1" style={{ color: theme.textPrimary }}>
                {metric.value}
              </p>
              <div className="flex items-center gap-1.5">
                {metric.changeType === 'positive' && (
                  <ArrowTrendingUpIcon className="h-3.5 w-3.5" style={{ color: theme.success }} />
                )}
                {metric.changeType === 'negative' && (
                  <ArrowTrendingDownIcon className="h-3.5 w-3.5" style={{ color: theme.danger }} />
                )}
                <span
                  className="text-xs"
                  style={{
                    color:
                      metric.changeType === 'positive'
                        ? theme.success
                        : metric.changeType === 'negative'
                          ? theme.danger
                          : theme.textMuted,
                  }}
                >
                  {metric.change}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Recent Campaigns ───────────────────────────────────────────── */}
      <div
        className="rounded-xl overflow-hidden mb-6"
        style={{
          background: theme.bgCard,
          border: `1px solid ${theme.border}`,
        }}
      >
        <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <div className="flex items-center gap-2">
            <MegaphoneIcon className="h-5 w-5" style={{ color: theme.primary }} />
            <h2 className="text-lg font-semibold" style={{ color: theme.textPrimary }}>
              Recent Campaigns
            </h2>
          </div>
          <span className="text-xs" style={{ color: theme.textMuted }}>
            {MOCK_CAMPAIGNS.length} campaigns
          </span>
        </div>

        {/* Table Header */}
        <div
          className="hidden md:grid grid-cols-7 gap-4 px-6 py-3 text-xs font-medium uppercase tracking-wider"
          style={{ color: theme.textMuted, borderBottom: `1px solid ${theme.border}` }}
        >
          <div className="col-span-2">Campaign</div>
          <div>Platform</div>
          <div>Status</div>
          <div className="text-right">Spend</div>
          <div className="text-right">ROAS</div>
          <div className="text-right">Conversions</div>
        </div>

        {/* Rows */}
        {MOCK_CAMPAIGNS.map((campaign) => {
          const badge = statusBadge(campaign.status);
          return (
            <div
              key={campaign.id}
              className="grid grid-cols-1 md:grid-cols-7 gap-2 md:gap-4 px-6 py-4 items-center transition-colors duration-150"
              style={{ borderBottom: `1px solid ${theme.border}` }}
              onMouseEnter={(e) => (e.currentTarget.style.background = theme.bgCardHover)}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
            >
              <div className="col-span-2">
                <p className="font-medium text-sm" style={{ color: theme.textPrimary }}>
                  {campaign.name}
                </p>
                <p className="text-xs md:hidden mt-0.5" style={{ color: theme.textMuted }}>
                  {campaign.platform}
                </p>
              </div>
              <div className="hidden md:block text-sm" style={{ color: theme.textSecondary }}>
                {campaign.platform}
              </div>
              <div>
                <span
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                  style={{ background: badge.bg, color: badge.text }}
                >
                  {badge.label}
                </span>
              </div>
              <div className="text-sm text-right" style={{ color: theme.textPrimary }}>
                {campaign.spend}
              </div>
              <div className="text-sm text-right font-medium" style={{ color: theme.primary }}>
                {campaign.roas}
              </div>
              <div className="text-sm text-right" style={{ color: theme.textPrimary }}>
                {campaign.conversions.toLocaleString()}
              </div>
            </div>
          );
        })}

        {/* Footer with last-updated */}
        <div className="px-6 py-3 flex items-center gap-1.5" style={{ background: theme.bgSurface }}>
          <ClockIcon className="h-3.5 w-3.5" style={{ color: theme.textMuted }} />
          <span className="text-xs" style={{ color: theme.textMuted }}>
            Last updated: just now
          </span>
        </div>
      </div>

      {/* ── Request Changes Button ─────────────────────────────────────── */}
      <div className="flex justify-end">
        <button
          onClick={() => setShowRequestModal(true)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all duration-200"
          style={{
            background: theme.primary,
            color: '#000',
            boxShadow: `0 0 20px ${theme.primaryLight}`,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = `0 0 30px rgba(0, 199, 190, 0.35)`;
            e.currentTarget.style.transform = 'translateY(-1px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = `0 0 20px ${theme.primaryLight}`;
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          <PaperAirplaneIcon className="h-4 w-4" />
          Request Changes
        </button>
      </div>

      {/* ── Request Changes Modal ──────────────────────────────────────── */}
      {showRequestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div
            className="w-full max-w-lg rounded-2xl p-6"
            style={{
              background: 'rgba(11, 18, 21, 0.95)',
              border: `1px solid ${theme.border}`,
              boxShadow: '0 25px 50px rgba(0, 0, 0, 0.5)',
            }}
          >
            {requestSubmitted ? (
              /* ── Success state ── */
              <div className="text-center py-8">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
                  style={{ background: `${theme.success}20` }}
                >
                  <CheckCircleIcon className="h-8 w-8" style={{ color: theme.success }} />
                </div>
                <h3 className="text-xl font-semibold mb-2" style={{ color: theme.textPrimary }}>
                  Request Submitted
                </h3>
                <p className="text-sm" style={{ color: theme.textSecondary }}>
                  Your account manager will review this and get back to you shortly.
                </p>
              </div>
            ) : (
              /* ── Form state ── */
              <>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xl font-semibold" style={{ color: theme.textPrimary }}>
                    Request Changes
                  </h3>
                  <button
                    onClick={() => setShowRequestModal(false)}
                    className="p-1.5 rounded-lg transition-colors duration-150"
                    style={{ color: theme.textMuted }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = theme.bgCardHover)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                <div className="space-y-4">
                  {/* Request type */}
                  <div>
                    <label
                      className="block text-sm font-medium mb-1.5"
                      style={{ color: theme.textSecondary }}
                    >
                      Request Type
                    </label>
                    <select
                      value={requestForm.type}
                      onChange={(e) =>
                        setRequestForm((prev) => ({
                          ...prev,
                          type: e.target.value as ClientRequest['type'],
                        }))
                      }
                      className="w-full px-4 py-2.5 rounded-xl text-sm outline-none transition-all duration-200"
                      style={{
                        background: theme.bgInput,
                        border: `1px solid ${theme.border}`,
                        color: theme.textPrimary,
                      }}
                      onFocus={(e) => {
                        e.target.style.borderColor = theme.primary;
                        e.target.style.boxShadow = `0 0 0 2px ${theme.primaryLight}`;
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = theme.border;
                        e.target.style.boxShadow = 'none';
                      }}
                    >
                      {REQUEST_TYPES.map((rt) => (
                        <option key={rt.value} value={rt.value}>
                          {rt.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Campaign name */}
                  <div>
                    <label
                      className="block text-sm font-medium mb-1.5"
                      style={{ color: theme.textSecondary }}
                    >
                      Campaign Name (optional)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Summer Sale - Search"
                      value={requestForm.campaignName}
                      onChange={(e) =>
                        setRequestForm((prev) => ({ ...prev, campaignName: e.target.value }))
                      }
                      className="w-full px-4 py-2.5 rounded-xl text-sm outline-none transition-all duration-200"
                      style={{
                        background: theme.bgInput,
                        border: `1px solid ${theme.border}`,
                        color: theme.textPrimary,
                      }}
                      onFocus={(e) => {
                        e.target.style.borderColor = theme.primary;
                        e.target.style.boxShadow = `0 0 0 2px ${theme.primaryLight}`;
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = theme.border;
                        e.target.style.boxShadow = 'none';
                      }}
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <label
                      className="block text-sm font-medium mb-1.5"
                      style={{ color: theme.textSecondary }}
                    >
                      Description
                    </label>
                    <textarea
                      rows={4}
                      placeholder="Describe the changes you would like..."
                      value={requestForm.description}
                      onChange={(e) =>
                        setRequestForm((prev) => ({ ...prev, description: e.target.value }))
                      }
                      className="w-full px-4 py-2.5 rounded-xl text-sm outline-none resize-none transition-all duration-200"
                      style={{
                        background: theme.bgInput,
                        border: `1px solid ${theme.border}`,
                        color: theme.textPrimary,
                      }}
                      onFocus={(e) => {
                        e.target.style.borderColor = theme.primary;
                        e.target.style.boxShadow = `0 0 0 2px ${theme.primaryLight}`;
                      }}
                      onBlur={(e) => {
                        e.target.style.borderColor = theme.border;
                        e.target.style.boxShadow = 'none';
                      }}
                    />
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-3 mt-6">
                  <button
                    onClick={() => setShowRequestModal(false)}
                    className="px-4 py-2 rounded-xl text-sm font-medium transition-colors duration-150"
                    style={{ color: theme.textSecondary, border: `1px solid ${theme.border}` }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = theme.bgCardHover)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSubmitRequest}
                    disabled={!requestForm.description.trim()}
                    className="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-semibold transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
                    style={{
                      background: theme.primary,
                      color: '#000',
                    }}
                    onMouseEnter={(e) => {
                      if (requestForm.description.trim()) {
                        e.currentTarget.style.boxShadow = `0 0 20px ${theme.primaryLight}`;
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    <PaperAirplaneIcon className="h-4 w-4" />
                    Submit Request
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
