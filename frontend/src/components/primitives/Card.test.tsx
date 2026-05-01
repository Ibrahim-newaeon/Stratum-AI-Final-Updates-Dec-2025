import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Card } from './Card';

describe('Card', () => {
  it('renders children', () => {
    render(<Card data-testid="card">hello</Card>);
    expect(screen.getByTestId('card')).toHaveTextContent('hello');
  });

  it('applies the default variant background', () => {
    render(<Card data-testid="card" />);
    expect(screen.getByTestId('card')).toHaveClass('bg-card');
  });

  it('applies the elevated variant background', () => {
    render(<Card variant="elevated" data-testid="card" />);
    expect(screen.getByTestId('card')).toHaveClass('bg-surface-tier2');
  });

  it('renders the ember glow layer for variant="glow"', () => {
    const { container } = render(<Card variant="glow" data-testid="card" />);
    // Glow is a sibling div with aria-hidden inside the card.
    const glow = container.querySelector('[aria-hidden="true"]');
    expect(glow).not.toBeNull();
  });

  it('does not render glow layer for default variant', () => {
    const { container } = render(<Card data-testid="card" />);
    const glow = container.querySelector('[aria-hidden="true"]');
    expect(glow).toBeNull();
  });

  it('adds hover-border class when interactive', () => {
    render(<Card interactive data-testid="card" />);
    expect(screen.getByTestId('card').className).toContain('hover:border-primary/30');
  });

  it('forwards arbitrary classes', () => {
    render(<Card className="custom-thing" data-testid="card" />);
    expect(screen.getByTestId('card')).toHaveClass('custom-thing');
  });

  it('exposes Header / Title / Description / Body / Footer subcomponents', () => {
    render(
      <Card>
        <Card.Header>
          <Card.Title>Title text</Card.Title>
          <Card.Description>Desc text</Card.Description>
        </Card.Header>
        <Card.Body>Body text</Card.Body>
        <Card.Footer>Footer text</Card.Footer>
      </Card>
    );
    expect(screen.getByText('Title text').tagName).toBe('H3');
    expect(screen.getByText('Desc text')).toBeInTheDocument();
    expect(screen.getByText('Body text')).toBeInTheDocument();
    expect(screen.getByText('Footer text')).toBeInTheDocument();
  });
});
