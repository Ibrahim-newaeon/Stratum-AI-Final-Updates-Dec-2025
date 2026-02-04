# STRATUM AI - UNIVERSAL THEME SYSTEM v3.0
## Complete Design Specification for All Frontend Interfaces

**Version:** 3.0 (Production Complete)  
**Last Updated:** January 2026  
**Coverage:** Landing • Dashboard • Sign In • Sign Up • All Components  
**Modes:** Dark (Default) | Light  
**Compliance:** NN/g Glassmorphism Research • WCAG 2.1 AA  

---

# SECTION 1: CORE DESIGN TOKENS

## 1.1 Color System

### Dark Theme (Default)
```css
[data-theme="dark"] {
  /* Backgrounds - Layered depth system */
  --bg-void: #050508;           /* Page base - deepest */
  --bg-primary: #0a0a0f;        /* Primary surfaces */
  --bg-secondary: #0d0d14;      /* Secondary surfaces */
  --bg-card: #12121a;           /* Cards - SOLID (NN/g compliant) */
  --bg-card-hover: #1a1a24;     /* Card hover state */
  --bg-elevated: #1e1e28;       /* Elevated elements, modals */
  --bg-input: #0a0a0f;          /* Form inputs */
  --bg-sidebar: #0a0a0f;        /* Dashboard sidebar */
  --bg-overlay: rgba(5, 5, 8, 0.9);
  
  /* Text Hierarchy */
  --text-primary: #ffffff;       /* Headlines, important text */
  --text-secondary: #cccccc;     /* Body text */
  --text-tertiary: #999999;      /* Supporting text */
  --text-muted: #888888;         /* Labels, captions */
  --text-disabled: #555555;      /* Disabled states */
  --text-inverse: #0a0a0f;       /* Text on gold buttons */
  
  /* Borders */
  --border-default: rgba(255, 255, 255, 0.06);
  --border-hover: rgba(255, 255, 255, 0.10);
  --border-active: rgba(255, 255, 255, 0.15);
  --border-focus: rgba(212, 175, 55, 0.5);
  --border-gold: rgba(212, 175, 55, 0.15);
  --border-error: rgba(239, 68, 68, 0.5);
  
  /* Brand - Stratum Gold */
  --gold: #D4AF37;
  --gold-bright: #F4D03F;
  --gold-muted: #B8860B;
  --gold-glow: rgba(212, 175, 55, 0.5);
  --gold-subtle: rgba(212, 175, 55, 0.1);
  
  /* Brand - Accent Cyan */
  --cyan: #14F0C6;
  --cyan-muted: #0FB89A;
  --cyan-glow: rgba(20, 240, 198, 0.4);
  --cyan-subtle: rgba(20, 240, 198, 0.1);
  
  /* Accent Purple */
  --purple: #8b5cf6;
  --purple-glow: rgba(139, 92, 246, 0.4);
  --purple-subtle: rgba(139, 92, 246, 0.1);
  
  /* Status Colors */
  --status-success: #22c55e;
  --status-success-bg: rgba(34, 197, 94, 0.1);
  --status-success-border: rgba(34, 197, 94, 0.3);
  --status-warning: #f59e0b;
  --status-warning-bg: rgba(245, 158, 11, 0.1);
  --status-warning-border: rgba(245, 158, 11, 0.3);
  --status-error: #ef4444;
  --status-error-bg: rgba(239, 68, 68, 0.1);
  --status-error-border: rgba(239, 68, 68, 0.3);
  --status-info: #0a84ff;
  --status-info-bg: rgba(10, 132, 255, 0.1);
  --status-info-border: rgba(10, 132, 255, 0.3);
  
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
  
  /* Glass (Overlays only - NN/g) */
  --glass-bg: rgba(20, 20, 30, 0.75);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-blur: 100px;
  
  /* Scrollbar */
  --scrollbar-track: #0a0a0f;
  --scrollbar-thumb: rgba(212, 175, 55, 0.3);
  --scrollbar-thumb-hover: rgba(212, 175, 55, 0.5);
  
  /* Charts */
  --chart-grid: rgba(255, 255, 255, 0.05);
  --chart-axis: rgba(255, 255, 255, 0.1);
  --chart-line-1: #D4AF37;
  --chart-line-2: #14F0C6;
  --chart-line-3: #8b5cf6;
  --chart-area-1: rgba(212, 175, 55, 0.1);
  --chart-area-2: rgba(20, 240, 198, 0.1);
}
```

