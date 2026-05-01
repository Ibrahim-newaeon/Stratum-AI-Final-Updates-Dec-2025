import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// localStorage + matchMedia mocks for ThemeToggle (which reads ThemeProvider).
const mockStore: Record<string, string> = {};
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: (k: string) => mockStore[k] ?? null,
    setItem: (k: string, v: string) => {
      mockStore[k] = v;
    },
    removeItem: (k: string) => {
      delete mockStore[k];
    },
    clear: () => {
      Object.keys(mockStore).forEach((k) => delete mockStore[k]);
    },
    length: 0,
    key: () => null,
  },
});
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

import { Topbar } from './Topbar';
import { ThemeProvider } from '../theme/ThemeProvider';

function renderTopbar(props: Parameters<typeof Topbar>[0] = {}) {
  return render(
    <ThemeProvider>
      <Topbar {...props} />
    </ThemeProvider>
  );
}

describe('Topbar', () => {
  it('renders the search input with default placeholder', () => {
    renderTopbar();
    const input = screen.getByLabelText('Search');
    expect(input).toBeInTheDocument();
    expect(input.getAttribute('placeholder')).toMatch(/Search campaigns/);
  });

  it('renders a custom search placeholder', () => {
    renderTopbar({ searchPlaceholder: 'Find anything…' });
    const input = screen.getByLabelText('Search');
    expect(input.getAttribute('placeholder')).toBe('Find anything…');
  });

  it('fires onSearchChange on every keystroke', () => {
    const handler = vi.fn();
    renderTopbar({ onSearchChange: handler });
    const input = screen.getByLabelText('Search') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'autopilot' } });
    expect(handler).toHaveBeenCalledWith('autopilot');
  });

  it('fires onSearch when the form is submitted', () => {
    const handler = vi.fn();
    renderTopbar({ onSearch: handler });
    const input = screen.getByLabelText('Search') as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'roas' } });
    fireEvent.submit(input.closest('form')!);
    expect(handler).toHaveBeenCalledWith('roas');
  });

  it('clears value on Escape', () => {
    const onSearch = vi.fn();
    const onSearchChange = vi.fn();
    renderTopbar({ defaultSearch: 'active', onSearch, onSearchChange });
    const input = screen.getByLabelText('Search') as HTMLInputElement;
    expect(input.value).toBe('active');
    fireEvent.keyDown(input, { key: 'Escape' });
    expect(input.value).toBe('');
    expect(onSearchChange).toHaveBeenCalledWith('');
    expect(onSearch).toHaveBeenCalledWith('');
  });

  it('renders the theme toggle by default', () => {
    renderTopbar();
    expect(screen.getByRole('radiogroup', { name: 'Theme' })).toBeInTheDocument();
  });

  it('hides the theme toggle when hideThemeToggle=true', () => {
    renderTopbar({ hideThemeToggle: true });
    expect(screen.queryByRole('radiogroup', { name: 'Theme' })).not.toBeInTheDocument();
  });

  it('renders left and right slots', () => {
    renderTopbar({
      leftSlot: <span data-testid="left">L</span>,
      rightSlot: <span data-testid="right">R</span>,
    });
    expect(screen.getByTestId('left')).toBeInTheDocument();
    expect(screen.getByTestId('right')).toBeInTheDocument();
  });
});
