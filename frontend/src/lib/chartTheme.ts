import type { TooltipProps } from 'recharts'

/**
 * Centralized Chart Theme Configuration
 * Analytics Design System + Stratum AI Brand
 *
 * Colors reference CSS custom properties so charts adapt to light/dark mode.
 * Platform colors are brand identities and remain static.
 */

export const chartTheme = {
  // Brand colors — read from CSS variables where possible
  colors: {
    primary: 'hsl(var(--primary))',
    primaryLight: 'hsl(var(--primary) / 0.7)',
    secondary: 'hsl(var(--secondary))',
    secondaryLight: 'hsl(var(--secondary) / 0.7)',

    // Metrics — status + accent tokens
    spend: 'hsl(var(--insight))',
    revenue: 'hsl(var(--info))',
    roas: 'hsl(var(--success))',
    conversions: 'hsl(var(--secondary))',
    ctr: 'hsl(var(--primary))',
    cpa: 'hsl(var(--warning))',
    impressions: 'hsl(var(--secondary))',
    clicks: 'hsl(var(--status-healthy))',

    // Platforms — brand identities (static)
    meta: '#0866FF',
    google: '#4285F4',
    tiktok: '#00F2EA',
    snapchat: '#FFFC00',
    linkedin: '#0A66C2',
    whatsapp: '#25D366',

    // Status — design system tokens
    success: 'hsl(var(--success))',
    warning: 'hsl(var(--warning))',
    error: 'hsl(var(--danger))',
    info: 'hsl(var(--info))',
    insight: 'hsl(var(--insight))',

    // Neutral — theme-aware
    muted: 'hsl(var(--muted-foreground))',
    border: 'hsl(var(--border))',
    grid: 'hsl(var(--border) / 0.5)',
  },

  // Platform color palette (ordered) — brand identities
  platformColors: ['#0866FF', '#4285F4', '#00F2EA', '#FFFC00', '#0A66C2', '#25D366'],

  // Regional breakdown colors — kept as static accent palette
  regionColors: ['#6366f1', '#ec4899', '#f97316', '#14b8a6', '#8b5cf6', '#f43f5e'],

  // Chart series colors (for multi-series) — static accent palette
  seriesColors: [
    '#6366f1',
    '#0ea5e9',
    '#10b981',
    '#f59e0b',
    '#ec4899',
    '#8b5cf6',
    '#14b8a6',
    '#f97316',
  ],

  // Tooltip styling — theme-aware surface
  tooltip: {
    contentStyle: {
      backgroundColor: 'hsl(var(--card))',
      border: '1px solid hsl(var(--border))',
      borderRadius: '14px',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
      padding: '12px 16px',
    },
    labelStyle: {
      color: 'hsl(var(--card-foreground))',
      fontWeight: 600,
      marginBottom: '4px',
    },
    itemStyle: {
      color: 'hsl(var(--muted-foreground))',
      fontSize: '14px',
    },
    cursor: {
      fill: 'hsl(var(--primary) / 0.10)',
    },
  },

  // Axis styling — theme-aware
  axis: {
    tick: {
      fontSize: 12,
      fill: 'hsl(var(--muted-foreground))',
    },
    tickLine: false,
    axisLine: false,
  },

  // Grid styling — theme-aware
  grid: {
    strokeDasharray: '3 3',
    stroke: 'hsl(var(--border) / 0.5)',
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

  // Gradient definitions — theme-aware where possible
  gradients: {
    revenue: {
      id: 'colorRevenue',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: 'hsl(var(--info))', opacity: 0.3 },
        { offset: '95%', color: 'hsl(var(--info))', opacity: 0 },
      ],
    },
    spend: {
      id: 'colorSpend',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: 'hsl(var(--insight))', opacity: 0.3 },
        { offset: '95%', color: 'hsl(var(--insight))', opacity: 0 },
      ],
    },
    primary: {
      id: 'colorPrimary',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: 'hsl(var(--primary))', opacity: 0.3 },
        { offset: '95%', color: 'hsl(var(--primary))', opacity: 0 },
      ],
    },
    brand: {
      id: 'colorBrand',
      x1: '0',
      y1: '0',
      x2: '1',
      y2: '1',
      stops: [
        { offset: '0%', color: 'hsl(var(--primary))', opacity: 1 },
        { offset: '100%', color: 'hsl(var(--secondary))', opacity: 1 },
      ],
    },
  },
}

// Helper function to get platform color — brand identities (static)
export function getPlatformChartColor(platform: string): string {
  const platformMap: Record<string, string> = {
    'meta ads': '#0866FF',
    meta: '#0866FF',
    'google ads': '#4285F4',
    google: '#4285F4',
    'tiktok ads': '#00F2EA',
    tiktok: '#00F2EA',
    'snapchat ads': '#FFFC00',
    snapchat: '#FFFC00',
    'linkedin ads': '#0A66C2',
    linkedin: '#0A66C2',
    whatsapp: '#25D366',
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

/** Recharts tooltip formatter type alias to avoid `as any` */
export type ChartTooltipFormatter = NonNullable<TooltipProps<number, string>['formatter']>

export default chartTheme
