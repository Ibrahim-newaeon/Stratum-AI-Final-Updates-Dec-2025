/**
 * MetricCard Component Tests
 *
 * Tests for MetricCard, MetricValue, MetricLabel, MetricBadge, MetricTrend
 * including variants, progress bars, click handlers, and keyboard accessibility.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MetricCard, MetricValue, MetricLabel, MetricBadge, MetricTrend } from './MetricCard';

// ---------------------------------------------------------------------------
// MetricCard
// ---------------------------------------------------------------------------

describe('MetricCard', () => {
  it('renders children', () => {
    render(
      <MetricCard>
        <span>Revenue</span>
      </MetricCard>
    );

    expect(screen.getByText('Revenue')).toBeInTheDocument();
  });

  it('applies default variant class (metric-card)', () => {
    const { container } = render(
      <MetricCard>Content</MetricCard>
    );

    expect(container.firstChild).toHaveClass('metric-card');
  });

  it('applies variant class when not default', () => {
    const { container } = render(
      <MetricCard variant="success">Content</MetricCard>
    );

    expect(container.firstChild).toHaveClass('success');
  });

  it('does not apply variant class when variant is default', () => {
    const { container } = render(
      <MetricCard variant="default">Content</MetricCard>
    );

    expect(container.firstChild).not.toHaveClass('default');
  });

  it('renders progress bar when progress prop is provided', () => {
    const { container } = render(
      <MetricCard progress={75}>Content</MetricCard>
    );

    const fill = container.querySelector('.fill');
    expect(fill).toBeInTheDocument();
    expect(fill).toHaveStyle({ width: '75%' });
  });

  it('clamps progress bar between 0 and 100', () => {
    const { container } = render(
      <MetricCard progress={150}>Content</MetricCard>
    );

    const fill = container.querySelector('.fill');
    expect(fill).toHaveStyle({ width: '100%' });
  });

  it('does not render progress bar when progress is undefined', () => {
    const { container } = render(
      <MetricCard>Content</MetricCard>
    );

    expect(container.querySelector('.progress-bar')).not.toBeInTheDocument();
  });

  it('adds cursor-pointer class when onClick is provided', () => {
    const { container } = render(
      <MetricCard onClick={() => {}}>Content</MetricCard>
    );

    expect(container.firstChild).toHaveClass('cursor-pointer');
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<MetricCard onClick={handleClick}>Click me</MetricCard>);

    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('has button role and tabIndex when onClick is provided', () => {
    const { container } = render(
      <MetricCard onClick={() => {}}>Content</MetricCard>
    );

    expect(container.firstChild).toHaveAttribute('role', 'button');
    expect(container.firstChild).toHaveAttribute('tabindex', '0');
  });

  it('triggers onClick on Enter keydown', () => {
    const handleClick = vi.fn();
    const { container } = render(
      <MetricCard onClick={handleClick}>Content</MetricCard>
    );

    fireEvent.keyDown(container.firstChild!, { key: 'Enter' });
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('applies custom className', () => {
    const { container } = render(
      <MetricCard className="my-custom">Content</MetricCard>
    );

    expect(container.firstChild).toHaveClass('my-custom');
  });
});

// ---------------------------------------------------------------------------
// MetricValue
// ---------------------------------------------------------------------------

describe('MetricValue', () => {
  it('renders children', () => {
    render(<MetricValue>$12,500</MetricValue>);

    expect(screen.getByText('$12,500')).toBeInTheDocument();
  });

  it('applies metric-value class', () => {
    const { container } = render(<MetricValue>Test</MetricValue>);

    expect(container.firstChild).toHaveClass('metric-value');
  });
});

// ---------------------------------------------------------------------------
// MetricLabel
// ---------------------------------------------------------------------------

describe('MetricLabel', () => {
  it('renders children', () => {
    render(<MetricLabel>Total Revenue</MetricLabel>);

    expect(screen.getByText('Total Revenue')).toBeInTheDocument();
  });

  it('applies metric-label class', () => {
    const { container } = render(<MetricLabel>Label</MetricLabel>);

    expect(container.firstChild).toHaveClass('metric-label');
  });
});

// ---------------------------------------------------------------------------
// MetricBadge
// ---------------------------------------------------------------------------

describe('MetricBadge', () => {
  it('renders children', () => {
    render(<MetricBadge>Healthy</MetricBadge>);

    expect(screen.getByText('Healthy')).toBeInTheDocument();
  });

  it('applies info variant by default', () => {
    const { container } = render(<MetricBadge>Info</MetricBadge>);

    expect(container.firstChild).toHaveClass('bg-blue-500/10');
    expect(container.firstChild).toHaveClass('text-blue-400');
  });

  it('applies success variant classes', () => {
    const { container } = render(<MetricBadge variant="success">OK</MetricBadge>);

    expect(container.firstChild).toHaveClass('bg-green-500/10');
    expect(container.firstChild).toHaveClass('text-green-400');
  });

  it('applies warning variant classes', () => {
    const { container } = render(<MetricBadge variant="warning">Warn</MetricBadge>);

    expect(container.firstChild).toHaveClass('bg-amber-500/10');
    expect(container.firstChild).toHaveClass('text-amber-400');
  });

  it('applies error variant classes', () => {
    const { container } = render(<MetricBadge variant="error">Error</MetricBadge>);

    expect(container.firstChild).toHaveClass('bg-red-500/10');
    expect(container.firstChild).toHaveClass('text-red-400');
  });
});

// ---------------------------------------------------------------------------
// MetricTrend
// ---------------------------------------------------------------------------

describe('MetricTrend', () => {
  it('renders positive trend arrow and value', () => {
    render(<MetricTrend value={12} />);

    expect(screen.getByText('12%')).toBeInTheDocument();
  });

  it('shows green color for positive values by default', () => {
    const { container } = render(<MetricTrend value={5} />);

    expect(container.firstChild).toHaveClass('text-green-400');
  });

  it('shows red color for negative values by default', () => {
    const { container } = render(<MetricTrend value={-5} />);

    expect(container.firstChild).toHaveClass('text-red-400');
  });

  it('inverts colors when inverted prop is true', () => {
    const { container } = render(<MetricTrend value={-5} inverted />);

    // Negative value with inverted = positive display
    expect(container.firstChild).toHaveClass('text-green-400');
  });

  it('uses custom suffix', () => {
    render(<MetricTrend value={3} suffix="pts" />);

    expect(screen.getByText('3pts')).toBeInTheDocument();
  });
});
