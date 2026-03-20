/**
 * useDocumentDirection Hook Tests
 *
 * Tests for syncing HTML lang and dir attributes with i18n language changes.
 * Mocks react-i18next to control the current language.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mock react-i18next
// ---------------------------------------------------------------------------

let mockLanguage = 'en';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    i18n: {
      get language() {
        return mockLanguage;
      },
    },
  }),
}));

import { useDocumentDirection } from './useDocumentDirection';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useDocumentDirection', () => {
  beforeEach(() => {
    mockLanguage = 'en';
    // Reset document state
    document.documentElement.lang = '';
    document.documentElement.dir = '';
    document.body.classList.remove('ltr', 'rtl');
    document.documentElement.style.removeProperty('--direction');
    document.documentElement.style.removeProperty('--rtl-multiplier');
  });

  afterEach(() => {
    document.body.classList.remove('ltr', 'rtl');
  });

  // -------------------------------------------------------------------------
  // LTR Languages
  // -------------------------------------------------------------------------

  describe('LTR Languages', () => {
    it('should set direction to ltr for English', () => {
      mockLanguage = 'en';
      const { result } = renderHook(() => useDocumentDirection());

      expect(result.current.direction).toBe('ltr');
      expect(result.current.isRTL).toBe(false);
      expect(result.current.language).toBe('en');
    });

    it('should set HTML lang attribute', () => {
      mockLanguage = 'en';
      renderHook(() => useDocumentDirection());

      expect(document.documentElement.lang).toBe('en');
    });

    it('should set HTML dir attribute to ltr', () => {
      mockLanguage = 'en';
      renderHook(() => useDocumentDirection());

      expect(document.documentElement.dir).toBe('ltr');
    });

    it('should add ltr class to body', () => {
      mockLanguage = 'en';
      renderHook(() => useDocumentDirection());

      expect(document.body.classList.contains('ltr')).toBe(true);
      expect(document.body.classList.contains('rtl')).toBe(false);
    });

    it('should set CSS custom properties for LTR', () => {
      mockLanguage = 'en';
      renderHook(() => useDocumentDirection());

      expect(document.documentElement.style.getPropertyValue('--direction')).toBe('ltr');
      expect(document.documentElement.style.getPropertyValue('--rtl-multiplier')).toBe('1');
    });

    it('should handle French as LTR', () => {
      mockLanguage = 'fr';
      const { result } = renderHook(() => useDocumentDirection());

      expect(result.current.direction).toBe('ltr');
      expect(result.current.isRTL).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // RTL Languages
  // -------------------------------------------------------------------------

  describe('RTL Languages', () => {
    it('should set direction to rtl for Arabic', () => {
      mockLanguage = 'ar';
      const { result } = renderHook(() => useDocumentDirection());

      expect(result.current.direction).toBe('rtl');
      expect(result.current.isRTL).toBe(true);
      expect(result.current.language).toBe('ar');
    });

    it('should set HTML dir attribute to rtl for Arabic', () => {
      mockLanguage = 'ar';
      renderHook(() => useDocumentDirection());

      expect(document.documentElement.dir).toBe('rtl');
    });

    it('should add rtl class to body for Arabic', () => {
      mockLanguage = 'ar';
      renderHook(() => useDocumentDirection());

      expect(document.body.classList.contains('rtl')).toBe(true);
      expect(document.body.classList.contains('ltr')).toBe(false);
    });

    it('should set CSS custom properties for RTL', () => {
      mockLanguage = 'ar';
      renderHook(() => useDocumentDirection());

      expect(document.documentElement.style.getPropertyValue('--direction')).toBe('rtl');
      expect(document.documentElement.style.getPropertyValue('--rtl-multiplier')).toBe('-1');
    });

    it('should handle Hebrew as RTL', () => {
      mockLanguage = 'he';
      const { result } = renderHook(() => useDocumentDirection());

      expect(result.current.direction).toBe('rtl');
      expect(result.current.isRTL).toBe(true);
    });

    it('should handle Persian as RTL', () => {
      mockLanguage = 'fa';
      const { result } = renderHook(() => useDocumentDirection());

      expect(result.current.direction).toBe('rtl');
      expect(result.current.isRTL).toBe(true);
    });

    it('should handle Urdu as RTL', () => {
      mockLanguage = 'ur';
      const { result } = renderHook(() => useDocumentDirection());

      expect(result.current.direction).toBe('rtl');
      expect(result.current.isRTL).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // Language switching
  // -------------------------------------------------------------------------

  describe('Language Switching', () => {
    it('should update direction when language changes from LTR to RTL', () => {
      mockLanguage = 'en';
      const { result, rerender } = renderHook(() => useDocumentDirection());

      expect(result.current.direction).toBe('ltr');

      mockLanguage = 'ar';
      rerender();

      expect(result.current.direction).toBe('rtl');
      expect(result.current.isRTL).toBe(true);
      expect(document.documentElement.dir).toBe('rtl');
    });

    it('should remove previous direction class when switching', () => {
      mockLanguage = 'en';
      const { rerender } = renderHook(() => useDocumentDirection());

      expect(document.body.classList.contains('ltr')).toBe(true);

      mockLanguage = 'ar';
      rerender();

      expect(document.body.classList.contains('rtl')).toBe(true);
      expect(document.body.classList.contains('ltr')).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // Cleanup
  // -------------------------------------------------------------------------

  describe('Cleanup', () => {
    it('should remove direction class on unmount', () => {
      mockLanguage = 'ar';
      const { unmount } = renderHook(() => useDocumentDirection());

      expect(document.body.classList.contains('rtl')).toBe(true);

      unmount();

      expect(document.body.classList.contains('rtl')).toBe(false);
    });
  });
});
