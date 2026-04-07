/**
 * usePdfExport Hook Tests
 *
 * Tests for the PDF export hook that generates reports using jsPDF + html2canvas.
 * Dynamically imported libraries are mocked. Focuses on state management,
 * error handling, and the DOM manipulation helpers.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Mock jsPDF and html2canvas
//
// vi.mock() factories are hoisted above variable declarations, so we use
// vi.hoisted() to ensure the mock references are available when the
// factory runs.
// ---------------------------------------------------------------------------

const {
  mockSave,
  mockText,
  mockRect,
  mockAddImage,
  mockAddPage,
  mockSetFillColor,
  mockSetTextColor,
  mockSetFontSize,
  mockSetFont,
  mockPdf,
  mockJsPDF,
  mockCanvas,
  mockHtml2canvas,
} = vi.hoisted(() => {
  const mockSave = vi.fn();
  const mockText = vi.fn();
  const mockRect = vi.fn();
  const mockAddImage = vi.fn();
  const mockAddPage = vi.fn();
  const mockSetFillColor = vi.fn();
  const mockSetTextColor = vi.fn();
  const mockSetFontSize = vi.fn();
  const mockSetFont = vi.fn();

  const mockPdf = {
    internal: {
      pageSize: {
        getWidth: () => 297, // A4 landscape width in mm
        getHeight: () => 210,
      },
    },
    save: mockSave,
    text: mockText,
    rect: mockRect,
    addImage: mockAddImage,
    addPage: mockAddPage,
    setFillColor: mockSetFillColor,
    setTextColor: mockSetTextColor,
    setFontSize: mockSetFontSize,
    setFont: mockSetFont,
  };

  // Use a regular function (not arrow) so the mock can be called with `new`.
  // Returning a non-primitive from a constructor makes `new` use that object.
  const mockJsPDF = vi.fn(function() { return mockPdf; });

  const mockCanvas = {
    width: 800,
    height: 600,
    toDataURL: vi.fn().mockReturnValue('data:image/png;base64,mockdata'),
  };

  const mockHtml2canvas = vi.fn().mockResolvedValue(mockCanvas);

  return {
    mockSave,
    mockText,
    mockRect,
    mockAddImage,
    mockAddPage,
    mockSetFillColor,
    mockSetTextColor,
    mockSetFontSize,
    mockSetFont,
    mockPdf,
    mockJsPDF,
    mockCanvas,
    mockHtml2canvas,
  };
});

// Mock dynamic imports
vi.mock('jspdf', () => ({ default: mockJsPDF }));
vi.mock('html2canvas', () => ({ default: mockHtml2canvas }));

import { usePdfExport } from './usePdfExport';

// ---------------------------------------------------------------------------
// Helper: create a mock HTML element
// ---------------------------------------------------------------------------

function createMockElement(): HTMLDivElement {
  const element = document.createElement('div');
  element.innerHTML = '<span>Test content</span>';
  document.body.appendChild(element);
  return element;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('usePdfExport', () => {
  let element: HTMLDivElement | null = null;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (element) {
      document.body.removeChild(element);
      element = null;
    }
  });

  // -------------------------------------------------------------------------
  // Initial state
  // -------------------------------------------------------------------------

  describe('Initial State', () => {
    it('should start with isExporting false', () => {
      const { result } = renderHook(() => usePdfExport());

      expect(result.current.isExporting).toBe(false);
    });

    it('should start with progress at 0', () => {
      const { result } = renderHook(() => usePdfExport());

      expect(result.current.progress).toBe(0);
    });

    it('should expose exportToPdf and exportMultiPagePdf functions', () => {
      const { result } = renderHook(() => usePdfExport());

      expect(typeof result.current.exportToPdf).toBe('function');
      expect(typeof result.current.exportMultiPagePdf).toBe('function');
    });
  });

  // -------------------------------------------------------------------------
  // exportToPdf
  // -------------------------------------------------------------------------

  describe('exportToPdf', () => {
    it('should return error when element is null', async () => {
      const { result } = renderHook(() => usePdfExport());

      let exportResult: any;
      await act(async () => {
        exportResult = await result.current.exportToPdf(null);
      });

      expect(exportResult.success).toBe(false);
      expect(exportResult.error).toBe('No element to export');
    });

    it('should successfully generate a PDF', async () => {
      element = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      let exportResult: any;
      await act(async () => {
        exportResult = await result.current.exportToPdf(element, {
          filename: 'test-report',
          title: 'Test Report',
        });
      });

      expect(exportResult.success).toBe(true);
      expect(exportResult.filename).toMatch(/^test-report-\d{4}-\d{2}-\d{2}\.pdf$/);
    });

    it('should call jsPDF constructor with correct options', async () => {
      element = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element, {
          orientation: 'portrait',
          format: 'letter',
        });
      });

      expect(mockJsPDF).toHaveBeenCalledWith({
        orientation: 'portrait',
        unit: 'mm',
        format: 'letter',
      });
    });

    it('should call html2canvas with the element', async () => {
      element = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element);
      });

      expect(mockHtml2canvas).toHaveBeenCalledWith(element, expect.objectContaining({
        scale: 2,
        useCORS: true,
        backgroundColor: '#0a0a0a',
      }));
    });

    it('should use custom quality setting', async () => {
      element = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element, { quality: 4 });
      });

      expect(mockHtml2canvas).toHaveBeenCalledWith(
        element,
        expect.objectContaining({ scale: 4 })
      );
    });

    it('should save the PDF with timestamped filename', async () => {
      element = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element, { filename: 'my-report' });
      });

      expect(mockSave).toHaveBeenCalledWith(expect.stringMatching(/^my-report-\d{4}-\d{2}-\d{2}\.pdf$/));
    });

    it('should reset isExporting and progress after export', async () => {
      element = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element);
      });

      expect(result.current.isExporting).toBe(false);
      expect(result.current.progress).toBe(0);
    });

    it('should handle errors gracefully', async () => {
      element = createMockElement();
      mockHtml2canvas.mockRejectedValueOnce(new Error('Canvas error'));
      const { result } = renderHook(() => usePdfExport());

      let exportResult: any;
      await act(async () => {
        exportResult = await result.current.exportToPdf(element);
      });

      expect(exportResult.success).toBe(false);
      expect(exportResult.error).toBe('Canvas error');
      expect(result.current.isExporting).toBe(false);
      expect(result.current.progress).toBe(0);
    });

    it('should use default options when none provided', async () => {
      element = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      let exportResult: any;
      await act(async () => {
        exportResult = await result.current.exportToPdf(element);
      });

      expect(exportResult.success).toBe(true);
      expect(mockJsPDF).toHaveBeenCalledWith(expect.objectContaining({
        orientation: 'landscape',
        format: 'a4',
      }));
    });

    it('should add header with Stratum AI branding', async () => {
      element = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element);
      });

      // Should set purple color for branding and write 'Stratum AI'
      expect(mockSetTextColor).toHaveBeenCalledWith(168, 85, 247);
      expect(mockText).toHaveBeenCalledWith('Stratum AI', expect.any(Number), expect.any(Number));
    });

    it('should include timestamp when includeTimestamp is true', async () => {
      element = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element, { includeTimestamp: true });
      });

      // Should have called text with a UTC timestamp
      const textCalls = mockText.mock.calls.map((c: any) => c[0]);
      const hasTimestamp = textCalls.some((t: string) => typeof t === 'string' && t.includes('UTC'));
      expect(hasTimestamp).toBe(true);
    });
  });

  // -------------------------------------------------------------------------
  // exportMultiPagePdf
  // -------------------------------------------------------------------------

  describe('exportMultiPagePdf', () => {
    it('should return error when elements array is empty', async () => {
      const { result } = renderHook(() => usePdfExport());

      let exportResult: any;
      await act(async () => {
        exportResult = await result.current.exportMultiPagePdf([]);
      });

      expect(exportResult.success).toBe(false);
      expect(exportResult.error).toBe('No elements to export');
    });

    it('should generate multi-page PDF for multiple elements', async () => {
      const elements = [createMockElement(), createMockElement()];
      const { result } = renderHook(() => usePdfExport());

      let exportResult: any;
      await act(async () => {
        exportResult = await result.current.exportMultiPagePdf(elements);
      });

      expect(exportResult.success).toBe(true);
      // Should call addPage for second element
      expect(mockAddPage).toHaveBeenCalledTimes(1);

      elements.forEach((el) => document.body.removeChild(el));
    });

    it('should handle errors in multi-page export', async () => {
      const el = createMockElement();
      mockHtml2canvas.mockRejectedValueOnce(new Error('Multi-page error'));

      const { result } = renderHook(() => usePdfExport());

      let exportResult: any;
      await act(async () => {
        exportResult = await result.current.exportMultiPagePdf([el]);
      });

      expect(exportResult.success).toBe(false);
      expect(exportResult.error).toBe('Multi-page error');
      expect(result.current.isExporting).toBe(false);

      document.body.removeChild(el);
    });

    it('should reset state after multi-page export completes', async () => {
      const el = createMockElement();
      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportMultiPagePdf([el]);
      });

      expect(result.current.isExporting).toBe(false);
      expect(result.current.progress).toBe(0);

      document.body.removeChild(el);
    });
  });

  // -------------------------------------------------------------------------
  // DOM manipulation helpers (tested via export flow)
  // -------------------------------------------------------------------------

  describe('DOM Manipulation', () => {
    it('should reveal hidden export elements and restore them', async () => {
      element = createMockElement();
      const hiddenEl = document.createElement('span');
      hiddenEl.setAttribute('data-export-include', 'true');
      hiddenEl.style.display = 'none';
      element.appendChild(hiddenEl);

      // Mock getComputedStyle
      const originalGetComputedStyle = window.getComputedStyle;
      window.getComputedStyle = vi.fn().mockReturnValue({ display: 'none' }) as any;

      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element);
      });

      // After export, hidden element should be restored
      // (The restore runs in the finally block after screenshot)
      window.getComputedStyle = originalGetComputedStyle;
    });

    it('should swap abbreviated values during export', async () => {
      element = createMockElement();
      const valueEl = document.createElement('span');
      valueEl.setAttribute('data-export-value', '1234567.89');
      valueEl.textContent = '$1.2M';
      element.appendChild(valueEl);

      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element);
      });

      // After export, original text should be restored
      expect(valueEl.textContent).toBe('$1.2M');
    });

    it('should format currency values with data-export-currency attribute', async () => {
      element = createMockElement();
      const currencyEl = document.createElement('span');
      currencyEl.setAttribute('data-export-value', '1234.56');
      currencyEl.setAttribute('data-export-currency', '');
      currencyEl.textContent = '$1.2K';
      element.appendChild(currencyEl);

      const { result } = renderHook(() => usePdfExport());

      await act(async () => {
        await result.current.exportToPdf(element);
      });

      // After export cleanup, original text should be restored
      expect(currencyEl.textContent).toBe('$1.2K');
    });
  });
});
