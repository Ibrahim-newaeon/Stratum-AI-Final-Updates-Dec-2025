/**
 * useRetry Hook
 * Provides retry functionality for async operations with exponential backoff
 */

import { useCallback, useRef, useState } from 'react';

interface UseRetryOptions {
  /** Maximum number of retry attempts */
  maxRetries?: number;
  /** Base delay in milliseconds */
  baseDelay?: number;
  /** Maximum delay in milliseconds */
  maxDelay?: number;
  /** Whether to use exponential backoff */
  exponentialBackoff?: boolean;
  /** Callback when all retries are exhausted */
  onMaxRetriesReached?: (error: Error) => void;
  /** Callback on each retry attempt */
  onRetry?: (attempt: number, error: Error) => void;
}

interface UseRetryResult<T> {
  /** Execute the async function with retry logic */
  execute: (fn: () => Promise<T>) => Promise<T>;
  /** Current retry count */
  retryCount: number;
  /** Whether currently retrying */
  isRetrying: boolean;
  /** Last error encountered */
  lastError: Error | null;
  /** Reset the retry state */
  reset: () => void;
  /** Manually trigger a retry */
  retry: () => Promise<T | undefined>;
}

export function useRetry<T = unknown>(options: UseRetryOptions = {}): UseRetryResult<T> {
  const {
    maxRetries = 3,
    baseDelay = 1000,
    maxDelay = 10000,
    exponentialBackoff = true,
    onMaxRetriesReached,
    onRetry,
  } = options;

  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const [lastError, setLastError] = useState<Error | null>(null);
  const lastFnRef = useRef<(() => Promise<T>) | null>(null);

  const calculateDelay = useCallback(
    (attempt: number): number => {
      if (!exponentialBackoff) return baseDelay;
      const delay = baseDelay * Math.pow(2, attempt);
      return Math.min(delay, maxDelay);
    },
    [baseDelay, maxDelay, exponentialBackoff]
  );

  const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

  const execute = useCallback(
    async (fn: () => Promise<T>): Promise<T> => {
      lastFnRef.current = fn;
      setRetryCount(0);
      setLastError(null);

      let attempt = 0;

      while (attempt <= maxRetries) {
        try {
          setIsRetrying(attempt > 0);
          const result = await fn();
          setIsRetrying(false);
          return result;
        } catch (error) {
          const err = error instanceof Error ? error : new Error(String(error));
          setLastError(err);

          if (attempt === maxRetries) {
            setIsRetrying(false);
            onMaxRetriesReached?.(err);
            throw err;
          }

          attempt++;
          setRetryCount(attempt);
          onRetry?.(attempt, err);

          const delay = calculateDelay(attempt - 1);
          await sleep(delay);
        }
      }

      // This should never be reached, but TypeScript needs it
      throw lastError || new Error('Max retries reached');
    },
    [maxRetries, calculateDelay, onMaxRetriesReached, onRetry]
  );

  const reset = useCallback(() => {
    setRetryCount(0);
    setIsRetrying(false);
    setLastError(null);
    lastFnRef.current = null;
  }, []);

  const retry = useCallback(async (): Promise<T | undefined> => {
    if (lastFnRef.current) {
      return execute(lastFnRef.current);
    }
    return undefined;
  }, [execute]);

  return {
    execute,
    retryCount,
    isRetrying,
    lastError,
    reset,
    retry,
  };
}

/**
 * Wrapper function for fetch with retry
 */
export async function fetchWithRetry<T>(
  url: string,
  options?: RequestInit,
  retryOptions?: UseRetryOptions
): Promise<T> {
  const {
    maxRetries = 3,
    baseDelay = 1000,
    maxDelay = 10000,
    exponentialBackoff = true,
  } = retryOptions || {};

  let attempt = 0;

  while (attempt <= maxRetries) {
    try {
      const response = await fetch(url, options);

      if (!response.ok) {
        // Don't retry 4xx errors (except 429 rate limit)
        if (response.status >= 400 && response.status < 500 && response.status !== 429) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return response.json();
    } catch (error) {
      if (attempt === maxRetries) {
        throw error;
      }

      attempt++;
      const delay = exponentialBackoff
        ? Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay)
        : baseDelay;

      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw new Error('Max retries reached');
}

export default useRetry;
