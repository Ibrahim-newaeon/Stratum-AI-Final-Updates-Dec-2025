import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AutopilotPanel } from './AutopilotPanel';

// Mock autopilot API
const mockRefetch = vi.fn();
const mockApproveMutate = vi.fn();
const mockDismissMutate = vi.fn();
const mockApproveAllMutate = vi.fn();

vi.mock('@/api/autopilot', () => ({
  useAutopilotStatus: vi.fn(),
  useAutopilotActions: vi.fn(),
  useApproveAction: vi.fn(),
  useDismissAction: vi.fn(),
  useApproveAllActions: vi.fn(),
  getActionTypeLabel: (type: string) => {
    const labels: Record<string, string> = {
      pause_campaign: 'Pause Campaign',
      increase_budget: 'Increase Budget',
      decrease_budget: 'Decrease Budget',
    };
    return labels[type] || type;
  },
  getActionStatusLabel: (status: string) => {
    const labels: Record<string, string> = {
      queued: 'Queued',
      approved: 'Approved',
      applied: 'Applied',
      failed: 'Failed',
      dismissed: 'Dismissed',
    };
    return labels[status] || status;
  },
  getPlatformIcon: (platform: string) => {
    const icons: Record<string, string> = { meta: 'M', google: 'G' };
    return icons[platform] || '?';
  },
}));

vi.mock('@/stores/featureFlagsStore', () => ({
  useAutopilotLevel: vi.fn(),
}));

import {
  useAutopilotStatus,
  useAutopilotActions,
  useApproveAction,
  useDismissAction,
  useApproveAllActions,
} from '@/api/autopilot';
import { useAutopilotLevel } from '@/stores/featureFlagsStore';

const mockUseAutopilotStatus = useAutopilotStatus as ReturnType<typeof vi.fn>;
const mockUseAutopilotActions = useAutopilotActions as ReturnType<typeof vi.fn>;
const mockUseApproveAction = useApproveAction as ReturnType<typeof vi.fn>;
const mockUseDismissAction = useDismissAction as ReturnType<typeof vi.fn>;
const mockUseApproveAllActions = useApproveAllActions as ReturnType<typeof vi.fn>;
const mockUseAutopilotLevel = useAutopilotLevel as ReturnType<typeof vi.fn>;

const sampleActions = [
  {
    id: 'act-1',
    action_type: 'increase_budget',
    entity_type: 'campaign',
    entity_id: 'camp-1',
    entity_name: 'Summer Sale Campaign',
    platform: 'meta',
    status: 'queued' as const,
    action_json: { new_budget: 500, old_budget: 300 },
    created_at: '2025-12-15T10:00:00Z',
    approved_at: null,
    applied_at: null,
    error: null,
  },
  {
    id: 'act-2',
    action_type: 'pause_campaign',
    entity_type: 'campaign',
    entity_id: 'camp-2',
    entity_name: 'Low ROAS Campaign',
    platform: 'google',
    status: 'applied' as const,
    action_json: {},
    created_at: '2025-12-14T08:00:00Z',
    approved_at: '2025-12-14T09:00:00Z',
    applied_at: '2025-12-14T09:05:00Z',
    error: null,
  },
];

function setupMocks(overrides: {
  level?: number;
  status?: any;
  actions?: any[];
  statusLoading?: boolean;
  actionsLoading?: boolean;
} = {}) {
  const {
    level = 1,
    status = {
      autopilot_level: 1,
      autopilot_level_name: 'Guarded',
      pending_actions: 1,
      caps: { max_daily_budget_change: 500, max_budget_pct_change: 20, max_actions_per_day: 10 },
    },
    actions = sampleActions,
    statusLoading = false,
    actionsLoading = false,
  } = overrides;

  mockUseAutopilotLevel.mockReturnValue(level);
  mockUseAutopilotStatus.mockReturnValue({
    data: status,
    isLoading: statusLoading,
  });
  mockUseAutopilotActions.mockReturnValue({
    data: { actions },
    isLoading: actionsLoading,
    refetch: mockRefetch,
  });
  mockUseApproveAction.mockReturnValue({ mutate: mockApproveMutate, isPending: false });
  mockUseDismissAction.mockReturnValue({ mutate: mockDismissMutate, isPending: false });
  mockUseApproveAllActions.mockReturnValue({ mutate: mockApproveAllMutate, isPending: false });
}

