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
        // Stratum AI brand — Cyber Pink
        stratum: {
          50: '#FDF0F5',
          100: '#FCDDE8',
          200: '#FAB6CE',
          300: '#F984AD',
          400: '#FA508C',
          500: '#FF1F6D',
          600: '#CC1857',
          700: '#991242',
          800: '#660C2C',
          900: '#330616',
          950: '#1A030B',
        },
        // Platform colors — refined
        meta: '#0866FF',
        google: '#4285F4',
        tiktok: '#00F2EA',
        snapchat: '#FFFC00',
        whatsapp: '#25D366',
        // Widget status tokens
        'status-healthy': 'hsl(var(--status-healthy))',
        'status-critical': 'hsl(var(--status-critical))',
        // Data/Status colors
        success: 'hsl(var(--success))',
        warning: 'hsl(var(--warning))',
        danger: 'hsl(var(--danger))',
        info: 'hsl(var(--info))',
        insight: 'hsl(var(--insight))',
        // Surface colors — theme-aware
        surface: {
          primary: 'hsl(var(--surface-primary))',
          secondary: 'hsl(var(--surface-secondary))',
          tertiary: 'hsl(var(--surface-tertiary))',
          elevated: 'hsl(var(--surface-elevated))',
        },
        // Text colors
        'text-primary': '#F0EDE5',
        'text-secondary': '#8B92A8',
        'text-muted': '#5A6278',
      },
      borderRadius: {
        sm: '8px',
        md: '10px',
        lg: '14px',
        xl: '18px',
      },
      fontFamily: {
        sans: ['Satoshi', 'system-ui', 'sans-serif'],
        display: ['Clash Display', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      fontSize: {
        'micro': ['10px', { lineHeight: '1.4', fontWeight: '400' }],
        'meta': ['12px', { lineHeight: '1.5', fontWeight: '400' }],
        'body': ['14px', { lineHeight: '1.55', fontWeight: '400' }],
        'h3': ['18px', { lineHeight: '1.35', fontWeight: '600' }],
        'h2': ['22px', { lineHeight: '1.3', fontWeight: '600' }],
        'h1': ['28px', { lineHeight: '1.25', fontWeight: '700' }],
        'display-xs': ['32px', { lineHeight: '1.15', fontWeight: '700', letterSpacing: '-0.02em' }],
        'display-sm': ['40px', { lineHeight: '1.1', fontWeight: '700', letterSpacing: '-0.02em' }],
        'display': ['56px', { lineHeight: '1.05', fontWeight: '700', letterSpacing: '-0.03em' }],
        'display-lg': ['72px', { lineHeight: '1.0', fontWeight: '700', letterSpacing: '-0.03em' }],
      },
      boxShadow: {
        'glow-sm': '0 0 12px rgba(255, 31, 109, 0.15)',
        'glow': '0 0 24px rgba(255, 31, 109, 0.18)',
        'glow-lg': '0 0 40px rgba(255, 31, 109, 0.22)',
        'glow-cyan': '0 0 24px rgba(0, 245, 255, 0.15)',
        'glow-orange': '0 0 24px rgba(255, 140, 0, 0.18)',
        'card': '0 1px 3px rgba(0, 0, 0, 0.2)',
        'card-hover': '0 8px 32px rgba(0, 0, 0, 0.35)',
        'glass': '0 2px 8px rgba(0, 0, 0, 0.15)',
        'elevated': '0 4px 24px rgba(0, 0, 0, 0.3)',
      },
      spacing: {
        '1': '4px',
        '2': '8px',
        '3': '12px',
        '4': '16px',
        '5': '24px',
        '6': '32px',
        '7': '48px',
        '8': '64px',
        '9': '96px',
        '10': '128px',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-primary': 'linear-gradient(135deg, #FF4D8F 0%, #FF1F6D 50%, #CC1857 100%)',
        'gradient-primary-soft': 'linear-gradient(135deg, rgba(255, 77, 143, 0.08) 0%, rgba(255, 31, 109, 0.04) 100%)',
        'gradient-cyber': 'linear-gradient(135deg, #FF4D8F 0%, #FF1F6D 50%, #FF8C00 100%)',
        'gradient-void': 'linear-gradient(180deg, #050B18 0%, #0A1020 100%)',
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
        'fade-up': {
          '0%': { opacity: 0, transform: 'translateY(12px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        'scale-in': {
          '0%': { opacity: 0, transform: 'scale(0.96)' },
          '100%': { opacity: 1, transform: 'scale(1)' },
        },
        'delta-pop': {
          '0%': { transform: 'scale(0.98)', opacity: 0.6 },
          '100%': { transform: 'scale(1)', opacity: 1 },
        },
        'sweep': {
          '0%': { opacity: 0, transform: 'translateX(-12px)' },
          '100%': { opacity: 1, transform: 'translateX(0)' },
        },
        'glow-pulse': {
          '0%': { boxShadow: '0 0 0 rgba(0,0,0,0)' },
          '60%': { boxShadow: '0 0 32px rgba(255, 31, 109, 0.2)' },
          '100%': { boxShadow: '0 0 0 rgba(0,0,0,0)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        'orbit': {
          '0%': { transform: 'rotate(0deg) translateX(80px) rotate(0deg)' },
          '100%': { transform: 'rotate(360deg) translateX(80px) rotate(-360deg)' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'slide-in': 'slide-in-from-right 0.3s ease-out',
        'slide-in-left': 'slide-in-from-left 0.3s ease-out',
        'fade-in': 'fade-in 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        'enter': 'fade-up 0.4s cubic-bezier(0.16, 1, 0.3, 1) both',
        'delta': 'delta-pop 0.2s cubic-bezier(0.16, 1, 0.3, 1) both',
        'sweep': 'sweep 0.35s cubic-bezier(0.16, 1, 0.3, 1) both',
        'glow-pulse': 'glow-pulse 0.6s cubic-bezier(0.16, 1, 0.3, 1) both',
        'scale-in': 'scale-in 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        'shimmer': 'shimmer 1.2s linear infinite',
        'float': 'float 4s ease-in-out infinite',
        'orbit': 'orbit 20s linear infinite',
      },
      transitionDuration: {
        'fast': '120ms',
        'base': '200ms',
        'slow': '350ms',
        'xl': '500ms',
      },
      transitionTimingFunction: {
        'standard': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'enter': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'exit': 'cubic-bezier(0.7, 0, 0.84, 0)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}
