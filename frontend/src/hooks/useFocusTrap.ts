/**
 * useFocusTrap Hook
 * Traps focus within a container element for accessibility (modals, dialogs)
 */

import { useEffect, useRef, useCallback } from 'react';

const FOCUSABLE_SELECTORS = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

interface UseFocusTrapOptions {
  /** Whether the trap is active */
  enabled?: boolean;
  /** Return focus to trigger element on close */
  returnFocus?: boolean;
  /** Auto-focus first focusable element */
  autoFocus?: boolean;
}

export function useFocusTrap<T extends HTMLElement = HTMLDivElement>(
  options: UseFocusTrapOptions = {}
) {
  const { enabled = true, returnFocus = true, autoFocus = true } = options;
  const containerRef = useRef<T>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  const getFocusableElements = useCallback((): HTMLElement[] => {
    if (!containerRef.current) return [];
    const elements = containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS);
    return Array.from(elements).filter(
      (el) => el.offsetParent !== null // Filter out hidden elements
    );
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled || event.key !== 'Tab') return;

      const focusableElements = getFocusableElements();
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const activeElement = document.activeElement as HTMLElement;

      // Shift + Tab
      if (event.shiftKey) {
        if (activeElement === firstElement || !containerRef.current?.contains(activeElement)) {
          event.preventDefault();
          lastElement.focus();
        }
      }
      // Tab
      else {
        if (activeElement === lastElement || !containerRef.current?.contains(activeElement)) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    },
    [enabled, getFocusableElements]
  );

  // Store previous active element and set up trap
  useEffect(() => {
    if (!enabled) return;

    // Store current active element
    previousActiveElement.current = document.activeElement as HTMLElement;

    // Auto-focus first element
    if (autoFocus) {
      const focusableElements = getFocusableElements();
      if (focusableElements.length > 0) {
        // Small delay to ensure DOM is ready
        requestAnimationFrame(() => {
          focusableElements[0].focus();
        });
      }
    }

    // Add event listener
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);

      // Return focus to previous element
      if (returnFocus && previousActiveElement.current) {
        previousActiveElement.current.focus();
      }
    };
  }, [enabled, autoFocus, returnFocus, handleKeyDown, getFocusableElements]);

  return containerRef;
}

/**
 * Focus the first focusable element in a container
 */
export function focusFirstElement(container: HTMLElement | null): void {
  if (!container) return;
  const focusable = container.querySelector<HTMLElement>(FOCUSABLE_SELECTORS);
  focusable?.focus();
}

/**
 * Check if an element is focusable
 */
export function isFocusable(element: HTMLElement): boolean {
  return element.matches(FOCUSABLE_SELECTORS) && element.offsetParent !== null;
}

export default useFocusTrap;
