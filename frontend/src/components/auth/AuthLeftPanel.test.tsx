/**
 * AuthLeftPanel Component Tests
 *
 * Tests for the shared left panel on Login/Signup pages,
 * including brand elements, trust gauge, and stats display.
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

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AuthLeftPanel', () => {
  it('renders the component', () => {
    const { container } = render(<AuthLeftPanel />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('renders the Stratum AI logo', () => {
    render(<AuthLeftPanel />);

    const logo = screen.getByAltText('Stratum AI');
    expect(logo).toBeInTheDocument();
    expect(logo).toHaveAttribute('src', '/images/stratum-logo.png');
  });

  it('renders the logo as a link to home page', () => {
    render(<AuthLeftPanel />);

    const logo = screen.getByAltText('Stratum AI');
    expect(logo.closest('a')).toHaveAttribute('href', '/');
  });

  it('displays the trust score of 94.7%', () => {
    render(<AuthLeftPanel />);

    expect(screen.getByText(/94\.7/)).toBeInTheDocument();
    expect(screen.getByText('Trust Score')).toBeInTheDocument();
  });

  it('displays the Revenue Growth stat', () => {
    render(<AuthLeftPanel />);

    expect(screen.getByText('Revenue Growth')).toBeInTheDocument();
    expect(screen.getByText('+124.8%')).toBeInTheDocument();
  });

  it('displays the AI Efficiency stat', () => {
    render(<AuthLeftPanel />);

    expect(screen.getByText('AI Efficiency')).toBeInTheDocument();
    expect(screen.getByText('99.2%')).toBeInTheDocument();
  });

  it('displays the System Monitoring status', () => {
    render(<AuthLeftPanel />);

    expect(screen.getByText('System Monitoring Active')).toBeInTheDocument();
  });

  it('displays the protocol version', () => {
    render(<AuthLeftPanel />);

    expect(
      screen.getByText('Protocol v4.0.26 // Quantum Encrypted Session')
    ).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<AuthLeftPanel className="hidden lg:flex" />);

    expect(container.firstChild).toHaveClass('hidden');
    expect(container.firstChild).toHaveClass('lg:flex');
  });
});
