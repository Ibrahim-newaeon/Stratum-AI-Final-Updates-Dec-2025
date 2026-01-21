import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format a number as currency
 */
export function formatCurrency(value: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value)
}

/**
 * Format a number in compact notation (e.g., 1.2K, 3.4M)
 */
export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  }).format(value)
}

/**
 * Format a number as percentage
 */
export function formatPercent(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`
}

/**
 * Get platform brand color - Analytics Design System
 * Colors aligned with tailwind.config.js and chartTheme.ts
 */
export function getPlatformColor(platform: string): string {
  const colors: Record<string, string> = {
    // Primary ad platforms - Analytics Design System colors
    meta: '#0866FF',
    'meta ads': '#0866FF',
    facebook: '#0866FF',
    google: '#4285F4',
    'google ads': '#4285F4',
    tiktok: '#00F2EA',
    'tiktok ads': '#00F2EA',
    snapchat: '#FFFC00',
    'snapchat ads': '#FFFC00',
    whatsapp: '#25D366',
    // Other platforms
    instagram: '#E4405F',
    linkedin: '#0A66C2',
    twitter: '#1DA1F2',
    x: '#000000',
    youtube: '#FF0000',
    pinterest: '#E60023',
  }
  return colors[platform.toLowerCase()] || '#6B7280'
}

/**
 * Format date to relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: Date | string): string {
  const now = new Date()
  const then = new Date(date)
  const diffMs = now.getTime() - then.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return then.toLocaleDateString()
}
