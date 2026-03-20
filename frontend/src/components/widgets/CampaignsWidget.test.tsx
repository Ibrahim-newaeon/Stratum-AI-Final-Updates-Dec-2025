import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CampaignsWidget } from './CampaignsWidget';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  TrendingUp: (props: any) => <svg data-testid="trending-up" {...props} />,
  TrendingDown: (props: any) => <svg data-testid="trending-down" {...props} />,
}));

// Mock utils
vi.mock('@/lib/utils', async () => {
  return {
    cn: (...args: any[]) => args.filter(Boolean).join(' '),
    formatCurrency: (value: number) =>
      new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(value),
    getPlatformColor: (platform: string) => {
      const colors: Record<string, string> = { meta: '#1877F2', google: '#EA4335', tiktok: '#000000' };
      return colors[platform] || '#666666';
    },
  };
});

// Mock DashboardSimulationContext
const mockUseDashboardSimulation = vi.fn();
vi.mock('@/contexts/DashboardSimulationContext', () => ({
  useDashboardSimulation: () => mockUseDashboardSimulation(),
}));

const sampleCampaigns = [
  {
    campaign_id: 1,
    campaign_name: 'Summer Brand Awareness',
    platform: 'Meta Ads',
    status: 'Active',
    roas: 4.5,
    spend: 12000,
  },
  {
    campaign_id: 2,
    campaign_name: 'Search Retargeting',
    platform: 'Google Ads',
    status: 'Active',
    roas: 3.8,
    spend: 8500,
  },
  {
    campaign_id: 3,
    campaign_name: 'TikTok Viral Push',
    platform: 'TikTok Ads',
    status: 'Active',
    roas: 2.5,
    spend: 5000,
  },
  {
    campaign_id: 4,
    campaign_name: 'Low Performer',
    platform: 'Meta Ads',
    status: 'Active',
    roas: 1.2,
    spend: 3000,
  },
  {
    campaign_id: 5,
    campaign_name: 'Paused Campaign',
    platform: 'Google Ads',
    status: 'Paused',
    roas: 3.0,
    spend: 0,
  },
];

describe('CampaignsWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton when no campaigns exist', () => {
    mockUseDashboardSimulation.mockReturnValue({ campaigns: [] });
    const { container } = render(<CampaignsWidget />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders loading skeleton when campaigns is undefined', () => {
    mockUseDashboardSimulation.mockReturnValue({ campaigns: undefined });
    const { container } = render(<CampaignsWidget />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders top active campaigns sorted by ROAS', () => {
    mockUseDashboardSimulation.mockReturnValue({ campaigns: sampleCampaigns });
    render(<CampaignsWidget />);
    // Should show active campaigns only, sorted by ROAS descending
    expect(screen.getByText('Summer Brand Awareness')).toBeInTheDocument();
    expect(screen.getByText('Search Retargeting')).toBeInTheDocument();
    expect(screen.getByText('TikTok Viral Push')).toBeInTheDocument();
    expect(screen.getByText('Low Performer')).toBeInTheDocument();
    // Paused campaign should not be shown
    expect(screen.queryByText('Paused Campaign')).not.toBeInTheDocument();
  });

  it('renders ROAS values for each campaign', () => {
    mockUseDashboardSimulation.mockReturnValue({ campaigns: sampleCampaigns });
    render(<CampaignsWidget />);
    expect(screen.getByText('4.5x')).toBeInTheDocument();
    expect(screen.getByText('3.8x')).toBeInTheDocument();
    expect(screen.getByText('2.5x')).toBeInTheDocument();
    expect(screen.getByText('1.2x')).toBeInTheDocument();
  });

  it('renders spend amounts formatted as currency', () => {
    mockUseDashboardSimulation.mockReturnValue({ campaigns: sampleCampaigns });
    render(<CampaignsWidget />);
    expect(screen.getByText('$12,000 spent')).toBeInTheDocument();
    expect(screen.getByText('$8,500 spent')).toBeInTheDocument();
  });

  it('shows trending up icon for high ROAS campaigns', () => {
    mockUseDashboardSimulation.mockReturnValue({ campaigns: sampleCampaigns });
    render(<CampaignsWidget />);
    // ROAS >= 3.5 should show trending up
    const trendUpIcons = screen.getAllByTestId('trending-up');
    expect(trendUpIcons.length).toBeGreaterThanOrEqual(1);
  });

  it('shows trending down icon for low ROAS campaigns', () => {
    mockUseDashboardSimulation.mockReturnValue({ campaigns: sampleCampaigns });
    render(<CampaignsWidget />);
    // ROAS < 2.0 should show trending down
    const trendDownIcons = screen.getAllByTestId('trending-down');
    expect(trendDownIcons.length).toBeGreaterThanOrEqual(1);
  });

  it('limits display to top 5 campaigns', () => {
    const manyCampaigns = Array.from({ length: 10 }, (_, i) => ({
      campaign_id: i + 1,
      campaign_name: `Campaign ${i + 1}`,
      platform: 'Meta Ads',
      status: 'Active',
      roas: 5 - i * 0.3,
      spend: 10000 - i * 500,
    }));
    mockUseDashboardSimulation.mockReturnValue({ campaigns: manyCampaigns });
    render(<CampaignsWidget />);
    // Only top 5 active campaigns should appear
    expect(screen.getByText('Campaign 1')).toBeInTheDocument();
    expect(screen.getByText('Campaign 5')).toBeInTheDocument();
    expect(screen.queryByText('Campaign 6')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    mockUseDashboardSimulation.mockReturnValue({ campaigns: sampleCampaigns });
    const { container } = render(<CampaignsWidget className="test-class" />);
    expect(container.firstChild).toHaveClass('test-class');
  });
});
