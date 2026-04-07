/**
 * Badge Component Tests
 *
 * Tests for the Badge UI component with its variant styles,
 * custom classNames, and children rendering.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from './badge';

describe('Badge', () => {
  it('renders children text', () => {
    render(<Badge>Active</Badge>);

    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('renders with default variant styles', () => {
    render(<Badge>Default</Badge>);

    const badge = screen.getByText('Default');
    expect(badge).toHaveClass('bg-primary');
    expect(badge).toHaveClass('text-primary-foreground');
  });

  it('renders with secondary variant', () => {
    render(<Badge variant="secondary">Secondary</Badge>);

    const badge = screen.getByText('Secondary');
    expect(badge).toHaveClass('bg-secondary');
    expect(badge).toHaveClass('text-secondary-foreground');
  });

  it('renders with destructive variant', () => {
    render(<Badge variant="destructive">Error</Badge>);

    const badge = screen.getByText('Error');
    expect(badge).toHaveClass('bg-destructive');
    expect(badge).toHaveClass('text-destructive-foreground');
  });

  it('renders with outline variant', () => {
    render(<Badge variant="outline">Outline</Badge>);

    const badge = screen.getByText('Outline');
    expect(badge).toHaveClass('text-foreground');
    // Should NOT have bg-primary
    expect(badge).not.toHaveClass('bg-primary');
  });

  it('applies custom className alongside variant classes', () => {
    render(<Badge className="custom-class">Custom</Badge>);

    const badge = screen.getByText('Custom');
    expect(badge).toHaveClass('custom-class');
    // Also retains default variant classes
    expect(badge).toHaveClass('bg-primary');
  });

  it('renders as a div element', () => {
    render(<Badge data-testid="badge-element">Test</Badge>);

    const badge = screen.getByTestId('badge-element');
    expect(badge.tagName).toBe('DIV');
  });

  it('includes shared base classes', () => {
    render(<Badge>Base</Badge>);

    const badge = screen.getByText('Base');
    expect(badge).toHaveClass('inline-flex');
    expect(badge).toHaveClass('items-center');
    expect(badge).toHaveClass('rounded-md');
    expect(badge).toHaveClass('text-xs');
    expect(badge).toHaveClass('font-semibold');
  });

  it('passes through HTML attributes', () => {
    render(
      <Badge data-testid="my-badge" id="badge-1">
        Props
      </Badge>
    );

    const badge = screen.getByTestId('my-badge');
    expect(badge).toHaveAttribute('id', 'badge-1');
  });
});
