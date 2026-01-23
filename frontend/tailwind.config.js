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
  			stratum: {
  				'50': '#faf5ff',
  				'100': '#f3e8ff',
  				'200': '#e9d5ff',
  				'300': '#d8b4fe',
  				'400': '#A78BFA',      // 2026: More electric violet hover
  				'500': '#8B5CF6',      // 2026: Primary brand electric violet
  				'600': '#7C3AED',      // 2026: Active/pressed
  				'700': '#6D28D9',
  				'800': '#5B21B6',
  				'900': '#4C1D95',
  				'950': '#2E1065'
  			},
  			cyan: {
  				'50': '#ecfeff',
  				'100': '#cffafe',
  				'200': '#a5f3fc',
  				'300': '#67e8f9',
  				'400': '#22d3ee',
  				'500': '#00D4FF',      // 2026: Electric cyan
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
  			success: '#00FF88',        // 2026: Neon green
  			warning: '#FFB800',        // 2026: Amber glow
  			danger: '#FF4757',         // 2026: Neon red
  			info: '#00B4FF',           // 2026: Electric blue
  			insight: '#FF6B6B',        // 2026: Coral accent
  			surface: {
  				primary: '#020204',    // 2026: Near-black with blue hint
  				secondary: '#0A0A0F',  // 2026: Subtle blue undertone
  				tertiary: '#12121A',   // 2026: Elevated with depth
  				elevated: '#1A1A26'    // 2026: Cards/dialogs
  			},
  			'text-primary': '#FAFAFA',     // 2026: Slightly softer white
  			'text-secondary': '#94A3B8',   // 2026: Cooler gray
  			'text-muted': '#64748B',       // 2026: Slate muted
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
  			xl: '20px'
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
  			]
  		},
  		fontSize: {
  			// Base typography scale
  			micro: ['10px', { lineHeight: '1.4', fontWeight: '400' }],
  			meta: ['12px', { lineHeight: '1.5', fontWeight: '400' }],
  			body: ['14px', { lineHeight: '1.55', fontWeight: '400' }],
  			'body-lg': ['16px', { lineHeight: '1.6', fontWeight: '400' }],
  			h3: ['18px', { lineHeight: '1.35', fontWeight: '600' }],
  			h2: ['22px', { lineHeight: '1.3', fontWeight: '600' }],
  			h1: ['28px', { lineHeight: '1.25', fontWeight: '700' }],
  			// Display typography for landing pages
  			'display-sm': ['32px', { lineHeight: '1.2', fontWeight: '700', letterSpacing: '-0.02em' }],
  			'display': ['40px', { lineHeight: '1.15', fontWeight: '700', letterSpacing: '-0.02em' }],
  			'display-lg': ['48px', { lineHeight: '1.1', fontWeight: '800', letterSpacing: '-0.025em' }],
  			'display-xl': ['56px', { lineHeight: '1.05', fontWeight: '800', letterSpacing: '-0.03em' }],
  			'display-2xl': ['72px', { lineHeight: '1', fontWeight: '800', letterSpacing: '-0.03em' }],
  		},
  		boxShadow: {
  			'glow-sm': '0 0 12px rgba(139, 92, 246, 0.2)',      // 2026: Electric violet glow
  			glow: '0 0 20px rgba(139, 92, 246, 0.4)',           // 2026: Primary glow
  			'glow-lg': '0 0 32px rgba(139, 92, 246, 0.5)',      // 2026: Large glow
  			'glow-insight': '0 0 20px rgba(255, 107, 107, 0.4)', // 2026: Coral glow
				'glow-cyan': '0 0 20px rgba(0, 212, 255, 0.4)',         // 2026: Cyan glow
  			card: '0 4px 12px rgba(0, 0, 0, 0.20)',
  			'card-hover': '0 10px 30px rgba(0, 0, 0, 0.28)'
  		},
  		spacing: {
  			// Base spacing scale (4px increments)
  			'1': '4px',
  			'2': '8px',
  			'3': '12px',
  			'4': '16px',
  			'5': '24px',
  			'6': '32px',
  			'7': '48px',
  			'8': '64px',
  			// Section spacing for landing pages
  			'section-sm': '64px',
  			'section': '96px',
  			'section-lg': '128px',
  			'section-xl': '160px',
  			// Container max-widths
  			'container-sm': '640px',
  			'container-md': '768px',
  			'container-lg': '1024px',
  			'container-xl': '1280px',
  			'container-2xl': '1400px',
  		},
  		backgroundImage: {
  			'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
  			'gradient-stratum': 'linear-gradient(135deg, #8B5CF6 0%, #00D4FF 50%, #FF6B6B 100%)', // 2026: Holographic
  			'gradient-stratum-soft': 'linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(0, 212, 255, 0.05) 100%)'
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			},
  			'slide-in-from-right': {
  				'0%': {
  					transform: 'translateX(100%)'
  				},
  				'100%': {
  					transform: 'translateX(0)'
  				}
  			},
  			'slide-in-from-left': {
  				'0%': {
  					transform: 'translateX(-100%)'
  				},
  				'100%': {
  					transform: 'translateX(0)'
  				}
  			},
  			'fade-in': {
  				'0%': {
  					opacity: 0
  				},
  				'100%': {
  					opacity: 1
  				}
  			},
  			'fade-up': {
  				'0%': {
  					opacity: 0,
  					transform: 'translateY(8px)'
  				},
  				'100%': {
  					opacity: 1,
  					transform: 'translateY(0)'
  				}
  			},
  			'scale-in': {
  				'0%': {
  					opacity: 0,
  					transform: 'scale(0.95)'
  				},
  				'100%': {
  					opacity: 1,
  					transform: 'scale(1)'
  				}
  			},
  			'delta-pop': {
  				'0%': {
  					transform: 'scale(0.98)',
  					opacity: 0.6
  				},
  				'100%': {
  					transform: 'scale(1)',
  					opacity: 1
  				}
  			},
  			sweep: {
  				'0%': {
  					opacity: 0,
  					transform: 'translateX(-12px)'
  				},
  				'100%': {
  					opacity: 1,
  					transform: 'translateX(0)'
  				}
  			},
  			'glow-pulse': {
  				'0%': {
  					boxShadow: '0 0 0 rgba(0,0,0,0)'
  				},
  				'60%': {
  					boxShadow: '0 0 22px rgba(168,85,247,0.18)'
  				},
  				'100%': {
  					boxShadow: '0 0 0 rgba(0,0,0,0)'
  				}
  			},
  			'ember-glow': {
  				'0%': {
  					boxShadow: '0 0 0 rgba(0,0,0,0)'
  				},
  				'50%': {
  					boxShadow: '0 0 18px rgba(249,115,22,0.22)'
  				},
  				'100%': {
  					boxShadow: '0 0 0 rgba(0,0,0,0)'
  				}
  			},
  			'micro-shake': {
  				'0%, 100%': {
  					transform: 'translateX(0)'
  				},
  				'20%': {
  					transform: 'translateX(-2px)'
  				},
  				'40%': {
  					transform: 'translateX(2px)'
  				},
  				'60%': {
  					transform: 'translateX(-1px)'
  				},
  				'80%': {
  					transform: 'translateX(1px)'
  				}
  			},
  			shimmer: {
  				'0%': {
  					backgroundPosition: '-200% 0'
  				},
  				'100%': {
  					backgroundPosition: '200% 0'
  				}
  			},
  			// 2026 Theme animations
  			morph: {
  				'0%, 100%': {
  					borderRadius: '60% 40% 30% 70% / 60% 30% 70% 40%'
  				},
  				'50%': {
  					borderRadius: '30% 60% 70% 40% / 50% 60% 30% 60%'
  				}
  			},
  			'gradient-shift': {
  				'0%, 100%': {
  					backgroundPosition: '0% 50%'
  				},
  				'50%': {
  					backgroundPosition: '100% 50%'
  				}
  			},
  			float: {
  				'0%, 100%': {
  					transform: 'translateY(0) rotate(0deg)'
  				},
  				'50%': {
  					transform: 'translateY(-20px) rotate(2deg)'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out',
  			'slide-in': 'slide-in-from-right 0.3s ease-out',
  			'slide-in-left': 'slide-in-from-left 0.3s ease-out',
  			'fade-in': 'fade-in 0.18s cubic-bezier(0.2, 0.8, 0.2, 1)',
  			enter: 'fade-up 0.28s cubic-bezier(0.16, 1, 0.3, 1) both',
  			delta: 'delta-pop 0.18s cubic-bezier(0.2, 0.8, 0.2, 1) both',
  			sweep: 'sweep 0.28s cubic-bezier(0.16, 1, 0.3, 1) both',
  			'glow-pulse': 'glow-pulse 0.42s cubic-bezier(0.16, 1, 0.3, 1) both',
  			insight: 'ember-glow 0.42s cubic-bezier(0.16, 1, 0.3, 1) both',
  			critical: 'micro-shake 0.18s cubic-bezier(0.2, 0.8, 0.2, 1) both',
  			'scale-in': 'scale-in 0.18s cubic-bezier(0.2, 0.8, 0.2, 1)',
  			shimmer: 'shimmer 0.9s linear infinite',
  			// 2026 Theme animations
  			morph: 'morph 8s ease-in-out infinite',
  			'gradient-shift': 'gradient-shift 8s ease infinite',
  			float: 'float 6s ease-in-out infinite'
  		},
  		transitionDuration: {
  			fast: '120ms',
  			base: '180ms',
  			slow: '280ms',
  			xl: '420ms'
  		},
  		transitionTimingFunction: {
  			standard: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
  			enter: 'cubic-bezier(0.16, 1, 0.3, 1)',
  			exit: 'cubic-bezier(0.7, 0, 0.84, 0)'
  		},
  		// Z-index scale for consistent layering
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
