/**
 * AuthLeftPanel Component Tests
 *
 * Tests for the shared left panel on Login/Signup pages —
 * Stratum figma theme (testimonial, ember accent, status marker).
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('react-router-dom', () => ({
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}));

import AuthLeftPanel from './AuthLeftPanel';

describe('AuthLeftPanel', () => {
  it('renders the component', () => {
    const { container } = render(<AuthLeftPanel />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('renders the stratum.ai wordmark linking to the figma landing', () => {
    render(<AuthLeftPanel />);
    const wordmark = screen.getAllByText('stratum.ai')[0];
    expect(wordmark).toBeInTheDocument();
    // Plain <a> (not React Router Link) so the browser does a full page
    // load and lands on the figma marketing page, not the SPA route.
    expect(wordmark.closest('a')).toHaveAttribute('href', '/landing.html');
  });

  it('states what the product does', () => {
    render(<AuthLeftPanel />);
    expect(screen.getByText(/declines to act on data it cannot trust/i)).toBeInTheDocument();
    expect(screen.getByText(/gated on signal health/i)).toBeInTheDocument();
  });

  it('renders the trust badge', () => {
    render(<AuthLeftPanel />);
    expect(screen.getByText(/Trust-gated automation/i)).toBeInTheDocument();
  });

  it('makes no claim about customers, ratings, or endorsements', () => {
    // These tests previously asserted the presence of a fabricated testimonial
    // ("Jane Doe, CMO, GrowthCo") and an unverifiable "500+ growth teams"
    // badge — encoding the fabrication as a requirement. This asserts the
    // opposite, so the placeholder copy cannot quietly return.
    render(<AuthLeftPanel />);
    expect(screen.queryByText(/Jane Doe/i)).toBeNull();
    expect(screen.queryByText(/GrowthCo/i)).toBeNull();
    expect(screen.queryByText(/\d+\+?\s*(growth teams|teams|companies|customers)/i)).toBeNull();
    expect(screen.queryByText(/\d(\.\d)?\s*\/\s*5/)).toBeNull();
  });

  it('renders the trust engine status marker', () => {
    render(<AuthLeftPanel />);
    expect(screen.getByText(/Trust engine — operational/i)).toBeInTheDocument();
  });

  it('hides on mobile and shows on lg breakpoint', () => {
    const { container } = render(<AuthLeftPanel />);
    expect(container.firstChild).toHaveClass('hidden');
    expect(container.firstChild).toHaveClass('lg:flex');
  });
});
