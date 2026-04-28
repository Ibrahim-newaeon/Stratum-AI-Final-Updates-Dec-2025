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

  it('renders the stratum.ai wordmark linking home', () => {
    render(<AuthLeftPanel />);
    const wordmark = screen.getAllByText('stratum.ai')[0];
    expect(wordmark).toBeInTheDocument();
    expect(wordmark.closest('a')).toHaveAttribute('href', '/');
  });

  it('renders the testimonial', () => {
    render(<AuthLeftPanel />);
    expect(screen.getByText(/partners with us to grow revenue/)).toBeInTheDocument();
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('CMO, GrowthCo')).toBeInTheDocument();
  });

  it('renders the trust badge', () => {
    render(<AuthLeftPanel />);
    expect(screen.getByText(/Trusted by 500\+ growth teams/i)).toBeInTheDocument();
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
