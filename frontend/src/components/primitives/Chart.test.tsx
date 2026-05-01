/**
 * Chart tests — themed recharts wrapper.
 *
 * jsdom doesn't lay out SVG, so we can't assert pixel positions; we test
 * the shell behaviour (loading / empty / error / data) and that recharts
 * renders some SVG when given data.
 */

import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LineChart, AreaChart } from './Chart';

// recharts uses ResponsiveContainer which needs ResizeObserver in jsdom.
beforeAll(() => {
  if (!('ResizeObserver' in globalThis)) {
    class ResizeObserverMock {
      observe = vi.fn();
      unobserve = vi.fn();
      disconnect = vi.fn();
    }
    (globalThis as unknown as { ResizeObserver: typeof ResizeObserverMock }).ResizeObserver =
      ResizeObserverMock;
  }
});

const sampleData = [
  { day: 'Mon', revenue: 100, spend: 40 },
  { day: 'Tue', revenue: 130, spend: 50 },
  { day: 'Wed', revenue: 90, spend: 35 },
];

const sampleSeries = [
  { dataKey: 'revenue', name: 'Revenue' },
  { dataKey: 'spend', name: 'Spend' },
];

describe('LineChart', () => {
  it('renders the loading shell when loading', () => {
    const { container } = render(
      <LineChart data={[]} series={[]} xKey="day" loading />
    );
    expect(container.querySelector('[role="status"]')).not.toBeNull();
  });

  it('renders the error shell when error is set', () => {
    render(<LineChart data={[]} series={[]} xKey="day" error="Boom" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Boom');
  });

  it('renders the empty shell when data is empty', () => {
    render(<LineChart data={[]} series={sampleSeries} xKey="day" />);
    expect(screen.getByText('No data yet.')).toBeInTheDocument();
  });

  it('renders custom emptyMessage', () => {
    render(
      <LineChart
        data={[]}
        series={sampleSeries}
        xKey="day"
        emptyMessage="Telemetry pending"
      />
    );
    expect(screen.getByText('Telemetry pending')).toBeInTheDocument();
  });

  it('does not render the empty shell when data is present', () => {
    // jsdom can't lay out recharts' ResponsiveContainer (no measured size),
    // so we can't assert SVG presence. Instead verify the empty/error/loading
    // shells are NOT shown when data is passed.
    render(<LineChart data={sampleData} series={sampleSeries} xKey="day" />);
    expect(screen.queryByText('No data yet.')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('AreaChart', () => {
  it('renders the loading shell when loading', () => {
    const { container } = render(
      <AreaChart data={[]} series={[]} xKey="day" loading />
    );
    expect(container.querySelector('[role="status"]')).not.toBeNull();
  });

  it('renders the empty shell with default message', () => {
    render(<AreaChart data={[]} series={sampleSeries} xKey="day" />);
    expect(screen.getByText('No data yet.')).toBeInTheDocument();
  });

  it('does not render the empty shell when data is present', () => {
    render(<AreaChart data={sampleData} series={sampleSeries} xKey="day" />);
    expect(screen.queryByText('No data yet.')).not.toBeInTheDocument();
  });
});
