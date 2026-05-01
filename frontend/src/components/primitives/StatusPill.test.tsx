import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusPill } from './StatusPill';

describe('StatusPill', () => {
  it('renders the label', () => {
    render(<StatusPill>Operational</StatusPill>);
    expect(screen.getByText('Operational')).toBeInTheDocument();
  });

  it('exposes role=status with aria-live=polite', () => {
    render(<StatusPill>Operational</StatusPill>);
    const pill = screen.getByRole('status');
    expect(pill.getAttribute('aria-live')).toBe('polite');
  });

  it.each([
    ['healthy', 'bg-success'],
    ['degraded', 'bg-warning'],
    ['unhealthy', 'bg-danger'],
    ['neutral', 'bg-primary'],
  ] as const)('applies the right dot color for variant=%s', (variant, dotClass) => {
    const { container } = render(<StatusPill variant={variant}>x</StatusPill>);
    const dot = container.querySelector('[aria-hidden="true"]');
    expect(dot?.className).toContain(dotClass);
  });

  it('applies pulse animation when pulse=true', () => {
    const { container } = render(
      <StatusPill variant="healthy" pulse>
        Live
      </StatusPill>
    );
    const dot = container.querySelector('[aria-hidden="true"]');
    expect(dot?.className).toContain('animate-pulse');
  });

  it('omits pulse animation by default', () => {
    const { container } = render(<StatusPill>Idle</StatusPill>);
    const dot = container.querySelector('[aria-hidden="true"]');
    expect(dot?.className).not.toContain('animate-pulse');
  });

  it('size=sm uses smaller padding', () => {
    render(
      <StatusPill size="sm" data-testid="pill">
        x
      </StatusPill>
    );
    expect(screen.getByTestId('pill').className).toContain('px-2.5');
  });

  it('size=md uses default padding', () => {
    render(
      <StatusPill size="md" data-testid="pill">
        x
      </StatusPill>
    );
    expect(screen.getByTestId('pill').className).toContain('px-3');
  });
});
