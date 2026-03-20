import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AlertsWidget } from './AlertsWidget';

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  AlertTriangle: (props: any) => <svg data-testid="alert-triangle-icon" {...props} />,
  CheckCircle: (props: any) => <svg data-testid="check-circle-icon" {...props} />,
  Info: (props: any) => <svg data-testid="info-icon" {...props} />,
  XCircle: (props: any) => <svg data-testid="x-circle-icon" {...props} />,
}));

// Mock cn utility
vi.mock('@/lib/utils', async () => {
  const actual = await vi.importActual('@/lib/utils');
  return {
    ...actual,
    cn: (...args: any[]) => args.filter(Boolean).join(' '),
  };
});

// Mock DashboardSimulationContext
const mockUseDashboardSimulation = vi.fn();
vi.mock('@/contexts/DashboardSimulationContext', () => ({
  useDashboardSimulation: () => mockUseDashboardSimulation(),
}));

const sampleAlerts = [
  {
    id: 'alert-1',
    severity: 'warning',
    title: 'Budget pacing ahead of schedule',
    message: 'Meta campaign spending 15% faster than expected.',
    time: '2 hours ago',
  },
  {
    id: 'alert-2',
    severity: 'critical',
    title: 'ROAS dropped below threshold',
    message: 'Google Ads ROAS fell below 2.0x safety threshold.',
    time: '30 minutes ago',
  },
  {
    id: 'alert-3',
    severity: 'success',
    title: 'Campaign optimized',
    message: 'Autopilot scaled budget for top performer.',
    time: '1 hour ago',
  },
  {
    id: 'alert-4',
    severity: 'info',
    title: 'New data sync complete',
    message: 'All platform data updated successfully.',
    time: '5 minutes ago',
  },
];

describe('AlertsWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when there are no alerts', () => {
    mockUseDashboardSimulation.mockReturnValue({ alerts: [] });
    render(<AlertsWidget />);
    expect(screen.getByText('All clear — no alerts')).toBeInTheDocument();
  });

  it('renders empty state when alerts is undefined', () => {
    mockUseDashboardSimulation.mockReturnValue({ alerts: undefined });
    render(<AlertsWidget />);
    expect(screen.getByText('All clear — no alerts')).toBeInTheDocument();
  });

  it('renders all alert items', () => {
    mockUseDashboardSimulation.mockReturnValue({ alerts: sampleAlerts });
    render(<AlertsWidget />);
    expect(screen.getByText('Budget pacing ahead of schedule')).toBeInTheDocument();
    expect(screen.getByText('ROAS dropped below threshold')).toBeInTheDocument();
    expect(screen.getByText('Campaign optimized')).toBeInTheDocument();
    expect(screen.getByText('New data sync complete')).toBeInTheDocument();
  });

  it('renders alert messages', () => {
    mockUseDashboardSimulation.mockReturnValue({ alerts: sampleAlerts });
    render(<AlertsWidget />);
    expect(screen.getByText(/Meta campaign spending 15% faster/)).toBeInTheDocument();
    expect(screen.getByText(/Google Ads ROAS fell below/)).toBeInTheDocument();
  });

  it('renders alert timestamps', () => {
    mockUseDashboardSimulation.mockReturnValue({ alerts: sampleAlerts });
    render(<AlertsWidget />);
    expect(screen.getByText('2 hours ago')).toBeInTheDocument();
    expect(screen.getByText('30 minutes ago')).toBeInTheDocument();
    expect(screen.getByText('1 hour ago')).toBeInTheDocument();
    expect(screen.getByText('5 minutes ago')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    mockUseDashboardSimulation.mockReturnValue({ alerts: [] });
    const { container } = render(<AlertsWidget className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });

  it('renders correct number of alert items', () => {
    mockUseDashboardSimulation.mockReturnValue({ alerts: sampleAlerts });
    const { container } = render(<AlertsWidget />);
    const alertItems = container.querySelectorAll('.flex.items-start.gap-3');
    expect(alertItems.length).toBe(4);
  });

  it('applies staggered animation delays', () => {
    mockUseDashboardSimulation.mockReturnValue({ alerts: sampleAlerts });
    const { container } = render(<AlertsWidget />);
    const alertItems = container.querySelectorAll('[style*="animationDelay"]');
    expect(alertItems.length).toBe(4);
  });
});
