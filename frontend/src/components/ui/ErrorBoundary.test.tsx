/**
 * Stratum AI - ErrorBoundary Tests
 *
 * Tests for error catching, chunk load error detection,
 * retry/reload behavior, and fallback components.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary, ChartErrorFallback, WidgetErrorFallback } from './ErrorBoundary';

// Suppress console.error during error boundary tests
const originalConsoleError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});
afterEach(() => {
  console.error = originalConsoleError;
});

// ---------------------------------------------------------------------------
// Helper: a component that throws on render
// ---------------------------------------------------------------------------

function ThrowingComponent({ error }: { error: Error }) {
  throw error;
}

function GoodComponent() {
  return <div data-testid="good-child">Hello</div>;
}

// =============================================================================
// ErrorBoundary
// =============================================================================

describe('ErrorBoundary', () => {
  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <GoodComponent />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('good-child')).toBeInTheDocument();
  });

  it('renders default fallback UI when a child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent error={new Error('test error')} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText('test error')).toBeInTheDocument();
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom Error</div>}>
        <ThrowingComponent error={new Error('test')} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });

  it('renders custom message when provided', () => {
    render(
      <ErrorBoundary message="Custom error message">
        <ThrowingComponent error={new Error('test')} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error message')).toBeInTheDocument();
  });

  it('calls onError callback when error is caught', () => {
    const onError = vi.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ThrowingComponent error={new Error('callback test')} />
      </ErrorBoundary>
    );

    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'callback test' }),
      expect.objectContaining({ componentStack: expect.any(String) })
    );
  });

  it('resets error state when "Try Again" is clicked', () => {
    let shouldThrow = true;

    function ConditionalThrower() {
      if (shouldThrow) {
        throw new Error('conditional error');
      }
      return <div data-testid="recovered">Recovered!</div>;
    }

    render(
      <ErrorBoundary>
        <ConditionalThrower />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    // Fix the error before retrying
    shouldThrow = false;
    fireEvent.click(screen.getByText('Try Again'));

    expect(screen.getByTestId('recovered')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Chunk loading error detection
  // -------------------------------------------------------------------------

  it('detects "Failed to fetch dynamically imported module" as chunk error', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent error={new Error('Failed to fetch dynamically imported module /chunk.js')} />
      </ErrorBoundary>
    );

    expect(screen.getByText('New version available')).toBeInTheDocument();
    expect(screen.getByText('Reload Page')).toBeInTheDocument();
  });

  it('detects "Loading chunk" as chunk error', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent error={new Error('Loading chunk 42 failed')} />
      </ErrorBoundary>
    );

    expect(screen.getByText('New version available')).toBeInTheDocument();
  });

  it('detects "Loading CSS chunk" as chunk error', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent error={new Error('Loading CSS chunk 7 failed')} />
      </ErrorBoundary>
    );

    expect(screen.getByText('New version available')).toBeInTheDocument();
  });

  it('detects ChunkLoadError by error name', () => {
    const error = new Error('chunk failed');
    error.name = 'ChunkLoadError';

    render(
      <ErrorBoundary>
        <ThrowingComponent error={error} />
      </ErrorBoundary>
    );

    expect(screen.getByText('New version available')).toBeInTheDocument();
  });

  it('chunk error shows reload button that calls window.location.reload', () => {
    const reloadMock = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { ...window.location, reload: reloadMock },
      writable: true,
    });

    render(
      <ErrorBoundary>
        <ThrowingComponent error={new Error('Failed to fetch dynamically imported module /chunk.js')} />
      </ErrorBoundary>
    );

    fireEvent.click(screen.getByText('Reload Page'));
    expect(reloadMock).toHaveBeenCalled();
  });

  it('applies custom className to fallback UI', () => {
    const { container } = render(
      <ErrorBoundary className="custom-error-class">
        <ThrowingComponent error={new Error('test')} />
      </ErrorBoundary>
    );

    expect(container.querySelector('.custom-error-class')).toBeInTheDocument();
  });
});

// =============================================================================
// ChartErrorFallback
// =============================================================================

describe('ChartErrorFallback', () => {
  it('renders chart unavailable message', () => {
    render(<ChartErrorFallback />);

    expect(screen.getByText('Chart unavailable')).toBeInTheDocument();
    expect(screen.getByText('Failed to render chart data')).toBeInTheDocument();
  });

  it('shows retry button when onRetry is provided', () => {
    const onRetry = vi.fn();
    render(<ChartErrorFallback onRetry={onRetry} />);

    const retryButton = screen.getByText('Retry');
    expect(retryButton).toBeInTheDocument();

    fireEvent.click(retryButton);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('does not show retry button when onRetry is not provided', () => {
    render(<ChartErrorFallback />);

    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });

  it('applies custom height', () => {
    const { container } = render(<ChartErrorFallback height={500} />);
    const wrapper = container.firstChild as HTMLElement;

    expect(wrapper.style.height).toBe('500px');
  });

  it('defaults to 300px height', () => {
    const { container } = render(<ChartErrorFallback />);
    const wrapper = container.firstChild as HTMLElement;

    expect(wrapper.style.height).toBe('300px');
  });
});

// =============================================================================
// WidgetErrorFallback
// =============================================================================

describe('WidgetErrorFallback', () => {
  it('renders widget unavailable message', () => {
    render(<WidgetErrorFallback />);

    expect(screen.getByText('Unable to load this widget')).toBeInTheDocument();
  });

  it('renders title when provided', () => {
    render(<WidgetErrorFallback title="Revenue Widget" />);

    expect(screen.getByText('Revenue Widget')).toBeInTheDocument();
  });

  it('does not render title when not provided', () => {
    render(<WidgetErrorFallback />);

    // The only text should be the error message
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
  });

  it('shows retry button when onRetry is provided', () => {
    const onRetry = vi.fn();
    render(<WidgetErrorFallback onRetry={onRetry} />);

    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('does not show retry button when onRetry is not provided', () => {
    render(<WidgetErrorFallback />);

    expect(screen.queryByText('Retry')).not.toBeInTheDocument();
  });
});
