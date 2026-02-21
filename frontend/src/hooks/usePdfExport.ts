/**
 * PDF Export Hook - Generate professional PDF reports from dashboard views
 * Uses jsPDF + html2canvas for high-quality exports
 *
 * Libraries are dynamically imported to reduce initial bundle size
 */

import { useCallback, useState } from 'react';

export interface PdfExportOptions {
  filename?: string;
  title?: string;
  subtitle?: string;
  includeTimestamp?: boolean;
  orientation?: 'portrait' | 'landscape';
  format?: 'a4' | 'letter';
  quality?: number;
  margin?: number;
}

export interface PdfExportResult {
  success: boolean;
  filename?: string;
  error?: string;
}

/**
 * Format a UTC timestamp with timezone label for PDF headers.
 * Includes timezone abbreviation to avoid ambiguity across timezones.
 */
function formatTimestampUTC(): string {
  const now = new Date();
  const utcStr = now.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
  });
  return `${utcStr} UTC`;
}

/**
 * Before taking a screenshot, temporarily reveal any elements hidden by
 * cost/price toggle so they appear in the exported PDF. Elements must have
 * the attribute data-export-include="true" to be affected.
 *
 * Returns a cleanup function that restores original display values.
 */
function revealHiddenExportElements(container: HTMLElement): () => void {
  const hiddenEls = container.querySelectorAll<HTMLElement>(
    '[data-export-include="true"]'
  );
  const originals: string[] = [];

  hiddenEls.forEach((el, i) => {
    originals[i] = el.style.display;
    if (window.getComputedStyle(el).display === 'none') {
      el.style.display = '';
    }
  });

  return () => {
    hiddenEls.forEach((el, i) => {
      el.style.display = originals[i];
    });
  };
}

/**
 * Temporarily swap abbreviated values ($1.2M) with full-precision values
 * for the screenshot. Elements must have a data-export-value attribute
 * containing the raw number (e.g., data-export-value="1234567.89").
 *
 * Returns a cleanup function that restores original text.
 */
