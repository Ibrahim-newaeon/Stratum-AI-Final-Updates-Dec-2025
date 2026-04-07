/**
 * useDemoMode Hook Tests
 *
 * Tests for the first-time user onboarding demo data hook.
 * Verifies localStorage integration, demo/banner visibility logic,
 * and dismiss behavior.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDemoMode } from './useDemoMode';

// ---------------------------------------------------------------------------
// Mock localStorage
// ---------------------------------------------------------------------------

const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
    _reset: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useDemoMode', () => {
  beforeEach(() => {
    mockLocalStorage._reset();
    mockLocalStorage.getItem.mockClear();
    mockLocalStorage.setItem.mockClear();
  });

  // -------------------------------------------------------------------------
  // Default / first-visit behavior
  // -------------------------------------------------------------------------

  describe('First Visit (localStorage empty)', () => {
    it('should show demo data when localStorage key is absent and no real data', () => {
      const { result } = renderHook(() => useDemoMode());

      expect(result.current.showDemoData).toBe(true);
      expect(result.current.showDemoBanner).toBe(true);
    });

    it('should read the storage key on mount', () => {
      renderHook(() => useDemoMode());

      expect(mockLocalStorage.getItem).toHaveBeenCalledWith(
        'stratum_onboarding_demo_dismissed'
      );
    });

    it('should not show demo data when hasRealData is true', () => {
      const { result } = renderHook(() => useDemoMode(true));

      expect(result.current.showDemoData).toBe(false);
      expect(result.current.showDemoBanner).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // Dismissed state
  // -------------------------------------------------------------------------

  describe('Already Dismissed', () => {
    beforeEach(() => {
      mockLocalStorage._reset();
      mockLocalStorage.setItem('stratum_onboarding_demo_dismissed', 'true');
    });

    it('should not show demo data when already dismissed', () => {
      const { result } = renderHook(() => useDemoMode());

      expect(result.current.showDemoData).toBe(false);
      expect(result.current.showDemoBanner).toBe(false);
    });

    it('should not show demo data even when hasRealData is false', () => {
      const { result } = renderHook(() => useDemoMode(false));

      expect(result.current.showDemoData).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // Dismiss action
  // -------------------------------------------------------------------------

  describe('dismissDemo', () => {
    it('should hide demo data after dismissing', () => {
      const { result } = renderHook(() => useDemoMode());

      expect(result.current.showDemoData).toBe(true);

      act(() => {
        result.current.dismissDemo();
      });

      expect(result.current.showDemoData).toBe(false);
      expect(result.current.showDemoBanner).toBe(false);
    });

    it('should persist dismissal to localStorage', () => {
      const { result } = renderHook(() => useDemoMode());

      act(() => {
        result.current.dismissDemo();
      });

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        'stratum_onboarding_demo_dismissed',
        'true'
      );
    });

    it('should remain dismissed across re-renders', () => {
      const { result, rerender } = renderHook(() => useDemoMode());

      act(() => {
        result.current.dismissDemo();
      });

      rerender();

      expect(result.current.showDemoData).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // hasRealData parameter
  // -------------------------------------------------------------------------

  describe('hasRealData parameter', () => {
    it('should default hasRealData to false', () => {
      const { result } = renderHook(() => useDemoMode());
      expect(result.current.showDemoData).toBe(true);
    });

    it('should hide demo when real data exists even if not dismissed', () => {
      const { result } = renderHook(() => useDemoMode(true));
      expect(result.current.showDemoData).toBe(false);
      expect(result.current.showDemoBanner).toBe(false);
    });

    it('should react to hasRealData changing from false to true', () => {
      let hasRealData = false;
      const { result, rerender } = renderHook(() => useDemoMode(hasRealData));

      expect(result.current.showDemoData).toBe(true);

      hasRealData = true;
      rerender();

      expect(result.current.showDemoData).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // showDemoBanner parity
  // -------------------------------------------------------------------------

  describe('showDemoBanner', () => {
    it('should match showDemoData value', () => {
      const { result } = renderHook(() => useDemoMode());
      expect(result.current.showDemoBanner).toBe(result.current.showDemoData);
    });

    it('should be false when dismissed', () => {
      const { result } = renderHook(() => useDemoMode());

      act(() => {
        result.current.dismissDemo();
      });

      expect(result.current.showDemoBanner).toBe(false);
    });
  });
});
