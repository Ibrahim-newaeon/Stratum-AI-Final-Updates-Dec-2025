/**
 * ThemeProvider — Stratum figma theme system.
 *
 * Contract:
 * - Theme = 'dark' | 'light' | 'system'.
 * - resolvedTheme = 'dark' | 'light' (what's actually applied).
 * - Persists choice to localStorage('stratum-theme').
 * - Defaults to system preference if no stored choice.
 * - Listens for OS dark-mode changes (only acts when theme === 'system').
 *
 * The initial paint already has the correct class set by the inline script
 * in index.html, so this component is responsible only for runtime updates
 * (user toggle + OS preference change while in 'system' mode).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export type Theme = 'dark' | 'light' | 'system';
export type ResolvedTheme = 'dark' | 'light';

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme) => void;
}

const STORAGE_KEY = 'stratum-theme';
const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function readStoredTheme(): Theme {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === 'dark' || raw === 'light' || raw === 'system') return raw;
  } catch {
    // localStorage unavailable (sandboxed iframe, etc.)
  }
  return 'system';
}

function resolve(theme: Theme): ResolvedTheme {
  if (theme === 'system') {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'dark';
  }
  return theme;
}

interface ThemeProviderProps {
  children: ReactNode;
  /** Default theme when nothing is stored. */
  defaultTheme?: Theme;
}

export function ThemeProvider({ children, defaultTheme = 'system' }: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = readStoredTheme();
    return stored ?? defaultTheme;
  });
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() => resolve(theme));

  // Apply class to <html> + persist on theme change.
  useEffect(() => {
    const next = resolve(theme);
    setResolvedTheme(next);

    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(next);

    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // ignore quota / privacy-mode failures
    }
  }, [theme]);

  // React to OS dark-mode changes — only when user has chosen 'system'.
  useEffect(() => {
    if (theme !== 'system') return;
    if (typeof window === 'undefined' || !window.matchMedia) return;

    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      const next: ResolvedTheme = mq.matches ? 'dark' : 'light';
      setResolvedTheme(next);
      const root = document.documentElement;
      root.classList.remove('light', 'dark');
      root.classList.add(next);
    };

    // Both for compatibility — older Safari uses addListener.
    if (mq.addEventListener) {
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    }
    mq.addListener(handler);
    return () => mq.removeListener(handler);
  }, [theme]);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme, setTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return ctx;
}
