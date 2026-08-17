import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

const mockUseRules = vi.fn();

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        'rules.title': 'Rules',
        'rules.subtitle': 'Automation rules',
        'rules.createRule': 'New rule',
        'rules.searchPlaceholder': 'Search rules',
        'rules.allStatuses': 'All statuses',
        'rules.active': 'Active',
        'rules.paused': 'Paused',
        'rules.draft': 'Draft',
      })[key] ?? key,
  }),
}));

vi.mock('@/api/hooks', () => ({
  useRules: () => mockUseRules(),
  useToggleRule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDuplicateRule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateRule: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/usePriceMetrics', () => ({
  usePriceMetrics: () => ({ showPriceMetrics: true }),
}));

import { Rules } from './Rules';

const rule = {
  id: 7,
  name: 'Pause on ROAS collapse',
  description: 'Pause the campaign when ROAS falls below 2.0',
  status: 'active',
  is_active: true,
  condition: { field: 'roas', operator: 'less_than', value: '2.0' },
  action: { type: 'pause_campaign', config: {} },
  trigger_count: 12,
  last_triggered: null,
  cooldown_hours: 24,
  created_at: '2026-08-01T00:00:00Z',
};

function result(overrides: Record<string, unknown> = {}) {
  return {
    data: { items: [], total: 0, skip: 0, limit: 50 },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  mockUseRules.mockReset();
});

describe('Rules', () => {
  it('renders the page title as a level-1 heading', () => {
    mockUseRules.mockReturnValue(result());
    render(<Rules />);
    expect(screen.getByRole('heading', { level: 1, name: 'Rules' })).toBeInTheDocument();
  });

  it('shows an empty message when there are no rules', () => {
    mockUseRules.mockReturnValue(result());
    render(<Rules />);
    expect(screen.getByText(/no automation rules yet/i)).toBeInTheDocument();
  });

  it('surfaces a fetch failure rather than showing an empty list', () => {
    mockUseRules.mockReturnValue(result({ data: undefined, error: new Error('boom') }));
    render(<Rules />);

    expect(screen.getByText(/could not load rules/i)).toBeInTheDocument();
    expect(screen.queryByText(/no automation rules yet/i)).toBeNull();
  });

  it('renders a rule with its status pill', () => {
    mockUseRules.mockReturnValue(result({ data: { items: [rule], total: 1, skip: 0, limit: 50 } }));
    render(<Rules />);

    expect(screen.getByText('Pause on ROAS collapse')).toBeInTheDocument();
    const pill = screen.getAllByText('Active').find((el) => el.closest('[role="status"]'));
    expect(pill).toBeDefined();
  });

  it('derives the triggered-today figure instead of hardcoding it', () => {
    // This stat was the literal `23`, rendered as a live metric regardless of
    // the data. With one rule that has never triggered, the honest answer is 0.
    mockUseRules.mockReturnValue(result({ data: { items: [rule], total: 1, skip: 0, limit: 50 } }));
    const { container } = render(<Rules />);

    const values = Array.from(container.querySelectorAll('[data-slot="stat-value"]')).map(
      (el) => el.textContent,
    );
    expect(values).not.toContain('23');
    expect(values).toContain('0');
  });
});
