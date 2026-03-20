/**
 * Stratum AI - ThemeContext Tests
 *
 * Tests for theme provider rendering, useTheme hook,
 * theme switching, localStorage persistence, system theme
 * resolution, and default values.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, renderHook, act } from '@testing-library/react';
import { ThemeProvider, useTheme } from './ThemeContext';
import type { ReactNode } from 'react';

// =============================================================================
// Mock localStorage
// =============================================================================

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

// =============================================================================
// Mock matchMedia
// =============================================================================

let mockMatchMediaMatches = false;
const mockAddEventListener = vi.fn();
const mockRemoveEventListener = vi.fn();

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: mockMatchMediaMatches,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: mockAddEventListener,
    removeEventListener: mockRemoveEventListener,
    dispatchEvent: vi.fn(),
  })),
});

// =============================================================================
// Helper
// =============================================================================

function resetAll() {
  Object.keys(mockStore).forEach((k) => delete mockStore[k]);
  mockLocalStorage.getItem.mockClear();
  mockLocalStorage.setItem.mockClear();
  mockLocalStorage.removeItem.mockClear();
  mockAddEventListener.mockClear();
  mockRemoveEventListener.mockClear();
  mockMatchMediaMatches = false;
  // Clean up document class list
  document.documentElement.classList.remove('light', 'dark');
}

const wrapper = ({ children }: { children: ReactNode }) => (
  <ThemeProvider>{children}</ThemeProvider>
);

// =============================================================================
// Tests
// =============================================================================

describe('ThemeContext', () => {
  beforeEach(resetAll);

  // ---------------------------------------------------------------------------
  // useTheme outside provider
  // ---------------------------------------------------------------------------

  describe('useTheme outside provider', () => {
    it('throws an error when used outside ThemeProvider', () => {
      const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useTheme());
      }).toThrow('useTheme must be used within a ThemeProvider');

      spy.mockRestore();
    });
  });

  // ---------------------------------------------------------------------------
  // Default values
  // ---------------------------------------------------------------------------

  describe('Default values', () => {
    it('defaults to "dark" theme when localStorage is empty', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme).toBe('dark');
    });

    it('defaults resolvedTheme to "dark"', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.resolvedTheme).toBe('dark');
    });

    it('provides a setTheme function', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(typeof result.current.setTheme).toBe('function');
    });
  });

  // ---------------------------------------------------------------------------
  // localStorage persistence
  // ---------------------------------------------------------------------------

  describe('localStorage persistence', () => {
    it('reads theme from localStorage on mount', () => {
      mockStore['stratum-theme'] = 'light';

      const { result } = renderHook(() => useTheme(), { wrapper });

      expect(result.current.theme).toBe('light');
    });

    it('saves theme to localStorage when theme changes', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme('light');
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('stratum-theme', 'light');
    });

    it('persists "system" to localStorage when system theme is selected', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme('system');
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith('stratum-theme', 'system');
    });
  });

  // ---------------------------------------------------------------------------
  // Theme switching
  // ---------------------------------------------------------------------------

  describe('Theme switching', () => {
    it('switches from dark to light', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme('light');
      });

      expect(result.current.theme).toBe('light');
      expect(result.current.resolvedTheme).toBe('light');
    });

    it('switches from light to dark', () => {
      mockStore['stratum-theme'] = 'light';

      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme('dark');
      });

      expect(result.current.theme).toBe('dark');
      expect(result.current.resolvedTheme).toBe('dark');
    });

    it('applies "dark" class to document element when theme is dark', () => {
      renderHook(() => useTheme(), { wrapper });

      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(document.documentElement.classList.contains('light')).toBe(false);
    });

    it('applies "light" class to document element when theme is light', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme('light');
      });

      expect(document.documentElement.classList.contains('light')).toBe(true);
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  // ---------------------------------------------------------------------------
  // System theme resolution
  // ---------------------------------------------------------------------------

  describe('System theme resolution', () => {
    it('resolves to "dark" when system prefers dark', () => {
      mockMatchMediaMatches = true;

      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme('system');
      });

      expect(result.current.theme).toBe('system');
      expect(result.current.resolvedTheme).toBe('dark');
    });

    it('resolves to "light" when system prefers light', () => {
      mockMatchMediaMatches = false;

      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme('system');
      });

      expect(result.current.theme).toBe('system');
      expect(result.current.resolvedTheme).toBe('light');
    });

    it('adds a media query listener when theme is set to system', () => {
      const { result } = renderHook(() => useTheme(), { wrapper });

      act(() => {
        result.current.setTheme('system');
      });

      expect(mockAddEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    });

    it('removes media query listener on cleanup', () => {
      const { unmount } = renderHook(() => useTheme(), { wrapper });

      unmount();

      expect(mockRemoveEventListener).toHaveBeenCalledWith('change', expect.any(Function));
    });
  });

  // ---------------------------------------------------------------------------
  // Provider rendering
  // ---------------------------------------------------------------------------

  describe('Provider rendering', () => {
    it('renders children correctly', () => {
      render(
        <ThemeProvider>
          <div data-testid="child">Hello</div>
        </ThemeProvider>
      );

      expect(screen.getByTestId('child')).toBeDefined();
      expect(screen.getByText('Hello')).toBeDefined();
    });

    it('provides context value to nested components', () => {
      function ThemeConsumer() {
        const { theme, resolvedTheme } = useTheme();
        return (
          <div>
            <span data-testid="theme">{theme}</span>
            <span data-testid="resolved">{resolvedTheme}</span>
          </div>
        );
      }

      render(
        <ThemeProvider>
          <ThemeConsumer />
        </ThemeProvider>
      );

      expect(screen.getByTestId('theme').textContent).toBe('dark');
      expect(screen.getByTestId('resolved').textContent).toBe('dark');
    });
  });
});
