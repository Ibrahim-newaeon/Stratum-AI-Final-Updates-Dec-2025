/**
 * Launch Readiness view tests
 *
 * Covers:
 * - Header and overall progress rendering
 * - All 12 phases render
 * - The active phase is auto-expanded; locked phases show a lock badge
 * - Locked phase items cannot be toggled (checkbox disabled)
 * - Toggling an item in the active phase fires the mutation
 * - Unchecking an item in a completed phase triggers a confirm prompt
 *   and is cancelled if the user declines
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createElement, type ReactNode } from 'react'
import LaunchReadiness from './LaunchReadiness'
import type {
  LaunchReadinessState,
  LaunchReadinessPhase,
} from '@/api/launchReadiness'

// -----------------------------------------------------------------------------
// Mocks
// Factories for vi.mock are hoisted to the top of the file, so they can
// only reference symbols that are available at module-load time. Use
// createElement (not JSX) and vi.hoisted() for shared fn state.
// -----------------------------------------------------------------------------
const { mockUseState, mockUseEvents, mockToggleMutate } = vi.hoisted(() => ({
  mockUseState: vi.fn(),
  mockUseEvents: vi.fn(),
  mockToggleMutate: vi.fn(),
}))

vi.mock('@/api/launchReadiness', () => ({
  useLaunchReadinessState: () => mockUseState(),
  useLaunchReadinessEvents: () => mockUseEvents(),
  useToggleLaunchReadinessItem: () => ({
    mutate: mockToggleMutate,
    isPending: false,
  }),
}))

// Explicit icon exports — avoid Proxy-based factories because vitest's
// module namespace resolution treats those as broken modules.
vi.mock('@heroicons/react/24/outline', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const React = require('react')
  const Icon = (props: Record<string, unknown>) =>
    React.createElement('svg', props)
  return {
    CheckCircleIcon: Icon,
    LockClosedIcon: Icon,
    ChevronDownIcon: Icon,
    ChevronRightIcon: Icon,
    ClockIcon: Icon,
    RocketLaunchIcon: Icon,
    ExclamationTriangleIcon: Icon,
    BoltIcon: Icon,
  }
})

vi.mock('@heroicons/react/24/solid', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const React = require('react')
  const Icon = (props: Record<string, unknown>) =>
    React.createElement('svg', props)
  return {
    CheckCircleIcon: Icon,
  }
})

// -----------------------------------------------------------------------------
// Fixtures
// -----------------------------------------------------------------------------
function makePhase(
  number: number,
  overrides: Partial<LaunchReadinessPhase> = {}
): LaunchReadinessPhase {
  const base: LaunchReadinessPhase = {
    number,
    slug: `phase-${number}`,
    title: `Phase ${number}`,
    description: `Description for phase ${number}`,
    items: [
      {
        key: `p${number}_item_a`,
        title: `Phase ${number} item A`,
        description: null,
        is_checked: false,
      },
      {
        key: `p${number}_item_b`,
        title: `Phase ${number} item B`,
        description: null,
        is_checked: false,
      },
    ],
    completed_count: 0,
    total_count: 2,
    is_complete: false,
    is_active: false,
    is_locked: true,
  }
  return { ...base, ...overrides }
}

function makeState(currentPhase: number): LaunchReadinessState {
  const phases: LaunchReadinessPhase[] = Array.from({ length: 12 }, (_, i) => {
    const n = i + 1
    if (n < currentPhase) {
      return makePhase(n, {
        items: [
          {
            key: `p${n}_item_a`,
            title: `Phase ${n} item A`,
            description: null,
            is_checked: true,
            checked_by_user_name: 'Test Admin',
            checked_at: '2026-04-20T10:00:00Z',
          },
          {
            key: `p${n}_item_b`,
            title: `Phase ${n} item B`,
            description: null,
            is_checked: true,
            checked_by_user_name: 'Test Admin',
            checked_at: '2026-04-20T10:05:00Z',
          },
        ],
        completed_count: 2,
        is_complete: true,
        is_active: false,
        is_locked: false,
      })
    }
    if (n === currentPhase) {
      return makePhase(n, { is_active: true, is_locked: false })
    }
    return makePhase(n, { is_locked: true })
  })

  const overallCompleted = phases.reduce((s, p) => s + p.completed_count, 0)
  const overallTotal = phases.reduce((s, p) => s + p.total_count, 0)

  return {
    phases,
    current_phase_number: currentPhase,
    overall_completed: overallCompleted,
    overall_total: overallTotal,
    is_launched: false,
  }
}

function renderView() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  const Wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
  return render(createElement(LaunchReadiness), { wrapper: Wrapper })
}

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------
describe('LaunchReadiness', () => {
  beforeEach(() => {
    mockUseState.mockReset()
    mockUseEvents.mockReset()
    mockToggleMutate.mockReset()
    // Default: events empty
    mockUseEvents.mockReturnValue({ data: [], isLoading: false })
  })

  it('shows a loading skeleton while state is loading', () => {
    mockUseState.mockReturnValue({ data: undefined, isLoading: true, error: null })
    const { container } = renderView()
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })

  it('renders the header and overall progress', () => {
    mockUseState.mockReturnValue({
      data: makeState(3),
      isLoading: false,
      error: null,
    })
    renderView()
    expect(screen.getByText('Launch Readiness')).toBeInTheDocument()
    // Phase 1 and 2 complete = 4 of 24 total items checked → 17%
    expect(screen.getByText(/17%/)).toBeInTheDocument()
    expect(screen.getByText('/ 24')).toBeInTheDocument()
    expect(screen.getByText(/Phase 3 of 12/)).toBeInTheDocument()
  })

  it('renders all twelve phase cards', () => {
    mockUseState.mockReturnValue({
      data: makeState(1),
      isLoading: false,
      error: null,
    })
    renderView()
    for (let n = 1; n <= 12; n++) {
      expect(screen.getByText(`Phase ${n} — Phase ${n}`)).toBeInTheDocument()
    }
  })

  it('auto-expands the active phase and shows In progress badge', () => {
    mockUseState.mockReturnValue({
      data: makeState(2),
      isLoading: false,
      error: null,
    })
    renderView()
    // Active phase shows its items inline. Completed phases are
    // collapsed by default (only active auto-expands).
    expect(screen.getByText('Phase 2 item A')).toBeInTheDocument()
    expect(screen.getByText('Phase 2 item B')).toBeInTheDocument()
    expect(screen.getAllByText('In progress').length).toBeGreaterThan(0)
  })

  it('shows Locked pills on phases beyond the current one', () => {
    mockUseState.mockReturnValue({
      data: makeState(1),
      isLoading: false,
      error: null,
    })
    renderView()
    // Phases 2–12 are locked.
    expect(screen.getAllByText('Locked').length).toBe(11)
  })

  it('shows Complete pills on phases before the current one', () => {
    mockUseState.mockReturnValue({
      data: makeState(4),
      isLoading: false,
      error: null,
    })
    renderView()
    expect(screen.getAllByText('Complete').length).toBe(3)
  })

  it('fires the toggle mutation when clicking an unchecked item in the active phase', () => {
    mockUseState.mockReturnValue({
      data: makeState(2),
      isLoading: false,
      error: null,
    })
    renderView()

    // Active phase (2) is auto-expanded and has 2 items.
    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes.length).toBeGreaterThanOrEqual(2)

    fireEvent.click(checkboxes[0])

    expect(mockToggleMutate).toHaveBeenCalledTimes(1)
    const call = mockToggleMutate.mock.calls[0][0]
    expect(call.itemKey).toMatch(/^p2_item_/)
    expect(call.checked).toBe(true)
  })

  it('does not fire the mutation when a locked-phase item is clicked', () => {
    mockUseState.mockReturnValue({
      data: makeState(1),
      isLoading: false,
      error: null,
    })
    const { container } = renderView()

    // Find a locked phase card and expand it manually.
    const phase4Header = screen.getByText('Phase 4 — Phase 4').closest('button')!
    fireEvent.click(phase4Header)

    // Click should be a no-op because the checkbox is disabled.
    const allCheckboxes = container.querySelectorAll('[role="checkbox"]')
    const lockedBox = Array.from(allCheckboxes).find(
      (el) => (el as HTMLButtonElement).disabled
    )
    expect(lockedBox).toBeDefined()
    fireEvent.click(lockedBox!)
    expect(mockToggleMutate).not.toHaveBeenCalled()
  })

  it('prompts for confirmation when unchecking a completed-phase item, and respects cancel', () => {
    mockUseState.mockReturnValue({
      data: makeState(3),
      isLoading: false,
      error: null,
    })
    renderView()

    // Expand a completed phase (phase 1).
    const phase1Header = screen.getByText('Phase 1 — Phase 1').closest('button')!
    fireEvent.click(phase1Header)

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)

    // Find the first checkbox inside the phase 1 region (both items checked).
    const allCheckboxes = screen.getAllByRole('checkbox') as HTMLButtonElement[]
    const checkedBoxes = allCheckboxes.filter(
      (b) => b.getAttribute('aria-checked') === 'true'
    )
    expect(checkedBoxes.length).toBeGreaterThan(0)
    fireEvent.click(checkedBoxes[0])

    expect(confirmSpy).toHaveBeenCalled()
    expect(mockToggleMutate).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('proceeds with the mutation when the user confirms the reopen prompt', () => {
    mockUseState.mockReturnValue({
      data: makeState(3),
      isLoading: false,
      error: null,
    })
    renderView()

    const phase1Header = screen.getByText('Phase 1 — Phase 1').closest('button')!
    fireEvent.click(phase1Header)

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    const checkedBoxes = (
      screen.getAllByRole('checkbox') as HTMLButtonElement[]
    ).filter((b) => b.getAttribute('aria-checked') === 'true')
    fireEvent.click(checkedBoxes[0])

    expect(confirmSpy).toHaveBeenCalled()
    expect(mockToggleMutate).toHaveBeenCalledTimes(1)
    const call = mockToggleMutate.mock.calls[0][0]
    expect(call.checked).toBe(false)
    confirmSpy.mockRestore()
  })

  it('shows a cleared-to-launch message when every phase is complete', () => {
    const state = makeState(13) // currentPhase beyond last phase = all done
    state.is_launched = true
    // makeState(13) marks every phase as "before current" → all complete
    mockUseState.mockReturnValue({
      data: state,
      isLoading: false,
      error: null,
    })
    renderView()
    expect(screen.getByText(/cleared to launch/i)).toBeInTheDocument()
  })

  it('renders an error message when the state query fails', () => {
    mockUseState.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('boom'),
    })
    renderView()
    expect(
      screen.getByText(/Failed to load Launch Readiness state/i)
    ).toBeInTheDocument()
  })

  it('renders the audit trail with events', () => {
    mockUseState.mockReturnValue({
      data: makeState(2),
      isLoading: false,
      error: null,
    })
    mockUseEvents.mockReturnValue({
      data: [
        {
          id: 1,
          phase_number: 1,
          item_key: 'p1_item_a',
          action: 'checked',
          user_id: 1,
          user_name: 'Alice',
          note: null,
          created_at: '2026-04-20T10:00:00Z',
        },
      ],
      isLoading: false,
    })
    renderView()

    const activity = screen.getByText('Activity').parentElement!.parentElement!
    expect(within(activity).getByText('checked')).toBeInTheDocument()
    expect(within(activity).getByText(/p1_item_a/)).toBeInTheDocument()
  })
})
