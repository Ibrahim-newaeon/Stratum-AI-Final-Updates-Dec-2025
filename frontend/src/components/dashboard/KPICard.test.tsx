/**
 * KPICard Component Tests
 *
 * Tests for rendering, loading states, trend display,
 * action buttons, and accessibility.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock react-countup to avoid animation complexity in tests
vi.mock('react-countup', () => ({
  default: ({ end, prefix, suffix }: any) => (
    <span>{prefix}{end}{suffix}</span>
  ),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  TrendingUp: (props: any) => <svg data-testid="trending-up" {...props} />,
  TrendingDown: (props: any) => <svg data-testid="trending-down" {...props} />,
  Eye: (props: any) => <svg data-testid="icon-eye" {...props} />,
  Bell: (props: any) => <svg data-testid="icon-bell" {...props} />,
  Download: (props: any) => <svg data-testid="icon-download" {...props} />,
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

import { KPICard } from './KPICard';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('KPICard', () => {
  it('renders the title and string value', () => {
    render(<KPICard title="Total Revenue" value="$125,000" />);

    expect(screen.getByText('Total Revenue')).toBeInTheDocument();
    expect(screen.getByText('$125,000')).toBeInTheDocument();
  });

  it('renders with numeric value using CountUp animation', () => {
    render(
      <KPICard
        title="ROAS"
        value="3.5x"
        numericValue={3.5}
        prefix=""
        suffix="x"
        decimals={1}
      />
    );

    expect(screen.getByText('ROAS')).toBeInTheDocument();
    expect(screen.getByText('3.5x')).toBeInTheDocument();
  });

  it('renders loading skeleton when loading is true', () => {
    const { container } = render(<KPICard title="Loading" value="" loading />);

    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    expect(screen.queryByText('Loading')).not.toBeInTheDocument();
  });

  it('displays delta with trend arrow up', () => {
    render(
      <KPICard title="CTR" value="3.2%" delta={12.5} trend="up" trendIsGood />
    );

    expect(screen.getByText('+12.5%')).toBeInTheDocument();
    expect(screen.getByText('vs last period')).toBeInTheDocument();
    expect(screen.getByTestId('trending-up')).toBeInTheDocument();
  });

  it('displays delta with trend arrow down', () => {
    render(
      <KPICard title="CPA" value="$45" delta={-8.2} trend="down" />
    );

    expect(screen.getByText('-8.2%')).toBeInTheDocument();
    expect(screen.getByTestId('trending-down')).toBeInTheDocument();
  });

  it('renders custom deltaText', () => {
    render(
      <KPICard title="Spend" value="$50K" delta={5.0} trend="up" deltaText="vs last week" />
    );

    expect(screen.getByText('vs last week')).toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    render(
      <KPICard
        title="Revenue"
        value="$100K"
        icon={<span data-testid="custom-icon">$</span>}
      />
    );

    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
  });

  it('applies highlight styling', () => {
    const { container } = render(
      <KPICard title="Highlighted" value="100" highlight />
    );

    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('bg-gradient-to-br');
  });

  it('renders small size variant', () => {
    const { container } = render(
      <KPICard title="Small Card" value="42" size="small" />
    );

    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('p-4');
  });

  it('has proper aria-label for accessibility', () => {
    render(
      <KPICard title="Conversions" value="1,234" delta={15.3} trend="up" />
    );

    const article = screen.getByRole('article');
    expect(article).toHaveAttribute(
      'aria-label',
      expect.stringContaining('Conversions: 1,234')
    );
  });

  it('applies custom className', () => {
    const { container } = render(
      <KPICard title="Custom" value="0" className="my-custom-class" />
    );

    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('my-custom-class');
  });
});
