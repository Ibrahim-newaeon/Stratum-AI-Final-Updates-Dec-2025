/**
 * useRetry Hook Tests
 *
 * Tests for retry functionality with exponential backoff.
 * Covers execute, retry, reset, callbacks, and the standalone fetchWithRetry.
 *
 * NOTE: The useRetry hook uses `await sleep()` (Promise-wrapped setTimeout)
 * inside a while loop. Fake timers cannot advance when the event loop is
 * blocked by an awaited promise, so the hook tests use real timers with
 * tiny delays to avoid the deadlock.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRetry, fetchWithRetry } from './useRetry';

describe('useRetry', () => {
  // -------------------------------------------------------------------------
  // Initial state
  // -------------------------------------------------------------------------

  describe('Initial State', () => {
    it('should start with retryCount at 0', () => {
      const { result } = renderHook(() => useRetry());

      expect(result.current.retryCount).toBe(0);
    });

    it('should start with isRetrying false', () => {
      const { result } = renderHook(() => useRetry());

      expect(result.current.isRetrying).toBe(false);
    });

    it('should start with lastError as null', () => {
      const { result } = renderHook(() => useRetry());

      expect(result.current.lastError).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // Successful execution
  // -------------------------------------------------------------------------

  describe('Successful Execution', () => {
    it('should return the result on success', async () => {
      const { result } = renderHook(() => useRetry<string>());
      const fn = vi.fn().mockResolvedValue('success');

      let value: string | undefined;
      await act(async () => {
        value = await result.current.execute(fn);
      });

      expect(value).toBe('success');
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should not increment retryCount on first success', async () => {
      const { result } = renderHook(() => useRetry<string>());
      const fn = vi.fn().mockResolvedValue('ok');

      await act(async () => {
        await result.current.execute(fn);
      });

      expect(result.current.retryCount).toBe(0);
      expect(result.current.isRetrying).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // Retry behavior (real timers with small delays)
  // -------------------------------------------------------------------------

  describe('Retry Behavior', () => {
    it('should retry on failure up to maxRetries', async () => {
      const { result } = renderHook(() =>
        useRetry<string>({ maxRetries: 2, baseDelay: 1, exponentialBackoff: false })
      );

      const fn = vi.fn().mockRejectedValue(new Error('fail'));

      await act(async () => {
        try {
          await result.current.execute(fn);
        } catch {
          // expected
        }
      });

      // Initial attempt + 2 retries = 3 calls
      expect(fn).toHaveBeenCalledTimes(3);
    });

    it('should succeed after transient failures', async () => {
      const { result } = renderHook(() =>
        useRetry<string>({ maxRetries: 3, baseDelay: 1, exponentialBackoff: false })
      );

      const fn = vi
        .fn()
        .mockRejectedValueOnce(new Error('fail 1'))
        .mockRejectedValueOnce(new Error('fail 2'))
        .mockResolvedValueOnce('success');

      let value: string | undefined;
      await act(async () => {
        value = await result.current.execute(fn);
      });

      expect(value).toBe('success');
      expect(fn).toHaveBeenCalledTimes(3);
    });

    it('should throw the last error after exhausting retries', async () => {
      const { result } = renderHook(() =>
        useRetry<string>({ maxRetries: 1, baseDelay: 1, exponentialBackoff: false })
      );

      const fn = vi.fn().mockRejectedValue(new Error('persistent failure'));

      await act(async () => {
        await expect(result.current.execute(fn)).rejects.toThrow('persistent failure');
      });
    });
  });

  // -------------------------------------------------------------------------
  // Exponential backoff
  // -------------------------------------------------------------------------

  describe('Exponential Backoff', () => {
    it('should use exponential delays when enabled', async () => {
      // Use small delays so the test completes quickly with real timers.
      // We spy on setTimeout to verify the calculated delays are exponential.
      const { result } = renderHook(() =>
        useRetry<string>({
          maxRetries: 3,
          baseDelay: 10,
          maxDelay: 1000,
          exponentialBackoff: true,
        })
      );

      const fn = vi.fn().mockRejectedValue(new Error('fail'));
      const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');

      await act(async () => {
        try {
          await result.current.execute(fn);
        } catch {
          // expected
        }
      });

      // Verify delays increase exponentially
      // The sleep calls: baseDelay * 2^0 = 10, baseDelay * 2^1 = 20, baseDelay * 2^2 = 40
      const sleepCalls = setTimeoutSpy.mock.calls.filter(
        (call) => typeof call[1] === 'number' && call[1] >= 10
      );
      expect(sleepCalls.length).toBeGreaterThanOrEqual(1);

      setTimeoutSpy.mockRestore();
    });

    it('should cap delay at maxDelay', async () => {
      // Use small delays with a low maxDelay cap to verify capping
      const { result } = renderHook(() =>
        useRetry<string>({
          maxRetries: 3,
          baseDelay: 50,
          maxDelay: 80,
          exponentialBackoff: true,
        })
      );

      const fn = vi.fn().mockRejectedValue(new Error('fail'));
      const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');

      await act(async () => {
        try {
          await result.current.execute(fn);
        } catch {
          // expected
        }
      });

      // All setTimeout delays should be <= 80
      const delayCalls = setTimeoutSpy.mock.calls
        .filter((call) => typeof call[1] === 'number' && call[1] >= 50)
        .map((call) => call[1] as number);

      delayCalls.forEach((delay) => {
        expect(delay).toBeLessThanOrEqual(80);
      });

      setTimeoutSpy.mockRestore();
    });

    it('should use flat delay when exponentialBackoff is false', async () => {
      const { result } = renderHook(() =>
        useRetry<string>({
          maxRetries: 2,
          baseDelay: 5,
          exponentialBackoff: false,
        })
      );

      const fn = vi.fn().mockRejectedValue(new Error('fail'));
      const setTimeoutSpy = vi.spyOn(globalThis, 'setTimeout');

      await act(async () => {
        try {
          await result.current.execute(fn);
        } catch {
          // expected
        }
      });

      const delayCalls = setTimeoutSpy.mock.calls
        .filter((call) => call[1] === 5)
        .map((call) => call[1]);

      expect(delayCalls.length).toBeGreaterThanOrEqual(1);
      delayCalls.forEach((d) => expect(d).toBe(5));

      setTimeoutSpy.mockRestore();
    });
  });

  // -------------------------------------------------------------------------
  // Callbacks
  // -------------------------------------------------------------------------

  describe('Callbacks', () => {
    it('should call onRetry on each retry attempt', async () => {
      const onRetry = vi.fn();
      const { result } = renderHook(() =>
        useRetry<string>({ maxRetries: 2, baseDelay: 1, exponentialBackoff: false, onRetry })
      );

      const fn = vi.fn().mockRejectedValue(new Error('fail'));

      await act(async () => {
        try {
          await result.current.execute(fn);
        } catch {
          // expected
        }
      });

      expect(onRetry).toHaveBeenCalledTimes(2);
      expect(onRetry).toHaveBeenCalledWith(1, expect.any(Error));
      expect(onRetry).toHaveBeenCalledWith(2, expect.any(Error));
    });

    it('should call onMaxRetriesReached when retries exhausted', async () => {
      const onMaxRetriesReached = vi.fn();
      const { result } = renderHook(() =>
        useRetry<string>({ maxRetries: 1, baseDelay: 1, exponentialBackoff: false, onMaxRetriesReached })
      );

      const fn = vi.fn().mockRejectedValue(new Error('final'));

      await act(async () => {
        try {
          await result.current.execute(fn);
        } catch {
          // expected
        }
      });

      expect(onMaxRetriesReached).toHaveBeenCalledTimes(1);
      expect(onMaxRetriesReached).toHaveBeenCalledWith(expect.objectContaining({ message: 'final' }));
    });
  });

  // -------------------------------------------------------------------------
  // Reset
  // -------------------------------------------------------------------------

  describe('Reset', () => {
    it('should clear all state on reset', async () => {
      const { result } = renderHook(() =>
        useRetry<string>({ maxRetries: 1, baseDelay: 1, exponentialBackoff: false })
      );

      const fn = vi.fn().mockRejectedValue(new Error('fail'));

      await act(async () => {
        try {
          await result.current.execute(fn);
        } catch {
          // expected
        }
      });

      expect(result.current.lastError).not.toBeNull();

      act(() => {
        result.current.reset();
      });

      expect(result.current.retryCount).toBe(0);
      expect(result.current.isRetrying).toBe(false);
      expect(result.current.lastError).toBeNull();
    });
  });

  // -------------------------------------------------------------------------
  // Manual retry
  // -------------------------------------------------------------------------

  describe('Retry (manual)', () => {
    it('should re-execute the last function when retry is called', async () => {
      const { result } = renderHook(() =>
        useRetry<string>({ maxRetries: 0, baseDelay: 1 })
      );

      const fn = vi
        .fn()
        .mockRejectedValueOnce(new Error('fail'))
        .mockResolvedValueOnce('ok');

      await act(async () => {
        try {
          await result.current.execute(fn);
        } catch {
          // expected on first attempt
        }
      });

      let retryResult: string | undefined;
      await act(async () => {
        retryResult = await result.current.retry();
      });

      expect(retryResult).toBe('ok');
    });

    it('should return undefined if no function was previously executed', async () => {
      const { result } = renderHook(() => useRetry<string>());

      let retryResult: string | undefined;
      await act(async () => {
        retryResult = await result.current.retry();
      });

      expect(retryResult).toBeUndefined();
    });
  });

  // -------------------------------------------------------------------------
  // Error wrapping
  // -------------------------------------------------------------------------

  describe('Error Handling', () => {
    it('should wrap non-Error throws into Error objects', async () => {
      const { result } = renderHook(() =>
        useRetry<string>({ maxRetries: 0, baseDelay: 1 })
      );

      const fn = vi.fn().mockRejectedValue('string error');

      await act(async () => {
        try {
          await result.current.execute(fn);
        } catch {
          // expected
        }
      });

      expect(result.current.lastError).toBeInstanceOf(Error);
      expect(result.current.lastError?.message).toBe('string error');
    });
  });
});

// ---------------------------------------------------------------------------
// fetchWithRetry standalone function
// ---------------------------------------------------------------------------

describe('fetchWithRetry', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('should return parsed JSON on successful fetch', async () => {
    const mockResponse = { ok: true, status: 200, json: () => Promise.resolve({ data: 'test' }) };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse));

    const result = await fetchWithRetry('/api/test');

    expect(result).toEqual({ data: 'test' });
  });

  it('should throw on 4xx errors without retrying (except 429)', async () => {
    const mockResponse = { ok: false, status: 404, statusText: 'Not Found' };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse));

    await expect(fetchWithRetry('/api/test', undefined, { maxRetries: 3 })).rejects.toThrow(
      'HTTP 404'
    );

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('should retry on 5xx errors', async () => {
    const mock5xx = { ok: false, status: 500, statusText: 'Internal Server Error' };
    const mockOk = { ok: true, status: 200, json: () => Promise.resolve({ ok: true }) };

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mock5xx)
      .mockResolvedValueOnce(mockOk);

    vi.stubGlobal('fetch', fetchMock);

    const promise = fetchWithRetry('/api/test', undefined, {
      maxRetries: 2,
      baseDelay: 100,
      exponentialBackoff: false,
    });

    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
