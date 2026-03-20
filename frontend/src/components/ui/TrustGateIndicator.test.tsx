/**
 * TrustGateIndicator Component Tests
 *
 * Tests for rendering trust gate status, score display,
 * expand/collapse behavior, and accessibility attributes.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';

// Mock getComputedStyle for DOM access
const mockGetComputedStyle = vi.fn().mockReturnValue({
  getPropertyValue: (prop: string) => {
    const values: Record<string, string> = {
      '--teal': '#00c7be',
      '--teal-light': 'rgba(0, 199, 190, 0.15)',
      '--status-warning': '#f59e0b',
      '--status-warning-bg': 'rgba(245, 158, 11, 0.15)',
      '--coral': '#ff6b6b',
    };
    return values[prop] || '';
  },
});
Object.defineProperty(window, 'getComputedStyle', { value: mockGetComputedStyle });

// Mock cn utility
vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

// Mock the liveSimulation module
const mockGetSignalHealth = vi.fn();
vi.mock('@/lib/liveSimulation', () => ({
  getSignalHealth: () => mockGetSignalHealth(),
}));

import { TrustGateIndicator } from './TrustGateIndicator';

describe('TrustGateIndicator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockGetSignalHealth.mockReturnValue({
      overall: 85,
      emq: 90,
      apiHealth: 95,
      eventLoss: 88,
      platformStability: 80,
      dataQuality: 75,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders with PASS status for healthy signal health (>= 70)', () => {
    render(<TrustGateIndicator />);
    expect(screen.getByText('PASS')).toBeInTheDocument();
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('Signal Health')).toBeInTheDocument();
  });

  it('renders with HOLD status for degraded signal health (40-69)', () => {
    mockGetSignalHealth.mockReturnValue({
      overall: 55,
      emq: 60,
      apiHealth: 70,
      eventLoss: 50,
      platformStability: 45,
      dataQuality: 40,
    });

    render(<TrustGateIndicator />);
    expect(screen.getByText('HOLD')).toBeInTheDocument();
    expect(screen.getByText('55')).toBeInTheDocument();
  });

  it('renders with BLOCK status for unhealthy signal health (< 40)', () => {
    mockGetSignalHealth.mockReturnValue({
      overall: 25,
      emq: 30,
      apiHealth: 20,
      eventLoss: 25,
      platformStability: 15,
      dataQuality: 30,
    });

    render(<TrustGateIndicator />);
    expect(screen.getByText('BLOCK')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
  });

  it('has accessible role and aria-label', () => {
    render(<TrustGateIndicator />);
    const button = screen.getByRole('status');
    expect(button).toHaveAttribute('aria-label', 'Trust Gate: PASS, Signal Health: 85%');
  });

  it('toggles expanded detail panel on click', () => {
    render(<TrustGateIndicator />);
    // Initially collapsed
    expect(screen.queryByText('Signal Components')).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByRole('status'));
    expect(screen.getByText('Signal Components')).toBeInTheDocument();
    expect(screen.getByText('EMQ Score')).toBeInTheDocument();
    expect(screen.getByText('API Health')).toBeInTheDocument();
    expect(screen.getByText('Event Loss')).toBeInTheDocument();
    expect(screen.getByText('Platform Stability')).toBeInTheDocument();
    expect(screen.getByText('Data Quality')).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(screen.getByRole('status'));
    expect(screen.queryByText('Signal Components')).not.toBeInTheDocument();
  });

  it('shows correct autopilot status for PASS state', () => {
    render(<TrustGateIndicator />);
    fireEvent.click(screen.getByRole('status'));
    expect(screen.getByText(/Autopilot: Enabled/)).toBeInTheDocument();
  });

  it('shows "Alert Only" autopilot message for HOLD state', () => {
    mockGetSignalHealth.mockReturnValue({
      overall: 50,
      emq: 55,
      apiHealth: 60,
      eventLoss: 45,
      platformStability: 40,
      dataQuality: 50,
    });

    render(<TrustGateIndicator />);
    fireEvent.click(screen.getByRole('status'));
    expect(screen.getByText(/Autopilot: Alert Only/)).toBeInTheDocument();
  });

  it('shows "Manual Required" autopilot message for BLOCK state', () => {
    mockGetSignalHealth.mockReturnValue({
      overall: 20,
      emq: 25,
      apiHealth: 15,
      eventLoss: 20,
      platformStability: 10,
      dataQuality: 25,
    });

    render(<TrustGateIndicator />);
    fireEvent.click(screen.getByRole('status'));
    expect(screen.getByText(/Autopilot: Manual Required/)).toBeInTheDocument();
  });

  it('shows component weights in expanded view', () => {
    render(<TrustGateIndicator />);
    fireEvent.click(screen.getByRole('status'));
    expect(screen.getByText('(35%)')).toBeInTheDocument();
    expect(screen.getByText('(25%)')).toBeInTheDocument();
    expect(screen.getByText('(20%)')).toBeInTheDocument();
    const tenPercents = screen.getAllByText('(10%)');
    expect(tenPercents.length).toBe(2);
  });

  it('updates health data periodically', () => {
    render(<TrustGateIndicator />);
    expect(screen.getByText('85')).toBeInTheDocument();

    mockGetSignalHealth.mockReturnValue({
      overall: 60,
      emq: 65,
      apiHealth: 70,
      eventLoss: 55,
      platformStability: 50,
      dataQuality: 55,
    });

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByText('60')).toBeInTheDocument();
    expect(screen.getByText('HOLD')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<TrustGateIndicator className="my-custom" />);
    expect(container.firstChild).toHaveClass('my-custom');
  });
});
