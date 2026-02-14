/**
 * PDF Export Utility
 *
 * Generates client-safe PDF reports from dashboard data
 */

import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

interface ReportData {
  tenantName: string;
  dateRange: { start: string; end: string };
  emqScore: number;
  confidenceBand: 'reliable' | 'directional' | 'unsafe';
  kpis: {
    label: string;
    value: string | number;
    trend?: number;
  }[];
  summary?: string;
  recommendations?: string[];
}

/**
 * Generate a PDF report from the current view
 */
export async function exportViewToPDF(
  elementId: string,
  filename: string = 'report.pdf'
): Promise<void> {
  const element = document.getElementById(elementId);
  if (!element) {
    // Element not found
    return;
  }

  try {
    const canvas = await html2canvas(element, {
      scale: 2,
      backgroundColor: '#060606',
      logging: false,
      useCORS: true,
    });

    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF({
      orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
      unit: 'px',
      format: [canvas.width, canvas.height],
    });

    pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
    pdf.save(filename);
  } catch (error) {
    // Error re-thrown below
    throw error;
  }
}

/**
 * Generate a structured client report PDF
 */
export async function generateClientReport(data: ReportData): Promise<void> {
  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = pdf.internal.pageSize.getWidth();
  const margin = 20;
  let y = margin;

  // Helper functions
  const addText = (
    text: string,
    size: number,
    color: string = '#ffffff',
    bold: boolean = false
  ) => {
    pdf.setFontSize(size);
    pdf.setTextColor(color);
    if (bold) pdf.setFont('helvetica', 'bold');
    else pdf.setFont('helvetica', 'normal');
    pdf.text(text, margin, y);
    y += size * 0.5;
  };

  const addLine = () => {
    pdf.setDrawColor('#333333');
    pdf.line(margin, y, pageWidth - margin, y);
    y += 5;
  };

  // Background
  pdf.setFillColor('#060606');
  pdf.rect(0, 0, pageWidth, pdf.internal.pageSize.getHeight(), 'F');

  // Header
  addText('STRATUM AI', 24, '#a855f7', true);
  addText('Performance Report', 14, '#9ca3af');
  y += 5;

  // Tenant Info
  addText(data.tenantName, 18, '#ffffff', true);
  addText(`${data.dateRange.start} - ${data.dateRange.end}`, 10, '#9ca3af');
  y += 10;

  addLine();
  y += 5;

  // EMQ Score Section
  addText('Data Quality Score', 12, '#9ca3af');
  y += 2;

  // EMQ Score badge
  const emqColor = data.emqScore >= 80 ? '#34c759' : data.emqScore >= 60 ? '#eab308' : '#ef4444';
  pdf.setFillColor(emqColor);
  pdf.roundedRect(margin, y, 30, 15, 3, 3, 'F');
  pdf.setTextColor('#ffffff');
  pdf.setFontSize(16);
  pdf.setFont('helvetica', 'bold');
  pdf.text(data.emqScore.toString(), margin + 15, y + 10, { align: 'center' });

  // Confidence band
  const bandColors: Record<string, string> = {
    reliable: '#34c759',
    directional: '#eab308',
    unsafe: '#ef4444',
  };
  pdf.setFillColor(bandColors[data.confidenceBand] || '#9ca3af');
  pdf.roundedRect(margin + 35, y, 40, 15, 3, 3, 'F');
  pdf.setFontSize(10);
  pdf.text(data.confidenceBand.toUpperCase(), margin + 55, y + 10, { align: 'center' });

  y += 25;

  // KPIs Section
  addText('Key Performance Indicators', 12, '#9ca3af');
  y += 5;

  const kpiWidth = (pageWidth - margin * 2 - 15) / 2;
  let kpiX = margin;
  let kpiRow = 0;

  data.kpis.forEach((kpi, index) => {
    if (index > 0 && index % 2 === 0) {
      kpiRow++;
      kpiX = margin;
      y += 25;
    }

    // KPI box
    pdf.setFillColor('#121212');
    pdf.roundedRect(kpiX, y, kpiWidth, 20, 2, 2, 'F');

    // KPI label
    pdf.setTextColor('#9ca3af');
    pdf.setFontSize(8);
    pdf.setFont('helvetica', 'normal');
    pdf.text(kpi.label, kpiX + 5, y + 6);

    // KPI value
    pdf.setTextColor('#ffffff');
    pdf.setFontSize(14);
    pdf.setFont('helvetica', 'bold');
    pdf.text(String(kpi.value), kpiX + 5, y + 15);

    // Trend
    if (kpi.trend !== undefined) {
      const trendColor = kpi.trend >= 0 ? '#34c759' : '#ef4444';
      const trendText = `${kpi.trend >= 0 ? '+' : ''}${kpi.trend}%`;
      pdf.setTextColor(trendColor);
      pdf.setFontSize(8);
      pdf.text(trendText, kpiX + kpiWidth - 5, y + 15, { align: 'right' });
    }

    kpiX += kpiWidth + 5;
  });

  y += 30;

  // Summary Section
  if (data.summary) {
    addLine();
    y += 5;
    addText('Summary', 12, '#9ca3af');
    y += 3;

    pdf.setTextColor('#ffffff');
    pdf.setFontSize(10);
    pdf.setFont('helvetica', 'normal');

    const lines = pdf.splitTextToSize(data.summary, pageWidth - margin * 2);
    lines.forEach((line: string) => {
      pdf.text(line, margin, y);
      y += 5;
    });
  }

  // Recommendations Section
  if (data.recommendations && data.recommendations.length > 0) {
    y += 5;
    addLine();
    y += 5;
    addText('Recommendations', 12, '#9ca3af');
    y += 3;

    pdf.setTextColor('#ffffff');
    pdf.setFontSize(10);
    pdf.setFont('helvetica', 'normal');

    data.recommendations.forEach((rec, index) => {
      pdf.text(`${index + 1}. ${rec}`, margin, y);
      y += 6;
    });
  }

  // Footer
  const footerY = pdf.internal.pageSize.getHeight() - 15;
  pdf.setTextColor('#6b7280');
  pdf.setFontSize(8);
  pdf.text(
    `Generated by Stratum AI on ${new Date().toLocaleDateString()}`,
    pageWidth / 2,
    footerY,
    { align: 'center' }
  );
  pdf.text('Confidential - For internal use only', pageWidth / 2, footerY + 4, { align: 'center' });

  // Save
  const filename = `${data.tenantName.replace(/\s+/g, '_')}_Report_${data.dateRange.end}.pdf`;
  pdf.save(filename);
}

