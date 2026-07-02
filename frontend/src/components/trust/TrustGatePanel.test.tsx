import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TrustGatePanel } from './TrustGatePanel';

vi.mock('@/api/trustLayer', () => ({
  useTrustGateStatus: vi.fn(),
  useEvaluateTrustGate: vi.fn(),
}));

import { useTrustGateStatus, useEvaluateTrustGate } from '@/api/trustLayer';

const mockUseTrustGateStatus = useTrustGateStatus as ReturnType<typeof vi.fn>;
const mockUseEvaluateTrustGate = useEvaluateTrustGate as ReturnType<typeof vi.fn>;

const healthyGate = {
  data_available: true,
  as_of_date: '2026-07-01',
  signal_health: {
    score: 88.5,
    status: 'healthy',
    components: { emq: 90, freshness: 95, variance: 80, anomaly: 85 },
    issues: [],
  },
  autopilot_mode: 'normal',
  mode_reason: 'Signal health is excellent - full autopilot enabled',
  allowed_actions: ['increase_budget', 'pause_campaign'],
  restricted_actions: [],
  thresholds: {
    pass_threshold: 70,
    hold_threshold: 40,
    high_risk_threshold: 85,
    conservative_threshold: 60,
    high_risk_actions: ['increase_budget'],
    conservative_actions: ['decrease_budget'],
    always_allowed_actions: ['pause_campaign'],
  },
};

const noDataGate = {
  ...healthyGate,
  data_available: false,
  as_of_date: null,
  signal_health: {
    score: 0,
    status: 'critical',
    components: { emq: 0, freshness: 0, variance: 0, anomaly: 0 },
    issues: ['No signal health data for this tenant — run the rollup'],
  },
  autopilot_mode: 'frozen',
  mode_reason: 'Signal health is critical - automation frozen',
  allowed_actions: [],
  restricted_actions: ['increase_budget', 'pause_campaign'],
};

const idleMutation = {
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  data: undefined,
  error: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  mockUseEvaluateTrustGate.mockReturnValue({ ...idleMutation });
});

describe('TrustGatePanel', () => {
  it('shows a loading skeleton while fetching', () => {
    mockUseTrustGateStatus.mockReturnValue({ isLoading: true, isError: false, data: undefined });
    render(<TrustGatePanel tenantId={2} />);
    expect(screen.getByLabelText('Loading trust gate status')).toBeInTheDocument();
  });

  it('shows an error state with retry', () => {
    const refetch = vi.fn();
    mockUseTrustGateStatus.mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
      refetch,
    });
    render(<TrustGatePanel tenantId={2} />);
    fireEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(refetch).toHaveBeenCalled();
  });

  it('renders mode, score, and allowed/restricted actions', () => {
    mockUseTrustGateStatus.mockReturnValue({ isLoading: false, isError: false, data: healthyGate });
    render(<TrustGatePanel tenantId={2} />);

    expect(screen.getByText(/Autopilot: Normal/)).toBeInTheDocument();
    expect(screen.getByText('89')).toBeInTheDocument(); // rounded 88.5
    // Each action shows as an allowed chip AND a select option
    const chips = screen.getAllByRole('listitem').map((li) => li.textContent);
    expect(chips).toContain('increase_budget');
    expect(chips).toContain('pause_campaign');
    expect(screen.getByText(/Signal health as of 2026-07-01/)).toBeInTheDocument();
  });

  it('flags the no-rollup-data posture', () => {
    mockUseTrustGateStatus.mockReturnValue({ isLoading: false, isError: false, data: noDataGate });
    render(<TrustGatePanel tenantId={2} />);

    expect(screen.getByText(/Autopilot: Frozen/)).toBeInTheDocument();
    expect(screen.getByText(/No signal health rollup yet/)).toBeInTheDocument();
    expect(
      screen.getByText('No signal health data for this tenant — run the rollup')
    ).toBeInTheDocument();
  });

  it('submits an evaluation with the selected action and entity', () => {
    const mutate = vi.fn();
    mockUseTrustGateStatus.mockReturnValue({ isLoading: false, isError: false, data: healthyGate });
    mockUseEvaluateTrustGate.mockReturnValue({ ...idleMutation, mutate });
    render(<TrustGatePanel tenantId={2} />);

    fireEvent.change(screen.getByLabelText(/Entity ID/), { target: { value: 'camp-42' } });
    fireEvent.click(screen.getByRole('button', { name: /evaluate/i }));

    expect(mutate).toHaveBeenCalledWith({
      action_type: 'increase_budget',
      entity_type: 'campaign',
      entity_id: 'camp-42',
      platform: 'meta',
    });
  });

  it('renders the PASS decision with reason and recommendations', () => {
    mockUseTrustGateStatus.mockReturnValue({ isLoading: false, isError: false, data: healthyGate });
    mockUseEvaluateTrustGate.mockReturnValue({
      ...idleMutation,
      data: {
        decision: 'pass',
        signalHealth: { ...healthyGate.signal_health, hasCdpData: null },
        action: { type: 'increase_budget', entity: 'campaign/camp-42', platform: 'meta' },
        reason: 'Signal health is healthy (88.5)',
        allowedActions: ['increase_budget'],
        restrictedActions: [],
        recommendations: ['Proceed with automation'],
        evaluatedAt: '2026-07-02T12:00:00Z',
        data_available: true,
      },
    });
    render(<TrustGatePanel tenantId={2} />);

    expect(screen.getByText('PASS')).toBeInTheDocument();
    expect(screen.getByText('Signal health is healthy (88.5)')).toBeInTheDocument();
    expect(screen.getByText('Proceed with automation')).toBeInTheDocument();
  });

  it('disables the evaluate button while pending', () => {
    mockUseTrustGateStatus.mockReturnValue({ isLoading: false, isError: false, data: healthyGate });
    mockUseEvaluateTrustGate.mockReturnValue({ ...idleMutation, isPending: true });
    render(<TrustGatePanel tenantId={2} />);

    expect(screen.getByRole('button', { name: /evaluating/i })).toBeDisabled();
  });
});
