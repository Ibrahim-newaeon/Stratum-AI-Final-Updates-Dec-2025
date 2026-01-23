/**
 * Centralized Chart Theme Configuration
 * 2026 Design System + Stratum AI Brand
 */

export const chartTheme = {
  // 2026 Brand colors - Electric Neon
  colors: {
    primary: '#8B5CF6',               // 2026 Electric violet
    primaryLight: '#A78BFA',
    secondary: '#00D4FF',             // 2026 Electric cyan
    secondaryLight: '#67e8f9',

    // Metrics - 2026 Neon palette
    spend: '#FF6B6B',                  // 2026 Coral
    revenue: '#00B4FF',                // 2026 Electric blue
    roas: '#00FF88',                   // 2026 Neon green
    conversions: '#8B5CF6',            // 2026 Electric violet
    ctr: '#ec4899',                    // Pink
    cpa: '#FFB800',                    // 2026 Amber
    impressions: '#6366f1',            // Indigo
    clicks: '#00D4FF',                 // 2026 Electric cyan

    // Platforms - Analytics Design System
    meta: '#0866FF',
    google: '#4285F4',
    tiktok: '#00F2EA',
    snapchat: '#FFFC00',
    whatsapp: '#25D366',

    // Status - 2026 Neon Glow
    success: '#00FF88',               // 2026 Neon green
    warning: '#FFB800',               // 2026 Amber glow
    error: '#FF4757',                 // 2026 Neon red
    info: '#00B4FF',                  // 2026 Electric blue
    insight: '#FF6B6B',               // 2026 Coral

    // Neutral - 2026
    muted: '#64748B',                 // 2026 Slate muted
    border: 'rgba(255,255,255,0.08)',
    grid: 'rgba(255,255,255,0.06)',
  },

  // Platform color palette (ordered) - Analytics Design System
  platformColors: ['#0866FF', '#4285F4', '#00F2EA', '#FFFC00', '#0A66C2', '#25D366'],

  // Regional breakdown colors - 2026 Neon
  regionColors: ['#8B5CF6', '#00D4FF', '#FF6B6B', '#00FF88', '#FFB800', '#ec4899'],

  // Chart series colors (for multi-series) - 2026 Electric palette
  seriesColors: [
    '#8B5CF6', // Electric violet
    '#00D4FF', // Electric cyan
    '#00FF88', // Neon green
    '#FFB800', // Amber glow
    '#FF6B6B', // Coral
    '#00B4FF', // Electric blue
    '#A78BFA', // Violet light
    '#67e8f9', // Cyan light
  ],

  // Tooltip styling - 2026 Glass
  tooltip: {
    contentStyle: {
      backgroundColor: 'rgba(10, 10, 15, 0.9)',  // 2026 Glass
      border: '1px solid rgba(139, 92, 246, 0.15)',  // 2026 Violet border
      borderRadius: '12px',
      boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4), 0 0 16px rgba(139, 92, 246, 0.1)',  // 2026 Glow
      padding: '12px 16px',
      backdropFilter: 'blur(16px)',
    },
    labelStyle: {
      color: '#FAFAFA',  // 2026 Soft white
      fontWeight: 600,
      marginBottom: '4px',
    },
    itemStyle: {
      color: '#94A3B8',  // 2026 Cooler gray
      fontSize: '14px',
    },
    cursor: {
      fill: 'rgba(139, 92, 246, 0.08)',  // 2026 Electric violet
    },
  },

  // Axis styling - 2026
  axis: {
    tick: {
      fontSize: 12,
      fill: '#94A3B8',  // 2026 Cooler gray
    },
    tickLine: false,
    axisLine: false,
  },

  // Grid styling - 2026
  grid: {
    strokeDasharray: '3 3',
    stroke: 'rgba(255,255,255,0.06)',  // 2026 Subtler
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

  // Gradient definitions - 2026 Electric
  gradients: {
    revenue: {
      id: 'colorRevenue',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: '#00B4FF', opacity: 0.4 },   // 2026 Electric blue
        { offset: '95%', color: '#00B4FF', opacity: 0 },
      ],
    },
    spend: {
      id: 'colorSpend',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: '#FF6B6B', opacity: 0.4 },   // 2026 Coral
        { offset: '95%', color: '#FF6B6B', opacity: 0 },
      ],
    },
    primary: {
      id: 'colorPrimary',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: '#8B5CF6', opacity: 0.4 },   // 2026 Electric violet
        { offset: '95%', color: '#8B5CF6', opacity: 0 },
      ],
    },
    brand: {
      id: 'colorBrand',
      x1: '0',
      y1: '0',
      x2: '1',
      y2: '1',
      stops: [
        { offset: '0%', color: '#8B5CF6', opacity: 1 },     // 2026 Electric violet
        { offset: '50%', color: '#00D4FF', opacity: 1 },    // 2026 Electric cyan
        { offset: '100%', color: '#FF6B6B', opacity: 1 },   // 2026 Coral
      ],
    },
    // 2026 Additional gradients
    success: {
      id: 'colorSuccess',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: '#00FF88', opacity: 0.4 },   // 2026 Neon green
        { offset: '95%', color: '#00FF88', opacity: 0 },
      ],
    },
    cyan: {
      id: 'colorCyan',
      x1: '0',
      y1: '0',
      x2: '0',
      y2: '1',
      stops: [
        { offset: '5%', color: '#00D4FF', opacity: 0.4 },   // 2026 Electric cyan
        { offset: '95%', color: '#00D4FF', opacity: 0 },
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
