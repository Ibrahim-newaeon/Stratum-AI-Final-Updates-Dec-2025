import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceBandBadge, getConfidenceBand } from './ConfidenceBandBadge';

// Mock cn utility
vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

describe('getConfidenceBand', () => {
  it('returns "reliable" for scores >= 90', () => {
    expect(getConfidenceBand(90)).toBe('reliable');
    expect(getConfidenceBand(95)).toBe('reliable');
    expect(getConfidenceBand(100)).toBe('reliable');
  });

  it('returns "directional" for scores 60-89', () => {
    expect(getConfidenceBand(60)).toBe('directional');
    expect(getConfidenceBand(75)).toBe('directional');
    expect(getConfidenceBand(89)).toBe('directional');
  });

  it('returns "unsafe" for scores < 60', () => {
    expect(getConfidenceBand(0)).toBe('unsafe');
    expect(getConfidenceBand(30)).toBe('unsafe');
    expect(getConfidenceBand(59)).toBe('unsafe');
  });

  it('handles boundary values correctly', () => {
    expect(getConfidenceBand(90)).toBe('reliable');
    expect(getConfidenceBand(89)).toBe('directional');
    expect(getConfidenceBand(60)).toBe('directional');
    expect(getConfidenceBand(59)).toBe('unsafe');
  });
});

describe('ConfidenceBandBadge', () => {
  it('renders "Reliable" label for high scores', () => {
    render(<ConfidenceBandBadge score={95} />);
    expect(screen.getByText('Reliable')).toBeInTheDocument();
  });

  it('renders "Directional" label for mid-range scores', () => {
    render(<ConfidenceBandBadge score={75} />);
    expect(screen.getByText('Directional')).toBeInTheDocument();
  });

  it('renders "Unsafe" label for low scores', () => {
    render(<ConfidenceBandBadge score={40} />);
    expect(screen.getByText('Unsafe')).toBeInTheDocument();
  });

  it('hides label when showLabel is false', () => {
    render(<ConfidenceBandBadge score={95} showLabel={false} />);
    expect(screen.queryByText('Reliable')).not.toBeInTheDocument();
  });

  it('has correct title for reliable band', () => {
    render(<ConfidenceBandBadge score={95} />);
    const badge = screen.getByTitle('Data is trustworthy for decision-making');
    expect(badge).toBeInTheDocument();
  });

  it('has correct title for directional band', () => {
    render(<ConfidenceBandBadge score={75} />);
    const badge = screen.getByTitle('Data shows trends but may have gaps');
    expect(badge).toBeInTheDocument();
  });

  it('has correct title for unsafe band', () => {
    render(<ConfidenceBandBadge score={30} />);
    const badge = screen.getByTitle('Data quality too low for reliable decisions');
    expect(badge).toBeInTheDocument();
  });

  it('renders small size variant', () => {
    const { container } = render(<ConfidenceBandBadge score={95} size="sm" />);
    expect(container.firstChild).toHaveClass('text-xs');
  });

  it('renders medium size variant (default)', () => {
    const { container } = render(<ConfidenceBandBadge score={95} />);
    expect(container.firstChild).toHaveClass('text-sm');
  });

  it('renders large size variant', () => {
    const { container } = render(<ConfidenceBandBadge score={95} size="lg" />);
    expect(container.firstChild).toHaveClass('text-base');
  });

  it('applies custom className', () => {
    const { container } = render(
      <ConfidenceBandBadge score={95} className="my-badge" />
    );
    expect(container.firstChild).toHaveClass('my-badge');
  });

  it('renders colored dot indicator', () => {
    const { container } = render(<ConfidenceBandBadge score={95} />);
    const dot = container.querySelector('.w-1\\.5.h-1\\.5.rounded-full');
    expect(dot).toBeInTheDocument();
  });

  it('applies success color for reliable band', () => {
    const { container } = render(<ConfidenceBandBadge score={95} />);
    expect(container.firstChild).toHaveClass('text-success');
    expect(container.firstChild).toHaveClass('bg-success/10');
  });

  it('applies warning color for directional band', () => {
    const { container } = render(<ConfidenceBandBadge score={75} />);
    expect(container.firstChild).toHaveClass('text-warning');
    expect(container.firstChild).toHaveClass('bg-warning/10');
  });

  it('applies danger color for unsafe band', () => {
    const { container } = render(<ConfidenceBandBadge score={30} />);
    expect(container.firstChild).toHaveClass('text-danger');
    expect(container.firstChild).toHaveClass('bg-danger/10');
  });
});
