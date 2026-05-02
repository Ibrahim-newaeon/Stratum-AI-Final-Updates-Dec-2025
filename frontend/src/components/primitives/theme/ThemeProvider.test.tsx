/**
 * ThemeProvider tests — Stratum figma theme system.
 *
 * Contract under test:
 * - Defaults to 'system' when localStorage is empty.
 * - Honors stored 'dark' / 'light' / 'system'.
 * - Resolves 'system' against prefers-color-scheme: dark.
 * - Applies the resolved class to <html>; clears the other.
 * - Persists every theme change to localStorage('stratum-theme').
 * - Subscribes to matchMedia change while in 'system'.
 * - Throws when useTheme is consumed outside the provider.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, renderHook, act } from '@testing-library/react';
import type { ReactNode } from 'react';

const mockStore: Record<string, string> = {};
const mockLocalStorage = {
  getItem: vi.fn((key: string) => mockStore[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    mockStore[key] = value;
  }),
  removeItem: vi.fn((key: string) => {
    delete mockStore[key];
  }),
  clear: vi.fn(() => {
    Object.keys(mockStore).forEach((k) => delete mockStore[k]);
  }),
  get length() {
    return Object.keys(mockStore).length;
  },
  key: vi.fn((index: number) => Object.keys(mockStore)[index] ?? null),
};

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

let mockPrefersDark = false;
const mockAddEventListener = vi.fn();
const mockRemoveEventListener = vi.fn();

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: mockPrefersDark,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: mockAddEventListener,
    removeEventListener: mockRemoveEventListener,
    dispatchEvent: vi.fn(),
  })),
});

import { ThemeProvider, useTheme } from './ThemeProvider';

function resetAll() {
  Object.keys(mockStore).forEach((k) => delete mockStore[k]);
  mockLocalStorage.getItem.mockClear();
  mockLocalStorage.setItem.mockClear();
  mockLocalStorage.removeItem.mockClear();
  mockAddEventListener.mockClear();
  mockRemoveEventListener.mockClear();
  mockPrefersDark = false;
  document.documentElement.classList.remove('light', 'dark');
}

const wrapper = ({ children }: { children: ReactNode }) => (
  <ThemeProvider>{children}</ThemeProvider>
);

describe('ThemeProvider', () => {
  beforeEach(resetAll);

  describe('useTheme outside provider', () => {
    it('throws when called outside ThemeProvider', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
      expect(() => {
        renderHook(() => useTheme());
      }).toThrow('useTheme must be used within a ThemeProvider');
      spy.mockRestore();
    });
  });

  describe('Defaults', () => {
    it('defaults to "system" when localStorage is empty', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.theme).toBe('system');
    });

    it('resolves "system" to "light" when OS prefers light', () => {
      mockPrefersDark = false;
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.resolvedTheme).toBe('light');
    });

    it('resolves "system" to "dark" when OS prefers dark', () => {
      mockPrefersDark = true;
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.resolvedTheme).toBe('dark');
    });

    it('exposes a setTheme function', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(typeof result.current.setTheme).toBe('function');
    });
  });

  describe('localStorage persistence', () => {
    it('reads stored "light" on mount', () => {
      mockStore['stratum-theme'] = 'light';
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.theme).toBe('light');
    });

    it('reads stored "dark" on mount', () => {
      mockStore['stratum-theme'] = 'dark';
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.theme).toBe('dark');
    });

    it('persists every theme change to localStorage', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      act(() => {
        result.current.setTheme('light');
      });
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('stratum-theme', 'light');

      act(() => {
        result.current.setTheme('dark');
      });
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('stratum-theme', 'dark');

      act(() => {
        result.current.setTheme('system');
      });
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('stratum-theme', 'system');
    });

    it('ignores garbage stored values and falls back to system', () => {
      mockStore['stratum-theme'] = 'plaid';
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.theme).toBe('system');
    });
  });

  describe('Theme switching', () => {
    it('switches dark → light and updates resolvedTheme', () => {
      mockStore['stratum-theme'] = 'dark';
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(result.current.resolvedTheme).toBe('dark');

      act(() => {
        result.current.setTheme('light');
      });
      expect(result.current.theme).toBe('light');
      expect(result.current.resolvedTheme).toBe('light');
    });

    it('applies the resolved class to <html> and removes the other', () => {
      mockStore['stratum-theme'] = 'dark';
      const { result } = renderHook(() => useTheme(), { wrapper });
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(document.documentElement.classList.contains('light')).toBe(false);

      act(() => {
        result.current.setTheme('light');
      });
      expect(document.documentElement.classList.contains('light')).toBe(true);
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('System theme listener', () => {
    it('subscribes to matchMedia change while theme is "system"', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });
      act(() => {
        result.current.setTheme('system');
      });
      expect(mockAddEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    });

    it('cleans up the matchMedia listener on unmount', () => {
      const { unmount } = renderHook(() => useTheme(), { wrapper });
      unmount();
      expect(mockRemoveEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    });
  });

  describe('Provider rendering', () => {
    it('renders children', () => {
      render(
        <ThemeProvider>
          <div data-testid="child">Hello</div>
        </ThemeProvider>
      );
      expect(screen.getByTestId('child')).toBeDefined();
    });

    it('exposes context to nested consumers', () => {
      function Consumer() {
        const { theme, resolvedTheme } = useTheme();
        return (
          <>
            <span data-testid="theme">{theme}</span>
            <span data-testid="resolved">{resolvedTheme}</span>
          </>
        );
      }
      mockStore['stratum-theme'] = 'dark';
      render(
        <ThemeProvider>
          <Consumer />
        </ThemeProvider>
      );
      expect(screen.getByTestId('theme').textContent).toBe('dark');
      expect(screen.getByTestId('resolved').textContent).toBe('dark');
    });
  });
});
