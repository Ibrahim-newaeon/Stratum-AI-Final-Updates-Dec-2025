/**
 * NotFound (404) Page Tests
 *
 * Tests for the 404 page rendering, navigation links,
 * and go-back functionality.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>
      {children}
    </a>
  ),
}));

vi.mock('@/components/common/SEO', () => ({
  SEO: () => null,
}));

vi.mock('@heroicons/react/24/outline', () => ({
  ArrowLeftIcon: (props: any) => <svg data-testid="arrow-left-icon" {...props} />,
  HomeIcon: (props: any) => <svg data-testid="home-icon" {...props} />,
}));

import NotFound from './NotFound';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('NotFound', () => {
  it('renders the 404 text', () => {
    render(<NotFound />);

    expect(screen.getByText('404')).toBeInTheDocument();
  });

  it('renders the "Page Not Found" heading', () => {
    render(<NotFound />);

    expect(screen.getByRole('heading', { name: /page not found/i })).toBeInTheDocument();
  });

  it('renders a descriptive message', () => {
    render(<NotFound />);

    expect(
      screen.getByText(/the page you're looking for doesn't exist or has been moved/i)
    ).toBeInTheDocument();
  });

  it('renders a "Go Back" button', () => {
    render(<NotFound />);

    expect(screen.getByText('Go Back')).toBeInTheDocument();
  });

  it('calls navigate(-1) when "Go Back" is clicked', () => {
    render(<NotFound />);

    fireEvent.click(screen.getByText('Go Back'));
    expect(mockNavigate).toHaveBeenCalledWith(-1);
  });

  it('renders a "Back to Home" link pointing to "/"', () => {
    render(<NotFound />);

    const homeLink = screen.getByText('Back to Home');
    expect(homeLink.closest('a')).toHaveAttribute('href', '/');
  });

  it('renders helpful quick links section', () => {
    render(<NotFound />);

    expect(screen.getByText('Looking for something specific?')).toBeInTheDocument();
  });

  it('renders links to Dashboard, Features, Pricing, and Contact', () => {
    render(<NotFound />);

    const dashboardLink = screen.getByText('Dashboard');
    expect(dashboardLink.closest('a')).toHaveAttribute('href', '/dashboard');

    const featuresLink = screen.getByText('Features');
    expect(featuresLink.closest('a')).toHaveAttribute('href', '/features');

    const pricingLink = screen.getByText('Pricing');
    expect(pricingLink.closest('a')).toHaveAttribute('href', '/pricing');

    const contactLink = screen.getByText('Contact');
    expect(contactLink.closest('a')).toHaveAttribute('href', '/contact');
  });

  it('marks 404 text as aria-hidden for accessibility', () => {
    render(<NotFound />);

    const decorative404 = screen.getByText('404');
    expect(decorative404).toHaveAttribute('aria-hidden', 'true');
  });
});
