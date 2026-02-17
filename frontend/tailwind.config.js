/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    './node_modules/@tremor/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        // Stratum AI brand colors - Purple to Cyan gradient
        stratum: {
          50: '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',
          600: '#9333ea',
          700: '#7e22ce',
          800: '#6b21a8',
          900: '#581c87',
          950: '#3b0764',
        },
        // Cyan accent for gradients
        cyan: {
          50: '#ecfeff',
          100: '#cffafe',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
          950: '#083344',
        },
        // Platform colors - Analytics Design System
        meta: '#0866FF',
        google: '#4285F4',
        tiktok: '#00F2EA',
        snapchat: '#FFFC00',
        whatsapp: '#25D366',
        // Data/Status colors
        success: '#22C55E',
        warning: '#FACC15',
        danger: '#EF4444',
        info: '#3B82F6',
        insight: '#F97316',
        // Surface colors for dark mode
        surface: {
          primary: '#060606',
          secondary: '#0A0A0A',
          tertiary: '#121212',
          elevated: 'rgba(255,255,255,0.04)',
        },
        // Text colors
        'text-primary': '#FFFFFF',
        'text-secondary': '#A7AABB',
        'text-muted': '#6E7482',
      },
      borderRadius: {
        sm: '10px',
        md: '12px',
        lg: '16px',
        xl: '20px',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      fontSize: {
        // Analytics Design System typography scale
        'micro': ['10px', { lineHeight: '1.4', fontWeight: '400' }],
        'meta': ['12px', { lineHeight: '1.5', fontWeight: '400' }],
        'body': ['14px', { lineHeight: '1.55', fontWeight: '400' }],
        'h3': ['18px', { lineHeight: '1.35', fontWeight: '600' }],
        'h2': ['22px', { lineHeight: '1.3', fontWeight: '600' }],
        'h1': ['28px', { lineHeight: '1.25', fontWeight: '700' }],
      },
      boxShadow: {
        // Analytics Design System shadows
        'glow-sm': '0 0 10px rgba(168, 85, 247, 0.15)',
        'glow': '0 0 22px rgba(168, 85, 247, 0.18)',
        'glow-lg': '0 0 30px rgba(168, 85, 247, 0.25)',
        'glow-insight': '0 0 18px rgba(249, 115, 22, 0.22)',
        'card': '0 4px 12px rgba(0, 0, 0, 0.20)',
        'card-hover': '0 10px 30px rgba(0, 0, 0, 0.28)',
      },
      spacing: {
        // Analytics Design System spacing (8px grid)
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '5': '24px',
        '6': '32px',
        '7': '48px',
        '8': '64px',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-stratum': 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
        'gradient-stratum-soft': 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: 0 },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: 0 },
        },
        'slide-in-from-right': {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'slide-in-from-left': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        'fade-in': {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        // Analytics Design System - fadeUp entrance
        'fade-up': {
          '0%': { opacity: 0, transform: 'translateY(8px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        'scale-in': {
          '0%': { opacity: 0, transform: 'scale(0.95)' },
          '100%': { opacity: 1, transform: 'scale(1)' },
        },
        // Analytics Design System - KPI delta pop
        'delta-pop': {
          '0%': { transform: 'scale(0.98)', opacity: 0.6 },
          '100%': { transform: 'scale(1)', opacity: 1 },
        },
        // Analytics Design System - chart sweep
        'sweep': {
          '0%': { opacity: 0, transform: 'translateX(-12px)' },
          '100%': { opacity: 1, transform: 'translateX(0)' },
        },
        // Analytics Design System - brand glow pulse
        'glow-pulse': {
          '0%': { boxShadow: '0 0 0 rgba(0,0,0,0)' },
          '60%': { boxShadow: '0 0 22px rgba(168,85,247,0.18)' },
          '100%': { boxShadow: '0 0 0 rgba(0,0,0,0)' },
        },
        // Analytics Design System - insight ember glow
        'ember-glow': {
          '0%': { boxShadow: '0 0 0 rgba(0,0,0,0)' },
          '50%': { boxShadow: '0 0 18px rgba(249,115,22,0.22)' },
          '100%': { boxShadow: '0 0 0 rgba(0,0,0,0)' },
        },
        // Analytics Design System - critical alert shake
        'micro-shake': {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%': { transform: 'translateX(-2px)' },
          '40%': { transform: 'translateX(2px)' },
          '60%': { transform: 'translateX(-1px)' },
          '80%': { transform: 'translateX(1px)' },
        },
        // Analytics Design System - skeleton shimmer
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'slide-in': 'slide-in-from-right 0.3s ease-out',
        'slide-in-left': 'slide-in-from-left 0.3s ease-out',
        'fade-in': 'fade-in 0.18s cubic-bezier(0.2, 0.8, 0.2, 1)',
        // Analytics Design System motion
        'enter': 'fade-up 0.28s cubic-bezier(0.16, 1, 0.3, 1) both',
        'delta': 'delta-pop 0.18s cubic-bezier(0.2, 0.8, 0.2, 1) both',
        'sweep': 'sweep 0.28s cubic-bezier(0.16, 1, 0.3, 1) both',
        'glow-pulse': 'glow-pulse 0.42s cubic-bezier(0.16, 1, 0.3, 1) both',
        'insight': 'ember-glow 0.42s cubic-bezier(0.16, 1, 0.3, 1) both',
        'critical': 'micro-shake 0.18s cubic-bezier(0.2, 0.8, 0.2, 1) both',
        'scale-in': 'scale-in 0.18s cubic-bezier(0.2, 0.8, 0.2, 1)',
        'shimmer': 'shimmer 0.9s linear infinite',
      },
      transitionDuration: {
        'fast': '120ms',
        'base': '180ms',
        'slow': '280ms',
        'xl': '420ms',
      },
      transitionTimingFunction: {
        'standard': 'cubic-bezier(0.2, 0.8, 0.2, 1)',
        'enter': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'exit': 'cubic-bezier(0.7, 0, 0.84, 0)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
