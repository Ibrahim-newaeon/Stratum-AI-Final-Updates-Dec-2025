/**
 * ThemeToggle tests — segmented sun/moon/system control.
 *
 * Contract under test:
 * - Renders three radio buttons (light, dark, system).
 * - The active option has aria-checked="true".
 * - Clicking an option calls setTheme via the provider context.
 * - Buttons have accessible labels.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// localStorage + matchMedia mocks (shared with ThemeProvider tests)
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

import { ThemeProvider } from './ThemeProvider';
import { ThemeToggle } from './ThemeToggle';

beforeEach(() => {
  Object.keys(mockStore).forEach((k) => delete mockStore[k]);
  document.documentElement.classList.remove('light', 'dark');
});

function renderWithProvider() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>
  );
}

describe('ThemeToggle', () => {
  it('renders three radio buttons (light, dark, system)', () => {
    renderWithProvider();
    expect(screen.getByLabelText('Light theme')).toBeDefined();
    expect(screen.getByLabelText('Dark theme')).toBeDefined();
    expect(screen.getByLabelText('System theme')).toBeDefined();
  });

  it('exposes role=radiogroup with aria-label="Theme"', () => {
    renderWithProvider();
    expect(screen.getByRole('radiogroup', { name: 'Theme' })).toBeDefined();
  });

  it('marks the active theme with aria-checked="true"', () => {
    mockStore['stratum-theme'] = 'dark';
    renderWithProvider();
    const dark = screen.getByLabelText('Dark theme');
    const light = screen.getByLabelText('Light theme');
    expect(dark.getAttribute('aria-checked')).toBe('true');
    expect(light.getAttribute('aria-checked')).toBe('false');
  });

  it('changes theme when an option is clicked', () => {
    mockStore['stratum-theme'] = 'dark';
    renderWithProvider();
    const light = screen.getByLabelText('Light theme');
    fireEvent.click(light);
    expect(light.getAttribute('aria-checked')).toBe('true');
    expect(document.documentElement.classList.contains('light')).toBe(true);
  });
});
