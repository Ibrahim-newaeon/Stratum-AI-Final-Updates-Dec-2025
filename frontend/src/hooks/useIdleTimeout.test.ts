/**
 * useIdleTimeout Hook Tests
 *
 * Tests for auto-logout after user inactivity.
 * Uses fake timers to control timeout and warning countdown behavior.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useIdleTimeout } from './useIdleTimeout';

describe('useIdleTimeout', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // -------------------------------------------------------------------------
  // Initial state
  // -------------------------------------------------------------------------

  describe('Initial State', () => {
    it('should start with isWarning false', () => {
      const onTimeout = vi.fn();
      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout })
      );

      expect(result.current.isWarning).toBe(false);
    });

    it('should start with secondsLeft at 0', () => {
      const onTimeout = vi.fn();
      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout })
      );

      expect(result.current.secondsLeft).toBe(0);
    });

    it('should expose a resetTimer function', () => {
      const onTimeout = vi.fn();
      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout })
      );

      expect(typeof result.current.resetTimer).toBe('function');
    });
  });

  // -------------------------------------------------------------------------
  // Warning countdown
  // -------------------------------------------------------------------------

  describe('Warning Countdown', () => {
    it('should enter warning state after main timeout elapses', () => {
      const onTimeout = vi.fn();
      const timeout = 10_000; // 10 seconds total
      const warningDuration = 3_000; // 3 second warning

      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout, timeout, warningDuration })
      );

      // Advance past main timeout (10s - 3s = 7s)
      act(() => {
        vi.advanceTimersByTime(7_000);
      });

      expect(result.current.isWarning).toBe(true);
      expect(result.current.secondsLeft).toBe(3);
    });

    it('should count down seconds during warning period', () => {
      const onTimeout = vi.fn();
      const timeout = 5_000;
      const warningDuration = 3_000;

      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout, timeout, warningDuration })
      );

      // Advance to start of warning
      act(() => {
        vi.advanceTimersByTime(2_000);
      });

      expect(result.current.isWarning).toBe(true);
      expect(result.current.secondsLeft).toBe(3);

      // Tick 1 second
      act(() => {
        vi.advanceTimersByTime(1_000);
      });

      expect(result.current.secondsLeft).toBe(2);

      // Tick another second
      act(() => {
        vi.advanceTimersByTime(1_000);
      });

      expect(result.current.secondsLeft).toBe(1);
    });

    it('should call onTimeout when countdown reaches zero', () => {
      const onTimeout = vi.fn();
      const timeout = 5_000;
      const warningDuration = 2_000;

      renderHook(() =>
        useIdleTimeout({ onTimeout, timeout, warningDuration })
      );

      // Advance through entire timeout + warning
      act(() => {
        vi.advanceTimersByTime(3_000); // main timeout
      });

      act(() => {
        vi.advanceTimersByTime(2_000); // warning countdown
      });

      expect(onTimeout).toHaveBeenCalledTimes(1);
    });
  });

  // -------------------------------------------------------------------------
  // Manual reset
  // -------------------------------------------------------------------------

  describe('Manual Reset (resetTimer)', () => {
    it('should cancel warning and reset timer when resetTimer is called', () => {
      const onTimeout = vi.fn();
      const timeout = 5_000;
      const warningDuration = 2_000;

      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout, timeout, warningDuration })
      );

      // Enter warning state
      act(() => {
        vi.advanceTimersByTime(3_000);
      });

      expect(result.current.isWarning).toBe(true);

      // Reset
      act(() => {
        result.current.resetTimer();
      });

      expect(result.current.isWarning).toBe(false);
      expect(result.current.secondsLeft).toBe(0);
    });

    it('should restart the full timeout cycle after reset', () => {
      const onTimeout = vi.fn();
      const timeout = 5_000;
      const warningDuration = 2_000;

      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout, timeout, warningDuration })
      );

      // Enter warning
      act(() => {
        vi.advanceTimersByTime(3_000);
      });

      // Reset
      act(() => {
        result.current.resetTimer();
      });

      // Advance less than main timeout - should not warn yet
      act(() => {
        vi.advanceTimersByTime(2_000);
      });

      expect(result.current.isWarning).toBe(false);
      expect(onTimeout).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Enabled / disabled
  // -------------------------------------------------------------------------

  describe('Enabled Option', () => {
    it('should not trigger timeout when disabled', () => {
      const onTimeout = vi.fn();

      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout, timeout: 1_000, warningDuration: 500, enabled: false })
      );

      act(() => {
        vi.advanceTimersByTime(5_000);
      });

      expect(result.current.isWarning).toBe(false);
      expect(onTimeout).not.toHaveBeenCalled();
    });

    it('should clear timers when enabled changes to false', () => {
      const onTimeout = vi.fn();
      let enabled = true;

      const { result, rerender } = renderHook(() =>
        useIdleTimeout({ onTimeout, timeout: 5_000, warningDuration: 2_000, enabled })
      );

      // Advance partway
      act(() => {
        vi.advanceTimersByTime(2_000);
      });

      // Disable
      enabled = false;
      rerender();

      // Advance past original timeout
      act(() => {
        vi.advanceTimersByTime(10_000);
      });

      expect(result.current.isWarning).toBe(false);
      expect(onTimeout).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Activity events
  // -------------------------------------------------------------------------

  describe('Activity Events', () => {
    it('should reset timer on mouse activity when not in warning state', () => {
      const onTimeout = vi.fn();
      const timeout = 5_000;
      const warningDuration = 2_000;

      renderHook(() =>
        useIdleTimeout({ onTimeout, timeout, warningDuration })
      );

      // Advance halfway
      act(() => {
        vi.advanceTimersByTime(2_000);
      });

      // Simulate activity
      act(() => {
        document.dispatchEvent(new Event('mousemove'));
      });

      // Advance another 2.5 seconds - should not be in warning because timer was reset
      act(() => {
        vi.advanceTimersByTime(2_500);
      });

      expect(onTimeout).not.toHaveBeenCalled();
    });

    it('should not reset timer on activity during warning state', () => {
      const onTimeout = vi.fn();
      const timeout = 5_000;
      const warningDuration = 2_000;

      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout, timeout, warningDuration })
      );

      // Enter warning
      act(() => {
        vi.advanceTimersByTime(3_000);
      });

      expect(result.current.isWarning).toBe(true);

      // Simulate activity - should NOT reset during warning
      act(() => {
        document.dispatchEvent(new Event('mousemove'));
      });

      // Warning should still be active
      expect(result.current.isWarning).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // Cleanup on unmount
  // -------------------------------------------------------------------------

  describe('Cleanup', () => {
    it('should clear timers on unmount', () => {
      const onTimeout = vi.fn();

      const { unmount } = renderHook(() =>
        useIdleTimeout({ onTimeout, timeout: 5_000, warningDuration: 2_000 })
      );

      unmount();

      // Advance past all timers
      act(() => {
        vi.advanceTimersByTime(20_000);
      });

      expect(onTimeout).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Edge cases
  // -------------------------------------------------------------------------

  describe('Edge Cases', () => {
    it('should handle warningDuration >= timeout gracefully', () => {
      const onTimeout = vi.fn();

      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout, timeout: 2_000, warningDuration: 5_000 })
      );

      // mainTimeout = Math.max(2000 - 5000, 0) = 0, so warning starts immediately
      act(() => {
        vi.advanceTimersByTime(0);
      });

      expect(result.current.isWarning).toBe(true);
    });

    it('should use default timeout of 30 minutes', () => {
      const onTimeout = vi.fn();

      const { result } = renderHook(() =>
        useIdleTimeout({ onTimeout })
      );

      // Advance 29 minutes - should not be in warning yet (default warning is 60s)
      act(() => {
        vi.advanceTimersByTime(29 * 60 * 1000 - 60_001);
      });

      expect(result.current.isWarning).toBe(false);
    });
  });
});
