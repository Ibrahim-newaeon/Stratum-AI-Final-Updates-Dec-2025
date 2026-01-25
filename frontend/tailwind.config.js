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
  			'2xl': '1400px'
  		}
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
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			// NEBULA AURORA THEME - Revolutionary 2026 Palette
  			nebula: {
  				'50': '#f5f3ff',
  				'100': '#ede9fe',
  				'200': '#ddd6fe',
  				'300': '#c4b5fd',
  				'400': '#a78bfa',
  				'500': '#7C3AED',      // Deep violet core
  				'600': '#6D28D9',
  				'700': '#5B21B6',
  				'800': '#4C1D95',
  				'900': '#2E1065',
  				'950': '#1a0b3e'
  			},
  			aurora: {
  				cyan: '#00FFFF',       // Electric cyan
  				teal: '#00F5D4',       // Bioluminescent teal
  				mint: '#00FF9F',       // Neon mint
  				lime: '#B8FF00',       // Plasma lime
  				pink: '#FF00FF',       // Magenta plasma
  				rose: '#FF0080',       // Hot rose
  				coral: '#FF6B6B',      // Soft coral
  				gold: '#FFD700',       // Pure gold
  				amber: '#FFAA00',      // Warm amber
  			},
  			cosmic: {
  				void: '#000011',       // Deep space black with blue
  				abyss: '#020617',      // Slate abyss
  				deep: '#0a0a1a',       // Deep purple-black
  				dark: '#0f0f23',       // Dark nebula
  				medium: '#161629',     // Medium depth
  				light: '#1e1e3f',      // Lighter cosmic
  				glow: '#2a2a5a',       // Glowing surface
  			},
  			// Legacy support - mapped to new theme
  			stratum: {
  				'50': '#f5f3ff',
  				'100': '#ede9fe',
  				'200': '#ddd6fe',
  				'300': '#c4b5fd',
  				'400': '#a78bfa',
  				'500': '#7C3AED',
  				'600': '#6D28D9',
  				'700': '#5B21B6',
  				'800': '#4C1D95',
  				'900': '#2E1065',
  				'950': '#1a0b3e'
  			},
  			cyan: {
  				'50': '#ecfeff',
  				'100': '#cffafe',
  				'200': '#a5f3fc',
  				'300': '#67e8f9',
  				'400': '#22d3ee',
  				'500': '#00FFFF',
  				'600': '#0891b2',
  				'700': '#0e7490',
  				'800': '#155e75',
  				'900': '#164e63',
  				'950': '#083344'
  			},
  			meta: '#0866FF',
  			google: '#4285F4',
  			tiktok: '#00F2EA',
  			snapchat: '#FFFC00',
  			whatsapp: '#25D366',
  			success: '#00FF9F',        // Aurora mint
  			warning: '#FFAA00',        // Aurora amber
  			danger: '#FF0080',         // Aurora rose
  			info: '#00FFFF',           // Aurora cyan
  			insight: '#FF6B6B',        // Aurora coral
  			surface: {
  				primary: '#000011',    // Cosmic void
  				secondary: '#0a0a1a',  // Cosmic deep
  				tertiary: '#0f0f23',   // Cosmic dark
  				elevated: '#161629'    // Cosmic medium
  			},
  			'text-primary': '#FFFFFF',
  			'text-secondary': '#94A3B8',
  			'text-muted': '#64748B',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		borderRadius: {
  			sm: 'calc(var(--radius) - 4px)',
  			md: 'calc(var(--radius) - 2px)',
  			lg: 'var(--radius)',
  			xl: '20px',
  			'2xl': '24px',
  			'3xl': '32px'
  		},
  		fontFamily: {
  			sans: [
  				'Inter',
  				'system-ui',
  				'-apple-system',
  				'Segoe UI',
  				'Roboto',
  				'Arial',
  				'sans-serif'
  			],
  			mono: [
  				'JetBrains Mono',
  				'ui-monospace',
  				'SFMono-Regular',
  				'Menlo',
  				'Monaco',
  				'Consolas',
  				'monospace'
  			],
  			display: [
  				'Inter',
  				'system-ui',
  				'sans-serif'
  			]
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
  			'display': ['40px', { lineHeight: '1.15', fontWeight: '700', letterSpacing: '-0.02em' }],
  			'display-lg': ['48px', { lineHeight: '1.1', fontWeight: '800', letterSpacing: '-0.025em' }],
  			'display-xl': ['56px', { lineHeight: '1.05', fontWeight: '800', letterSpacing: '-0.03em' }],
  			'display-2xl': ['72px', { lineHeight: '1', fontWeight: '800', letterSpacing: '-0.03em' }],
  			'display-hero': ['96px', { lineHeight: '0.95', fontWeight: '900', letterSpacing: '-0.04em' }],
  		},
  		boxShadow: {
  			// Nebula Aurora Glows
  			'nebula-sm': '0 0 20px rgba(124, 58, 237, 0.3)',
  			'nebula': '0 0 40px rgba(124, 58, 237, 0.4)',
  			'nebula-lg': '0 0 60px rgba(124, 58, 237, 0.5)',
  			'nebula-xl': '0 0 100px rgba(124, 58, 237, 0.6)',
  			'aurora-cyan': '0 0 40px rgba(0, 255, 255, 0.4)',
  			'aurora-teal': '0 0 40px rgba(0, 245, 212, 0.4)',
  			'aurora-mint': '0 0 40px rgba(0, 255, 159, 0.4)',
  			'aurora-rose': '0 0 40px rgba(255, 0, 128, 0.4)',
  			'aurora-gold': '0 0 40px rgba(255, 215, 0, 0.4)',
  			// Multi-color aurora
  			'aurora-multi': '0 0 60px rgba(124, 58, 237, 0.3), 0 0 120px rgba(0, 255, 255, 0.2), 0 0 180px rgba(255, 0, 128, 0.1)',
  			// Glass effects
  			'glass': '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 0 0 1px rgba(255, 255, 255, 0.05)',
  			'glass-lg': '0 16px 64px rgba(0, 0, 0, 0.5), inset 0 0 0 1px rgba(255, 255, 255, 0.08)',
  			// Legacy support
  			'glow-sm': '0 0 12px rgba(124, 58, 237, 0.2)',
  			glow: '0 0 20px rgba(124, 58, 237, 0.4)',
  			'glow-lg': '0 0 32px rgba(124, 58, 237, 0.5)',
  			'glow-insight': '0 0 20px rgba(255, 107, 107, 0.4)',
  			'glow-cyan': '0 0 20px rgba(0, 255, 255, 0.4)',
  			card: '0 4px 12px rgba(0, 0, 0, 0.20)',
  			'card-hover': '0 10px 30px rgba(0, 0, 0, 0.28)'
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
  			'section-sm': '64px',
  			'section': '96px',
  			'section-lg': '128px',
  			'section-xl': '160px',
  			'container-sm': '640px',
  			'container-md': '768px',
  			'container-lg': '1024px',
  			'container-xl': '1280px',
  			'container-2xl': '1400px',
  		},
  		backgroundImage: {
  			// Nebula Aurora Gradients
  			'gradient-nebula': 'linear-gradient(135deg, #7C3AED 0%, #00FFFF 50%, #FF0080 100%)',
  			'gradient-aurora': 'linear-gradient(135deg, #00FFFF 0%, #00F5D4 25%, #00FF9F 50%, #B8FF00 75%, #FFD700 100%)',
  			'gradient-cosmic': 'linear-gradient(135deg, #000011 0%, #0a0a1a 50%, #1e1e3f 100%)',
  			'gradient-plasma': 'linear-gradient(135deg, #FF0080 0%, #7C3AED 50%, #00FFFF 100%)',
  			'gradient-bioluminescent': 'radial-gradient(ellipse at center, rgba(0, 255, 255, 0.15) 0%, transparent 70%)',
  			'gradient-void': 'radial-gradient(ellipse at center, rgba(124, 58, 237, 0.1) 0%, transparent 70%)',
  			// Legacy
  			'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
  			'gradient-stratum': 'linear-gradient(135deg, #7C3AED 0%, #00FFFF 50%, #FF0080 100%)',
  			'gradient-stratum-soft': 'linear-gradient(135deg, rgba(124, 58, 237, 0.08) 0%, rgba(0, 255, 255, 0.05) 100%)'
  		},
  		keyframes: {
  			'accordion-down': {
  				from: { height: '0' },
  				to: { height: 'var(--radix-accordion-content-height)' }
  			},
  			'accordion-up': {
  				from: { height: 'var(--radix-accordion-content-height)' },
  				to: { height: '0' }
  			},
  			// NEBULA AURORA ANIMATIONS
  			'aurora-flow': {
  				'0%, 100%': {
  					backgroundPosition: '0% 50%',
  					filter: 'hue-rotate(0deg)'
  				},
  				'50%': {
  					backgroundPosition: '100% 50%',
  					filter: 'hue-rotate(30deg)'
  				}
  			},
  			'nebula-pulse': {
  				'0%, 100%': {
  					opacity: '0.4',
  					transform: 'scale(1)'
  				},
  				'50%': {
  					opacity: '0.8',
  					transform: 'scale(1.05)'
  				}
  			},
  			'cosmic-drift': {
  				'0%': { transform: 'translate(0, 0) rotate(0deg)' },
  				'25%': { transform: 'translate(50px, -30px) rotate(90deg)' },
  				'50%': { transform: 'translate(0, -60px) rotate(180deg)' },
  				'75%': { transform: 'translate(-50px, -30px) rotate(270deg)' },
  				'100%': { transform: 'translate(0, 0) rotate(360deg)' }
  			},
  			'plasma-morph': {
  				'0%, 100%': { borderRadius: '60% 40% 30% 70% / 60% 30% 70% 40%' },
  				'25%': { borderRadius: '30% 60% 70% 40% / 50% 60% 30% 60%' },
  				'50%': { borderRadius: '50% 50% 30% 70% / 40% 70% 30% 60%' },
  				'75%': { borderRadius: '40% 60% 50% 50% / 60% 40% 60% 40%' }
  			},
  			'bioluminescent': {
  				'0%, 100%': {
  					boxShadow: '0 0 20px rgba(0, 255, 255, 0.3), 0 0 40px rgba(0, 255, 255, 0.2), 0 0 60px rgba(0, 255, 255, 0.1)'
  				},
  				'50%': {
  					boxShadow: '0 0 30px rgba(0, 255, 255, 0.5), 0 0 60px rgba(0, 255, 255, 0.3), 0 0 90px rgba(0, 255, 255, 0.2)'
  				}
  			},
  			'crystalline': {
  				'0%': {
  					backgroundPosition: '200% 0',
  					opacity: '0'
  				},
  				'50%': { opacity: '1' },
  				'100%': {
  					backgroundPosition: '-200% 0',
  					opacity: '0'
  				}
  			},
  			'holographic': {
  				'0%': {
  					backgroundPosition: '0% 50%',
  					filter: 'brightness(1) contrast(1)'
  				},
  				'25%': { filter: 'brightness(1.1) contrast(1.05)' },
  				'50%': {
  					backgroundPosition: '100% 50%',
  					filter: 'brightness(1.2) contrast(1.1)'
  				},
  				'75%': { filter: 'brightness(1.1) contrast(1.05)' },
  				'100%': {
  					backgroundPosition: '0% 50%',
  					filter: 'brightness(1) contrast(1)'
  				}
  			},
  			'particle-float': {
  				'0%, 100%': {
  					transform: 'translateY(0) translateX(0)',
  					opacity: '0.3'
  				},
  				'25%': {
  					transform: 'translateY(-20px) translateX(10px)',
  					opacity: '0.8'
  				},
  				'50%': {
  					transform: 'translateY(-40px) translateX(-5px)',
  					opacity: '0.5'
  				},
  				'75%': {
  					transform: 'translateY(-20px) translateX(-10px)',
  					opacity: '0.8'
  				}
  			},
  			// Legacy animations
  			'slide-in-from-right': {
  				'0%': { transform: 'translateX(100%)' },
  				'100%': { transform: 'translateX(0)' }
  			},
  			'slide-in-from-left': {
  				'0%': { transform: 'translateX(-100%)' },
  				'100%': { transform: 'translateX(0)' }
  			},
  			'fade-in': {
  				'0%': { opacity: 0 },
  				'100%': { opacity: 1 }
  			},
  			'fade-up': {
  				'0%': { opacity: 0, transform: 'translateY(20px)' },
  				'100%': { opacity: 1, transform: 'translateY(0)' }
  			},
  			'scale-in': {
  				'0%': { opacity: 0, transform: 'scale(0.9)' },
  				'100%': { opacity: 1, transform: 'scale(1)' }
  			},
  			'delta-pop': {
  				'0%': { transform: 'scale(0.98)', opacity: 0.6 },
  				'100%': { transform: 'scale(1)', opacity: 1 }
  			},
  			sweep: {
  				'0%': { opacity: 0, transform: 'translateX(-12px)' },
  				'100%': { opacity: 1, transform: 'translateX(0)' }
  			},
  			'glow-pulse': {
  				'0%': { boxShadow: '0 0 0 rgba(0,0,0,0)' },
  				'60%': { boxShadow: '0 0 30px rgba(124,58,237,0.3)' },
  				'100%': { boxShadow: '0 0 0 rgba(0,0,0,0)' }
  			},
  			shimmer: {
  				'0%': { backgroundPosition: '-200% 0' },
  				'100%': { backgroundPosition: '200% 0' }
  			},
  			morph: {
  				'0%, 100%': { borderRadius: '60% 40% 30% 70% / 60% 30% 70% 40%' },
  				'50%': { borderRadius: '30% 60% 70% 40% / 50% 60% 30% 60%' }
  			},
  			'gradient-shift': {
  				'0%, 100%': { backgroundPosition: '0% 50%' },
  				'50%': { backgroundPosition: '100% 50%' }
  			},
  			float: {
  				'0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
  				'50%': { transform: 'translateY(-20px) rotate(2deg)' }
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out',
  			// NEBULA AURORA ANIMATIONS
  			'aurora-flow': 'aurora-flow 8s ease infinite',
  			'nebula-pulse': 'nebula-pulse 4s ease-in-out infinite',
  			'cosmic-drift': 'cosmic-drift 20s linear infinite',
  			'plasma-morph': 'plasma-morph 8s ease-in-out infinite',
  			'bioluminescent': 'bioluminescent 3s ease-in-out infinite',
  			'crystalline': 'crystalline 3s ease-in-out infinite',
  			'holographic': 'holographic 6s ease infinite',
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
  			float: 'float 6s ease-in-out infinite'
  		},
  		transitionDuration: {
  			fast: '150ms',
  			base: '250ms',
  			slow: '400ms',
  			xl: '600ms'
  		},
  		transitionTimingFunction: {
  			standard: 'cubic-bezier(0.4, 0, 0.2, 1)',
  			enter: 'cubic-bezier(0.16, 1, 0.3, 1)',
  			exit: 'cubic-bezier(0.7, 0, 0.84, 0)',
  			bounce: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)'
  		},
  		zIndex: {
  			'hide': '-1',
  			'base': '0',
  			'raised': '1',
  			'dropdown': '10',
  			'sticky': '20',
  			'header': '30',
  			'overlay': '40',
  			'modal': '50',
  			'popover': '60',
  			'toast': '70',
  			'tooltip': '80',
  			'max': '9999',
  		}
  	}
  },
  plugins: [
    require('tailwindcss-animate'),
    require('tailwindcss-rtl'),
  ],
}