describe('AutopilotPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders suggest-only message when autopilot level is 0', () => {
    setupMocks({ level: 0 });
    render(<AutopilotPanel tenantId={1} />);
    expect(screen.getByText('Autopilot: Suggest Only')).toBeInTheDocument();
    expect(
      screen.getByText(/suggest-only mode/)
    ).toBeInTheDocument();
  });

  it('renders loading skeleton when data is loading', () => {
    setupMocks({ statusLoading: true, actionsLoading: true });
    const { container } = render(<AutopilotPanel tenantId={1} />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders the actions list with correct action types', () => {
    setupMocks();
    render(<AutopilotPanel tenantId={1} />);
    expect(screen.getByText('Autopilot Actions')).toBeInTheDocument();
    expect(screen.getByText('Increase Budget')).toBeInTheDocument();
    expect(screen.getByText('Pause Campaign')).toBeInTheDocument();
  });

  it('shows pending actions alert banner', () => {
    setupMocks();
    render(<AutopilotPanel tenantId={1} />);
    expect(screen.getByText('1 action pending approval')).toBeInTheDocument();
  });

  it('renders approve and dismiss buttons for queued actions', () => {
    setupMocks();
    render(<AutopilotPanel tenantId={1} />);
    // There should be approve/dismiss buttons for the queued action
    const approveButtons = screen.getAllByText('Approve');
    expect(approveButtons.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Dismiss')).toBeInTheDocument();
  });

  it('calls approve mutation when approve button is clicked', () => {
    setupMocks();
    render(<AutopilotPanel tenantId={1} />);
    // Click the Approve button (not the "Approve All")
    const approveButtons = screen.getAllByText('Approve');
    // The individual approve button (not "Approve All (1)")
    const individualApprove = approveButtons.find(
      (btn) => btn.textContent === 'Approve'
    );
    fireEvent.click(individualApprove!);
    expect(mockApproveMutate).toHaveBeenCalledWith('act-1');
  });

  it('calls dismiss mutation when dismiss button is clicked', () => {
    setupMocks();
    render(<AutopilotPanel tenantId={1} />);
    fireEvent.click(screen.getByText('Dismiss'));
    expect(mockDismissMutate).toHaveBeenCalledWith('act-1');
  });

  it('shows Approve All button with correct count', () => {
    setupMocks();
    render(<AutopilotPanel tenantId={1} />);
    expect(screen.getByText('Approve All (1)')).toBeInTheDocument();
  });

  it('renders empty state when no actions are available', () => {
    setupMocks({ actions: [] });
    render(<AutopilotPanel tenantId={1} />);
    expect(
      screen.getByText('Actions will appear here when recommendations are generated.')
    ).toBeInTheDocument();
  });

  it('renders auto-execution caps in footer', () => {
    setupMocks();
    render(<AutopilotPanel tenantId={1} />);
    expect(screen.getByText('Auto-execution caps:')).toBeInTheDocument();
    expect(screen.getByText(/Max 20% change/)).toBeInTheDocument();
    expect(screen.getByText(/Max 10 actions\/day/)).toBeInTheDocument();
  });

  it('renders status filter buttons', () => {
    setupMocks();
    render(<AutopilotPanel tenantId={1} />);
    // "Filter:" label appears once; status labels like "Queued"/"Applied" appear
    // both in the filter bar AND in action status badges, so use getAllByText.
    expect(screen.getAllByText('Filter:').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('All')).toBeInTheDocument();
    expect(screen.getAllByText('Queued').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Applied').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });

  it('renders autopilot level indicator', () => {
    setupMocks();
    render(<AutopilotPanel tenantId={1} />);
    expect(screen.getByText('Guarded')).toBeInTheDocument();
  });
});
