import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatRow } from './StatRow';

describe('StatRow', () => {
  const items = [
    { label: 'Spend 24h', value: '$12,480' },
    { label: 'ROAS', value: '3.42×' },
  ];

  it('renders every label and value', () => {
    render(<StatRow items={items} />);
    expect(screen.getByText('Spend 24h')).toBeInTheDocument();
    expect(screen.getByText('$12,480')).toBeInTheDocument();
    expect(screen.getByText('ROAS')).toBeInTheDocument();
    expect(screen.getByText('3.42×')).toBeInTheDocument();
  });

  it('renders figures in the mono face with tabular numerals', () => {
    const { container } = render(<StatRow items={items} />);
    const figure = container.querySelector('[data-slot="stat-value"]');
    expect(figure?.className).toContain('font-mono');
    expect(figure?.className).toContain('tabular-nums');
  });

  it('renders nothing when given no items', () => {
    const { container } = render(<StatRow items={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