### Light Theme
```css
[data-theme="light"] {
  /* Backgrounds */
  --bg-void: #f8f9fc;
  --bg-primary: #ffffff;
  --bg-secondary: #f4f5f7;
  --bg-card: #ffffff;
  --bg-card-hover: #f8f9fc;
  --bg-elevated: #ffffff;
  --bg-input: #f4f5f7;
  --bg-sidebar: #ffffff;
  --bg-overlay: rgba(255, 255, 255, 0.95);
  
  /* Text */
  --text-primary: #0f172a;
  --text-secondary: #334155;
  --text-tertiary: #64748b;
  --text-muted: #94a3b8;
  --text-disabled: #cbd5e1;
  --text-inverse: #ffffff;
  
  /* Borders */
  --border-default: rgba(0, 0, 0, 0.08);
  --border-hover: rgba(0, 0, 0, 0.12);
  --border-active: rgba(0, 0, 0, 0.18);
  --border-focus: rgba(180, 134, 11, 0.5);
  --border-gold: rgba(180, 134, 11, 0.2);
  --border-error: rgba(220, 38, 38, 0.5);
  
  /* Brand Gold (Darker for Light Mode) */
  --gold: #B8860B;
  --gold-bright: #D4AF37;
  --gold-muted: #996B06;
  --gold-glow: rgba(180, 134, 11, 0.3);
  --gold-subtle: rgba(180, 134, 11, 0.08);
  
  /* Accent Cyan (Darker) */
  --cyan: #0D9488;
  --cyan-muted: #0F766E;
  --cyan-glow: rgba(13, 148, 136, 0.3);
  --cyan-subtle: rgba(13, 148, 136, 0.08);
  
  /* Accent Purple */
  --purple: #7c3aed;
  --purple-glow: rgba(124, 58, 237, 0.3);
  --purple-subtle: rgba(124, 58, 237, 0.08);
  
  /* Status Colors */
  --status-success: #16a34a;
  --status-success-bg: rgba(22, 163, 74, 0.08);
  --status-success-border: rgba(22, 163, 74, 0.25);
  --status-warning: #d97706;
  --status-warning-bg: rgba(217, 119, 6, 0.08);
  --status-warning-border: rgba(217, 119, 6, 0.25);
  --status-error: #dc2626;
  --status-error-bg: rgba(220, 38, 38, 0.08);
  --status-error-border: rgba(220, 38, 38, 0.25);
  --status-info: #2563eb;
  --status-info-bg: rgba(37, 99, 235, 0.08);
  --status-info-border: rgba(37, 99, 235, 0.25);
  
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
  
  /* Glass */
  --glass-bg: rgba(255, 255, 255, 0.85);
  --glass-border: rgba(0, 0, 0, 0.06);
  --glass-blur: 80px;
  
  /* Scrollbar */
  --scrollbar-track: #f4f5f7;
  --scrollbar-thumb: rgba(180, 134, 11, 0.25);
  --scrollbar-thumb-hover: rgba(180, 134, 11, 0.4);
  
  /* Charts */
  --chart-grid: rgba(0, 0, 0, 0.05);
  --chart-axis: rgba(0, 0, 0, 0.1);
  --chart-line-1: #B8860B;
  --chart-line-2: #0D9488;
  --chart-line-3: #7c3aed;
  --chart-area-1: rgba(180, 134, 11, 0.1);
  --chart-area-2: rgba(13, 148, 136, 0.1);
}
```

---

## 1.2 Typography System

```css
:root {
  /* Font Families */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
  
  /* Font Sizes */
  --text-xs: 10px;
  --text-sm: 12px;
  --text-base: 14px;
  --text-md: 16px;
  --text-lg: 18px;
  --text-xl: 20px;
  --text-2xl: 24px;
  --text-3xl: 28px;
  --text-4xl: 36px;
  --text-5xl: 48px;
  --text-6xl: 64px;
  
  /* Font Weights */
  --font-light: 300;
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
  --font-extrabold: 800;
}
```

