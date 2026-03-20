import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BudgetAtRiskChip } from './BudgetAtRiskChip';

// Mock heroicons
vi.mock('@heroicons/react/24/outline', () => ({
  ExclamationTriangleIcon: (props: any) => <svg data-testid="warning-icon" {...props} />,
}));

// Mock cn utility
vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

describe('BudgetAtRiskChip', () => {
  it('renders formatted amount and "at risk" label', () => {
    render(<BudgetAtRiskChip amount={5000} />);
    expect(screen.getByText('$5,000')).toBeInTheDocument();
    expect(screen.getByText('at risk')).toBeInTheDocument();
  });

  it('renders low-risk styling when below threshold', () => {
    const { container } = render(<BudgetAtRiskChip amount={500} threshold={1000} />);
    // Below threshold: neutral styling, no icon
    expect(screen.queryByTestId('warning-icon')).not.toBeInTheDocument();
    expect(container.firstChild).toHaveClass('bg-surface-tertiary');
  });

  it('renders warning styling when at or above threshold', () => {
    const { container } = render(<BudgetAtRiskChip amount={1500} threshold={1000} />);
    expect(container.firstChild).toHaveClass('bg-warning/10');
    expect(screen.getByTestId('warning-icon')).toBeInTheDocument();
  });

  it('renders critical styling when amount is 5x or more above threshold', () => {
    const { container } = render(<BudgetAtRiskChip amount={6000} threshold={1000} />);
    expect(container.firstChild).toHaveClass('bg-danger/10');
    expect(screen.getByTestId('warning-icon')).toBeInTheDocument();
  });

  it('formats currency with custom currency code', () => {
    render(<BudgetAtRiskChip amount={3000} currency="EUR" />);
    // EUR formatting: different locale may show the euro sign
    const chip = screen.getByTitle('Budget at risk: \u20AC3,000');
    expect(chip).toBeInTheDocument();
  });

  it('has correct title attribute with formatted amount', () => {
    render(<BudgetAtRiskChip amount={12500} />);
    const chip = screen.getByTitle('Budget at risk: $12,500');
    expect(chip).toBeInTheDocument();
  });

  it('hides icon when showIcon is false', () => {
    render(<BudgetAtRiskChip amount={5000} threshold={1000} showIcon={false} />);
    expect(screen.queryByTestId('warning-icon')).not.toBeInTheDocument();
  });

  it('renders small size variant', () => {
    const { container } = render(<BudgetAtRiskChip amount={1000} size="sm" />);
    expect(container.firstChild).toHaveClass('text-xs');
  });

  it('renders medium size variant (default)', () => {
    const { container } = render(<BudgetAtRiskChip amount={1000} size="md" />);
    expect(container.firstChild).toHaveClass('text-sm');
  });

  it('renders large size variant', () => {
    const { container } = render(<BudgetAtRiskChip amount={1000} size="lg" />);
    expect(container.firstChild).toHaveClass('text-base');
  });

  it('applies custom className', () => {
    const { container } = render(
      <BudgetAtRiskChip amount={1000} className="custom-chip" />
    );
    expect(container.firstChild).toHaveClass('custom-chip');
  });

  it('formats zero amount correctly', () => {
    render(<BudgetAtRiskChip amount={0} />);
    expect(screen.getByText('$0')).toBeInTheDocument();
  });

  it('formats large amounts with comma separators', () => {
    render(<BudgetAtRiskChip amount={1250000} />);
    expect(screen.getByText('$1,250,000')).toBeInTheDocument();
  });
});