function swapAbbreviatedValues(container: HTMLElement): () => void {
  const els = container.querySelectorAll<HTMLElement>('[data-export-value]');
  const originals: string[] = [];

  els.forEach((el, i) => {
    originals[i] = el.textContent || '';
    const raw = el.getAttribute('data-export-value');
    if (raw !== null) {
      const num = parseFloat(raw);
      if (!isNaN(num)) {
        // Format with full precision using locale-aware number formatting
        const isCurrency = el.hasAttribute('data-export-currency');
        el.textContent = isCurrency
          ? `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          : num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
    }
  });

  return () => {
    els.forEach((el, i) => {
      el.textContent = originals[i];
    });
  };
}

export function usePdfExport() {
  const [isExporting, setIsExporting] = useState(false);
  const [progress, setProgress] = useState(0);

  const exportToPdf = useCallback(
    async (
      elementRef: HTMLElement | null,
      options: PdfExportOptions = {}
    ): Promise<PdfExportResult> => {
      if (!elementRef) {
        return { success: false, error: 'No element to export' };
      }

      const {
        filename = 'stratum-report',
        title = 'Stratum AI Report',
        subtitle,
        includeTimestamp = true,
        orientation = 'landscape',
        format = 'a4',
        quality = 2, // Higher = better quality
        margin = 10,
      } = options;

      setIsExporting(true);
      setProgress(10);

      // Reveal hidden elements and swap abbreviated values before screenshot
      const restoreHidden = revealHiddenExportElements(elementRef);
      const restoreValues = swapAbbreviatedValues(elementRef);

      try {
        // Dynamically import PDF libraries for better code splitting
        setProgress(20);
        const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
          import('jspdf'),
          import('html2canvas'),
        ]);

        // Create canvas from element
        setProgress(30);
        const canvas = await html2canvas(elementRef, {
          scale: quality,
          useCORS: true,
          allowTaint: true,
          backgroundColor: '#0a0a0a', // Match dark theme
          logging: false,
        });

        // Restore DOM immediately after screenshot
        restoreValues();
        restoreHidden();

        setProgress(60);

        // Calculate dimensions
        const imgWidth = canvas.width;
        const imgHeight = canvas.height;

        // Create PDF
        const pdf = new jsPDF({
          orientation,
          unit: 'mm',
          format,
        });

        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        const contentWidth = pageWidth - margin * 2;
        const contentHeight = pageHeight - margin * 2 - 25; // Leave space for header

        // Add header
        pdf.setFillColor(10, 10, 10);
        pdf.rect(0, 0, pageWidth, 20, 'F');

        // Stratum AI branding
        pdf.setTextColor(168, 85, 247); // Purple
        pdf.setFontSize(14);
        pdf.setFont('helvetica', 'bold');
        pdf.text('Stratum AI', margin, 13);

        // Title
        pdf.setTextColor(255, 255, 255);
        pdf.setFontSize(10);
        pdf.setFont('helvetica', 'normal');
        const titleText = subtitle ? `${title} - ${subtitle}` : title;
        pdf.text(titleText, pageWidth / 2, 13, { align: 'center' });

        // Timestamp with UTC timezone label
        if (includeTimestamp) {
          pdf.setTextColor(150, 150, 150);
          pdf.setFontSize(8);
          const timestamp = formatTimestampUTC();
          pdf.text(timestamp, pageWidth - margin, 13, { align: 'right' });
        }

        setProgress(80);

        // Add image with proper scaling
        const imgData = canvas.toDataURL('image/png');
        const ratio = Math.min(contentWidth / imgWidth, contentHeight / imgHeight);
        const scaledWidth = imgWidth * ratio;
        const scaledHeight = imgHeight * ratio;

        // Center the image
        const xOffset = margin + (contentWidth - scaledWidth) / 2;
        const yOffset = 25; // Below header

        pdf.addImage(imgData, 'PNG', xOffset, yOffset, scaledWidth, scaledHeight);

        // Add footer
        pdf.setFillColor(10, 10, 10);
        pdf.rect(0, pageHeight - 10, pageWidth, 10, 'F');
        pdf.setTextColor(100, 100, 100);
        pdf.setFontSize(7);
        pdf.text(
          'Generated by Stratum AI - Trust-Gated Revenue Operations',
          pageWidth / 2,
          pageHeight - 4,
          { align: 'center' }
        );
        pdf.text(`Page 1 of 1`, pageWidth - margin, pageHeight - 4, { align: 'right' });

        setProgress(95);

        // Generate filename with timestamp
        const dateStr = new Date().toISOString().slice(0, 10);
        const finalFilename = `${filename}-${dateStr}.pdf`;

        // Save the PDF
        pdf.save(finalFilename);

        setProgress(100);

        return { success: true, filename: finalFilename };
      } catch (error) {
        // Ensure DOM is restored on error
        restoreValues();
        restoreHidden();
        // Error returned in result object
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      } finally {
        setIsExporting(false);
        setProgress(0);
      }
    },
    []
  );

  // Export multiple elements as multi-page PDF
  const exportMultiPagePdf = useCallback(
    async (elements: HTMLElement[], options: PdfExportOptions = {}): Promise<PdfExportResult> => {
      if (elements.length === 0) {
        return { success: false, error: 'No elements to export' };
      }

      const {
        filename = 'stratum-report',
        title = 'Stratum AI Report',
        includeTimestamp = true,
        orientation = 'landscape',
        format = 'a4',
        quality = 2,
        margin = 10,
      } = options;

      setIsExporting(true);
      setProgress(5);

      try {
        // Dynamically import PDF libraries for better code splitting
        const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
          import('jspdf'),
          import('html2canvas'),
        ]);

        setProgress(10);

        const pdf = new jsPDF({
          orientation,
          unit: 'mm',
          format,
        });

        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();
        const contentWidth = pageWidth - margin * 2;
        const contentHeight = pageHeight - margin * 2 - 25;

        for (let i = 0; i < elements.length; i++) {
          const element = elements[i];
          setProgress(10 + 80 * (i / elements.length));

          if (i > 0) {
            pdf.addPage();
          }

          // Reveal hidden elements and swap abbreviated values
          const restoreHidden = revealHiddenExportElements(element);
          const restoreValues = swapAbbreviatedValues(element);

          // Create canvas
          const canvas = await html2canvas(element, {
            scale: quality,
            useCORS: true,
            allowTaint: true,
            backgroundColor: '#0a0a0a',
            logging: false,
          });

          // Restore DOM immediately after screenshot
          restoreValues();
          restoreHidden();

          // Add header
          pdf.setFillColor(10, 10, 10);
          pdf.rect(0, 0, pageWidth, 20, 'F');

          pdf.setTextColor(168, 85, 247);
          pdf.setFontSize(14);
          pdf.setFont('helvetica', 'bold');
          pdf.text('Stratum AI', margin, 13);

          pdf.setTextColor(255, 255, 255);
          pdf.setFontSize(10);
          pdf.setFont('helvetica', 'normal');
          pdf.text(title, pageWidth / 2, 13, { align: 'center' });

          if (includeTimestamp) {
            pdf.setTextColor(150, 150, 150);
            pdf.setFontSize(8);
            const timestamp = formatTimestampUTC();
            pdf.text(timestamp, pageWidth - margin, 13, { align: 'right' });
          }

          // Add image
          const imgData = canvas.toDataURL('image/png');
          const ratio = Math.min(contentWidth / canvas.width, contentHeight / canvas.height);
          const scaledWidth = canvas.width * ratio;
          const scaledHeight = canvas.height * ratio;
          const xOffset = margin + (contentWidth - scaledWidth) / 2;

          pdf.addImage(imgData, 'PNG', xOffset, 25, scaledWidth, scaledHeight);

          // Add footer
          pdf.setFillColor(10, 10, 10);
          pdf.rect(0, pageHeight - 10, pageWidth, 10, 'F');
          pdf.setTextColor(100, 100, 100);
          pdf.setFontSize(7);
          pdf.text(
            'Generated by Stratum AI - Trust-Gated Revenue Operations',
            pageWidth / 2,
            pageHeight - 4,
            { align: 'center' }
          );
          pdf.text(`Page ${i + 1} of ${elements.length}`, pageWidth - margin, pageHeight - 4, {
            align: 'right',
          });
        }

        setProgress(95);

        const dateStr = new Date().toISOString().slice(0, 10);
        const finalFilename = `${filename}-${dateStr}.pdf`;
        pdf.save(finalFilename);

        setProgress(100);
        return { success: true, filename: finalFilename };
      } catch (error) {
        // Error returned in result object
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      } finally {
        setIsExporting(false);
        setProgress(0);
      }
    },
    []
  );

  return {
    exportToPdf,
    exportMultiPagePdf,
    isExporting,
    progress,
  };
}

export default usePdfExport;
