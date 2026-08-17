import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const mockUseCampaigns = vi.fn();

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        'campaigns.title': 'Campaigns',
        'campaigns.createNew': 'New campaign',
        'campaigns.searchPlaceholder': 'Search campaigns',
        'campaigns.allStatuses': 'All statuses',
        'campaigns.allPlatforms': 'All platforms',
        'campaigns.active': 'Active',
        'campaigns.paused': 'Paused',
        'campaigns.completed': 'Completed',
        'campaigns.draft': 'Draft',
      })[key] ?? key,
  }),
}));

vi.mock('@/api/hooks', () => ({
  useCampaigns: () => mockUseCampaigns(),
  usePauseCampaign: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useActivateCampaign: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteCampaign: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/usePriceMetrics', () => ({
  usePriceMetrics: () => ({ showPriceMetrics: true }),
}));

vi.mock('@/components/campaigns/CampaignCreateModal', () => ({
  default: () => null,
}));

import { Campaigns } from './Campaigns';

function renderView() {
  return render(
    <MemoryRouter>
      <Campaigns />
    </MemoryRouter>,
  );
}

const row = {
  id: 41,
  name: 'Summer Prospecting',
  platform: 'meta',
  status: 'active',
  budget: 5000,
  spend: 1240.5,
  roas: 3.42,
  conversions: 87,
  revenue: 4242.51,
  impressions: 10000,
  clicks: 250,
};

function result(overrides: Record<string, unknown> = {}) {
  return {
    data: { items: [], total: 0, skip: 0, limit: 50 },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  mockUseCampaigns.mockReset();
});

describe('Campaigns', () => {
  it('renders the page title as a level-1 heading', () => {
    mockUseCampaigns.mockReturnValue(result());
    renderView();
    expect(screen.getByRole('heading', { level: 1, name: 'Campaigns' })).toBeInTheDocument();
  });

  it('shows an empty message when there are no campaigns', () => {
    mockUseCampaigns.mockReturnValue(result());
    renderView();
    expect(screen.getByText(/no campaigns yet/i)).toBeInTheDocument();
  });

  it('surfaces a fetch failure rather than showing an empty table', () => {
    mockUseCampaigns.mockReturnValue(
      result({ data: undefined, error: new Error('boom') }),
    );
    renderView();

    expect(screen.getByText(/could not load campaigns/i)).toBeInTheDocument();
    expect(screen.queryByText(/no campaigns yet/i)).toBeNull();
  });

  it('renders a campaign row with its status pill', () => {
    mockUseCampaigns.mockReturnValue(result({ data: { items: [row], total: 1, skip: 0, limit: 50 } }));
    renderView();

    expect(screen.getByText('Summer Prospecting')).toBeInTheDocument();

    // The status must render through StatusPill (role=status), not a bespoke
    // badge — that consolidation is the point of the rewrite. "Active" also
    // appears as a stat-row label and a filter option, so scope to the pill.
    const pill = screen.getAllByText('Active').find((el) => el.closest('[role="status"]'));
    expect(pill).toBeDefined();
  });

  it('renders the stat row with mono tabular figures', () => {
    mockUseCampaigns.mockReturnValue(result({ data: { items: [row], total: 1, skip: 0, limit: 50 } }));
    const { container } = renderView();

    const figure = container.querySelector('[data-slot="stat-value"]');
    expect(figure?.className).toContain('tabular-nums');
  });
});
