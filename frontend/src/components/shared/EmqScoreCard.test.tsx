import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EmqScoreCard } from './EmqScoreCard';

// Mock heroicons
vi.mock('@heroicons/react/24/outline', () => ({
  ClockIcon: (props: any) => <svg data-testid="clock-icon" {...props} />,
  ExclamationCircleIcon: (props: any) => <svg data-testid="exclamation-icon" {...props} />,
  ChartBarIcon: (props: any) => <svg data-testid="chart-icon" {...props} />,
  BugAntIcon: (props: any) => <svg data-testid="bug-icon" {...props} />,
}));

// Mock ConfidenceBandBadge
vi.mock('./ConfidenceBandBadge', () => ({
  ConfidenceBandBadge: ({ score, size }: { score: number; size?: string }) => (
    <span data-testid="confidence-badge">
      {score >= 90 ? 'Reliable' : score >= 60 ? 'Directional' : 'Unsafe'}
      {size && ` (${size})`}
    </span>
  ),
  getConfidenceBand: (score: number) => {
    if (score >= 90) return 'reliable';
    if (score >= 60) return 'directional';
    return 'unsafe';
  },
}));

// Mock cn utility
vi.mock('@/lib/utils', async () => {
  const actual = await vi.importActual('@/lib/utils');
  return {
    ...actual,
    cn: (...args: any[]) => args.filter(Boolean).join(' '),
  };
});

describe('EmqScoreCard', () => {
  it('renders the full card with title and score', () => {
    render(<EmqScoreCard score={85} />);
    expect(screen.getByText('Event Measurement Quality')).toBeInTheDocument();
    expect(screen.getByText('How reliable is your data today?')).toBeInTheDocument();
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('EMQ')).toBeInTheDocument();
  });

  it('renders the confidence band badge', () => {
    render(<EmqScoreCard score={95} />);
    const badges = screen.getAllByTestId('confidence-badge');
    expect(badges.length).toBeGreaterThanOrEqual(1);
    expect(badges[0]).toHaveTextContent('Reliable');
  });

  it('renders directional badge for mid-range scores', () => {
    render(<EmqScoreCard score={75} />);
    const badges = screen.getAllByTestId('confidence-badge');
    expect(badges[0]).toHaveTextContent('Directional');
  });

  it('renders unsafe badge for low scores', () => {
    render(<EmqScoreCard score={40} />);
    const badges = screen.getAllByTestId('confidence-badge');
    expect(badges[0]).toHaveTextContent('Unsafe');
  });

  it('renders driver breakdown by default', () => {
    render(<EmqScoreCard score={85} />);
    expect(screen.getByText('Freshness')).toBeInTheDocument();
    expect(screen.getByText('Data Loss')).toBeInTheDocument();
    expect(screen.getByText('Variance')).toBeInTheDocument();
    expect(screen.getByText('Errors')).toBeInTheDocument();
  });

  it('hides drivers when showDrivers is false', () => {
    render(<EmqScoreCard score={85} showDrivers={false} />);
    expect(screen.queryByText('Freshness')).not.toBeInTheDocument();
    expect(screen.queryByText('Data Loss')).not.toBeInTheDocument();
  });

  it('renders custom drivers', () => {
    const customDrivers = [
      { name: 'Custom Metric', value: 80, weight: 0.5, status: 'good' as const },
      { name: 'Another Metric', value: 45, weight: 0.5, status: 'critical' as const },
    ];
    render(<EmqScoreCard score={65} drivers={customDrivers} />);
    expect(screen.getByText('Custom Metric')).toBeInTheDocument();
    expect(screen.getByText('Another Metric')).toBeInTheDocument();
    expect(screen.getByText('80%')).toBeInTheDocument();
    expect(screen.getByText('45%')).toBeInTheDocument();
  });

  it('renders compact variant with smaller gauge', () => {
    render(<EmqScoreCard score={85} compact />);
    expect(screen.getByText('EMQ Score')).toBeInTheDocument();
    expect(screen.getByText('85')).toBeInTheDocument();
    // Compact should not show full title
    expect(screen.queryByText('Event Measurement Quality')).not.toBeInTheDocument();
  });

  it('renders delta from previous score (positive)', () => {
    render(<EmqScoreCard score={85} previousScore={80} />);
    expect(screen.getByText('+5 points from yesterday')).toBeInTheDocument();
  });

  it('renders delta from previous score (negative)', () => {
    render(<EmqScoreCard score={75} previousScore={80} />);
    expect(screen.getByText('-5 points from yesterday')).toBeInTheDocument();
  });

  it('renders delta in compact mode', () => {
    render(<EmqScoreCard score={90} previousScore={85} compact />);
    expect(screen.getByText('+5 from yesterday')).toBeInTheDocument();
  });

  it('does not render delta when previousScore is not provided', () => {
    render(<EmqScoreCard score={85} />);
    expect(screen.queryByText(/from yesterday/)).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<EmqScoreCard score={85} className="my-custom-class" />);
    expect(container.firstChild).toHaveClass('my-custom-class');
  });

  it('renders driver progress bars with correct widths', () => {
    const drivers = [
      { name: 'TestDriver', value: 75, weight: 1.0, status: 'warning' as const },
    ];
    const { container } = render(<EmqScoreCard score={75} drivers={drivers} />);
    // Look for the progress bar div with inline style
    const progressBars = container.querySelectorAll('[style*="width"]');
    const bar = Array.from(progressBars).find(
      (el) => (el as HTMLElement).style.width === '75%'
    );
    expect(bar).toBeTruthy();
  });
});