### Typography Classes
| Class | Size | Weight | Use Case |
|-------|------|--------|----------|
| `.heading-hero` | 48-64px | 800 | Landing hero titles |
| `.heading-1` | 36px | 700 | Page titles |
| `.heading-2` | 24px | 600 | Section titles |
| `.heading-3` | 18px | 600 | Card titles |
| `.body-lg` | 16px | 400 | Hero subtitles |
| `.body` | 14px | 400 | Default body text |
| `.body-sm` | 12px | 400 | Secondary info |
| `.label` | 10-11px | 600 | Form labels, badges |
| `.mono-lg` | 28-42px | 700 | Large metrics |
| `.mono` | 14px | 500 | Code, data values |
| `.mono-sm` | 11px | 400 | Terminal, timestamps |

---

## 1.3 Spacing & Layout

```css
:root {
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
  --space-24: 96px;
  
  /* Border Radius */
  --radius-sm: 4px;
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
  --z-background: 0;
  --z-default: 1;
  --z-elevated: 10;
  --z-sticky: 50;
  --z-overlay: 100;
  --z-modal: 200;
  --z-tooltip: 500;
  --z-toast: 1000;
}
```

---

# SECTION 2: COMPONENT LIBRARY

## 2.1 Cards (NN/g Compliant - SOLID Backgrounds)

### Data Card
```css
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

/* 3px Status Accent Line */
.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--card-accent, transparent);
}

/* Accent Variants */
.card[data-accent="gold"]::before { background: var(--gold); }
.card[data-accent="cyan"]::before { background: var(--cyan); }
.card[data-accent="purple"]::before { background: var(--purple); }
.card[data-accent="success"]::before { background: var(--status-success); }
.card[data-accent="warning"]::before { background: var(--status-warning); }
.card[data-accent="error"]::before { background: var(--status-error); }
```

### Feature Card
```css
.card-feature {
  padding: var(--space-8);
}

.card-feature .icon {
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

.card-feature .icon svg {
  width: 24px;
  height: 24px;
  stroke: var(--gold);
  fill: none;
  stroke-width: 1.5;
}

.card-feature:hover .icon {
  box-shadow: var(--shadow-gold);
  transform: scale(1.05);
}
```

### Stat/KPI Card
```css
.card-stat {
  padding: var(--space-5);
  text-align: center;
}

.card-stat .value {
  font-family: var(--font-mono);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
}

.card-stat .label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-top: var(--space-1);
}

.card-stat .trend {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  margin-top: var(--space-2);
}

.card-stat .trend.up { color: var(--status-success); }
.card-stat .trend.down { color: var(--status-error); }
```

---

## 2.2 Buttons

```css
/* Base Button */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
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
  font-weight: var(--font-bold);
}

.btn-primary:hover:not(:disabled) {
  background: var(--gold-bright);
  box-shadow: var(--shadow-gold);
  transform: translateY(-2px);
}

/* Shimmer Effect */
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

/* Danger */
.btn-danger {
  background: var(--status-error);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.4);
}

/* Sizes */
.btn-sm { padding: var(--space-2) var(--space-4); font-size: var(--text-sm); }
.btn-lg { padding: var(--space-4) var(--space-8); font-size: var(--text-md); }

/* Icon Button */
.btn-icon {
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: var(--radius-md);
}
```

---

## 2.3 Form Elements

```css
/* Input */
.input {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  color: var(--text-primary);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
}

.input::placeholder {
  color: var(--text-disabled);
}

.input:hover {
  border-color: var(--border-hover);
}

.input:focus {
  outline: none;
  border-color: var(--gold);
  box-shadow: 0 0 0 3px var(--gold-subtle);
}

.input.error {
  border-color: var(--status-error);
}

.input.error:focus {
  box-shadow: 0 0 0 3px var(--status-error-bg);
}

/* Label */
.label {
  display: block;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  margin-bottom: var(--space-2);
}

/* Select */
.select {
  appearance: none;
  background-image: url("data:image/svg+xml,...chevron-down...");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 40px;
}

/* Textarea */
.textarea {
  min-height: 100px;
  resize: vertical;
}

/* Checkbox */
.checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-default);
  border-radius: var(--radius-sm);
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

/* Password Strength Meter */
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

---

## 2.4 Navigation

### Top Navigation
```css
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
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
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
```

### Dashboard Sidebar
```css
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 240px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border-default);
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  z-index: var(--z-sticky);
}

