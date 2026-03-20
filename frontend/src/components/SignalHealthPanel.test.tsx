import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SignalHealthPanel } from './SignalHealthPanel';

// Mock the trustLayer API hooks
const mockRefetch = vi.fn();
vi.mock('@/api/trustLayer', () => ({
  useSignalHealth: vi.fn(),
  getStatusLabel: (status: string) => {
    const labels: Record<string, string> = {
      ok: 'Healthy',
      risk: 'At Risk',
      degraded: 'Degraded',
      critical: 'Critical',
      no_data: 'No Data',
    };
    return labels[status] || status;
  },
}));

vi.mock('@/stores/featureFlagsStore', () => ({
  useCanFeature: vi.fn(),
}));

import { useSignalHealth } from '@/api/trustLayer';
import { useCanFeature } from '@/stores/featureFlagsStore';

const mockUseSignalHealth = useSignalHealth as ReturnType<typeof vi.fn>;
const mockUseCanFeature = useCanFeature as ReturnType<typeof vi.fn>;

const healthyData = {
  status: 'ok',
  date: '2025-12-15',
  automation_blocked: false,
  cards: [
    { title: 'Overall EMQ', value: '92%', status: 'ok', description: 'Excellent' },
    { title: 'Event Loss', value: '1.2%', status: 'ok', description: 'Below threshold' },
    { title: 'Freshness', value: '15 min', status: 'ok', description: 'Real-time' },
    { title: 'API Health', value: '99.5%', status: 'ok', description: 'All systems go' },
  ],
  platform_rows: [
    {
      platform: 'meta',
      account_id: 'act_12345',
      emq_score: 95,
      event_loss_pct: 1.2,
      freshness_minutes: 15,
      api_error_rate: 0.5,
      status: 'ok',
    },
    {
      platform: 'google',
      account_id: 'cust_67890',
      emq_score: 88,
      event_loss_pct: 3.5,
      freshness_minutes: 45,
      api_error_rate: 1.5,
      status: 'ok',
    },
  ],
  issues: [],
  actions: [],
};

describe('SignalHealthPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCanFeature.mockReturnValue(true);
  });

  it('renders loading skeleton when data is loading', () => {
    mockUseSignalHealth.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
      refetch: mockRefetch,
    });

    const { container } = render(<SignalHealthPanel tenantId={1} />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders error state with retry button', () => {
    mockUseSignalHealth.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} />);
    expect(screen.getByText('Failed to load signal health data.')).toBeInTheDocument();
    expect(screen.getByText('Try again')).toBeInTheDocument();
  });

  it('calls refetch when retry button is clicked', () => {
    mockUseSignalHealth.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} />);
    fireEvent.click(screen.getByText('Try again'));
    expect(mockRefetch).toHaveBeenCalled();
  });

  it('renders feature disabled message when signal_health feature is off', () => {
    mockUseCanFeature.mockReturnValue(false);
    mockUseSignalHealth.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} />);
    expect(
      screen.getByText('Signal Health feature is not enabled for your plan.')
    ).toBeInTheDocument();
  });

  it('renders healthy signal health data with metric cards', () => {
    mockUseSignalHealth.mockReturnValue({
      data: healthyData,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} />);
    expect(screen.getByText('Signal Health')).toBeInTheDocument();
    expect(screen.getByText('Healthy')).toBeInTheDocument();
    expect(screen.getByText('Overall EMQ')).toBeInTheDocument();
    expect(screen.getByText('Event Loss')).toBeInTheDocument();
    expect(screen.getByText('Freshness')).toBeInTheDocument();
    expect(screen.getByText('API Health')).toBeInTheDocument();
  });

  it('renders platform rows in the table', () => {
    mockUseSignalHealth.mockReturnValue({
      data: healthyData,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} />);
    expect(screen.getByText('meta')).toBeInTheDocument();
    expect(screen.getByText('google')).toBeInTheDocument();
    expect(screen.getByText('act_12345')).toBeInTheDocument();
    expect(screen.getByText('95%')).toBeInTheDocument();
  });

  it('shows automation blocked badge when automation is blocked', () => {
    const blockedData = {
      ...healthyData,
      status: 'critical',
      automation_blocked: true,
    };
    mockUseSignalHealth.mockReturnValue({
      data: blockedData,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} />);
    expect(screen.getByText('Automation Blocked')).toBeInTheDocument();
  });

  it('collapses content when header is clicked', () => {
    mockUseSignalHealth.mockReturnValue({
      data: healthyData,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} />);
    // Content is expanded by default (compact=false)
    expect(screen.getByText('Overall EMQ')).toBeInTheDocument();

    // Click header to collapse
    fireEvent.click(screen.getByText('Signal Health'));
    expect(screen.queryByText('Overall EMQ')).not.toBeInTheDocument();
  });

  it('starts collapsed in compact mode', () => {
    mockUseSignalHealth.mockReturnValue({
      data: healthyData,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} compact />);
    // In compact mode, content should be collapsed
    expect(screen.queryByText('Overall EMQ')).not.toBeInTheDocument();
  });

  it('renders issues and recommended actions when present', () => {
    const dataWithIssues = {
      ...healthyData,
      status: 'degraded',
      issues: ['Meta EMQ score below threshold', 'High event loss on Google Ads'],
      actions: ['Check Meta CAPI configuration', 'Review server-side tagging'],
    };
    mockUseSignalHealth.mockReturnValue({
      data: dataWithIssues,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} />);
    expect(screen.getByText('Issues Detected')).toBeInTheDocument();
    expect(screen.getByText('Meta EMQ score below threshold')).toBeInTheDocument();
    expect(screen.getByText('Recommended Actions')).toBeInTheDocument();
    expect(screen.getByText('Check Meta CAPI configuration')).toBeInTheDocument();
  });

  it('renders empty state when no platform data or cards', () => {
    const emptyData = {
      ...healthyData,
      platform_rows: [],
      cards: [],
    };
    mockUseSignalHealth.mockReturnValue({
      data: emptyData,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    render(<SignalHealthPanel tenantId={1} />);
    expect(
      screen.getByText('No signal health data available for this date.')
    ).toBeInTheDocument();
  });

  it('returns null when data is undefined and not loading or error', () => {
    mockUseSignalHealth.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });

    const { container } = render(<SignalHealthPanel tenantId={1} />);
    expect(container.innerHTML).toBe('');
  });
});