/**
 * Export dashboard screenshot as PDF
 */
export async function exportDashboardPDF(tenantName: string): Promise<void> {
  const mainContent = document.querySelector('main');
  if (!mainContent) {
    // Main content not found
    return;
  }

  try {
    const canvas = await html2canvas(mainContent, {
      scale: 2,
      backgroundColor: '#060606',
      logging: false,
      useCORS: true,
      windowWidth: 1920,
    });

    const imgWidth = 210; // A4 width in mm
    const imgHeight = (canvas.height * imgWidth) / canvas.width;

    const pdf = new jsPDF({
      orientation: imgHeight > 297 ? 'portrait' : 'landscape',
      unit: 'mm',
      format: 'a4',
    });

    // Add header
    pdf.setFillColor('#060606');
    pdf.rect(0, 0, 210, 20, 'F');
    pdf.setTextColor('#a855f7');
    pdf.setFontSize(12);
    pdf.setFont('helvetica', 'bold');
    pdf.text('STRATUM AI', 10, 12);
    pdf.setTextColor('#ffffff');
    pdf.setFontSize(10);
    pdf.text(tenantName, 50, 12);
    pdf.setTextColor('#9ca3af');
    pdf.setFontSize(8);
    pdf.text(new Date().toLocaleDateString(), 190, 12, { align: 'right' });

    // Add screenshot
    const imgData = canvas.toDataURL('image/png');
    pdf.addImage(imgData, 'PNG', 0, 25, imgWidth, imgHeight);

    // Save
    const filename = `${tenantName.replace(/\s+/g, '_')}_Dashboard_${new Date().toISOString().split('T')[0]}.pdf`;
    pdf.save(filename);
  } catch (error) {
    // Error re-thrown below
    throw error;
  }
}

export default {
  exportViewToPDF,
  generateClientReport,
  exportDashboardPDF,
};
