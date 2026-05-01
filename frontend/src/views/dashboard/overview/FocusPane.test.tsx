/**
 * FocusPane tests — verifies the URL-driven adaptive surface renders
 * the right sub-view content per focus key. We don't assert pixel
 * detail; we assert which "kind of view" rendered (heading + key copy).
 */

import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FocusPane } from './FocusPane';
import { mockAutopilotDecisions } from './mockData';

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

describe('FocusPane', () => {
  it('renders the trust-holds table view', () => {
    render(<FocusPane focus="trust-holds" />);
    expect(screen.getByText('Trust holds')).toBeInTheDocument();
    expect(screen.getByText(/Summer Sale — Prospecting/)).toBeInTheDocument();
    // Per-row CTA buttons
    expect(screen.getAllByText(/Pause|Hold|Scale/).length).toBeGreaterThan(0);
  });

  it('renders the signal-drops EMQ view', () => {
    render(<FocusPane focus="signal-drops" />);
    expect(screen.getByText('Signal drops')).toBeInTheDocument();
    expect(screen.getByText(/EMQ score/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /View pipeline/ })).toBeInTheDocument();
  });

  it('renders the pacing-breaches table view', () => {
    render(<FocusPane focus="pacing-breaches" />);
    expect(screen.getByText('Pacing breaches')).toBeInTheDocument();
    expect(screen.getByText(/Q2 EU — Performance/)).toBeInTheDocument();
  });

  it('renders the autopilot-pending table view (filtered)', () => {
    const pending = mockAutopilotDecisions.filter((r) => r.result === 'pending');
    render(<FocusPane focus="autopilot-pending" autopilotPending={pending} />);
    expect(screen.getByText('Autopilot pending')).toBeInTheDocument();
    expect(screen.getByText(/Brand EU — Search/)).toBeInTheDocument();
  });

  it('renders the all-clear chart view', () => {
    render(<FocusPane focus="all-clear" />);
    expect(screen.getByText('System nominal')).toBeInTheDocument();
    expect(screen.getByText(/All signals operational/)).toBeInTheDocument();
  });
});