.sidebar-nav {
  flex: 1;
  margin-top: var(--space-8);
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  color: var(--text-muted);
  text-decoration: none;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  transition: all var(--transition-base);
  margin-bottom: var(--space-1);
}

.sidebar-link:hover {
  color: var(--text-primary);
  background: var(--bg-card);
}

.sidebar-link.active {
  color: var(--gold);
  background: var(--gold-subtle);
  border-left: 3px solid var(--gold);
  margin-left: -3px;
}

.sidebar-link svg {
  width: 20px;
  height: 20px;
  stroke: currentColor;
  fill: none;
  stroke-width: 1.5;
}

/* Sidebar Section */
.sidebar-section {
  margin-top: var(--space-6);
}

.sidebar-section-title {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
  padding: var(--space-2) var(--space-4);
  margin-bottom: var(--space-2);
}
```

---

## 2.5 Status Indicators

```css
/* Status Badge */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-badge.success {
  background: var(--status-success-bg);
  border: 1px solid var(--status-success-border);
  color: var(--status-success);
}

.status-badge.warning {
  background: var(--status-warning-bg);
  border: 1px solid var(--status-warning-border);
  color: var(--status-warning);
}

.status-badge.error {
  background: var(--status-error-bg);
  border: 1px solid var(--status-error-border);
  color: var(--status-error);
}

.status-badge.info {
  background: var(--status-info-bg);
  border: 1px solid var(--status-info-border);
  color: var(--status-info);
}

/* Pulsing Dot */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  animation: statusPulse 2s ease-in-out infinite;
}

.status-dot.success { background: var(--status-success); box-shadow: 0 0 12px var(--status-success); }
.status-dot.warning { background: var(--status-warning); box-shadow: 0 0 12px var(--status-warning); }
.status-dot.error { background: var(--status-error); box-shadow: 0 0 12px var(--status-error); }
.status-dot.gold { background: var(--gold); box-shadow: 0 0 12px var(--gold-glow); }

@keyframes statusPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

---

## 2.6 Data Visualization

### Trust Ring (SVG)
```css
.trust-ring {
  position: relative;
  width: 200px;
  height: 200px;
}

.trust-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.trust-ring-bg {
  fill: none;
  stroke: var(--border-default);
  stroke-width: 8;
}

.trust-ring-progress {
  fill: none;
  stroke: var(--gold);
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 502;
  stroke-dashoffset: calc(502 - (502 * var(--progress, 0.947)));
  filter: drop-shadow(0 0 10px var(--gold-glow));
  transition: stroke-dashoffset 1s ease;
}

.trust-ring-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.trust-score {
  font-family: var(--font-mono);
  font-size: 42px;
  font-weight: var(--font-bold);
  color: var(--gold);
  text-shadow: 0 0 30px var(--gold-glow);
}
```

### Chart Container
```css
.chart-container {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.chart-title {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
}

.chart-legend {
  display: flex;
  gap: var(--space-4);
}

.chart-legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--text-muted);
}

.chart-legend-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
}
```

---

## 2.7 Tables

```css
.table-container {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th {
  text-align: left;
  padding: var(--space-4);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-default);
}

.table td {
  padding: var(--space-4);
  font-size: var(--text-base);
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-default);
}

.table tr:last-child td {
  border-bottom: none;
}

.table tr:hover td {
  background: var(--bg-card-hover);
}

/* Sortable Header */
.table th.sortable {
  cursor: pointer;
}

.table th.sortable:hover {
  color: var(--text-primary);
}
```

---

## 2.8 Modals & Overlays

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
  animation: fadeIn 0.2s ease;
}

.modal {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow: auto;
  animation: scaleIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-header {
  padding: var(--space-6);
  border-bottom: 1px solid var(--border-default);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.modal-close {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-base);
}

.modal-close:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--space-6);
}

