import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InsightsPanel, type InsightItem } from './InsightsPanel';

const items: InsightItem[] = [
  { id: 'a', severity: 'info', title: 'Info item', body: 'something to know' },
  { id: 'b', severity: 'critical', title: 'Critical item', body: 'urgent' },
  { id: 'c', severity: 'warning', title: 'Warning item' },
  { id: 'd', severity: 'success', title: 'Success item' },
];

describe('InsightsPanel', () => {
  it('renders the default title', () => {
    render(<InsightsPanel items={items} />);
    expect(screen.getByText('What needs your attention')).toBeInTheDocument();
  });

  it('renders a custom title and description', () => {
    render(<InsightsPanel items={items} title="Heads up" description="Last 24h" />);
    expect(screen.getByText('Heads up')).toBeInTheDocument();
    expect(screen.getByText('Last 24h')).toBeInTheDocument();
  });

  it('sorts items by severity (critical first) by default', () => {
    render(<InsightsPanel items={items} />);
    const titles = screen.getAllByRole('listitem').map((li) => li.textContent ?? '');
    expect(titles[0]).toContain('Critical item');
    expect(titles[1]).toContain('Warning item');
    expect(titles[2]).toContain('Info item');
    expect(titles[3]).toContain('Success item');
  });

  it('preserves original order when sortBySeverity=false', () => {
    render(<InsightsPanel items={items} sortBySeverity={false} />);
    const titles = screen.getAllByRole('listitem').map((li) => li.textContent ?? '');
    expect(titles[0]).toContain('Info item');
    expect(titles[1]).toContain('Critical item');
  });

  it('caps items at maxItems', () => {
    render(<InsightsPanel items={items} maxItems={2} />);
    expect(screen.getAllByRole('listitem')).toHaveLength(2);
  });

  it('renders the loading skeleton', () => {
    const { container } = render(<InsightsPanel items={[]} loading />);
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('renders the error message', () => {
    render(<InsightsPanel items={[]} error="Boom" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Boom');
  });

  it('renders the empty message when items is []', () => {
    render(<InsightsPanel items={[]} emptyMessage="All quiet." />);
    expect(screen.getByText('All quiet.')).toBeInTheDocument();
  });

  it('renders an action button and triggers its onClick', () => {
    const handler = vi.fn();
    const withAction: InsightItem[] = [
      {
        id: 'x',
        severity: 'critical',
        title: 'Trust hold',
        action: { label: 'Review', onClick: handler },
      },
    ];
    render(<InsightsPanel items={withAction} />);
    const btn = screen.getByRole('button', { name: /Review/ });
    fireEvent.click(btn);
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('renders an <a> when href is provided', () => {
    const withHref: InsightItem[] = [
      {
        id: 'y',
        severity: 'warning',
        title: 'Pacing breach',
        action: { label: 'Investigate', onClick: () => {}, href: '/pacing/123' },
      },
    ];
    render(<InsightsPanel items={withHref} />);
    const link = screen.getByRole('link', { name: /Investigate/ });
    expect(link).toHaveAttribute('href', '/pacing/123');
  });
});
