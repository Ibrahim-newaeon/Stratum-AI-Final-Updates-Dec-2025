/**
 * OfflineIndicator Component Tests
 *
 * Tests for rendering behavior based on online/offline status,
 * including the reconnected message and the useOnlineStatus hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';

vi.mock('@heroicons/react/24/outline', () => ({
  WifiIcon: (props: any) => <svg data-testid="wifi-icon" {...props} />,
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

import { OfflineIndicator, useOnlineStatus } from './OfflineIndicator';

// ---------------------------------------------------------------------------
// Helper: capture hook value
// ---------------------------------------------------------------------------

function HookTester() {
  const isOnline = useOnlineStatus();
  return <div data-testid="hook-result">{isOnline ? 'online' : 'offline'}</div>;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('OfflineIndicator', () => {
  let originalOnLine: boolean;

  beforeEach(() => {
    originalOnLine = navigator.onLine;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    // Restore navigator.onLine
    Object.defineProperty(navigator, 'onLine', {
      value: originalOnLine,
      writable: true,
      configurable: true,
    });
  });

  it('does not render when online', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: true,
      writable: true,
      configurable: true,
    });

    const { container } = render(<OfflineIndicator />);
    expect(container.innerHTML).toBe('');
  });

  it('renders offline message when browser is offline', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });

    render(<OfflineIndicator />);
    expect(screen.getByText('You are offline')).toBeInTheDocument();
  });

  it('has role="status" for accessibility', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });

    render(<OfflineIndicator />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders the wifi icon', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });

    render(<OfflineIndicator />);
    expect(screen.getByTestId('wifi-icon')).toBeInTheDocument();
  });

  it('shows "Back online" message when going from offline to online', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });

    render(<OfflineIndicator />);
    expect(screen.getByText('You are offline')).toBeInTheDocument();

    // Simulate going online
    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        value: true,
        writable: true,
        configurable: true,
      });
      window.dispatchEvent(new Event('online'));
    });

    expect(screen.getByText('Back online')).toBeInTheDocument();
  });

  it('hides the reconnected message after 3 seconds', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });

    render(<OfflineIndicator />);

    // Go online
    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        value: true,
        writable: true,
        configurable: true,
      });
      window.dispatchEvent(new Event('online'));
    });

    expect(screen.getByText('Back online')).toBeInTheDocument();

    // Advance 3 seconds
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByText('Back online')).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });

    render(<OfflineIndicator className="extra-class" />);
    expect(screen.getByRole('status')).toHaveClass('extra-class');
  });
});

// ---------------------------------------------------------------------------
// useOnlineStatus hook
// ---------------------------------------------------------------------------

describe('useOnlineStatus', () => {
  it('returns true when navigator is online', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: true,
      writable: true,
      configurable: true,
    });

    render(<HookTester />);
    expect(screen.getByTestId('hook-result')).toHaveTextContent('online');
  });

  it('returns false when navigator is offline', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });

    render(<HookTester />);
    expect(screen.getByTestId('hook-result')).toHaveTextContent('offline');
  });

  it('updates when online event fires', () => {
    Object.defineProperty(navigator, 'onLine', {
      value: false,
      writable: true,
      configurable: true,
    });

    render(<HookTester />);
    expect(screen.getByTestId('hook-result')).toHaveTextContent('offline');

    act(() => {
      Object.defineProperty(navigator, 'onLine', {
        value: true,
        writable: true,
        configurable: true,
      });
      window.dispatchEvent(new Event('online'));
    });

    expect(screen.getByTestId('hook-result')).toHaveTextContent('online');
  });
});
