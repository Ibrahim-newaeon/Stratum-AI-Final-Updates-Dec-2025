import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TrustBanner, TrustBannerCompact } from './TrustBanner';

vi.mock('@/api/trustLayer', () => ({
  useTrustStatus: vi.fn(),
  getStatusLabel: (status: string) => {
    const labels: Record<string, string> = {
      ok: 'Healthy',
      healthy: 'Healthy',
      risk: 'At Risk',
      degraded: 'Degraded',
      critical: 'Critical',
      minor_variance: 'Minor Variance',
      moderate_variance: 'Moderate Variance',
      high_variance: 'High Variance',
      no_data: 'No Data',
    };
    return labels[status] || status;
  },
}));

vi.mock('@/stores/featureFlagsStore', () => ({
  useCanFeature: vi.fn(),
}));

import { useTrustStatus } from '@/api/trustLayer';
import { useCanFeature } from '@/stores/featureFlagsStore';

const mockUseTrustStatus = useTrustStatus as ReturnType<typeof vi.fn>;
const mockUseCanFeature = useCanFeature as ReturnType<typeof vi.fn>;

const healthyTrustStatus = {
  overall_status: 'ok',
  date: '2025-12-15',
  automation_allowed: true,
  signal_health: { status: 'ok', score: 92 },
  attribution_variance: { status: 'healthy', variance: 3.2 },
  banners: [],
};

const degradedTrustStatus = {
  overall_status: 'degraded',
  date: '2025-12-15',
  automation_allowed: false,
  signal_health: { status: 'degraded', score: 55 },
  attribution_variance: { status: 'moderate_variance', variance: 18 },
  banners: [
    {
      type: 'warning' as const,
      title: 'Signal health degraded',
      message: 'Meta Ads EMQ score has dropped below threshold.',
      actions: ['Check CAPI config', 'Review event mapping'],
    },
    {
      type: 'error' as const,
      title: 'Attribution variance high',
      message: 'Revenue attribution differs by 18% across platforms.',
      actions: ['Audit conversion tracking'],
    },
  ],
};

describe('TrustBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCanFeature.mockReturnValue(true);
  });

  it('renders nothing when both signal_health and attribution_variance features are disabled', () => {
    mockUseCanFeature.mockReturnValue(false);
    mockUseTrustStatus.mockReturnValue({
      data: healthyTrustStatus,
      isLoading: false,
      error: null,
    });

    const { container } = render(<TrustBanner tenantId={1} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders loading skeleton when loading', () => {
    mockUseTrustStatus.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    const { container } = render(<TrustBanner tenantId={1} />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders nothing when there is an error', () => {
    mockUseTrustStatus.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed'),
    });

    const { container } = render(<TrustBanner tenantId={1} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders healthy trust status with correct indicators', () => {
    mockUseTrustStatus.mockReturnValue({
      data: healthyTrustStatus,
      isLoading: false,
      error: null,
    });

    render(<TrustBanner tenantId={1} />);
    expect(screen.getByText('Trust Status:')).toBeInTheDocument();
    // Should show "Healthy" status labels
    const healthyElements = screen.getAllByText('Healthy');
    expect(healthyElements.length).toBeGreaterThanOrEqual(1);
  });

  it('renders signal health and attribution sections', () => {
    mockUseTrustStatus.mockReturnValue({
      data: healthyTrustStatus,
      isLoading: false,
      error: null,
    });

    render(<TrustBanner tenantId={1} />);
    expect(screen.getByText('Signal Health:')).toBeInTheDocument();
    expect(screen.getByText('Attribution:')).toBeInTheDocument();
  });

  it('shows Automation Blocked badge when automation is not allowed', () => {
    mockUseTrustStatus.mockReturnValue({
      data: degradedTrustStatus,
      isLoading: false,
      error: null,
    });

    render(<TrustBanner tenantId={1} />);
    expect(screen.getByText('Automation Blocked')).toBeInTheDocument();
  });

  it('renders alert banners for degraded trust status', () => {
    mockUseTrustStatus.mockReturnValue({
      data: degradedTrustStatus,
      isLoading: false,
      error: null,
    });

    render(<TrustBanner tenantId={1} />);
    expect(screen.getByText('Signal health degraded')).toBeInTheDocument();
    expect(screen.getByText(/Meta Ads EMQ score has dropped/)).toBeInTheDocument();
    expect(screen.getByText('Attribution variance high')).toBeInTheDocument();
    expect(screen.getByText('Check CAPI config')).toBeInTheDocument();
    expect(screen.getByText('Audit conversion tracking')).toBeInTheDocument();
  });

  it('renders View Details button when onViewDetails is provided', () => {
    mockUseTrustStatus.mockReturnValue({
      data: healthyTrustStatus,
      isLoading: false,
      error: null,
    });

    const onViewDetails = vi.fn();
    render(<TrustBanner tenantId={1} onViewDetails={onViewDetails} />);
    const button = screen.getByText('View Details');
    fireEvent.click(button);
    expect(onViewDetails).toHaveBeenCalled();
  });

  it('displays the date indicator', () => {
    mockUseTrustStatus.mockReturnValue({
      data: healthyTrustStatus,
      isLoading: false,
      error: null,
    });

    render(<TrustBanner tenantId={1} />);
    expect(screen.getByText(/Data as of:/)).toBeInTheDocument();
  });
});

describe('TrustBannerCompact', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCanFeature.mockReturnValue(true);
  });

  it('renders nothing when overall status is ok and no banners', () => {
    mockUseTrustStatus.mockReturnValue({
      data: healthyTrustStatus,
      isLoading: false,
      error: null,
    });

    const { container } = render(<TrustBannerCompact tenantId={1} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders compact banner when status is degraded', () => {
    mockUseTrustStatus.mockReturnValue({
      data: degradedTrustStatus,
      isLoading: false,
      error: null,
    });

    render(<TrustBannerCompact tenantId={1} />);
    expect(screen.getByText('Signal health degraded')).toBeInTheDocument();
  });

  it('calls onViewDetails when compact banner is clicked', () => {
    mockUseTrustStatus.mockReturnValue({
      data: degradedTrustStatus,
      isLoading: false,
      error: null,
    });

    const onViewDetails = vi.fn();
    render(<TrustBannerCompact tenantId={1} onViewDetails={onViewDetails} />);
    fireEvent.click(screen.getByLabelText('View trust status details'));
    expect(onViewDetails).toHaveBeenCalled();
  });

  it('renders nothing when features are disabled', () => {
    mockUseCanFeature.mockReturnValue(false);
    mockUseTrustStatus.mockReturnValue({
      data: degradedTrustStatus,
      isLoading: false,
      error: null,
    });

    const { container } = render(<TrustBannerCompact tenantId={1} />);
    expect(container.innerHTML).toBe('');
  });

  it('renders nothing while loading', () => {
    mockUseTrustStatus.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    const { container } = render(<TrustBannerCompact tenantId={1} />);
    expect(container.innerHTML).toBe('');
  });
});
