/**
 * NotFound (404) Page Tests
 *
 * The 404 page was redesigned as a trust-engine "instrument readout" via the
 * shared ErrorScreen (commit c82640a5). These tests assert the shipped UI:
 * the readout numeral, headline, go-back / back-to-home actions, and the
 * helpful-links nav.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  // The redesigned page reads the requested path from useLocation().
  useLocation: () => ({ pathname: '/does-not-exist' }),
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('@/components/common/SEO', () => ({
  SEO: () => null,
}));

import NotFound from './NotFound';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('NotFound', () => {
  it('renders the 404 readout numeral', () => {
    render(<NotFound />);

    expect(screen.getByText('404')).toBeInTheDocument();
  });

  it('marks the decorative 404 numeral as aria-hidden', () => {
    render(<NotFound />);

    expect(screen.getByText('404')).toHaveAttribute('aria-hidden', 'true');
  });

  it('renders the "No signal at this address" heading', () => {
    render(<NotFound />);

    expect(
      screen.getByRole('heading', { name: /no signal at this address/i })
    ).toBeInTheDocument();
  });

  it('renders a descriptive message', () => {
    render(<NotFound />);

    expect(
      screen.getByText(/the page you're looking for doesn't exist or has been moved/i)
    ).toBeInTheDocument();
  });

  it('surfaces the requested path in the diagnostics', () => {
    render(<NotFound />);

    expect(screen.getByText('/does-not-exist')).toBeInTheDocument();
  });

  it('renders a "Go back" button that calls navigate(-1)', () => {
    render(<NotFound />);

    const goBack = screen.getByRole('button', { name: /go back/i });
    expect(goBack).toBeInTheDocument();

    fireEvent.click(goBack);
    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  it('renders a "Back to home" link pointing to "/"', () => {
    render(<NotFound />);

    const homeLink = screen.getByRole('link', { name: /back to home/i });
    expect(homeLink).toHaveAttribute('href', '/');
  });

  it('renders the helpful-links nav', () => {
    render(<NotFound />);

    expect(screen.getByRole('navigation', { name: /helpful links/i })).toBeInTheDocument();
  });

  it('renders links to Dashboard, Features, Pricing, and Contact', () => {
    render(<NotFound />);

    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute(
      'href',
      '/dashboard'
    );
    expect(screen.getByRole('link', { name: 'Features' })).toHaveAttribute(
      'href',
      '/features'
    );
    expect(screen.getByRole('link', { name: 'Pricing' })).toHaveAttribute('href', '/pricing');
    expect(screen.getByRole('link', { name: 'Contact' })).toHaveAttribute('href', '/contact');
  });
});
