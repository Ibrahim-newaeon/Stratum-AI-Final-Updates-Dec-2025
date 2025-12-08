/**
 * Centralized Chart Theme Configuration
 * Stratum AI Brand Colors and Styling for Recharts
 */

export const chartTheme = {
  // Brand colors
  colors: {
    primary: 'hsl(262 83% 58%)',      // Stratum purple
    primaryLight: 'hsl(262 83% 70%)',
    secondary: 'hsl(199 89% 48%)',    // Cyan accent
    secondaryLight: 'hsl(199 89% 60%)',

    // Metrics
    spend: '#f97316',                  // Orange
    revenue: '#0ea5e9',                // Sky blue
    roas: '#10b981',                   // Emerald
    conversions: '#8b5cf6',            // Violet
    ctr: '#ec4899',                    // Pink
    cpa: '#f59e0b',                    // Amber
    impressions: '#6366f1',            // Indigo
    clicks: '#14b8a6',                 // Teal

    // Platforms
    meta: '#1877F2',
    google: '#EA4335',
    tiktok: '#00F2EA',
    snapchat: '#FFFC00',
    whatsapp: '#25D366',

    // Status
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',

    // Neutral
    muted: 'hsl(var(--muted-foreground))',
    border: 'hsl(var(--border))',
    grid: 'hsl(var(--muted))',
  },

  // Platform color palette (ordered)
  platformColors: ['#1877F2', '#EA4335', '#00F2EA', '#FFFC00', '#25D366'],

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

  // Tooltip styling
  tooltip: {
    contentStyle: {
      backgroundColor: 'hsl(var(--card))',
      border: '1px solid hsl(var(--border))',
      borderRadius: '0.5rem',
      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
      padding: '12px 16px',
    },
    labelStyle: {
      color: 'hsl(var(--foreground))',
      fontWeight: 600,
      marginBottom: '4px',
    },
    itemStyle: {
      color: 'hsl(var(--muted-foreground))',
      fontSize: '14px',
    },
    cursor: {
      fill: 'hsl(var(--primary) / 0.1)',
    },
  },

  // Axis styling
  axis: {
    tick: {
      fontSize: 12,
      fill: 'hsl(var(--muted-foreground))',
    },
    tickLine: false,
    axisLine: false,
  },

  // Grid styling
  grid: {
    strokeDasharray: '3 3',
    stroke: 'hsl(var(--border))',
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

  // Gradient definitions
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
        { offset: '5%', color: 'hsl(262 83% 58%)', opacity: 0.3 },
        { offset: '95%', color: 'hsl(262 83% 58%)', opacity: 0 },
      ],
    },
  },
}

// Helper function to get platform color
export function getPlatformChartColor(platform: string): string {
  const platformMap: Record<string, string> = {
    'meta ads': chartTheme.colors.meta,
    'meta': chartTheme.colors.meta,
    'google ads': chartTheme.colors.google,
    'google': chartTheme.colors.google,
    'tiktok ads': chartTheme.colors.tiktok,
    'tiktok': chartTheme.colors.tiktok,
    'snapchat ads': chartTheme.colors.snapchat,
    'snapchat': chartTheme.colors.snapchat,
    'whatsapp': chartTheme.colors.whatsapp,
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
