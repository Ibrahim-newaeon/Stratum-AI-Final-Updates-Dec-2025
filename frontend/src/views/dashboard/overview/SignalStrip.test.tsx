import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SignalStrip } from './SignalStrip';
import type { AlertSummary } from './types';

const summaries: AlertSummary[] = [
  { count: 3, severity: 'critical', focus: 'trust-holds', label: 'Trust holds' },
  { count: 2, severity: 'warning', focus: 'signal-drops', label: 'Signal drops' },
  { count: 5, severity: 'info', focus: 'autopilot-pending', label: 'Autopilot pending' },
];

describe('SignalStrip', () => {
  it('renders an "All clear" state when totals are zero', () => {
    render(
      <SignalStrip
        summaries={[
          { count: 0, severity: 'critical', focus: 'trust-holds', label: 'Trust holds' },
        ]}
        selectedFocus="all-clear"
        onSelectFocus={() => {}}
      />
    );
    expect(screen.getByText('All clear.')).toBeInTheDocument();
  });

  it('renders all alert chips with counts and labels', () => {
    render(
      <SignalStrip
        summaries={summaries}
        selectedFocus="trust-holds"
        onSelectFocus={() => {}}
      />
    );
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Trust holds')).toBeInTheDocument();
    expect(screen.getByText('Signal drops')).toBeInTheDocument();
    expect(screen.getByText('Autopilot pending')).toBeInTheDocument();
  });

  it('marks the selected chip with aria-pressed=true', () => {
    render(
      <SignalStrip
        summaries={summaries}
        selectedFocus="signal-drops"
        onSelectFocus={() => {}}
      />
    );
    const buttons = screen.getAllByRole('button', { pressed: true });
    expect(buttons.length).toBe(1);
    expect(buttons[0].textContent).toMatch(/Signal drops/);
  });

  it('calls onSelectFocus when a chip is clicked', () => {
    const handler = vi.fn();
    render(
      <SignalStrip
        summaries={summaries}
        selectedFocus="trust-holds"
        onSelectFocus={handler}
      />
    );
    const trustChip = screen.getByText('Trust holds').closest('button')!;
    const signalChip = screen.getByText('Signal drops').closest('button')!;
    fireEvent.click(signalChip);
    expect(handler).toHaveBeenCalledWith('signal-drops');
    fireEvent.click(trustChip);
    expect(handler).toHaveBeenCalledWith('trust-holds');
  });

  it('renders "Acknowledge all" only when there are alerts and a handler is provided', () => {
    const handler = vi.fn();
    const { rerender } = render(
      <SignalStrip
        summaries={summaries}
        selectedFocus="trust-holds"
        onSelectFocus={() => {}}
        onAcknowledgeAll={handler}
      />
    );
    const ack = screen.getByRole('button', { name: /Acknowledge all/ });
    fireEvent.click(ack);
    expect(handler).toHaveBeenCalledTimes(1);

    rerender(
      <SignalStrip
        summaries={summaries}
        selectedFocus="trust-holds"
        onSelectFocus={() => {}}
      />
    );
    expect(screen.queryByRole('button', { name: /Acknowledge all/ })).not.toBeInTheDocument();
  });

  it('shows skeleton chips while loading', () => {
    const { container } = render(
      <SignalStrip
        summaries={[]}
        selectedFocus="all-clear"
        onSelectFocus={() => {}}
        loading
      />
    );
    expect(container.querySelectorAll('.animate-pulse').length).toBe(3);
  });
});
