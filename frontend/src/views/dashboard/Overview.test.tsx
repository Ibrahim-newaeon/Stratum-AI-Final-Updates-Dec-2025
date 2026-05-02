/**
 * Overview composition tests.
 *
 * Verifies:
 * - Default focus is the highest-severity alert when no ?focus= is set.
 * - URL ?focus= drives the selected sub-view.
 * - Clicking a chip updates the URL.
 * - Sub-component contents render in their slot positions.
 */

import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useSearchParams } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';

// Mock the data adapter so the test doesn't import useAuth →
// AuthContext → main.tsx → createRoot (pre-existing module-load
// side-effect tracked separately).
vi.mock('./overview/useOverviewData', async () => {
  const mock = await import('./overview/mockData');
  return {
    useOverviewData: () => ({
      kpis: mock.mockKpis,
      alertSummaries: mock.mockAlertSummaries,
      autopilotDecisions: mock.mockAutopilotDecisions,
      isLoading: false,
      error: null,
      isMock: true,
    }),
  };
});

// Mock OutcomeNudge — it pulls in useAuth + useSubscriptionStatus +
// useUpgradePrompt + useAutopilotOutcomeSummary, all of which need
// providers we don't want to wire up for the composition test. The
// component has its own test (committed alongside in P14).
vi.mock('@/components/billing/OutcomeNudge', () => ({
  OutcomeNudge: () => null,
}));

import Overview from './Overview';

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

function renderWithRouter(initialPath = '/dashboard/overview') {
  return render(
    <HelmetProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/dashboard/overview" element={<Overview />} />
        </Routes>
      </MemoryRouter>
    </HelmetProvider>
  );
}

describe('Overview', () => {
  it('renders the page title and tagline', () => {
    renderWithRouter();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Overview' })
    ).toBeInTheDocument();
    expect(screen.getByText(/needs your attention/i)).toBeInTheDocument();
  });

  it('renders all four KPI labels', () => {
    renderWithRouter();
    expect(screen.getByText('Trust Gate')).toBeInTheDocument();
    expect(screen.getByText('Signal Health')).toBeInTheDocument();
    expect(screen.getByText('ROAS · today')).toBeInTheDocument();
    expect(screen.getByText('Pacing · today')).toBeInTheDocument();
  });

  it('renders the SignalStrip with alert chips', () => {
    renderWithRouter();
    // Each chip label appears at least once. ("Trust holds" also appears
    // as the FocusPane heading because it's the default-selected focus.)
    expect(screen.getAllByText('Trust holds').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Signal drops')).toBeInTheDocument();
    expect(screen.getByText('Autopilot pending')).toBeInTheDocument();
  });

  it('defaults focus to the highest-severity alert (trust-holds)', () => {
    renderWithRouter();
    // FocusPane heading "Trust holds" appears in two places:
    // 1) the chip label, 2) the FocusPane h2. Confirm the h2 is present.
    expect(
      screen.getByRole('heading', { level: 2, name: /Trust holds/i })
    ).toBeInTheDocument();
  });

  it('honors ?focus= query param', () => {
    renderWithRouter('/dashboard/overview?focus=signal-drops');
    expect(
      screen.getByRole('heading', { level: 2, name: /Signal drops/i })
    ).toBeInTheDocument();
  });

  it('falls back to the default focus when ?focus is invalid', () => {
    renderWithRouter('/dashboard/overview?focus=plaid');
    // Defaults to highest-severity (trust-holds).
    expect(
      screen.getByRole('heading', { level: 2, name: /Trust holds/i })
    ).toBeInTheDocument();
  });

  it('updates the URL when a chip is clicked', () => {
    let capturedSearch = '';
    function SearchSink() {
      const [params] = useSearchParams();
      capturedSearch = params.toString();
      return null;
    }

    render(
      <HelmetProvider>
        <MemoryRouter initialEntries={['/dashboard/overview']}>
          <Routes>
            <Route
              path="/dashboard/overview"
              element={
                <>
                  <Overview />
                  <SearchSink />
                </>
              }
            />
          </Routes>
        </MemoryRouter>
      </HelmetProvider>
    );

    const signalChip = screen.getByText('Signal drops').closest('button')!;
    fireEvent.click(signalChip);
    expect(capturedSearch).toContain('focus=signal-drops');
  });

  it('renders the RecentAutopilot section', () => {
    renderWithRouter();
    expect(screen.getByText('Recent autopilot decisions')).toBeInTheDocument();
    // First mock row campaign label
    expect(screen.getByText('Last 24h')).toBeInTheDocument();
  });
});
