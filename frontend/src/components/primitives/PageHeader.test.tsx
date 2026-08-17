import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PageHeader } from './PageHeader';

describe('PageHeader', () => {
  it('renders the title as a level-1 heading', () => {
    render(<PageHeader title="Campaigns" />);
    expect(screen.getByRole('heading', { level: 1, name: 'Campaigns' })).toBeInTheDocument();
  });

  it('renders the context line when given', () => {
    render(<PageHeader title="Campaigns" context="6 active · 2 held" />);
    expect(screen.getByText('6 active · 2 held')).toBeInTheDocument();
  });

  it('omits the context line entirely when not given', () => {
    const { container } = render(<PageHeader title="Campaigns" />);
    expect(container.querySelector('[data-slot="context"]')).toBeNull();
  });

  it('renders actions', () => {
    render(<PageHeader title="Campaigns" actions={<button>New campaign</button>} />);
    expect(screen.getByRole('button', { name: 'New campaign' })).toBeInTheDocument();
  });
});
