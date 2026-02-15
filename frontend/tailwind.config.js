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
        // STRATUM AI MIDNIGHT TEAL THEME
        stratum: {
          gold: '#e2b347',        // CTA accent
          'gold-bright': '#f0c95c',
          'gold-muted': '#c49a2c',
          cyan: '#00c7be',        // Primary teal
          'cyan-muted': '#00a89f',
          teal: '#00c7be',        // Alias
          jade: '#34c759',
          coral: '#ff6b6b',
          violet: '#a78bfa',
          purple: '#a78bfa',      // Tertiary accent
          'purple-muted': '#8b5cf6',
          green: '#34c759',       // Status success (jade)
          orange: '#f59e0b',      // Status warning
          red: '#ff6b6b',         // Status error (coral)
          blue: '#0a84ff',        // Status info
        },
        // Convergence Design System tokens
        'deep-space': '#0B0F1A',
        'stratum-blue': '#12233D',
        'signal-cyan': '#22D3EE',
        'trust-teal': '#00c7be',
        'premium-gold': '#e2b347',
        'cloud-white': '#F8FAFC',
        'conv-surface1': '#0F172A',
        'conv-surface2': '#16223C',
        'conv-surface3': '#1C2A47',
        // Glass surfaces
        glass: {
          card: 'rgba(255, 255, 255, 0.05)',
          cardHover: 'rgba(255, 255, 255, 0.08)',
          active: 'rgba(255, 255, 255, 0.12)',
          border: 'rgba(255, 255, 255, 0.08)',
          borderHover: 'rgba(255, 255, 255, 0.15)',
          subtle: 'rgba(255, 255, 255, 0.02)',
        },
        // Gold scale (CTA accent)
        gold: {
          50: '#fdf9eb',
          100: '#faf2d3',
          200: '#f5e5a7',
          300: '#efd872',
          400: '#f0c95c',
          500: '#e2b347', // CTA Gold
          600: '#c49a2c', // Gold muted
          700: '#8c6508',
          800: '#604507',
          900: '#342504',
          950: '#1a1202',
        },
        cyan: {
          50: '#e6fefb',
          100: '#ccfdfa',
          200: '#99fbf4',
          300: '#4df7ea',
          400: '#00c7be', // Primary Teal
          500: '#00c7be',
          600: '#00a89f',
          700: '#0a8a73',
          800: '#075c4d',
          900: '#032e26',
          950: '#011713',
        },
        meta: '#0866FF',
        google: '#4285F4',
        tiktok: '#00F2EA',
        snapchat: '#FFFC00',
        whatsapp: '#25D366',
        success: '#34c759', // Jade green
        warning: '#f59e0b', // Stratum orange
        danger: '#ff6b6b', // Coral
        info: '#00c7be', // Teal
        insight: '#a78bfa', // Violet
        surface: {
          primary: '#000000', // Pure black
          secondary: '#000000', // Pure black
          tertiary: 'rgba(255, 255, 255, 0.03)', // Glass card
          elevated: 'rgba(255, 255, 255, 0.05)', // Elevated glass
        },
        // Stratum Dashboard Theme Colors
        'bg-primary': '#0b1215',
        'bg-card': 'rgba(255, 255, 255, 0.05)',
        'bg-card-hover': 'rgba(255, 255, 255, 0.08)',
        'bg-elevated': 'rgba(255, 255, 255, 0.12)',
        'text-primary': '#FFFFFF',
        'text-secondary': 'rgba(255, 255, 255, 0.7)',
        'text-muted': 'rgba(255, 255, 255, 0.5)',
        chart: {
          1: 'hsl(var(--chart-1))',
          2: 'hsl(var(--chart-2))',
          3: 'hsl(var(--chart-3))',
          4: 'hsl(var(--chart-4))',
          5: 'hsl(var(--chart-5))',
        },
        // Vibe.co Design System
        vibe: {
          indigo: {
            light: '#4F46E5',
            DEFAULT: '#3730A3',
            dark: '#312E81',
          },
          bg: '#FFFFFF',
          text: '#000000',
          'text-secondary': '#6B7280',
        },
      },
      borderRadius: {
        sm: 'calc(var(--radius) - 4px)',
        md: 'calc(var(--radius) - 2px)',
        lg: 'var(--radius)',
        xl: '20px',
        '2xl': '24px',
        '3xl': '32px',
      },
      fontFamily: {
        sans: [
          'Inter',
          'SF Pro Display',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'SF Mono',
          'SFMono-Regular',
          'ui-monospace',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
        display: ['Plus Jakarta Sans', 'Outfit', 'Inter', 'SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      fontSize: {
        micro: ['10px', { lineHeight: '1.4', fontWeight: '400' }],
        meta: ['12px', { lineHeight: '1.5', fontWeight: '400' }],
        body: ['14px', { lineHeight: '1.55', fontWeight: '400' }],
        'body-lg': ['16px', { lineHeight: '1.6', fontWeight: '400' }],
        h3: ['18px', { lineHeight: '1.35', fontWeight: '600' }],
        h2: ['22px', { lineHeight: '1.3', fontWeight: '600' }],
        h1: ['28px', { lineHeight: '1.25', fontWeight: '700' }],
        'display-sm': ['32px', { lineHeight: '1.2', fontWeight: '700', letterSpacing: '-0.02em' }],
        display: ['40px', { lineHeight: '1.15', fontWeight: '700', letterSpacing: '-0.02em' }],
        'display-lg': ['48px', { lineHeight: '1.1', fontWeight: '800', letterSpacing: '-0.025em' }],
        'display-xl': ['56px', { lineHeight: '1.05', fontWeight: '800', letterSpacing: '-0.03em' }],
        'display-2xl': ['72px', { lineHeight: '1', fontWeight: '800', letterSpacing: '-0.03em' }],
        'display-hero': [
          '96px',
          { lineHeight: '0.95', fontWeight: '900', letterSpacing: '-0.04em' },
        ],
      },
      boxShadow: {
        // Midnight Teal - Gold CTA accent glows
        'gold-sm': '0 0 20px rgba(226, 179, 71, 0.1)',
        gold: '0 0 40px rgba(226, 179, 71, 0.15)',
        'gold-lg': '0 0 60px rgba(226, 179, 71, 0.2)',
        'gold-xl': '0 0 100px rgba(226, 179, 71, 0.25)',
        'glow-green': '0 0 40px rgba(52, 199, 89, 0.15)',
        'glow-orange': '0 0 40px rgba(245, 158, 11, 0.15)',
        'glow-purple': '0 0 40px rgba(167, 139, 250, 0.15)',
        'glow-cyan-accent': '0 0 40px rgba(0, 199, 190, 0.15)',
        // Glass effects - Midnight Teal style
        glass: '0 8px 32px rgba(0, 0, 0, 0.25), 0 2px 8px rgba(0, 0, 0, 0.12)',
        'glass-lg': '0 25px 50px rgba(0, 0, 0, 0.4)',
        'glass-glow': '0 0 40px rgba(0, 199, 190, 0.15), 0 25px 50px rgba(0, 0, 0, 0.4)',
        // Primary glow - Teal
        'glow-sm': '0 0 12px rgba(0, 199, 190, 0.15)',
        glow: '0 0 20px rgba(0, 199, 190, 0.2)',
        'glow-lg': '0 0 32px rgba(0, 199, 190, 0.25)',
        'glow-insight': '0 0 20px rgba(167, 139, 250, 0.2)',
        'glow-cyan': '0 0 20px rgba(0, 199, 190, 0.2)',
        // Convergence Design System shadows
        panel: '0 10px 30px rgba(0,0,0,0.35)',
        lift: '0 14px 40px rgba(0,0,0,0.45)',
        'glow-signal-cyan': '0 0 0 1px rgba(0,199,190,0.22), 0 10px 28px rgba(0,199,190,0.08)',
        'glow-trust-teal': '0 0 0 1px rgba(0,199,190,0.22), 0 10px 28px rgba(0,199,190,0.08)',
        'glow-premium-gold': '0 0 0 1px rgba(226,179,71,0.22), 0 10px 28px rgba(226,179,71,0.10)',
        card: '0 4px 12px rgba(0, 0, 0, 0.15)',
        'card-hover': '0 10px 30px rgba(0, 0, 0, 0.25)',
        // Ambient orb shadows
        'orb-gold': '0 0 120px 60px rgba(226, 179, 71, 0.08)',
        'orb-purple': '0 0 100px 50px rgba(167, 139, 250, 0.06)',
        'orb-cyan': '0 0 80px 40px rgba(0, 199, 190, 0.05)',
      },
      spacing: {
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        5: '24px',
        6: '32px',
        7: '48px',
        8: '64px',
        'section-sm': '64px',
        section: '96px',
        'section-lg': '128px',
        'section-xl': '160px',
        'container-sm': '640px',
        'container-md': '768px',
        'container-lg': '1024px',
        'container-xl': '1280px',
        'container-2xl': '1400px',
      },
      backgroundImage: {
        // Midnight Teal Gradients
        'gradient-gold': 'linear-gradient(135deg, #e2b347 0%, #f0c95c 100%)',
        'gradient-gold-warm': 'linear-gradient(135deg, #e2b347 0%, #f59e0b 100%)',
        'gradient-gold-cool': 'linear-gradient(135deg, #e2b347 0%, #00c7be 100%)',
        'gradient-gold-soft':
          'linear-gradient(135deg, rgba(226, 179, 71, 0.1) 0%, rgba(0, 199, 190, 0.05) 100%)',
        // Ambient orbs for glass dark backgrounds
        'ambient-orbs': `
          radial-gradient(ellipse 40% 40% at 20% 30%, rgba(0, 199, 190, 0.08), transparent),
          radial-gradient(ellipse 30% 30% at 80% 70%, rgba(167, 139, 250, 0.06), transparent),
          radial-gradient(ellipse 35% 35% at 60% 20%, rgba(226, 179, 71, 0.05), transparent)
        `,
        // Stratum primary gradient
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-stratum': 'linear-gradient(135deg, #00c7be 0%, #e2b347 100%)',
        'gradient-stratum-soft':
          'linear-gradient(135deg, rgba(0, 199, 190, 0.08) 0%, rgba(226, 179, 71, 0.05) 100%)',
      },
      backdropBlur: {
        '100': '100px',
        '120': '120px',
      },
      keyframes: {
        // Neural Network Animations
        'node-pulse': {
          '0%, 100%': { opacity: '0.4', transform: 'scale(1)' },
          '50%': { opacity: '0.8', transform: 'scale(1.1)' },
        },
        'line-pulse': {
          '0%, 100%': { opacity: '0.1', strokeDashoffset: '0' },
          '50%': { opacity: '0.3', strokeDashoffset: '20' },
        },
        'status-pulse': {
          '0%, 100%': { boxShadow: '0 0 0 0 currentColor' },
          '50%': { boxShadow: '0 0 0 4px transparent' },
        },
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        // NEBULA AURORA ANIMATIONS
        'aurora-flow': {
          '0%, 100%': {
            backgroundPosition: '0% 50%',
            filter: 'hue-rotate(0deg)',
          },
          '50%': {
            backgroundPosition: '100% 50%',
            filter: 'hue-rotate(30deg)',
          },
        },
        'nebula-pulse': {
          '0%, 100%': {
            opacity: '0.4',
            transform: 'scale(1)',
          },
          '50%': {
            opacity: '0.8',
            transform: 'scale(1.05)',
          },
        },
        'cosmic-drift': {
          '0%': { transform: 'translate(0, 0) rotate(0deg)' },
          '25%': { transform: 'translate(50px, -30px) rotate(90deg)' },
          '50%': { transform: 'translate(0, -60px) rotate(180deg)' },
          '75%': { transform: 'translate(-50px, -30px) rotate(270deg)' },
          '100%': { transform: 'translate(0, 0) rotate(360deg)' },
        },
        'plasma-morph': {
          '0%, 100%': { borderRadius: '60% 40% 30% 70% / 60% 30% 70% 40%' },
          '25%': { borderRadius: '30% 60% 70% 40% / 50% 60% 30% 60%' },
          '50%': { borderRadius: '50% 50% 30% 70% / 40% 70% 30% 60%' },
          '75%': { borderRadius: '40% 60% 50% 50% / 60% 40% 60% 40%' },
        },
        bioluminescent: {
          '0%, 100%': {
            boxShadow:
              '0 0 20px rgba(0, 255, 255, 0.3), 0 0 40px rgba(0, 255, 255, 0.2), 0 0 60px rgba(0, 255, 255, 0.1)',
          },
          '50%': {
            boxShadow:
              '0 0 30px rgba(0, 255, 255, 0.5), 0 0 60px rgba(0, 255, 255, 0.3), 0 0 90px rgba(0, 255, 255, 0.2)',
          },
        },
        crystalline: {
          '0%': {
            backgroundPosition: '200% 0',
            opacity: '0',
          },
          '50%': { opacity: '1' },
          '100%': {
            backgroundPosition: '-200% 0',
            opacity: '0',
          },
        },
        holographic: {
          '0%': {
            backgroundPosition: '0% 50%',
            filter: 'brightness(1) contrast(1)',
          },
          '25%': { filter: 'brightness(1.1) contrast(1.05)' },
          '50%': {
            backgroundPosition: '100% 50%',
            filter: 'brightness(1.2) contrast(1.1)',
          },
          '75%': { filter: 'brightness(1.1) contrast(1.05)' },
          '100%': {
            backgroundPosition: '0% 50%',
            filter: 'brightness(1) contrast(1)',
          },
        },
        'particle-float': {
          '0%, 100%': {
            transform: 'translateY(0) translateX(0)',
            opacity: '0.3',
          },
          '25%': {
            transform: 'translateY(-20px) translateX(10px)',
            opacity: '0.8',
          },
          '50%': {
            transform: 'translateY(-40px) translateX(-5px)',
            opacity: '0.5',
          },
          '75%': {
            transform: 'translateY(-20px) translateX(-10px)',
            opacity: '0.8',
          },
        },
        // Legacy animations
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
          '0%': { opacity: 0, transform: 'translateY(20px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        'scale-in': {
          '0%': { opacity: 0, transform: 'scale(0.9)' },
          '100%': { opacity: 1, transform: 'scale(1)' },
        },
        'delta-pop': {
          '0%': { transform: 'scale(0.98)', opacity: 0.6 },
          '100%': { transform: 'scale(1)', opacity: 1 },
        },
        sweep: {
          '0%': { opacity: 0, transform: 'translateX(-12px)' },
          '100%': { opacity: 1, transform: 'translateX(0)' },
        },
        'glow-pulse': {
          '0%': { boxShadow: '0 0 0 rgba(0,0,0,0)' },
          '60%': { boxShadow: '0 0 30px rgba(124,58,237,0.3)' },
          '100%': { boxShadow: '0 0 0 rgba(0,0,0,0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        morph: {
          '0%, 100%': { borderRadius: '60% 40% 30% 70% / 60% 30% 70% 40%' },
          '50%': { borderRadius: '30% 60% 70% 40% / 50% 60% 30% 60%' },
        },
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
          '50%': { transform: 'translateY(-20px) rotate(2deg)' },
        },
        // Convergence Design System animations
        convergence: {
          '0%, 100%': { transform: 'translateY(0)', opacity: '0.85' },
          '50%': { transform: 'translateY(-2px)', opacity: '1' },
        },
        'shimmer-conv': {
          '0%': { backgroundPosition: '0% 50%' },
          '100%': { backgroundPosition: '100% 50%' },
        },
        // Command Center Animations
        'terminal-blink': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        'scanline-sweep': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(1)', opacity: '0.4' },
          '100%': { transform: 'scale(2)', opacity: '0' },
        },
        'data-flow': {
          '0%': { strokeDashoffset: '100' },
          '100%': { strokeDashoffset: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        // Neural Network Animations
        'node-pulse': 'node-pulse 3s ease-in-out infinite',
        'line-pulse': 'line-pulse 4s ease-in-out infinite',
        'status-pulse': 'status-pulse 2s ease-in-out infinite',
        // NEBULA AURORA ANIMATIONS
        'aurora-flow': 'aurora-flow 8s ease infinite',
        'nebula-pulse': 'nebula-pulse 4s ease-in-out infinite',
        'cosmic-drift': 'cosmic-drift 20s linear infinite',
        'plasma-morph': 'plasma-morph 8s ease-in-out infinite',
        bioluminescent: 'bioluminescent 3s ease-in-out infinite',
        crystalline: 'crystalline 3s ease-in-out infinite',
        holographic: 'holographic 6s ease infinite',
        'particle-float': 'particle-float 6s ease-in-out infinite',
        // Legacy
        'slide-in': 'slide-in-from-right 0.3s ease-out',
        'slide-in-left': 'slide-in-from-left 0.3s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
        enter: 'fade-up 0.4s cubic-bezier(0.16, 1, 0.3, 1) both',
        delta: 'delta-pop 0.18s cubic-bezier(0.2, 0.8, 0.2, 1) both',
        sweep: 'sweep 0.28s cubic-bezier(0.16, 1, 0.3, 1) both',
        'glow-pulse': 'glow-pulse 0.42s cubic-bezier(0.16, 1, 0.3, 1) both',
        insight: 'ember-glow 0.42s cubic-bezier(0.16, 1, 0.3, 1) both',
        'scale-in': 'scale-in 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        shimmer: 'shimmer 2s linear infinite',
        morph: 'morph 8s ease-in-out infinite',
        'gradient-shift': 'gradient-shift 8s ease infinite',
        float: 'float 6s ease-in-out infinite',
        // Convergence Design System
        convergence: 'convergence 1.6s ease-in-out infinite',
        'shimmer-conv': 'shimmer-conv 2.2s ease-in-out infinite',
        // Command Center Animations
        'terminal-blink': 'terminal-blink 1s step-end infinite',
        'scanline-sweep': 'scanline-sweep 3s linear infinite',
        'pulse-ring': 'pulse-ring 2s ease-out infinite',
        'data-flow': 'data-flow 2s linear infinite',
      },
      transitionDuration: {
        fast: '150ms',
        base: '250ms',
        slow: '400ms',
        xl: '600ms',
      },
      transitionTimingFunction: {
        standard: 'cubic-bezier(0.4, 0, 0.2, 1)',
        enter: 'cubic-bezier(0.16, 1, 0.3, 1)',
        exit: 'cubic-bezier(0.7, 0, 0.84, 0)',
        bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        stratum: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
      },
      zIndex: {
        hide: '-1',
        base: '0',
        raised: '1',
        dropdown: '10',
        sticky: '20',
        header: '30',
        overlay: '40',
        modal: '50',
        popover: '60',
        toast: '70',
        tooltip: '80',
        max: '9999',
      },
    },
  },
  plugins: [require('tailwindcss-animate'), require('tailwindcss-rtl')],
};