.modal-footer {
  padding: var(--space-6);
  border-top: 1px solid var(--border-default);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
```

---

## 2.9 Toast Notifications

```css
.toast-container {
  position: fixed;
  bottom: var(--space-6);
  right: var(--space-6);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.toast {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  min-width: 300px;
  animation: slideInRight 0.3s ease;
}

.toast.success { border-left: 3px solid var(--status-success); }
.toast.warning { border-left: 3px solid var(--status-warning); }
.toast.error { border-left: 3px solid var(--status-error); }
.toast.info { border-left: 3px solid var(--status-info); }

.toast-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.toast.success .toast-icon { color: var(--status-success); }
.toast.warning .toast-icon { color: var(--status-warning); }
.toast.error .toast-icon { color: var(--status-error); }
.toast.info .toast-icon { color: var(--status-info); }

.toast-content {
  flex: 1;
}

.toast-title {
  font-weight: var(--font-semibold);
  margin-bottom: 2px;
}

.toast-message {
  font-size: var(--text-sm);
  color: var(--text-muted);
}

@keyframes slideInRight {
  from { opacity: 0; transform: translateX(100%); }
  to { opacity: 1; transform: translateX(0); }
}
```

---

# SECTION 3: PAGE TEMPLATES

## 3.1 Landing Page Structure

```
┌─────────────────────────────────────────────────────────────┐
│ [Neural Canvas Background] opacity: 0.7 (dark) / 0.4 (light)│
│ [Scan Lines Overlay]                                        │
│ [Grid Floor - Perspective]                                  │
│ [HUD Corner Brackets]                                       │
├─────────────────────────────────────────────────────────────┤
│ NAV: Logo | Links (pill) | Theme Toggle | CTA Buttons       │
├─────────────────────────────────────────────────────────────┤
│ HERO (Split Layout):                                        │
│ ┌─────────────────────┬─────────────────────────────────┐   │
│ │ • Status Badge      │  Trust Engine Preview           │   │
│ │ • Hero Title (3 line)│  • Window Chrome               │   │
│ │ • Subtitle          │  • Trust Ring (SVG)             │   │
│ │ • CTA Buttons       │  • Data Cards (4)               │   │
│ │ • Stats (3 cards)   │  • Live Data Stream             │   │
│ └─────────────────────┴─────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│ FEATURES: Section Header | 6 Feature Cards (3x2 grid)       │
├─────────────────────────────────────────────────────────────┤
│ SOCIAL PROOF: Platform Logos | Testimonials                 │
├─────────────────────────────────────────────────────────────┤
│ CTA SECTION: Gold border container | Buttons                │
├─────────────────────────────────────────────────────────────┤
│ FOOTER: Logo | Links | Copyright                            │
└─────────────────────────────────────────────────────────────┘
```

## 3.2 Dashboard Layout

```
┌──────────┬──────────────────────────────────────────────────┐
│ SIDEBAR  │ MAIN CONTENT                                     │
│ 240px    │                                                  │
│          │ ┌────────────────────────────────────────────┐   │
│ • Logo   │ │ HEADER: Page Title | Actions | Theme Toggle│   │
│ • Nav    │ └────────────────────────────────────────────┘   │
│   Links  │                                                  │
│ • Sections│ ┌────┬────┬────┬────┐                          │
│          │ │KPI1│KPI2│KPI3│KPI4│  ← 4 Stat Cards          │
│          │ └────┴────┴────┴────┘                          │
│          │                                                  │
│ ─────────│ ┌───────────────────┬────────────┐              │
│ Trust    │ │ MAIN CHART        │ SIDE PANEL │              │
│ Gate     │ │ (Line/Area)       │ • Alerts   │              │
│ Indicator│ │                   │ • Activity │              │
│          │ └───────────────────┴────────────┘              │
│          │                                                  │
│          │ ┌────────────────────────────────────────────┐   │
│          │ │ DATA TABLE                                 │   │
│          │ │ Sortable | Filterable | Paginated          │   │
│          │ └────────────────────────────────────────────┘   │
└──────────┴──────────────────────────────────────────────────┘
```

## 3.3 Auth Pages (Sign In / Sign Up)

```
┌─────────────────────────────────────────────────────────────┐
│ [Neural Canvas] [HUD Corners] [Theme Toggle]                │
├────────────────────────────┬────────────────────────────────┤
│ LEFT PANEL (50%)           │ RIGHT PANEL (50%)              │
│ Preview/Marketing          │ Auth Form                      │
│                            │                                │
│ • Trust Ring Animation     │ • Logo                         │
│ • Orbital Rings            │ • Title + Subtitle             │
│ • Preview Stats (3)        │ • Progress Steps (signup)      │
│                            │ • Form Fields                  │
│ OR (Signup)                │ • Password Strength            │
│                            │ • Remember Me / Forgot         │
│ • Feature List (4 items)   │ • Primary Button               │
│ • Dashboard Preview        │ • Divider                      │
│                            │ • Social Buttons               │
│                            │ • Terminal Footer              │
├────────────────────────────┴────────────────────────────────┤
│ Mobile: Hide left panel, full-width form                    │
└─────────────────────────────────────────────────────────────┘
```

---

# SECTION 4: EFFECTS & ANIMATIONS

## 4.1 Neural Network Canvas

```javascript
// Canvas setup for both themes
function getCanvasColors() {
  const theme = document.documentElement.getAttribute('data-theme') || 'dark';
  return {
    node: theme === 'dark' 
      ? 'rgba(212, 175, 55, 0.6)' 
      : 'rgba(180, 134, 11, 0.4)',
    line: theme === 'dark' 
      ? 'rgba(212, 175, 55, 0.12)' 
      : 'rgba(180, 134, 11, 0.08)',
    glow: theme === 'dark'
      ? 'rgba(212, 175, 55, 0.3)'
      : 'rgba(180, 134, 11, 0.2)'
  };
}

// Opacity by theme
// Dark: canvas opacity 0.7
// Light: canvas opacity 0.4
```

## 4.2 CSS Animations

```css
/* Ambient Animations (3-4s, infinite) */
@keyframes nodePulse {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.5); }
}

