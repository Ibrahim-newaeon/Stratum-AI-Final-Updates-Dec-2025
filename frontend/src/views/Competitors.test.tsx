import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

/**
 * The Competitors view shows only what the scanner can source: Meta Ad Library
 * activity and site metadata. Estimated ad spend, share of voice and keyword
 * overlap need a paid provider that is not wired, so the API does not serve
 * them.
 *
 * The trap these tests exist for: this view used to read camelCase keys the
 * API has never sent (`c.estimatedSpend`, `c.shareOfVoice`, `c.activeCreatives`)
 * through `Number(... ?? 0)`, so every card rendered "$0/mo · 0% share of
 * voice · 0% keyword overlap" and presented it as measurement. The whole
 * surface was 503 behind a feature flag, so nobody saw it.
 *
 * The distinction that matters most is null vs zero. A null ad count means the
 * Ad Library lookup could not run — no Graph token, or an API error. Rendering
 * that as 0 claims the competitor runs no ads, which is a different and
 * confidently wrong statement.
 */

const mockUseCompetitors = vi.fn();

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock('@/api/hooks', () => ({
  useCompetitors: () => mockUseCompetitors(),
  useCreateCompetitor: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDeleteCompetitor: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

import { Competitors } from './Competitors';

function competitor(overrides = {}) {
  return {
    id: 1,
    tenant_id: 3,
    domain: 'acme.com',
    name: 'Acme',
    is_primary: false,
    fb_page_name: null,
    meta_title: 'Acme — everything you need',
    meta_description: null,
    social_links: null,
    ad_creatives_count: 12,
    detected_ad_platforms: ['facebook', 'instagram'],
    data_source: 'meta_ad_library',
    last_fetched_at: new Date().toISOString(),
    fetch_error: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  };
}

function renderWith(items: unknown[]) {
  mockUseCompetitors.mockReturnValue({
    data: { items },
    isLoading: false,
    refetch: vi.fn(),
  });
  render(<Competitors />);
}

beforeEach(() => {
  mockUseCompetitors.mockReset();
});

describe('Competitors', () => {
  it('shows the Ad Library count the scanner actually observed', () => {
    renderWith([competitor({ ad_creatives_count: 12 })]);

    expect(screen.getByText('Acme')).toBeInTheDocument();
    expect(screen.getByText('Active on Meta')).toBeInTheDocument();

    // Scoped to the card: the "Active Ads Seen" stat tile also renders 12, so
    // a bare getByText('12') is ambiguous rather than wrong.
    const label = screen.getByText('Active ads');
    expect(label.parentElement).toHaveTextContent('12');
  });

  it('renders an unknown ad count as unknown, never as zero', () => {
    // null = the Ad Library query could not run. "0" here would assert the
    // competitor is running no ads, which we have not established.
    renderWith([competitor({ ad_creatives_count: null, data_source: 'website_scrape' })]);

    expect(screen.getByText('Unknown')).toBeInTheDocument();
    expect(screen.getByText('Ad activity unknown')).toBeInTheDocument();
    expect(screen.queryByText('No ads detected')).not.toBeInTheDocument();
  });

  it('distinguishes a confirmed zero from an unknown', () => {
    renderWith([competitor({ ad_creatives_count: 0 })]);

    expect(screen.getByText('No ads detected')).toBeInTheDocument();
    expect(screen.queryByText('Unknown')).not.toBeInTheDocument();
  });

  it('offers no ad spend, share of voice or keyword overlap', () => {
    renderWith([competitor()]);

    // Not "renders them as zero" — absent. No source fills them.
    expect(screen.queryByText(/Est\. Ad Spend/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Share of Voice/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Keyword Overlap/i)).not.toBeInTheDocument();
  });

  it('does not divide by zero competitors', () => {
    // avgKeywordOverlap used to be a mean over an empty array, rendering NaN%.
    renderWith([]);

    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });

  it('reports a competitor that could not be reached', () => {
    renderWith([
      competitor({
        data_source: 'unavailable',
        ad_creatives_count: null,
        fetch_error: 'connection timed out',
        last_fetched_at: null,
      }),
    ]);

    expect(screen.getByText('connection timed out')).toBeInTheDocument();
    expect(screen.getByText(/Scanned Never/)).toBeInTheDocument();
  });
});
