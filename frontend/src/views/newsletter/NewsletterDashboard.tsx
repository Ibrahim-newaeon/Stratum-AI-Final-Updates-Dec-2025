/**
 * Newsletter Dashboard - Main overview page for Newsletter & Email Campaigns
 */

import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  DocumentTextIcon,
  UserGroupIcon,
  EnvelopeOpenIcon,
  CursorArrowRaysIcon,
  PlusCircleIcon,
  QueueListIcon,
  UsersIcon,
} from '@heroicons/react/24/outline';
import {
  useCampaigns,
  useSubscriberStats,
  useTemplates,
  type NewsletterCampaign,
  type CampaignStatus,
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
// StatCard Component
// ---------------------------------------------------------------------------
function StatCard({
  title,
  value,
  icon: Icon,
  loading,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  loading?: boolean;
}) {
  return (
    <div
      style={{
        background: theme.bgCard,
        border: `1px solid ${theme.border}`,
        borderRadius: '1rem',
        padding: '1.5rem',
        backdropFilter: 'blur(12px)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ flex: 1 }}>
          <p
            style={{
              fontSize: '0.875rem',
              fontWeight: 500,
              color: theme.textSecondary,
              margin: 0,
            }}
          >
            {title}
          </p>
          {loading ? (
            <div
              style={{
                height: '2rem',
                width: '6rem',
                background: 'rgba(255,255,255,0.08)',
                borderRadius: '0.375rem',
                marginTop: '0.5rem',
                animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
              }}
            />
          ) : (
            <p
              style={{
                fontSize: '1.5rem',
                fontWeight: 700,
                color: theme.textPrimary,
                margin: 0,
                marginTop: '0.5rem',
              }}
            >
              {value}
            </p>
          )}
        </div>
        <div
          style={{
            height: '3rem',
            width: '3rem',
            borderRadius: '0.75rem',
            background: theme.primaryLight,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Icon style={{ height: '1.5rem', width: '1.5rem', color: theme.primary }} />
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status Badge
// ---------------------------------------------------------------------------
const statusColors: Record<CampaignStatus, { bg: string; text: string }> = {
  draft: { bg: 'rgba(156, 163, 175, 0.2)', text: 'rgb(156, 163, 175)' },
  scheduled: { bg: 'rgba(96, 165, 250, 0.2)', text: 'rgb(96, 165, 250)' },
  sending: { bg: 'rgba(251, 191, 36, 0.2)', text: 'rgb(251, 191, 36)' },
  sent: { bg: 'rgba(74, 222, 128, 0.2)', text: 'rgb(74, 222, 128)' },
  paused: { bg: 'rgba(251, 146, 60, 0.2)', text: 'rgb(251, 146, 60)' },
  cancelled: { bg: 'rgba(248, 113, 113, 0.2)', text: 'rgb(248, 113, 113)' },
};

function StatusBadge({ status }: { status: CampaignStatus }) {
  const colors = statusColors[status] || statusColors.draft;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '0.25rem 0.75rem',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600,
        background: colors.bg,
        color: colors.text,
        textTransform: 'capitalize',
      }}
    >
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Subscriber Overview Chart (horizontal bars)
// ---------------------------------------------------------------------------
function SubscriberOverviewChart({
  active,
  unsubscribed,
}: {
  active: number;
  unsubscribed: number;
}) {
  const total = active + unsubscribed;
  const segments = [
    { label: 'Active', count: active, color: '#4ade80' },
    { label: 'Unsubscribed', count: unsubscribed, color: '#f87171' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {segments.map((seg) => {
        const pct = total > 0 ? (seg.count / total) * 100 : 0;
        return (
          <div key={seg.label}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '0.875rem',
                marginBottom: '0.25rem',
              }}
            >
              <span style={{ fontWeight: 500, color: theme.textPrimary }}>{seg.label}</span>
              <span style={{ color: theme.textSecondary }}>
                {seg.count.toLocaleString()} ({pct.toFixed(1)}%)
              </span>
            </div>
            <div
              style={{
                height: '0.5rem',
                background: 'rgba(255,255,255,0.08)',
                borderRadius: '9999px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${pct}%`,
                  background: seg.color,
                  borderRadius: '9999px',
                  transition: 'width 0.5s ease',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------
export default function NewsletterDashboard() {
  const { data: campaignData, isLoading: campaignsLoading } = useCampaigns({});
  const { data: subscriberStats, isLoading: subscriberLoading } = useSubscriberStats();
  const { isLoading: templatesLoading } = useTemplates();

  // Calculate average open & click rates from sent campaigns
  const { avgOpenRate, avgClickRate, recentCampaigns } = useMemo(() => {
    const campaigns = campaignData?.campaigns || [];

    const sentCampaigns = campaigns.filter(
      (c: NewsletterCampaign) => c.status === 'sent' && c.total_sent > 0
    );

    let openRate = 0;
    let clickRate = 0;

    if (sentCampaigns.length > 0) {
      const totalOpen = sentCampaigns.reduce(
        (sum: number, c: NewsletterCampaign) => sum + (c.total_opened / c.total_sent) * 100,
        0
      );
      const totalClick = sentCampaigns.reduce(
        (sum: number, c: NewsletterCampaign) => sum + (c.total_clicked / c.total_sent) * 100,
        0
      );
      openRate = totalOpen / sentCampaigns.length;
      clickRate = totalClick / sentCampaigns.length;
    }

    // Sort by created_at desc, take last 5
    const sorted = [...campaigns].sort(
      (a: NewsletterCampaign, b: NewsletterCampaign) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    return {
      avgOpenRate: openRate,
      avgClickRate: clickRate,
      recentCampaigns: sorted.slice(0, 5),
    };
  }, [campaignData]);

  const isLoading = campaignsLoading || subscriberLoading || templatesLoading;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header */}
      <div>
        <h1
          style={{
            fontSize: '1.5rem',
            fontWeight: 700,
            color: theme.textPrimary,
            margin: 0,
          }}
        >
          Newsletter & Email Campaigns
        </h1>
        <p
          style={{
            color: theme.textSecondary,
            marginTop: '0.25rem',
            fontSize: '0.875rem',
          }}
        >
          Manage campaigns, track engagement, and grow your subscriber base
        </p>
      </div>

      {/* Stats Cards Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1rem',
        }}
      >
        <StatCard
          title="Total Campaigns"
          value={campaignData?.total?.toLocaleString() || '0'}
          icon={DocumentTextIcon}
          loading={campaignsLoading}
        />
        <StatCard
          title="Active Subscribers"
          value={subscriberStats?.active?.toLocaleString() || '0'}
          icon={UserGroupIcon}
          loading={subscriberLoading}
        />
        <StatCard
          title="Avg Open Rate"
          value={isLoading ? '...' : `${avgOpenRate.toFixed(1)}%`}
          icon={EnvelopeOpenIcon}
          loading={campaignsLoading}
        />
        <StatCard
          title="Avg Click Rate"
          value={isLoading ? '...' : `${avgClickRate.toFixed(1)}%`}
          icon={CursorArrowRaysIcon}
          loading={campaignsLoading}
        />
      </div>

      {/* Main Content: Table + Sidebar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 20rem',
          gap: '1.5rem',
        }}
      >
        {/* Recent Campaigns Table */}
        <div
          style={{
            background: theme.bgCard,
            border: `1px solid ${theme.border}`,
            borderRadius: '1rem',
            padding: '1.5rem',
            backdropFilter: 'blur(12px)',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1rem',
            }}
          >
            <h3
              style={{
                fontSize: '1.125rem',
                fontWeight: 600,
                color: theme.textPrimary,
                margin: 0,
              }}
            >
              Recent Campaigns
            </h3>
            <Link
              to="/dashboard/newsletter/campaigns"
              style={{
                fontSize: '0.875rem',
                color: theme.primary,
                textDecoration: 'none',
              }}
            >
              View all
            </Link>
          </div>

          {campaignsLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  style={{
                    height: '2.5rem',
                    background: 'rgba(255,255,255,0.08)',
                    borderRadius: '0.375rem',
                    animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                  }}
                />
              ))}
            </div>
          ) : recentCampaigns.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '3rem 1rem',
                color: theme.textMuted,
              }}
            >
              <DocumentTextIcon
                style={{ height: '2.5rem', width: '2.5rem', margin: '0 auto 0.75rem' }}
              />
              <p style={{ margin: 0, fontSize: '0.875rem' }}>No campaigns yet</p>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem' }}>
                Create your first campaign to get started
              </p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '0.875rem',
                }}
              >
                <thead>
                  <tr
                    style={{
                      borderBottom: `1px solid ${theme.border}`,
                    }}
                  >
                    {['Name', 'Status', 'Recipients', 'Open Rate', 'Click Rate', 'Sent Date'].map(
                      (col) => (
                        <th
                          key={col}
                          style={{
                            textAlign: 'left',
                            padding: '0.75rem 0.5rem',
                            color: theme.textMuted,
                            fontWeight: 500,
                            fontSize: '0.75rem',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                          }}
                        >
                          {col}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {recentCampaigns.map((campaign: NewsletterCampaign) => {
                    const openRate =
                      campaign.total_sent > 0
                        ? ((campaign.total_opened / campaign.total_sent) * 100).toFixed(1)
                        : '--';
                    const clickRate =
                      campaign.total_sent > 0
                        ? ((campaign.total_clicked / campaign.total_sent) * 100).toFixed(1)
                        : '--';
                    const sentDate = campaign.sent_at
                      ? new Date(campaign.sent_at).toLocaleDateString()
                      : '--';

                    return (
                      <tr
                        key={campaign.id}
                        style={{
                          borderBottom: `1px solid ${theme.border}`,
                        }}
                      >
                        <td
                          style={{
                            padding: '0.75rem 0.5rem',
                            color: theme.textPrimary,
                            fontWeight: 500,
                            maxWidth: '12rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {campaign.name}
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>
                          <StatusBadge status={campaign.status} />
                        </td>
                        <td
                          style={{
                            padding: '0.75rem 0.5rem',
                            color: theme.textSecondary,
                          }}
                        >
                          {campaign.total_recipients.toLocaleString()}
                        </td>
                        <td
                          style={{
                            padding: '0.75rem 0.5rem',
                            color: theme.textSecondary,
                          }}
                        >
                          {openRate === '--' ? openRate : `${openRate}%`}
                        </td>
                        <td
                          style={{
                            padding: '0.75rem 0.5rem',
                            color: theme.textSecondary,
                          }}
                        >
                          {clickRate === '--' ? clickRate : `${clickRate}%`}
                        </td>
                        <td
                          style={{
                            padding: '0.75rem 0.5rem',
                            color: theme.textSecondary,
                          }}
                        >
                          {sentDate}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Sidebar: Quick Actions + Subscriber Overview */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Quick Actions */}
          <div
            style={{
              background: theme.bgCard,
              border: `1px solid ${theme.border}`,
              borderRadius: '1rem',
              padding: '1.5rem',
              backdropFilter: 'blur(12px)',
            }}
          >
            <h3
              style={{
                fontSize: '1.125rem',
                fontWeight: 600,
                color: theme.textPrimary,
                margin: '0 0 1rem 0',
              }}
            >
              Quick Actions
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <Link
                to="/dashboard/newsletter/campaigns/new"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.75rem',
                  borderRadius: '0.75rem',
                  background: theme.primaryLight,
                  color: theme.primary,
                  textDecoration: 'none',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  transition: 'opacity 0.15s',
                }}
              >
                <PlusCircleIcon style={{ height: '1.25rem', width: '1.25rem' }} />
                New Campaign
              </Link>
              <Link
                to="/dashboard/newsletter/campaigns"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.75rem',
                  borderRadius: '0.75rem',
                  background: 'rgba(255,255,255,0.04)',
                  color: theme.textPrimary,
                  textDecoration: 'none',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  transition: 'opacity 0.15s',
                }}
              >
                <QueueListIcon style={{ height: '1.25rem', width: '1.25rem' }} />
                View All Campaigns
              </Link>
              <Link
                to="/dashboard/newsletter/subscribers"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  padding: '0.75rem',
                  borderRadius: '0.75rem',
                  background: 'rgba(255,255,255,0.04)',
                  color: theme.textPrimary,
                  textDecoration: 'none',
                  fontWeight: 500,
                  fontSize: '0.875rem',
                  transition: 'opacity 0.15s',
                }}
              >
                <UsersIcon style={{ height: '1.25rem', width: '1.25rem' }} />
                Manage Subscribers
              </Link>
            </div>
          </div>

          {/* Subscriber Overview */}
          <div
            style={{
              background: theme.bgCard,
              border: `1px solid ${theme.border}`,
              borderRadius: '1rem',
              padding: '1.5rem',
              backdropFilter: 'blur(12px)',
            }}
          >
            <h3
              style={{
                fontSize: '1.125rem',
                fontWeight: 600,
                color: theme.textPrimary,
                margin: '0 0 1rem 0',
              }}
            >
              Subscriber Overview
            </h3>
            {subscriberLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {[1, 2].map((i) => (
                  <div
                    key={i}
                    style={{
                      height: '2rem',
                      background: 'rgba(255,255,255,0.08)',
                      borderRadius: '0.375rem',
                      animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                    }}
                  />
                ))}
              </div>
            ) : subscriberStats ? (
              <>
                <SubscriberOverviewChart
                  active={subscriberStats.active}
                  unsubscribed={subscriberStats.unsubscribed}
                />
                <div
                  style={{
                    marginTop: '1rem',
                    paddingTop: '1rem',
                    borderTop: `1px solid ${theme.border}`,
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: '0.875rem',
                  }}
                >
                  <div>
                    <p style={{ color: theme.textMuted, margin: 0, fontSize: '0.75rem' }}>
                      Total Subscribers
                    </p>
                    <p
                      style={{
                        color: theme.textPrimary,
                        fontWeight: 600,
                        margin: '0.125rem 0 0',
                      }}
                    >
                      {subscriberStats.total.toLocaleString()}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ color: theme.textMuted, margin: 0, fontSize: '0.75rem' }}>
                      Retention Rate
                    </p>
                    <p
                      style={{
                        color: theme.primary,
                        fontWeight: 600,
                        margin: '0.125rem 0 0',
                      }}
                    >
                      {subscriberStats.total > 0
                        ? ((subscriberStats.active / subscriberStats.total) * 100).toFixed(1)
                        : '0.0'}
                      %
                    </p>
                  </div>
                </div>
              </>
            ) : (
              <p style={{ color: theme.textMuted, fontSize: '0.875rem', margin: 0 }}>
                No subscriber data available
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