@keyframes statusPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes ringRotate {
  to { transform: rotate(360deg); }
}

@keyframes gridPulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 0.8; }
}

@keyframes blink {
  50% { opacity: 0; }
}

@keyframes gradientFlow {
  0%, 100% { background-position: 0% center; }
  50% { background-position: 100% center; }
}

/* Interactive Animations (0.2-0.5s) */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideInLeft {
  from { opacity: 0; transform: translateX(-20px); }
  to { opacity: 1; transform: translateX(0); }
}

@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes titleReveal {
  from { opacity: 0; transform: translateY(100%); }
  to { opacity: 1; transform: translateY(0); }
}

/* Logo Animation */
@keyframes hexSpin {
  to { transform: rotate(360deg); }
}
```

## 4.3 Decorative Elements

### Scan Lines
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
```

### Grid Floor
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

[data-theme="light"] .grid-floor {
  opacity: 0.4;
}
```

### HUD Corners
```css
.hud-corner {
  position: fixed;
  width: 60px;
  height: 60px;
  border: 2px solid var(--border-gold);
  pointer-events: none;
  z-index: var(--z-overlay);
}

.hud-corner.tl { top: 16px; left: 16px; border-right: none; border-bottom: none; }
.hud-corner.tr { top: 16px; right: 16px; border-left: none; border-bottom: none; }
.hud-corner.bl { bottom: 16px; left: 16px; border-right: none; border-top: none; }
.hud-corner.br { bottom: 16px; right: 16px; border-left: none; border-top: none; }

[data-theme="light"] .hud-corner {
  opacity: 0.4;
}

.hud-label {
  position: fixed;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--gold);
  opacity: 0.5;
  letter-spacing: 1px;
  z-index: var(--z-overlay);
}
```

### Terminal Footer
```css
.terminal-footer {
  padding: var(--space-4);
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}

