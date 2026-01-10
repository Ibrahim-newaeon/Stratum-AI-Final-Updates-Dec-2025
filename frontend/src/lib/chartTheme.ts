/**
 * Centralized Chart Theme Configuration
 * Analytics Design System + Stratum AI Brand
 */

export const chartTheme = {
  // Brand colors - Analytics Design System
  colors: {
    primary: '#a855f7',               // Stratum purple
    primaryLight: '#c084fc',
    secondary: '#06b6d4',             // Cyan accent
    secondaryLight: '#22d3ee',

    // Metrics
    spend: '#f97316',                  // Orange
    revenue: '#0ea5e9',                // Sky blue
    roas: '#22C55E',                   // Success green (design system)
    conversions: '#8b5cf6',            // Violet
    ctr: '#ec4899',                    // Pink
    cpa: '#FACC15',                    // Warning (design system)
    impressions: '#6366f1',            // Indigo
    clicks: '#14b8a6',                 // Teal

    // Platforms - Analytics Design System
    meta: '#0866FF',
    google: '#4285F4',
    tiktok: '#00F2EA',
    snapchat: '#FFFC00',
    whatsapp: '#25D366',

    // Status - Analytics Design System data colors
    success: '#22C55E',
    warning: '#FACC15',
    error: '#EF4444',
    info: '#3B82F6',
    insight: '#F97316',               // Quantum Ember

    // Neutral
    muted: '#6E7482',
    border: 'rgba(255,255,255,0.10)',
    grid: 'rgba(255,255,255,0.08)',
  },

  // Platform color palette (ordered) - Analytics Design System
  platformColors: ['#0866FF', '#4285F4', '#00F2EA', '#FFFC00', '#0A66C2', '#25D366'],

  // Regional breakdown colors
  regionColors: ['#6366f1', '#ec4899', '#f97316', '#14b8a6', '#8b5cf6', '#f43f5e'],

  // Chart series colors (for multi-series)
  seriesColors: [
    '#6366f1', // Indigo
    '#0ea5e9', // Sky
    '#10b981', // Emerald
    '#f59e0b', // Amber
    '#ec4899', // Pink
    '#8b5cf6', // Violet
    '#14b8a6', // Teal
    '#f97316', // Orange
  ],

  // Tooltip styling - Analytics Design System
  tooltip: {
    contentStyle: {
      backgroundColor: '#0A0A0A',
      border: '1px solid rgba(255,255,255,0.10)',
      borderRadius: '12px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.20)',
      padding: '12px 16px',
    },
    labelStyle: {
      color: '#FFFFFF',
      fontWeight: 600,
      marginBottom: '4px',
    },
    itemStyle: {
      color: '#A7AABB',
      fontSize: '14px',
    },
    cursor: {
      fill: 'rgba(168, 85, 247, 0.10)',
    },
  },

  // Axis styling - Analytics Design System
  axis: {
    tick: {
      fontSize: 12,
      fill: '#A7AABB',
    },
    tickLine: false,
    axisLine: false,
  },

  // Grid styling - Analytics Design System
  grid: {
    strokeDasharray: '3 3',
    stroke: 'rgba(255,255,255,0.08)',
    opacity: 0.5,
  },

  // Legend styling
  legend: {
    wrapperStyle: {
      paddingTop: '20px',
    },
    iconType: 'circle' as const,
    iconSize: 8,
  },

  // Animation config
  animation: {
    duration: 800,
    easing: 'ease-out',
  },

  // Gradient definitions - Analytics Design System
  gradients: {
    revenue: {
      id: 'colorRevenue',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: '#0ea5e9', opacity: 0.3 },
        { offset: '95%', color: '#0ea5e9', opacity: 0 },
      ],
    },
    spend: {
      id: 'colorSpend',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: '#f97316', opacity: 0.3 },
        { offset: '95%', color: '#f97316', opacity: 0 },
      ],
    },
    primary: {
      id: 'colorPrimary',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: '#a855f7', opacity: 0.3 },
        { offset: '95%', color: '#a855f7', opacity: 0 },
      ],
    },
    brand: {
      id: 'colorBrand',
      x1: '0',
      y1: '0',
      x2: '1',
      y2: '1',
      stops: [
        { offset: '0%', color: '#a855f7', opacity: 1 },
        { offset: '100%', color: '#06b6d4', opacity: 1 },
      ],
    },
  },
}

// Helper function to get platform color - Analytics Design System
export function getPlatformChartColor(platform: string): string {
  const platformMap: Record<string, string> = {
    'meta ads': '#0866FF',
    'meta': '#0866FF',
    'google ads': '#4285F4',
    'google': '#4285F4',
    'tiktok ads': '#00F2EA',
    'tiktok': '#00F2EA',
    'snapchat ads': '#FFFC00',
    'snapchat': '#FFFC00',
    'whatsapp': '#25D366',
  }
  return platformMap[platform.toLowerCase()] || chartTheme.seriesColors[0]
}

// Helper to format chart values
export const chartFormatters = {
  currency: (value: number) => {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
    if (value >= 1000) return `$${(value / 1000).toFixed(1)}K`
    return `$${value.toFixed(0)}`
  },
  compact: (value: number) => {
    if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
    if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
    return value.toString()
  },
  percent: (value: number) => `${value.toFixed(1)}%`,
  roas: (value: number) => `${value.toFixed(2)}x`,
}

export default chartTheme
