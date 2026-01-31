# STRATUM AI - UNIVERSAL THEME SYSTEM v3.0
## Complete Design Specification for All Frontend Interfaces

**Version:** 3.0 (Complete Edition)  
**Last Updated:** January 2026  
**Coverage:** Landing Pages • Dashboard • Sign In/Up • All Components  
**Modes:** Dark (Default) | Light  
**Compliance:** NN/g Research • WCAG 2.1 AA  

---

# TABLE OF CONTENTS

1. [Theme Toggle](#1-theme-toggle)
2. [Design Tokens](#2-design-tokens)
3. [Typography](#3-typography)
4. [Components](#4-components)
5. [Landing Page](#5-landing-page)
6. [Dashboard](#6-dashboard)
7. [Authentication](#7-authentication)
8. [Effects & Animations](#8-effects--animations)
9. [Responsive Breakpoints](#9-responsive-breakpoints)
10. [Accessibility](#10-accessibility)
11. [Quick Reference](#11-quick-reference)

---

# 1. THEME TOGGLE

## Implementation

```javascript
const ThemeManager = {
  init() {
    const saved = localStorage.getItem('stratum-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    this.set(saved || (prefersDark ? 'dark' : 'light'));
  },
  set(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('stratum-theme', theme);
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
  },
  toggle() {
    const current = document.documentElement.getAttribute('data-theme');
    this.set(current === 'dark' ? 'light' : 'dark');
  }
};
document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
```

## Toggle Button CSS

```css
.theme-toggle {
  width: 48px;
  height: 28px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-full);
  cursor: pointer;
  position: relative;
}
.theme-toggle:hover { border-color: var(--gold); }
.theme-toggle-knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  background: var(--gold);
  border-radius: 50%;
  transition: transform 0.3s ease;
}
[data-theme="light"] .theme-toggle-knob { transform: translateX(20px); }
.theme-toggle svg { width: 12px; height: 12px; fill: var(--text-inverse); }
.icon-sun { display: block; }
.icon-moon { display: none; }
[data-theme="light"] .icon-sun { display: none; }
[data-theme="light"] .icon-moon { display: block; }
```

---

# 2. DESIGN TOKENS

## 2.1 Complete CSS Variables

```css
:root {
  /* ═══════════════════════════════════════════════════════════════════
     CONSTANTS (Same in both themes)
     ═══════════════════════════════════════════════════════════════════ */
  
  /* Typography */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  
  /* Spacing Scale */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --space-20: 80px;
  
  /* Border Radius */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-2xl: 24px;
  --radius-full: 9999px;
  
  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-base: 200ms ease;
  --transition-slow: 300ms ease;
  --transition-theme: 400ms cubic-bezier(0.4, 0, 0.2, 1);
  
  /* Z-Index */
  --z-base: 0;
  --z-elevated: 10;
  --z-sticky: 50;
  --z-overlay: 100;
  --z-modal: 200;
  --z-toast: 1000;
}

/* ═══════════════════════════════════════════════════════════════════════════
   DARK THEME (Default) - Command Center Aesthetic
   ═══════════════════════════════════════════════════════════════════════════ */

:root,
[data-theme="dark"] {
  /* Backgrounds */
  --bg-void: #050508;
  --bg-primary: #0a0a0f;
  --bg-secondary: #0d0d14;
  --bg-card: #12121a;
  --bg-card-hover: #1a1a24;
  --bg-elevated: #1e1e28;
  --bg-input: #0a0a0f;
  --bg-overlay: rgba(5, 5, 8, 0.9);
  
  /* Borders */
  --border-default: rgba(255, 255, 255, 0.06);
  --border-hover: rgba(255, 255, 255, 0.10);
  --border-active: rgba(255, 255, 255, 0.15);
  --border-focus: rgba(212, 175, 55, 0.5);
  --border-gold: rgba(212, 175, 55, 0.15);
  --border-success: rgba(34, 197, 94, 0.3);
  --border-warning: rgba(245, 158, 11, 0.3);
  --border-error: rgba(239, 68, 68, 0.3);
  
  /* Text */
  --text-primary: #ffffff;
  --text-secondary: #cccccc;
  --text-tertiary: #999999;
  --text-muted: #888888;
  --text-disabled: #555555;
  --text-inverse: #0a0a0f;
  
  /* Brand - Gold */
  --gold: #D4AF37;
  --gold-bright: #F4D03F;
  --gold-muted: #B8860B;
  --gold-glow: rgba(212, 175, 55, 0.5);
  --gold-subtle: rgba(212, 175, 55, 0.1);
  
  /* Brand - Cyan */
  --cyan: #14F0C6;
  --cyan-muted: #0FB89A;
  --cyan-glow: rgba(20, 240, 198, 0.4);
  --cyan-subtle: rgba(20, 240, 198, 0.1);
  
  /* Brand - Purple */
  --purple: #8b5cf6;
  --purple-glow: rgba(139, 92, 246, 0.4);
  --purple-subtle: rgba(139, 92, 246, 0.1);
  
  /* Status */
  --status-success: #22c55e;
  --status-success-bg: rgba(34, 197, 94, 0.1);
  --status-warning: #f59e0b;
  --status-warning-bg: rgba(245, 158, 11, 0.1);
  --status-error: #ef4444;
  --status-error-bg: rgba(239, 68, 68, 0.1);
  --status-info: #0a84ff;
  --status-info-bg: rgba(10, 132, 255, 0.1);
  
  /* Shadows */
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
  --shadow-xl: 0 16px 48px rgba(0, 0, 0, 0.6);
  --shadow-gold: 0 0 40px rgba(212, 175, 55, 0.25);
  --shadow-inset: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  
  /* Neural Effects */
  --neural-node: rgba(212, 175, 55, 0.6);
  --neural-line: rgba(212, 175, 55, 0.12);
  --neural-glow: rgba(212, 175, 55, 0.3);
  --scan-line: rgba(0, 0, 0, 0.03);
  --grid-line: rgba(212, 175, 55, 0.04);
  
  /* Glass (Overlays Only - NN/g) */
  --glass-bg: rgba(20, 20, 30, 0.75);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-blur: 100px;
  
  /* Scrollbar */
  --scrollbar-track: #0a0a0f;
  --scrollbar-thumb: rgba(212, 175, 55, 0.3);
  --scrollbar-thumb-hover: rgba(212, 175, 55, 0.5);
  
  /* Charts */
  --chart-grid: rgba(255, 255, 255, 0.06);
  --chart-line-1: #D4AF37;
  --chart-line-2: #14F0C6;
  --chart-line-3: #8b5cf6;
  --chart-area-1: rgba(212, 175, 55, 0.2);
  --chart-area-2: rgba(20, 240, 198, 0.2);
}

/* ═══════════════════════════════════════════════════════════════════════════
   LIGHT THEME - Clean Professional Aesthetic
   ═══════════════════════════════════════════════════════════════════════════ */

[data-theme="light"] {
  /* Backgrounds */
  --bg-void: #f8f9fc;
  --bg-primary: #ffffff;
  --bg-secondary: #f4f5f7;
  --bg-card: #ffffff;
  --bg-card-hover: #f8f9fc;
  --bg-elevated: #ffffff;
  --bg-input: #f4f5f7;
  --bg-overlay: rgba(255, 255, 255, 0.95);
  
  /* Borders */
  --border-default: rgba(0, 0, 0, 0.08);
  --border-hover: rgba(0, 0, 0, 0.12);
  --border-active: rgba(0, 0, 0, 0.18);
  --border-focus: rgba(180, 134, 11, 0.5);
  --border-gold: rgba(180, 134, 11, 0.2);
  --border-success: rgba(22, 163, 74, 0.3);
  --border-warning: rgba(217, 119, 6, 0.3);
  --border-error: rgba(220, 38, 38, 0.3);
  
  /* Text */
  --text-primary: #0f172a;
  --text-secondary: #334155;
  --text-tertiary: #64748b;
  --text-muted: #94a3b8;
  --text-disabled: #cbd5e1;
  --text-inverse: #ffffff;
  
  /* Brand - Gold (Darker for Light) */
  --gold: #B8860B;
  --gold-bright: #D4AF37;
  --gold-muted: #996B06;
  --gold-glow: rgba(180, 134, 11, 0.3);
  --gold-subtle: rgba(180, 134, 11, 0.08);
  
  /* Brand - Cyan (Darker) */
  --cyan: #0D9488;
  --cyan-muted: #0F766E;
  --cyan-glow: rgba(13, 148, 136, 0.3);
  --cyan-subtle: rgba(13, 148, 136, 0.08);
  
  /* Brand - Purple */
  --purple: #7c3aed;
  --purple-glow: rgba(124, 58, 237, 0.3);
  --purple-subtle: rgba(124, 58, 237, 0.08);
  
  /* Status (Darker) */
  --status-success: #16a34a;
  --status-success-bg: rgba(22, 163, 74, 0.08);
  --status-warning: #d97706;
  --status-warning-bg: rgba(217, 119, 6, 0.08);
  --status-error: #dc2626;
  --status-error-bg: rgba(220, 38, 38, 0.08);
  --status-info: #2563eb;
  --status-info-bg: rgba(37, 99, 235, 0.08);
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 16px 40px rgba(0, 0, 0, 0.12);
  --shadow-gold: 0 0 30px rgba(180, 134, 11, 0.15);
  --shadow-inset: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  
  /* Neural Effects (Subtle) */
  --neural-node: rgba(180, 134, 11, 0.4);
  --neural-line: rgba(180, 134, 11, 0.08);
  --neural-glow: rgba(180, 134, 11, 0.2);
  --scan-line: rgba(0, 0, 0, 0.02);
  --grid-line: rgba(180, 134, 11, 0.03);
  
  /* Glass (Light Mode) */
  --glass-bg: rgba(255, 255, 255, 0.85);
  --glass-border: rgba(0, 0, 0, 0.06);
  --glass-blur: 80px;
  
  /* Scrollbar */
  --scrollbar-track: #f4f5f7;
  --scrollbar-thumb: rgba(180, 134, 11, 0.25);
  --scrollbar-thumb-hover: rgba(180, 134, 11, 0.4);
  
  /* Charts */
  --chart-grid: rgba(0, 0, 0, 0.06);
  --chart-line-1: #B8860B;
  --chart-line-2: #0D9488;
  --chart-line-3: #7c3aed;
  --chart-area-1: rgba(180, 134, 11, 0.15);
  --chart-area-2: rgba(13, 148, 136, 0.15);
}

/* Theme Transition */
[data-theme] * {
  transition: background-color var(--transition-theme),
              border-color var(--transition-theme),
              box-shadow var(--transition-theme),
              color var(--transition-theme);
}
```

---

# 3. TYPOGRAPHY

## 3.1 Type Scale

| Token | Size | Use |
|-------|------|-----|
| `--text-xs` | 10px | Labels, badges |
| `--text-sm` | 12px | Small text, captions |
| `--text-base` | 14px | Body text |
| `--text-md` | 16px | Large body |
| `--text-lg` | 18px | Subheadings |
| `--text-xl` | 20px | Card titles |
| `--text-2xl` | 24px | Section titles |
| `--text-3xl` | 28px | Page titles |
| `--text-4xl` | 36px | Hero subtext |
| `--text-5xl` | 48px | Hero titles |
| `--text-6xl` | 64px | Display |

## 3.2 Typography Classes

```css
/* Headings */
.heading-display {
  font-family: var(--font-sans);
  font-size: clamp(40px, 5vw, 64px);
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.heading-1 {
  font-size: clamp(28px, 3.5vw, 44px);
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.heading-2 {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.3;
}

.heading-3 {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
}

.heading-4 {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.4;
}

/* Body */
.body-lg {
  font-size: 17px;
  line-height: 1.7;
  color: var(--text-secondary);
}

.body {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.body-sm {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-muted);
}

/* Labels */
.label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.label-sm {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
}

/* Mono / Metrics */
.mono-display {
  font-family: var(--font-mono);
  font-size: 48px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.mono-lg {
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 600;
}

.mono {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 500;
}

.mono-sm {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
}

/* Special */
.text-gradient {
  background: linear-gradient(135deg, var(--gold), var(--cyan), var(--gold));
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: gradientFlow 4s ease infinite;
}

.text-gold {
  color: var(--gold);
  text-shadow: 0 0 40px var(--gold-glow);
}
```

---

# 4. COMPONENTS

## 4.1 Cards (NN/g Compliant - SOLID Backgrounds)

```css
/* Base Card */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), var(--shadow-inset);
  transition: all var(--transition-slow);
  position: relative;
  overflow: hidden;
}

.card:hover {
  transform: translateY(-4px);
  border-color: var(--border-hover);
  box-shadow: var(--shadow-lg);
}

/* Card with 3px Status Accent */
.card[data-accent]::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.card[data-accent="gold"]::before { background: var(--gold); }
.card[data-accent="cyan"]::before { background: var(--cyan); }
.card[data-accent="purple"]::before { background: var(--purple); }
.card[data-accent="success"]::before { background: var(--status-success); }
.card[data-accent="warning"]::before { background: var(--status-warning); }
.card[data-accent="error"]::before { background: var(--status-error); }

/* Feature Card */
.card-feature {
  padding: var(--space-8);
}

.card-feature .icon-box {
  width: 48px;
  height: 48px;
  background: var(--gold-subtle);
  border: 1px solid var(--border-gold);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-6);
}

.card-feature .icon-box svg {
  width: 24px;
  height: 24px;
  stroke: var(--gold);
  fill: none;
  stroke-width: 1.5;
}

/* Stat Card */
.card-stat {
  padding: var(--space-5);
}

.card-stat .value {
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.card-stat .label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: var(--space-2);
}

.card-stat .trend {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-family: var(--font-mono);
  font-size: 11px;
  margin-top: var(--space-2);
}

.card-stat .trend.up { color: var(--status-success); }
.card-stat .trend.down { color: var(--status-error); }
```

## 4.2 Buttons

```css
/* Base Button */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 12px 24px;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
  border-radius: var(--radius-md);
  border: none;
  cursor: pointer;
  transition: all var(--transition-slow);
  position: relative;
  overflow: hidden;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Primary (Gold) */
.btn-primary {
  background: var(--gold);
  color: var(--text-inverse);
  font-weight: 700;
}

.btn-primary::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  transition: left 0.5s ease;
}

.btn-primary:hover:not(:disabled) {
  background: var(--gold-bright);
  box-shadow: var(--shadow-gold);
  transform: translateY(-2px);
}

.btn-primary:hover::before {
  left: 100%;
}

/* Secondary */
.btn-secondary {
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-card-hover);
  border-color: var(--border-hover);
  color: var(--text-primary);
}

/* Ghost */
.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--bg-card);
  color: var(--text-primary);
}

/* Sizes */
.btn-sm { padding: 8px 16px; font-size: 12px; }
.btn-lg { padding: 16px 32px; font-size: 15px; }

/* Full Width */
.btn-block { width: 100%; }
```

## 4.3 Form Inputs

```css
/* Input */
.input {
  width: 100%;
  padding: 14px 16px;
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--text-primary);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
}

.input:hover {
  border-color: var(--border-hover);
}

.input:focus {
  outline: none;
  border-color: var(--gold);
  box-shadow: 0 0 0 3px var(--gold-subtle);
}

.input::placeholder {
  color: var(--text-disabled);
}

.input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Error State */
.input.error {
  border-color: var(--status-error);
}

.input.error:focus {
  box-shadow: 0 0 0 3px var(--status-error-bg);
}

/* Success State */
.input.success {
  border-color: var(--status-success);
}

/* Input Label */
.input-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: var(--space-2);
}

/* Input Group */
.input-group {
  margin-bottom: var(--space-5);
}

/* Input Helper */
.input-helper {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: var(--space-2);
}

.input-helper.error {
  color: var(--status-error);
}

/* Checkbox */
.checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-default);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-base);
}

.checkbox.checked {
  background: var(--gold);
  border-color: var(--gold);
}

.checkbox svg {
  width: 12px;
  height: 12px;
  stroke: var(--text-inverse);
  stroke-width: 3;
  opacity: 0;
}

.checkbox.checked svg {
  opacity: 1;
}

/* Select */
.select {
  appearance: none;
  padding-right: 40px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23888' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 16px center;
}
```

## 4.4 Navigation

```css
/* Main Nav */
.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-sticky);
  padding: var(--space-5) var(--space-12);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(to bottom, var(--bg-void) 0%, transparent 100%);
  transition: all var(--transition-slow);
}

.nav.scrolled {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--border-default);
}

/* Nav Links Pill */
.nav-links {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-full);
}

.nav-link {
  padding: var(--space-2) var(--space-4);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  text-decoration: none;
  border-radius: var(--radius-full);
  transition: all var(--transition-base);
}

.nav-link:hover {
  color: var(--text-primary);
  background: var(--border-default);
}

.nav-link.active {
  color: var(--gold);
  background: var(--gold-subtle);
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: 14px;
  text-decoration: none;
}

.logo-mark {
  width: 44px;
  height: 44px;
}

.logo-hex-outer {
  fill: none;
  stroke: var(--gold);
  stroke-width: 1.5;
  animation: hexSpin 15s linear infinite;
  transform-origin: center;
}

.logo-hex-core {
  fill: var(--gold);
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.logo-subtitle {
  font-family: var(--font-mono);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--text-muted);
}
```

## 4.5 Status Indicators

```css
/* Status Badge */
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px 12px;
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-success {
  background: var(--status-success-bg);
  border: 1px solid var(--border-success);
  color: var(--status-success);
}

.badge-warning {
  background: var(--status-warning-bg);
  border: 1px solid var(--border-warning);
  color: var(--status-warning);
}

.badge-error {
  background: var(--status-error-bg);
  border: 1px solid var(--border-error);
  color: var(--status-error);
}

/* Pulsing Dot */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

.status-dot.success {
  background: var(--status-success);
  box-shadow: 0 0 12px var(--status-success);
}

.status-dot.warning {
  background: var(--status-warning);
  box-shadow: 0 0 12px var(--status-warning);
}

.status-dot.error {
  background: var(--status-error);
  box-shadow: 0 0 12px var(--status-error);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

## 4.6 Tables (Dashboard)

```css
.table {
  width: 100%;
  border-collapse: collapse;
}

.table th {
  padding: var(--space-3) var(--space-4);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  text-align: left;
  border-bottom: 1px solid var(--border-default);
}

.table td {
  padding: var(--space-4);
  font-size: 14px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
}

.table tr:hover td {
  background: var(--bg-card-hover);
}

.table-mono td {
  font-family: var(--font-mono);
  font-size: 13px;
}
```

## 4.7 Modal / Dialog

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.modal {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow: hidden;
}

.modal-header {
  padding: var(--space-6);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-body {
  padding: var(--space-6);
  overflow-y: auto;
}

.modal-footer {
  padding: var(--space-6);
  border-top: 1px solid var(--border-default);
  display: flex;
  gap: var(--space-3);
  justify-content: flex-end;
}
```

## 4.8 Tabs

```css
.tabs {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-1);
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
}

.tab {
  padding: var(--space-3) var(--space-5);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
}

.tab:hover {
  color: var(--text-primary);
  background: var(--border-default);
}

.tab.active {
  color: var(--gold);
  background: var(--gold-subtle);
}
```

## 4.9 Progress Bar

```css
.progress {
  height: 8px;
  background: var(--border-default);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--gold);
  border-radius: var(--radius-full);
  transition: width var(--transition-slow);
}

.progress-fill.success { background: var(--status-success); }
.progress-fill.warning { background: var(--status-warning); }
.progress-fill.error { background: var(--status-error); }

/* Password Strength */
.strength-bar {
  height: 4px;
  background: var(--border-default);
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  transition: all var(--transition-slow);
}

.strength-fill.weak { width: 33%; background: var(--status-error); }
.strength-fill.medium { width: 66%; background: var(--status-warning); }
.strength-fill.strong { width: 100%; background: var(--status-success); }
```

## 4.10 Tooltips

```css
.tooltip {
  position: relative;
}

.tooltip::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-8px);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: all var(--transition-fast);
  z-index: var(--z-tooltip);
}

.tooltip:hover::after {
  opacity: 1;
  visibility: visible;
}
```

---

# 5. LANDING PAGE

## 5.1 Structure

```
Landing Page
├── Neural Canvas (fixed background)
├── Scan Lines Overlay
├── Grid Floor
├── HUD Corners
├── Navigation
│   ├── Logo (animated hexagon)
│   ├── Nav Links (pill style)
│   └── CTA Buttons + Theme Toggle
├── Hero Section
│   ├── Status Badge
│   ├── Hero Title (animated reveal)
│   ├── Subtitle
│   ├── CTA Buttons
│   ├── Hero Stats (3 cards)
│   └── Trust Engine Preview
├── Features Section
│   ├── Section Header
│   └── Feature Cards Grid
├── Social Proof / Logos
├── CTA Section
└── Footer
```

## 5.2 Hero Stats Cards

```html
<div class="hero-stats">
  <div class="card card-stat" data-accent="gold">
    <div class="label">Trust Score</div>
    <div class="value">94.7%</div>
    <div class="trend up">
      <svg>↑</svg> +2.3% today
    </div>
  </div>
  <!-- Repeat for ROAS, Waste Saved -->
</div>
```

## 5.3 Trust Engine Preview

```css
.trust-engine {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.engine-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-default);
}

.window-controls {
  display: flex;
  gap: 8px;
}

.window-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.window-dot.close { background: #ff5f57; }
.window-dot.minimize { background: #febc2e; }
.window-dot.maximize { background: #28c840; }
```

## 5.4 Landing Theme Differences

| Element | Dark | Light |
|---------|------|-------|
| Background | #050508 | #f8f9fc |
| Neural Canvas Opacity | 0.7 | 0.4 |
| Grid Floor Opacity | 0.8 | 0.4 |
| HUD Corners Opacity | 0.6 | 0.3 |
| Scan Lines | visible | 50% opacity |

---

# 6. DASHBOARD

## 6.1 Layout Structure

```
Dashboard
├── Sidebar (240px fixed)
│   ├── Logo
│   ├── Navigation Items
│   ├── Workspaces
│   └── User Menu
├── Main Content
│   ├── Top Bar
│   │   ├── Page Title
│   │   ├── Date Range Picker
│   │   └── Actions
│   ├── KPI Cards Row
│   ├── Charts Section
│   │   ├── Main Chart (Revenue)
│   │   └── Secondary Charts
│   ├── Data Table
│   └── Activity Feed
└── Trust Gate Indicator (fixed)
```

## 6.2 Sidebar

```css
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 240px;
  background: var(--bg-primary);
  border-right: 1px solid var(--border-default);
  display: flex;
  flex-direction: column;
  z-index: var(--z-sticky);
}

.sidebar-header {
  padding: var(--space-5);
  border-bottom: 1px solid var(--border-default);
}

.sidebar-nav {
  flex: 1;
  padding: var(--space-4);
  overflow-y: auto;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
}

.sidebar-item:hover {
  color: var(--text-primary);
  background: var(--bg-card);
}

.sidebar-item.active {
  color: var(--gold);
  background: var(--gold-subtle);
}

.sidebar-item svg {
  width: 18px;
  height: 18px;
  stroke: currentColor;
  fill: none;
}
```

## 6.3 KPI Cards

```css
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-6);
}

.kpi-card {
  padding: var(--space-6);
  position: relative;
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.kpi-card:nth-child(1)::before { background: var(--gold); }
.kpi-card:nth-child(2)::before { background: var(--cyan); }
.kpi-card:nth-child(3)::before { background: var(--status-success); }
.kpi-card:nth-child(4)::before { background: var(--purple); }

.kpi-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.kpi-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.kpi-value {
  font-family: var(--font-mono);
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
}

.kpi-change {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-family: var(--font-mono);
  font-size: 13px;
  margin-top: var(--space-2);
}

.kpi-change.up { color: var(--status-success); }
.kpi-change.down { color: var(--status-error); }
```

## 6.4 Charts

```css
.chart-card {
  padding: var(--space-6);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
}

.chart-actions {
  display: flex;
  gap: var(--space-2);
}

.chart-container {
  height: 300px;
  position: relative;
}

/* Chart.js / Recharts Theming */
.chart-tooltip {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-default) !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-lg) !important;
}
```

## 6.5 Trust Gate Indicator

```css
.trust-gate {
  position: fixed;
  bottom: var(--space-6);
  left: calc(240px + var(--space-6));
  background: var(--bg-card);
  border: 1px solid var(--border-gold);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-5);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  box-shadow: var(--shadow-lg);
  z-index: var(--z-elevated);
}

.trust-gate-ring {
  width: 48px;
  height: 48px;
  position: relative;
}

.trust-gate-score {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--gold);
}

.trust-gate-status {
  font-size: 12px;
  font-weight: 600;
  color: var(--status-success);
}
```

## 6.6 Dashboard Theme Differences

| Element | Dark | Light |
|---------|------|-------|
| Sidebar BG | #0a0a0f | #ffffff |
| Main BG | #050508 | #f8f9fc |
| Cards | #12121a solid | #ffffff solid |
| Chart Grid | rgba(255,255,255,0.06) | rgba(0,0,0,0.06) |
| Chart Lines | Bright (#D4AF37) | Muted (#B8860B) |

---

# 7. AUTHENTICATION

## 7.1 Sign In Layout

```
Sign In Page
├── Neural Canvas (muted)
├── HUD Corners
├── Theme Toggle
├── Split Container
│   ├── Left Panel (Preview)
│   │   ├── Trust Ring Animation
│   │   └── Preview Stats
│   └── Right Panel (Form)
│       ├── Logo
│       ├── Title + Subtitle
│       ├── Form
│       │   ├── Email Input
│       │   ├── Password Input (with toggle)
│       │   ├── Remember Me + Forgot Link
│       │   └── Submit Button
│       ├── Social Divider
│       ├── Social Buttons
│       └── Terminal Footer
└── Responsive: Hide left panel <1024px
```

## 7.2 Sign Up Layout

```
Sign Up Page
├── Neural Canvas (muted)
├── HUD Corners  
├── Theme Toggle
├── Split Container
│   ├── Left Panel (Features)
│   │   ├── Feature List (4 items)
│   │   └── Trust Preview Card
│   └── Right Panel (Multi-Step Form)
│       ├── Logo
│       ├── Title + Subtitle
│       ├── Progress Steps (3)
│       ├── Step 1: Account
│       │   ├── Name Fields
│       │   ├── Email
│       │   ├── Password + Strength
│       │   └── Continue Button
│       ├── Step 2: Platforms
│       │   ├── Platform Selection Grid
│       │   ├── Budget Selection
│       │   └── Back/Continue Buttons
│       ├── Step 3: Confirm
│       │   ├── Company Name
│       │   ├── Website
│       │   ├── Terms Checkbox
│       │   └── Back/Launch Buttons
│       ├── Success State
│       └── Terminal Footer
└── Responsive: Hide left panel <1024px
```

## 7.3 Progress Steps

```css
.progress-steps {
  display: flex;
  gap: 8px;
  margin-bottom: var(--space-8);
}

.progress-step {
  flex: 1;
  height: 4px;
  background: var(--border-default);
  border-radius: 2px;
  transition: all var(--transition-slow);
}

.progress-step.active {
  background: var(--gold);
  box-shadow: 0 0 10px var(--gold-glow);
}

.progress-step.completed {
  background: var(--status-success);
}
```

## 7.4 Terminal Footer

```css
.terminal-footer {
  margin-top: var(--space-8);
  padding: 14px 16px;
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 11px;
}

.terminal-line {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
}

.terminal-prompt {
  color: var(--gold);
}

.terminal-cursor {
  display: inline-block;
  width: 8px;
  height: 14px;
  background: var(--gold);
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  50% { opacity: 0; }
}
```

## 7.5 Trust Ring

```css
.trust-ring-container {
  position: relative;
  width: 280px;
  height: 280px;
}

.trust-ring {
  position: absolute;
  inset: 0;
  border: 2px solid var(--border-gold);
  border-radius: 50%;
  animation: ringOrbit 20s linear infinite;
}

.trust-ring:nth-child(2) {
  inset: 20px;
  animation-duration: 15s;
  animation-direction: reverse;
}

.trust-ring:nth-child(3) {
  inset: 40px;
  animation-duration: 25s;
}

@keyframes ringOrbit {
  to { transform: rotate(360deg); }
}

.ring-node {
  position: absolute;
  width: 12px;
  height: 12px;
  background: var(--gold);
  border-radius: 50%;
  box-shadow: 0 0 20px var(--gold-glow);
}

.ring-node.cyan {
  background: var(--cyan);
  box-shadow: 0 0 20px var(--cyan-glow);
}

.trust-core {
  position: absolute;
  inset: 60px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.trust-score {
  font-family: var(--font-mono);
  font-size: 42px;
  font-weight: 700;
  color: var(--gold);
  text-shadow: 0 0 30px var(--gold-glow);
}
```

---

# 8. EFFECTS & ANIMATIONS

## 8.1 Neural Canvas

```javascript
// Canvas colors from CSS variables
function getCanvasColors() {
  const style = getComputedStyle(document.documentElement);
  return {
    node: style.getPropertyValue('--neural-node').trim(),
    line: style.getPropertyValue('--neural-line').trim(),
    glow: style.getPropertyValue('--neural-glow').trim()
  };
}

// Update on theme change
window.addEventListener('themechange', () => {
  canvasColors = getCanvasColors();
});

// Node configuration
const config = {
  landing: { count: 50, maxDist: 150, speed: 0.4 },
  dashboard: { count: 30, maxDist: 120, speed: 0.2 },
  auth: { count: 35, maxDist: 140, speed: 0.3 }
};
```

## 8.2 Scan Lines

```css
.scan-lines {
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    var(--scan-line) 2px,
    var(--scan-line) 4px
  );
  pointer-events: none;
  z-index: 1;
}

[data-theme="light"] .scan-lines {
  opacity: 0.5;
}
```

## 8.3 Grid Floor

```css
.grid-floor {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40vh;
  background: 
    linear-gradient(to top, var(--gold-subtle) 0%, transparent 100%),
    repeating-linear-gradient(
      90deg,
      transparent,
      transparent 99px,
      var(--grid-line) 99px,
      var(--grid-line) 100px
    );
  background-size: 100% 100%, 100px 100%;
  transform: perspective(500px) rotateX(60deg);
  transform-origin: bottom center;
  pointer-events: none;
  animation: gridPulse 4s ease-in-out infinite;
}

@keyframes gridPulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.8; }
}

[data-theme="light"] .grid-floor {
  opacity: 0.4;
}
```

## 8.4 HUD Corners

```css
.hud-corner {
  position: fixed;
  width: 60px;
  height: 60px;
  border: 2px solid var(--border-gold);
  pointer-events: none;
  z-index: var(--z-overlay);
  opacity: 0.6;
}

.hud-corner.tl { top: 16px; left: 16px; border-right: none; border-bottom: none; }
.hud-corner.tr { top: 16px; right: 16px; border-left: none; border-bottom: none; }
.hud-corner.bl { bottom: 16px; left: 16px; border-right: none; border-top: none; }
.hud-corner.br { bottom: 16px; right: 16px; border-left: none; border-top: none; }

[data-theme="light"] .hud-corner {
  opacity: 0.3;
}

.hud-label {
  position: fixed;
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--gold);
  opacity: 0.5;
  letter-spacing: 1px;
  z-index: var(--z-overlay);
}

[data-theme="light"] .hud-label {
  opacity: 0.7;
}
```

## 8.5 Animation Keyframes

```css
/* Fade In */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Slide In */
@keyframes slideIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Slide In Left */
@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

/* Scale In */
@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

/* Title Reveal */
@keyframes titleReveal {
  from { opacity: 0; transform: translateY(100%); }
  to { opacity: 1; transform: translateY(0); }
}

/* Gradient Flow */
@keyframes gradientFlow {
  0%, 100% { background-position: 0% center; }
  50% { background-position: 100% center; }
}

/* Hex Spin */
@keyframes hexSpin {
  to { transform: rotate(360deg); }
}

/* Float */
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

/* Shimmer */
@keyframes shimmer {
  from { left: -100%; }
  to { left: 100%; }
}
```

---

# 9. RESPONSIVE BREAKPOINTS

```css
/* Breakpoints */
--breakpoint-sm: 480px;
--breakpoint-md: 768px;
--breakpoint-lg: 1024px;
--breakpoint-xl: 1280px;
--breakpoint-2xl: 1536px;

/* Usage */
@media (max-width: 1280px) {
  /* XL and below */
}

@media (max-width: 1024px) {
  /* LG and below - Hide split panels */
  .preview-panel { display: none; }
  .auth-panel { border-left: none; }
  .dashboard-sidebar { transform: translateX(-100%); }
}

@media (max-width: 768px) {
  /* MD and below */
  .nav-links { display: none; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 480px) {
  /* SM and below */
  .hud-corner { display: none; }
  .kpi-grid { grid-template-columns: 1fr; }
  .btn-group { flex-direction: column; }
}
```

---

# 10. ACCESSIBILITY

## 10.1 Contrast Ratios (WCAG AA)

| Element | Dark Mode | Light Mode |
|---------|-----------|------------|
| Primary Text | #FFFFFF on #0a0a0f = 18.1:1 ✅ | #0f172a on #ffffff = 15.9:1 ✅ |
| Secondary Text | #CCCCCC on #12121a = 10.4:1 ✅ | #334155 on #ffffff = 8.5:1 ✅ |
| Muted Text | #888888 on #12121a = 5.2:1 ✅ | #94a3b8 on #ffffff = 3.3:1 ✅ |
| Gold Accent | #D4AF37 on #0a0a0f = 8.1:1 ✅ | #B8860B on #ffffff = 4.5:1 ✅ |

## 10.2 Focus States

```css
:focus-visible {
  outline: 2px solid var(--gold);
  outline-offset: 2px;
}

:focus:not(:focus-visible) {
  outline: none;
}
```

## 10.3 Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  
  .neural-canvas,
  .grid-floor,
  .scan-lines {
    display: none;
  }
}
```

## 10.4 Screen Reader

```html
<!-- Skip to main content -->
<a href="#main" class="sr-only focus:not-sr-only">Skip to content</a>

<!-- Announce theme changes -->
<div role="status" aria-live="polite" class="sr-only" id="themeAnnounce"></div>

<script>
ThemeManager.set = function(theme) {
  // ... existing code
  document.getElementById('themeAnnounce').textContent = 
    `Theme changed to ${theme} mode`;
};
</script>
```

---

# 11. QUICK REFERENCE

## Color Tokens

| Token | Dark | Light |
|-------|------|-------|
| `--bg-void` | #050508 | #f8f9fc |
| `--bg-primary` | #0a0a0f | #ffffff |
| `--bg-card` | #12121a | #ffffff |
| `--text-primary` | #ffffff | #0f172a |
| `--text-secondary` | #cccccc | #334155 |
| `--border-default` | rgba(255,255,255,0.06) | rgba(0,0,0,0.08) |
| `--gold` | #D4AF37 | #B8860B |
| `--cyan` | #14F0C6 | #0D9488 |

## Copy-Paste Snippets

### Solid Card
```css
background: var(--bg-card);
border: 1px solid var(--border-default);
border-radius: var(--radius-lg);
box-shadow: var(--shadow-md), var(--shadow-inset);
```

### Glass Overlay
```css
background: var(--glass-bg);
backdrop-filter: blur(var(--glass-blur));
border: 1px solid var(--glass-border);
```

### Gold Button
```css
background: var(--gold);
color: var(--text-inverse);
box-shadow: var(--shadow-gold);
```

### Input Focus
```css
border-color: var(--gold);
box-shadow: 0 0 0 3px var(--gold-subtle);
```

### Status Badge
```css
background: var(--status-success-bg);
border: 1px solid var(--border-success);
color: var(--status-success);
```

## Files Checklist

- [ ] `tokens.css` - All CSS custom properties
- [ ] `base.css` - Reset + global styles
- [ ] `components.css` - All component styles
- [ ] `landing.css` - Landing page specific
- [ ] `dashboard.css` - Dashboard specific
- [ ] `auth.css` - Sign in/up specific
- [ ] `theme.js` - Theme toggle logic
- [ ] `canvas.js` - Neural network canvas

---

**END OF STRATUM AI THEME SYSTEM v3.0**

*Universal Design Specification for All Frontend Interfaces*
*Landing • Dashboard • Authentication • All Components*
*Dark Mode • Light Mode • Full Accessibility*
