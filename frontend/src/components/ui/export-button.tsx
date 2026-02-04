/**
 * Export Button Component - One-click PDF/CSV export for dashboards
 */

import * as React from 'react';
import { AlertCircle, Check, Download, FileSpreadsheet, FileText, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { PdfExportOptions, usePdfExport } from '@/hooks/usePdfExport';

interface ExportButtonProps {
  /** Reference to the element to export */
  targetRef: React.RefObject<HTMLElement>;
  /** PDF export options */
  pdfOptions?: PdfExportOptions;
  /** CSV data for spreadsheet export */
  csvData?: Record<string, any>[];
  /** CSV filename */
  csvFilename?: string;
  /** Show dropdown with format options */
  showFormatSelector?: boolean;
  /** Button variant */
  variant?: 'default' | 'outline' | 'ghost';
  /** Button size */
  size?: 'sm' | 'md' | 'lg';
  /** Additional class names */
  className?: string;
  /** Callback after successful export */
  onExportComplete?: (result: { type: 'pdf' | 'csv'; filename: string }) => void;
  /** Callback on export error */
  onExportError?: (error: string) => void;
}

export function ExportButton({
  targetRef,
  pdfOptions = {},
  csvData,
  csvFilename = 'export',
  showFormatSelector = true,
  variant = 'default',
  size = 'md',
  className,
  onExportComplete,
  onExportError,
}: ExportButtonProps) {
  const { exportToPdf, isExporting, progress } = usePdfExport();
  const [showDropdown, setShowDropdown] = React.useState(false);
  const [exportStatus, setExportStatus] = React.useState<'idle' | 'success' | 'error'>('idle');
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Reset status after showing success/error
  React.useEffect(() => {
    if (exportStatus !== 'idle') {
      const timer = setTimeout(() => setExportStatus('idle'), 3000);
      return () => clearTimeout(timer);
    }
  }, [exportStatus]);

  const handlePdfExport = async () => {
    setShowDropdown(false);
    const result = await exportToPdf(targetRef.current, pdfOptions);
    if (result.success) {
      setExportStatus('success');
      onExportComplete?.({ type: 'pdf', filename: result.filename! });
    } else {
      setExportStatus('error');
      onExportError?.(result.error || 'Export failed');
    }
  };

  const handleCsvExport = () => {
    if (!csvData || csvData.length === 0) {
      onExportError?.('No data to export');
      return;
    }

    setShowDropdown(false);

    try {
      // Get headers from first object
      const headers = Object.keys(csvData[0]);

      // Build CSV content
      const csvContent = [
        headers.join(','),
        ...csvData.map((row) =>
          headers
            .map((header) => {
              const value = row[header];
              // Handle values with commas or quotes
              if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                return `"${value.replace(/"/g, '""')}"`;
              }
              return value ?? '';
            })
            .join(',')
        ),
      ].join('\n');

      // Create and download file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const dateStr = new Date().toISOString().slice(0, 10);
      const filename = `${csvFilename}-${dateStr}.csv`;

      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);

      setExportStatus('success');
      onExportComplete?.({ type: 'csv', filename });
    } catch (error) {
      setExportStatus('error');
      onExportError?.(error instanceof Error ? error.message : 'CSV export failed');
    }
  };

  const sizeClasses = {
    sm: 'h-8 px-3 text-xs',
    md: 'h-9 px-4 text-sm',
    lg: 'h-10 px-5 text-base',
  };

  const variantClasses = {
    default: 'bg-primary text-primary-foreground hover:bg-primary/90',
    outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
    ghost: 'hover:bg-accent hover:text-accent-foreground',
  };

  const buttonContent = () => {
    if (isExporting) {
      return (
        <>
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
          <span>Exporting {progress}%</span>
        </>
      );
    }

    if (exportStatus === 'success') {
      return (
        <>
          <Check className="h-4 w-4 mr-2 text-green-500" />
          <span>Exported!</span>
        </>
      );
    }

    if (exportStatus === 'error') {
      return (
        <>
          <AlertCircle className="h-4 w-4 mr-2 text-red-500" />
          <span>Failed</span>
        </>
      );
    }

    return (
      <>
        <Download className="h-4 w-4 mr-2" />
        <span>Export</span>
      </>
    );
  };

  // Simple button without dropdown
  if (!showFormatSelector || !csvData) {
    return (
      <button
        onClick={handlePdfExport}
        disabled={isExporting}
        className={cn(
          'inline-flex items-center justify-center rounded-lg font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'disabled:pointer-events-none disabled:opacity-50',
          sizeClasses[size],
          variantClasses[variant],
          className
        )}
      >
        {buttonContent()}
      </button>
    );
  }

  // Button with dropdown for format selection
  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        disabled={isExporting}
        className={cn(
          'inline-flex items-center justify-center rounded-lg font-medium transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          'disabled:pointer-events-none disabled:opacity-50',
          sizeClasses[size],
          variantClasses[variant],
          className
        )}
      >
        {buttonContent()}
      </button>

      {showDropdown && !isExporting && (
        <div className="absolute right-0 mt-2 w-48 py-2 rounded-lg border bg-card shadow-lg z-50 animate-in fade-in-0 zoom-in-95">
          <button
            onClick={handlePdfExport}
            className="w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-muted transition-colors"
          >
            <FileText className="h-4 w-4 text-red-500" />
            <div className="text-left">
              <div className="font-medium">PDF Report</div>
              <div className="text-xs text-muted-foreground">Professional document</div>
            </div>
          </button>
          <button
            onClick={handleCsvExport}
            className="w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-muted transition-colors"
          >
            <FileSpreadsheet className="h-4 w-4 text-green-500" />
            <div className="text-left">
              <div className="font-medium">CSV Spreadsheet</div>
              <div className="text-xs text-muted-foreground">For Excel/Sheets</div>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}

export default ExportButton;
