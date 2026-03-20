/**
 * useKeyboardShortcuts Hook Tests
 *
 * Tests for the global keyboard shortcuts system.
 * Mocks react-router-dom's useNavigate and the JoyrideWrapper context.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mock dependencies
// ---------------------------------------------------------------------------

const mockNavigate = vi.fn();
const mockStartTour = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('@/components/guide/JoyrideWrapper', () => ({
  useJoyride: () => ({ startTour: mockStartTour }),
}));

import { useKeyboardShortcuts } from './useKeyboardShortcuts';

// ---------------------------------------------------------------------------
// Helper to dispatch keyboard events on window
// ---------------------------------------------------------------------------

function pressKey(
  key: string,
  options: { ctrlKey?: boolean; altKey?: boolean; shiftKey?: boolean; metaKey?: boolean } = {}
) {
  const event = new KeyboardEvent('keydown', {
    key,
    ctrlKey: options.ctrlKey ?? false,
    altKey: options.altKey ?? false,
    shiftKey: options.shiftKey ?? false,
    metaKey: options.metaKey ?? false,
    bubbles: true,
    cancelable: true,
  });
  window.dispatchEvent(event);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useKeyboardShortcuts', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    mockStartTour.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // -------------------------------------------------------------------------
  // Return value
  // -------------------------------------------------------------------------

  describe('Return Value', () => {
    it('should return shortcuts array', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());

      expect(Array.isArray(result.current.shortcuts)).toBe(true);
      expect(result.current.shortcuts.length).toBeGreaterThan(0);
    });

    it('should return showHelp state', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());

      expect(typeof result.current.showHelp).toBe('boolean');
      expect(result.current.showHelp).toBe(false);
    });

    it('should return setShowHelp function', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());

      expect(typeof result.current.setShowHelp).toBe('function');
    });

    it('should have shortcuts with correct structure', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());

      const shortcut = result.current.shortcuts[0];
      expect(shortcut).toHaveProperty('key');
      expect(shortcut).toHaveProperty('description');
      expect(shortcut).toHaveProperty('action');
      expect(shortcut).toHaveProperty('category');
    });

    it('should categorize shortcuts into navigation, actions, and help', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());

      const categories = new Set(result.current.shortcuts.map((s) => s.category));
      expect(categories.has('navigation')).toBe(true);
      expect(categories.has('actions')).toBe(true);
      expect(categories.has('help')).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // Navigation shortcuts
  // -------------------------------------------------------------------------

  describe('Navigation Shortcuts', () => {
    it('should navigate to Overview on "g" key', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('g');
      });

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard/overview');
    });

    it('should navigate to Campaigns on "c" key', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('c');
      });

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard/campaigns');
    });

    it('should navigate to Settings on "s" key', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('s');
      });

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard/settings');
    });

    it('should navigate to EMQ Dashboard on "e" key', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('e');
      });

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard/emq-dashboard');
    });

    it('should navigate to Assets on "a" key', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('a');
      });

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard/assets');
    });

    it('should navigate to Rules on "r" key', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('r');
      });

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard/rules');
    });
  });

  // -------------------------------------------------------------------------
  // Action shortcuts
  // -------------------------------------------------------------------------

  describe('Action Shortcuts', () => {
    it('should focus search input on Ctrl+F', () => {
      // Create a mock search input
      const searchInput = document.createElement('input');
      searchInput.type = 'search';
      document.body.appendChild(searchInput);
      const focusSpy = vi.spyOn(searchInput, 'focus');

      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('f', { ctrlKey: true });
      });

      expect(focusSpy).toHaveBeenCalled();

      focusSpy.mockRestore();
      document.body.removeChild(searchInput);
    });
  });

  // -------------------------------------------------------------------------
  // Help shortcuts
  // -------------------------------------------------------------------------

  describe('Help Shortcuts', () => {
    it('should toggle showHelp on Shift+?', () => {
      const { result } = renderHook(() => useKeyboardShortcuts());

      expect(result.current.showHelp).toBe(false);

      act(() => {
        pressKey('?', { shiftKey: true });
      });

      expect(result.current.showHelp).toBe(true);

      act(() => {
        pressKey('?', { shiftKey: true });
      });

      expect(result.current.showHelp).toBe(false);
    });

    it('should start tour on "t" key', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('t');
      });

      expect(mockStartTour).toHaveBeenCalledTimes(1);
    });
  });

  // -------------------------------------------------------------------------
  // Input suppression
  // -------------------------------------------------------------------------

  describe('Input Suppression', () => {
    it('should not trigger shortcuts when typing in an input field', () => {
      renderHook(() => useKeyboardShortcuts());

      // Create and focus an input element
      const input = document.createElement('input');
      document.body.appendChild(input);
      input.focus();

      // Dispatch event with input as target
      const event = new KeyboardEvent('keydown', {
        key: 'g',
        bubbles: true,
        cancelable: true,
      });

      // Override the target to be an input
      Object.defineProperty(event, 'target', { value: input });

      act(() => {
        window.dispatchEvent(event);
      });

      expect(mockNavigate).not.toHaveBeenCalled();

      document.body.removeChild(input);
    });

    it('should not trigger shortcuts when typing in a textarea', () => {
      renderHook(() => useKeyboardShortcuts());

      const textarea = document.createElement('textarea');
      document.body.appendChild(textarea);
      textarea.focus();

      const event = new KeyboardEvent('keydown', {
        key: 'c',
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(event, 'target', { value: textarea });

      act(() => {
        window.dispatchEvent(event);
      });

      expect(mockNavigate).not.toHaveBeenCalled();

      document.body.removeChild(textarea);
    });

    it('should allow Escape in input fields', () => {
      renderHook(() => useKeyboardShortcuts());

      const input = document.createElement('input');
      document.body.appendChild(input);
      input.focus();

      const dispatchSpy = vi.spyOn(document, 'dispatchEvent');

      const event = new KeyboardEvent('keydown', {
        key: 'Escape',
        bubbles: true,
        cancelable: true,
      });
      Object.defineProperty(event, 'target', { value: input });

      act(() => {
        window.dispatchEvent(event);
      });

      // Escape should still work in inputs
      expect(dispatchSpy).toHaveBeenCalled();

      dispatchSpy.mockRestore();
      document.body.removeChild(input);
    });
  });

  // -------------------------------------------------------------------------
  // Enabled option
  // -------------------------------------------------------------------------

  describe('Enabled Option', () => {
    it('should not register listener when disabled', () => {
      const addEventSpy = vi.spyOn(window, 'addEventListener');

      renderHook(() => useKeyboardShortcuts({ enabled: false }));

      const keydownCalls = addEventSpy.mock.calls.filter(
        (call) => call[0] === 'keydown'
      );

      expect(keydownCalls).toHaveLength(0);

      addEventSpy.mockRestore();
    });

    it('should not trigger navigation when disabled', () => {
      renderHook(() => useKeyboardShortcuts({ enabled: false }));

      act(() => {
        pressKey('g');
      });

      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('should register listener when enabled', () => {
      const addEventSpy = vi.spyOn(window, 'addEventListener');

      renderHook(() => useKeyboardShortcuts({ enabled: true }));

      const keydownCalls = addEventSpy.mock.calls.filter(
        (call) => call[0] === 'keydown'
      );

      expect(keydownCalls.length).toBeGreaterThan(0);

      addEventSpy.mockRestore();
    });
  });

  // -------------------------------------------------------------------------
  // Modifier key matching
  // -------------------------------------------------------------------------

  describe('Modifier Key Matching', () => {
    it('should not trigger plain shortcuts when Ctrl is held', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('g', { ctrlKey: true });
      });

      // 'g' shortcut requires no Ctrl, so it should not match
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('should not trigger plain shortcuts when Alt is held', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('g', { altKey: true });
      });

      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('should not trigger plain shortcuts when Shift is held (unless required)', () => {
      renderHook(() => useKeyboardShortcuts());

      act(() => {
        pressKey('g', { shiftKey: true });
      });

      // 'g' requires no shift
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // Cleanup
  // -------------------------------------------------------------------------

  describe('Cleanup', () => {
    it('should remove event listener on unmount', () => {
      const removeEventSpy = vi.spyOn(window, 'removeEventListener');

      const { unmount } = renderHook(() => useKeyboardShortcuts({ enabled: true }));
      unmount();

      const keydownCalls = removeEventSpy.mock.calls.filter(
        (call) => call[0] === 'keydown'
      );

      expect(keydownCalls.length).toBeGreaterThan(0);

      removeEventSpy.mockRestore();
    });
  });
});