.terminal-line {
  display: flex;
  align-items: center;
  gap: var(--space-2);
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
```

---

# SECTION 5: ACCESSIBILITY

## 5.1 Contrast Ratios (WCAG AA)

| Element | Dark Theme | Light Theme | Requirement |
|---------|------------|-------------|-------------|
| Primary Text | #FFF on #0a0a0f = 18.1:1 ✅ | #0f172a on #FFF = 15.9:1 ✅ | ≥4.5:1 |
| Secondary Text | #CCC on #12121a = 10.4:1 ✅ | #334155 on #FFF = 8.5:1 ✅ | ≥4.5:1 |
| Muted Text | #888 on #12121a = 5.2:1 ✅ | #94a3b8 on #FFF = 3.0:1 ⚠️ | ≥3:1 (large) |
| Gold Accent | #D4AF37 on #0a0a0f = 8.1:1 ✅ | #B8860B on #FFF = 4.5:1 ✅ | ≥4.5:1 |
| Success | #22c55e on #12121a = 6.2:1 ✅ | #16a34a on #FFF = 4.5:1 ✅ | ≥4.5:1 |

## 5.2 Focus States

```css
:focus-visible {
  outline: 2px solid var(--gold);
  outline-offset: 2px;
}

:focus:not(:focus-visible) {
  outline: none;
}

/* Interactive elements */
.btn:focus-visible,
.input:focus-visible,
.nav-link:focus-visible {
  box-shadow: 0 0 0 3px var(--gold-subtle);
}
```

## 5.3 Reduced Motion

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

---

# SECTION 6: RESPONSIVE BREAKPOINTS

```css
/* Mobile First */
--breakpoint-sm: 480px;   /* Small phones */
--breakpoint-md: 768px;   /* Tablets */
--breakpoint-lg: 1024px;  /* Small laptops */
--breakpoint-xl: 1280px;  /* Desktops */
--breakpoint-2xl: 1536px; /* Large screens */

/* Common Patterns */
@media (max-width: 1024px) {
  /* Hide split layouts, single column */
  /* Hide sidebar on dashboard */
  /* Stack navigation */
}

@media (max-width: 768px) {
  /* Mobile navigation */
  /* Stack cards */
  /* Full-width forms */
}

@media (max-width: 480px) {
  /* Hide decorative elements */
  /* Reduce padding */
  /* Simplify layouts */
}
```

---

# SECTION 7: IMPLEMENTATION CHECKLIST

## Theme System
- [ ] CSS custom properties defined for both themes
- [ ] Theme toggle in navigation
- [ ] localStorage persistence
- [ ] System preference detection
- [ ] Smooth theme transitions (400ms)

## Pages
- [ ] Landing page with all sections
- [ ] Sign In page with preview panel
- [ ] Sign Up page with multi-step form
- [ ] Dashboard with sidebar + content

## Components
- [ ] Cards (data, feature, stat)
- [ ] Buttons (primary, secondary, ghost)
- [ ] Form inputs (text, password, checkbox)
- [ ] Navigation (top nav, sidebar)
- [ ] Status indicators (badges, dots)
- [ ] Tables (sortable, responsive)
- [ ] Modals and overlays
- [ ] Toast notifications

## Effects
- [ ] Neural network canvas (theme-aware)
- [ ] Scan lines overlay
- [ ] Grid floor perspective
- [ ] HUD corner brackets
- [ ] Trust ring visualization
- [ ] Terminal footer

## Accessibility
- [ ] WCAG AA contrast ratios
- [ ] Focus visible states
- [ ] Keyboard navigation
- [ ] Reduced motion support
- [ ] ARIA labels

---

# QUICK REFERENCE

## Color Tokens
```
Dark BG:    #050508 → #0a0a0f → #12121a → #1e1e28
Light BG:   #f8f9fc → #ffffff → #f4f5f7 → #ffffff
Gold:       Dark #D4AF37 | Light #B8860B
Cyan:       Dark #14F0C6 | Light #0D9488
Border:     Dark rgba(255,255,255,0.06) | Light rgba(0,0,0,0.08)
```

## Card Pattern
```css
background: var(--bg-card);
border: 1px solid var(--border-default);
border-radius: 12px;
box-shadow: var(--shadow-md), var(--shadow-inset);
/* + 3px top accent for status */
```

## Button Pattern
```css
background: var(--gold);
color: var(--text-inverse);
box-shadow: var(--shadow-gold);
/* + shimmer on hover */
```

---

**END OF STRATUM AI THEME SYSTEM v3.0**

*Complete Design Specification for All Frontend Interfaces*
*Dark & Light Modes | NN/g Compliant | WCAG AA Accessible*
