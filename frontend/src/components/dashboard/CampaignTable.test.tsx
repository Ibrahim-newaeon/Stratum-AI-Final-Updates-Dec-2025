/**
 * CampaignTable Component Tests
 *
 * Tests for rendering, sorting, searching, pagination,
 * and sync functionality.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';

vi.mock('lucide-react', () => ({
  ArrowUp: (props: any) => <svg data-testid="arrow-up" {...props} />,
  ArrowDown: (props: any) => <svg data-testid="arrow-down" {...props} />,
  Filter: (props: any) => <svg data-testid="icon-filter" {...props} />,
  Search: (props: any) => <svg data-testid="icon-search" {...props} />,
  RefreshCw: (props: any) => <svg data-testid="icon-refresh" {...props} />,
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
  formatCurrency: (val: number) => `$${val.toLocaleString()}`,
}));

import { CampaignTable } from './CampaignTable';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const mockCampaigns = [
  {
    campaign_id: 'c1',
    campaign_name: 'Summer Sale',
    platform: 'Google Ads',
    campaign_type: 'Search',
    region: 'US',
    spend: 5000,
    revenue: 15000,
    roas: 3.0,
    cpa: 25,
    conversions: 200,
    ctr: 3.5,
  },
  {
    campaign_id: 'c2',
    campaign_name: 'Brand Awareness',
    platform: 'Meta',
    campaign_type: 'Display',
    region: 'UAE',
    spend: 3000,
    revenue: 6000,
    roas: 2.0,
    cpa: 30,
    conversions: 100,
    ctr: 2.1,
  },
  {
    campaign_id: 'c3',
    campaign_name: 'Retargeting Q1',
    platform: 'TikTok',
    campaign_type: 'Video',
    region: 'UK',
    spend: 8000,
    revenue: 4000,
    roas: 0.5,
    cpa: 80,
    conversions: 50,
    ctr: 1.2,
  },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CampaignTable', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the search input', () => {
    render(<CampaignTable campaigns={mockCampaigns} />);

    expect(
      screen.getByPlaceholderText('Search campaigns...')
    ).toBeInTheDocument();
  });

  it('renders campaign names in the table', () => {
    render(<CampaignTable campaigns={mockCampaigns} />);

    expect(screen.getByText('Summer Sale')).toBeInTheDocument();
    expect(screen.getByText('Brand Awareness')).toBeInTheDocument();
    expect(screen.getByText('Retargeting Q1')).toBeInTheDocument();
  });

  it('renders platform badges', () => {
    render(<CampaignTable campaigns={mockCampaigns} />);

    expect(screen.getByText('Google Ads')).toBeInTheDocument();
    expect(screen.getByText('Meta')).toBeInTheDocument();
    expect(screen.getByText('TikTok')).toBeInTheDocument();
  });

  it('renders ROAS values with correct formatting', () => {
    render(<CampaignTable campaigns={mockCampaigns} />);

    expect(screen.getByText('3.00x')).toBeInTheDocument();
    expect(screen.getByText('2.00x')).toBeInTheDocument();
    expect(screen.getByText('0.50x')).toBeInTheDocument();
  });

  it('filters campaigns by search term', () => {
    render(<CampaignTable campaigns={mockCampaigns} />);

    const searchInput = screen.getByPlaceholderText('Search campaigns...');
    fireEvent.change(searchInput, { target: { value: 'Summer' } });

    expect(screen.getByText('Summer Sale')).toBeInTheDocument();
    expect(screen.queryByText('Brand Awareness')).not.toBeInTheDocument();
    expect(screen.queryByText('Retargeting Q1')).not.toBeInTheDocument();
  });

  it('filters campaigns by platform search', () => {
    render(<CampaignTable campaigns={mockCampaigns} />);

    const searchInput = screen.getByPlaceholderText('Search campaigns...');
    fireEvent.change(searchInput, { target: { value: 'Meta' } });

    expect(screen.getByText('Brand Awareness')).toBeInTheDocument();
    expect(screen.queryByText('Summer Sale')).not.toBeInTheDocument();
  });

  it('calls onCampaignClick when a row is clicked', () => {
    const handleClick = vi.fn();
    render(
      <CampaignTable campaigns={mockCampaigns} onCampaignClick={handleClick} />
    );

    fireEvent.click(screen.getByText('Summer Sale'));
    expect(handleClick).toHaveBeenCalledWith('c1');
  });

  it('renders column headers with sort buttons', () => {
    render(<CampaignTable campaigns={mockCampaigns} />);

    expect(screen.getByRole('button', { name: /sort by campaign name/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sort by platform/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sort by roas/i })).toBeInTheDocument();
  });

  it('hides price metrics when showPriceMetrics is false', () => {
    render(<CampaignTable campaigns={mockCampaigns} showPriceMetrics={false} />);

    // ROAS, Spend, Revenue, CPA columns should not appear
    expect(screen.queryByText('3.00x')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /sort by spend/i })).not.toBeInTheDocument();
  });

  it('renders sync buttons when onSyncCampaign is provided', () => {
    const handleSync = vi.fn();
    render(
      <CampaignTable campaigns={mockCampaigns} onSyncCampaign={handleSync} />
    );

    const syncButtons = screen.getAllByTitle(/Sync .+ from/);
    expect(syncButtons).toHaveLength(3);
  });

  it('calls onSyncCampaign with campaign ID when sync is clicked', () => {
    const handleSync = vi.fn();
    render(
      <CampaignTable campaigns={mockCampaigns} onSyncCampaign={handleSync} />
    );

    const syncButton = screen.getByTitle('Sync Summer Sale from Google Ads');
    fireEvent.click(syncButton);

    expect(handleSync).toHaveBeenCalledWith('c1');
  });

  it('shows pagination when campaigns exceed pageSize', () => {
    // Create enough campaigns to trigger pagination
    const manyCampaigns = Array.from({ length: 15 }, (_, i) => ({
      ...mockCampaigns[0],
      campaign_id: `c${i}`,
      campaign_name: `Campaign ${i}`,
    }));

    render(<CampaignTable campaigns={manyCampaigns} pageSize={10} />);

    expect(screen.getByText(/Showing 1 to 10 of 15/)).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();
    expect(screen.getByText('Previous')).toBeInTheDocument();
  });

  it('does not show pagination when all campaigns fit on one page', () => {
    render(<CampaignTable campaigns={mockCampaigns} pageSize={10} />);

    expect(screen.queryByText('Next')).not.toBeInTheDocument();
    expect(screen.queryByText('Previous')).not.toBeInTheDocument();
  });
});
