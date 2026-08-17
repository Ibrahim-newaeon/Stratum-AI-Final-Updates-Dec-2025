import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

const mockUseTrustGateStatus = vi.fn();

vi.mock('@/api/trustLayer', () => ({
  useTrustGateStatus: () => mockUseTrustGateStatus(),
}));

vi.mock('@/stores/tenantStore', () => ({
  useTenantStore: (selector: (s: unknown) => unknown) => selector({ currentTenant: { id: 1 } }),
  selectTenantId: (s: { currentTenant?: { id: number } }) => s.currentTenant?.id ?? 0,
}));

import { TrustEngine } from './TrustEngine';

function result(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      data_available: true,
      as_of_date: '2026-08-17',
      signal_health: {
        score: 82,
        status: 'healthy',
        components: { emq: 78, freshness: 91, variance: 85, anomaly: 88 },
        issues: ['EMQ score below target: 78.0 (target: 90)'],
      },
      autopilot_mode: 'normal',
      mode_reason: 'Signal health is healthy; all automation permitted.',
      allowed_actions: ['adjust_budget', 'pause_campaign'],
      restricted_actions: [],
      thresholds: { pass_threshold: 70, hold_threshold: 40 },
    },
    isLoading: false,
    error: null,
    ...overrides,
  };
}

beforeEach(() => {
  mockUseTrustGateStatus.mockReset();
});

describe('TrustEngine', () => {
  it('renders the page title as a level-1 heading', () => {
    mockUseTrustGateStatus.mockReturnValue(result());
    render(<TrustEngine />);
    expect(screen.getByRole('heading', { level: 1, name: /trust engine/i })).toBeInTheDocument();
  });

  it('shows the composite score and gate status', () => {
    mockUseTrustGateStatus.mockReturnValue(result());
    render(<TrustEngine />);

    // The score appears twice by design: once in the stat row, once as the
    // large composite figure.
    expect(screen.getAllByText('82').length).toBeGreaterThan(0);
    const pill = screen.getAllByText(/healthy/i).find((el) => el.closest('[role="status"]'));
    expect(pill).toBeDefined();
  });

  it('decomposes the score into its real components', () => {
    // The score alone is a claim; the score beside the inputs that produced it
    // is a method. These are the components the API actually returns — emq,
    // freshness, variance, anomaly — not the five weighted ones CLAUDE.md
    // documents but no code computes.
    mockUseTrustGateStatus.mockReturnValue(result());
    render(<TrustEngine />);

    // "emq" also appears inside the issue string, so assert presence rather
    // than uniqueness.
    for (const name of ['emq', 'freshness', 'variance', 'anomaly']) {
      expect(screen.getAllByText(new RegExp(name, 'i')).length).toBeGreaterThan(0);
    }
    expect(screen.getAllByText('78').length).toBeGreaterThan(0);
  });

  it("renders the calculator's own reason strings verbatim", () => {
    // Rendering the backend's issue text rather than re-deriving a sentence in
    // the frontend is what stops the UI drifting from the logic.
    mockUseTrustGateStatus.mockReturnValue(result());
    render(<TrustEngine />);
    expect(
      screen.getByText('EMQ score below target: 78.0 (target: 90)'),
    ).toBeInTheDocument();
  });

  it('shows the tenant-configured thresholds, not hardcoded defaults', () => {
    mockUseTrustGateStatus.mockReturnValue(
      result({
        data: {
          ...result().data,
          thresholds: { pass_threshold: 85, hold_threshold: 55 },
        },
      }),
    );
    render(<TrustEngine />);

    expect(screen.getAllByText('85').length).toBeGreaterThan(0);
    expect(screen.getAllByText('55').length).toBeGreaterThan(0);
  });

  it('surfaces a fetch failure rather than an empty screen', () => {
    mockUseTrustGateStatus.mockReturnValue(
      result({ data: undefined, error: new Error('boom') }),
    );
    render(<TrustEngine />);
    expect(screen.getByText(/could not load trust status/i)).toBeInTheDocument();
  });

  it('says plainly when no signal data exists yet', () => {
    // data_available=false is not the same as an error, and neither is the same
    // as a healthy gate. All three must look different.
    mockUseTrustGateStatus.mockReturnValue(
      result({ data: { ...result().data, data_available: false } }),
    );
    render(<TrustEngine />);
    expect(screen.getByText(/no signal data/i)).toBeInTheDocument();
  });
});
