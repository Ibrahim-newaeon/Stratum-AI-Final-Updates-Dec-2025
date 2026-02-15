/**
 * useIdleTimeout - Auto-logout after user inactivity
 *
 * BUG-014: Sessions persist indefinitely without any idle timeout.
 * This hook monitors user activity (mouse, keyboard, scroll, touch)
 * and triggers a callback after a configurable period of inactivity.
 *
 * Default: 30 minutes idle timeout, with a 60-second warning before logout.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

/** Events that count as user activity */
const ACTIVITY_EVENTS: (keyof DocumentEventMap)[] = [
  'mousedown',
  'mousemove',
  'keydown',
  'scroll',
  'touchstart',
  'click',
];

interface UseIdleTimeoutOptions {
  /** Idle timeout in milliseconds (default: 30 minutes) */
  timeout?: number;
  /** Warning period before logout in milliseconds (default: 60 seconds) */
  warningDuration?: number;
  /** Called when timeout expires and user should be logged out */
  onTimeout: () => void;
  /** Whether the hook is active (e.g. only when authenticated) */
  enabled?: boolean;
}

interface UseIdleTimeoutReturn {
  /** Whether the warning is currently showing */
  isWarning: boolean;
  /** Seconds remaining before auto-logout (only valid when isWarning is true) */
  secondsLeft: number;
  /** Manually reset the idle timer (e.g. user clicks "Stay logged in") */
  resetTimer: () => void;
}

const THIRTY_MINUTES = 30 * 60 * 1000;
const ONE_MINUTE = 60 * 1000;

export function useIdleTimeout({
  timeout = THIRTY_MINUTES,
  warningDuration = ONE_MINUTE,
  onTimeout,
  enabled = true,
}: UseIdleTimeoutOptions): UseIdleTimeoutReturn {
  const [isWarning, setIsWarning] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(0);

  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const warningIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onTimeoutRef = useRef(onTimeout);
  onTimeoutRef.current = onTimeout;

  const clearAllTimers = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (warningIntervalRef.current) {
      clearInterval(warningIntervalRef.current);
      warningIntervalRef.current = null;
    }
  }, []);

  const startWarningCountdown = useCallback(() => {
    setIsWarning(true);
    const warningSec = Math.ceil(warningDuration / 1000);
    setSecondsLeft(warningSec);

    let remaining = warningSec;
    warningIntervalRef.current = setInterval(() => {
      remaining -= 1;
      setSecondsLeft(remaining);
      if (remaining <= 0) {
        clearAllTimers();
        setIsWarning(false);
        onTimeoutRef.current();
      }
    }, 1000);
  }, [warningDuration, clearAllTimers]);

  const resetTimer = useCallback(() => {
    clearAllTimers();
    setIsWarning(false);
    setSecondsLeft(0);

    if (!enabled) return;

    // Set main timeout (fires warning before full logout)
    const mainTimeout = timeout - warningDuration;
    timeoutRef.current = setTimeout(() => {
      startWarningCountdown();
    }, Math.max(mainTimeout, 0));
  }, [enabled, timeout, warningDuration, clearAllTimers, startWarningCountdown]);

  // Attach activity listeners
  useEffect(() => {
    if (!enabled) {
      clearAllTimers();
      setIsWarning(false);
      return;
    }

    // Start timer initially
    resetTimer();

    const handleActivity = () => {
      // Only reset if NOT already in warning state
      // (user must explicitly click "Stay logged in" during warning)
      if (!isWarning) {
        resetTimer();
      }
    };

    ACTIVITY_EVENTS.forEach((event) => {
      document.addEventListener(event, handleActivity, { passive: true });
    });

    return () => {
      ACTIVITY_EVENTS.forEach((event) => {
        document.removeEventListener(event, handleActivity);
      });
      clearAllTimers();
    };
  }, [enabled, resetTimer, clearAllTimers, isWarning]);

  return { isWarning, secondsLeft, resetTimer };
}
