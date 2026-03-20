/**
 * EmptyState Component Tests
 *
 * Tests for EmptyState and its specialized variants:
 * NoFilterResultsState, NoCampaignsState, NoChartDataState, LoadErrorState.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('lucide-react', () => ({
  SearchX: (props: any) => <svg data-testid="icon-searchx" {...props} />,
  Filter: (props: any) => <svg data-testid="icon-filter" {...props} />,
  BarChart3: (props: any) => <svg data-testid="icon-barchart" {...props} />,
  FileX: (props: any) => <svg data-testid="icon-filex" {...props} />,
  Inbox: (props: any) => <svg data-testid="icon-inbox" {...props} />,
  RefreshCw: (props: any) => <svg data-testid="icon-refresh" {...props} />,
  Plus: (props: any) => <svg data-testid="icon-plus" {...props} />,
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

import {
  EmptyState,
  NoFilterResultsState,
  NoCampaignsState,
  NoChartDataState,
  LoadErrorState,
} from './EmptyState';

// ---------------------------------------------------------------------------
// EmptyState
// ---------------------------------------------------------------------------

describe('EmptyState', () => {
  it('renders default no-data variant', () => {
    render(<EmptyState />);

    expect(screen.getByText('No data available')).toBeInTheDocument();
    expect(
      screen.getByText(/there's no data to display yet/i)
    ).toBeInTheDocument();
  });

  it('renders no-results variant', () => {
    render(<EmptyState variant="no-results" />);

    expect(screen.getByText('No results found')).toBeInTheDocument();
    expect(
      screen.getByText(/no items match your current filters/i)
    ).toBeInTheDocument();
  });

  it('renders no-filters variant', () => {
    render(<EmptyState variant="no-filters" />);

    expect(screen.getByText('No filters selected')).toBeInTheDocument();
  });

  it('renders error variant', () => {
    render(<EmptyState variant="error" />);

    expect(screen.getByText('Unable to load data')).toBeInTheDocument();
    expect(
      screen.getByText(/something went wrong while loading the data/i)
    ).toBeInTheDocument();
  });

  it('renders empty variant', () => {
    render(<EmptyState variant="empty" />);

    expect(screen.getByText('Nothing here yet')).toBeInTheDocument();
    expect(
      screen.getByText(/this section is empty/i)
    ).toBeInTheDocument();
  });

  it('overrides title with custom prop', () => {
    render(<EmptyState title="Custom Title" />);

    expect(screen.getByText('Custom Title')).toBeInTheDocument();
    expect(screen.queryByText('No data available')).not.toBeInTheDocument();
  });

  it('overrides description with custom prop', () => {
    render(<EmptyState description="Custom description text" />);

    expect(screen.getByText('Custom description text')).toBeInTheDocument();
  });

  it('renders custom icon when provided', () => {
    render(
      <EmptyState icon={<span data-testid="custom-icon">!</span>} />
    );

    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });

  it('renders primary action button', () => {
    const handleClick = vi.fn();
    render(
      <EmptyState
        action={{ label: 'Try Again', onClick: handleClick }}
      />
    );

    const button = screen.getByText('Try Again');
    expect(button).toBeInTheDocument();

    fireEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('renders secondary action button', () => {
    const handlePrimary = vi.fn();
    const handleSecondary = vi.fn();
    render(
      <EmptyState
        action={{ label: 'Primary', onClick: handlePrimary }}
        secondaryAction={{ label: 'Secondary', onClick: handleSecondary }}
      />
    );

    const secondary = screen.getByText('Secondary');
    expect(secondary).toBeInTheDocument();

    fireEvent.click(secondary);
    expect(handleSecondary).toHaveBeenCalledTimes(1);
  });

  it('applies custom className', () => {
    const { container } = render(
      <EmptyState className="custom-empty-state" />
    );

    expect(container.firstChild).toHaveClass('custom-empty-state');
  });

  it('does not render action buttons when none provided', () => {
    render(<EmptyState />);

    const buttons = screen.queryAllByRole('button');
    expect(buttons).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// NoFilterResultsState
// ---------------------------------------------------------------------------

describe('NoFilterResultsState', () => {
  it('renders with clear filters action', () => {
    const handleClear = vi.fn();
    render(<NoFilterResultsState onClearFilters={handleClear} />);

    expect(screen.getByText('No campaigns match your filters')).toBeInTheDocument();
    expect(screen.getByText('Clear all filters')).toBeInTheDocument();
  });

  it('calls onClearFilters when button is clicked', () => {
    const handleClear = vi.fn();
    render(<NoFilterResultsState onClearFilters={handleClear} />);

    fireEvent.click(screen.getByText('Clear all filters'));
    expect(handleClear).toHaveBeenCalledTimes(1);
  });

  it('shows filter count in description when provided', () => {
    render(
      <NoFilterResultsState onClearFilters={vi.fn()} filterCount={3} />
    );

    expect(
      screen.getByText(/3 active filters are hiding all results/i)
    ).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// NoCampaignsState
// ---------------------------------------------------------------------------

describe('NoCampaignsState', () => {
  it('renders empty campaigns message', () => {
    render(<NoCampaignsState />);

    expect(screen.getByText('No campaigns yet')).toBeInTheDocument();
  });

  it('renders create button when onCreateCampaign is provided', () => {
    const handleCreate = vi.fn();
    render(<NoCampaignsState onCreateCampaign={handleCreate} />);

    const button = screen.getByText('Create campaign');
    fireEvent.click(button);
    expect(handleCreate).toHaveBeenCalledTimes(1);
  });

  it('does not render create button when no handler is provided', () => {
    render(<NoCampaignsState />);

    expect(screen.queryByText('Create campaign')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// NoChartDataState
// ---------------------------------------------------------------------------

describe('NoChartDataState', () => {
  it('renders chart-specific empty state', () => {
    render(<NoChartDataState />);

    expect(screen.getByText('No chart data')).toBeInTheDocument();
  });

  it('renders refresh button when onRefresh is provided', () => {
    const handleRefresh = vi.fn();
    render(<NoChartDataState onRefresh={handleRefresh} />);

    const button = screen.getByText('Refresh');
    fireEvent.click(button);
    expect(handleRefresh).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// LoadErrorState
// ---------------------------------------------------------------------------

describe('LoadErrorState', () => {
  it('renders error state with retry button', () => {
    const handleRetry = vi.fn();
    render(<LoadErrorState onRetry={handleRetry} />);

    expect(screen.getByText('Unable to load data')).toBeInTheDocument();

    const retryButton = screen.getByText('Try again');
    fireEvent.click(retryButton);
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });
});
