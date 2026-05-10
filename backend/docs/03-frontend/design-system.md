# Design System

## Overview

Stratum AI's design system is built on Tailwind CSS with custom design tokens for consistent branding.

---

## Color Palette

### Brand Colors

```css
/* Primary - Electric Violet */
--stratum-50: #faf5ff;
--stratum-100: #f3e8ff;
--stratum-200: #e9d5ff;
--stratum-300: #d8b4fe;
--stratum-400: #A78BFA;  /* Hover */
--stratum-500: #8B5CF6;  /* Primary */
--stratum-600: #7C3AED;  /* Active */
--stratum-700: #6D28D9;
--stratum-800: #5B21B6;
--stratum-900: #4C1D95;
--stratum-950: #2E1065;

/* Secondary - Electric Cyan */
--cyan-500: #00D4FF;
```

### Platform Colors

```css
--meta: #0866FF;
--google: #4285F4;
--tiktok: #00F2EA;
--snapchat: #FFFC00;
--whatsapp: #25D366;
```

### Semantic Colors

```css
--success: #00FF88;   /* Neon green */
--warning: #FFB800;   /* Amber glow */
--danger: #FF4757;    /* Neon red */
--info: #00B4FF;      /* Electric blue */
--insight: #FF6B6B;   /* Coral accent */
```

### Surface Colors

```css
--surface-primary: #020204;    /* Near-black */
--surface-secondary: #0A0A0F;  /* Subtle blue */
--surface-tertiary: #12121A;   /* Elevated */
--surface-elevated: #1A1A26;   /* Cards/dialogs */
```

### Text Colors

```css
--text-primary: #FAFAFA;    /* Soft white */
--text-secondary: #94A3B8;  /* Cool gray */
--text-muted: #64748B;      /* Slate muted */
```

---

## Typography

### Font Families

```css
font-sans: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
font-mono: JetBrains Mono, ui-monospace, SFMono-Regular, monospace;
```

### Type Scale

| Name | Size | Line Height | Weight |
|------|------|-------------|--------|
| micro | 10px | 1.4 | 400 |
| meta | 12px | 1.5 | 400 |
| body | 14px | 1.55 | 400 |
| body-lg | 16px | 1.6 | 400 |
| h3 | 18px | 1.35 | 600 |
| h2 | 22px | 1.3 | 600 |
| h1 | 28px | 1.25 | 700 |
| display-sm | 32px | 1.2 | 700 |
| display | 40px | 1.15 | 700 |
| display-lg | 48px | 1.1 | 800 |
| display-xl | 56px | 1.05 | 800 |
| display-2xl | 72px | 1.0 | 800 |

### Usage

```html
<h1 class="text-h1">Page Title</h1>
<h2 class="text-h2">Section Title</h2>
<p class="text-body">Body text</p>
<span class="text-meta text-text-secondary">Meta information</span>
```

---

## Spacing Scale

Based on 4px increments:

| Token | Value |
|-------|-------|
| 1 | 4px |
| 2 | 8px |
| 3 | 12px |
| 4 | 16px |
| 5 | 24px |
| 6 | 32px |
| 7 | 48px |
| 8 | 64px |

### Section Spacing

| Token | Value |
|-------|-------|
| section-sm | 64px |
| section | 96px |
| section-lg | 128px |
| section-xl | 160px |

---

## Border Radius

```css
--radius-sm: calc(var(--radius) - 4px);
--radius-md: calc(var(--radius) - 2px);
--radius-lg: var(--radius);
--radius-xl: 20px;
```

---

## Shadows

### Glow Effects

```css
--shadow-glow-sm: 0 0 12px rgba(139, 92, 246, 0.2);
--shadow-glow: 0 0 20px rgba(139, 92, 246, 0.4);
--shadow-glow-lg: 0 0 32px rgba(139, 92, 246, 0.5);
--shadow-glow-insight: 0 0 20px rgba(255, 107, 107, 0.4);
--shadow-glow-cyan: 0 0 20px rgba(0, 212, 255, 0.4);
```

### Card Shadows

```css
--shadow-card: 0 4px 12px rgba(0, 0, 0, 0.20);
--shadow-card-hover: 0 10px 30px rgba(0, 0, 0, 0.28);
```

---

## Z-Index Scale

```css
--z-hide: -1;
--z-base: 0;
--z-raised: 1;
--z-dropdown: 10;
--z-sticky: 20;
--z-header: 30;
--z-overlay: 40;
--z-modal: 50;
--z-popover: 60;
--z-toast: 70;
--z-tooltip: 80;
--z-max: 9999;
```

---

## Animations

### Timing Functions

```css
--ease-standard: cubic-bezier(0.2, 0.8, 0.2, 1);
--ease-enter: cubic-bezier(0.16, 1, 0.3, 1);
--ease-exit: cubic-bezier(0.7, 0, 0.84, 0);
```

### Durations

```css
--duration-fast: 120ms;
--duration-base: 180ms;
--duration-slow: 280ms;
--duration-xl: 420ms;
```

### Animation Classes

```css
.animate-fade-in      /* Fade in */
.animate-enter        /* Fade up + scale */
.animate-sweep        /* Sweep from left */
.animate-glow-pulse   /* Violet glow pulse */
.animate-insight      /* Coral glow pulse */
.animate-critical     /* Micro shake */
.animate-scale-in     /* Scale in */
.animate-shimmer      /* Loading shimmer */
.animate-morph        /* Blob morph */
.animate-gradient-shift  /* Gradient movement */
.animate-float        /* Floating animation */
```

---

## Gradients

### Brand Gradient

```css
--gradient-stratum: linear-gradient(135deg, #8B5CF6 0%, #00D4FF 50%, #FF6B6B 100%);
--gradient-stratum-soft: linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(0, 212, 255, 0.05) 100%);
```

### Usage

```html
<div class="bg-gradient-stratum">Holographic gradient</div>
<div class="bg-gradient-stratum-soft">Soft gradient background</div>
```

---

## Dark Mode

Dark mode is the default and only mode. Configured via:

```js
// tailwind.config.js
darkMode: ['class'],
```

All colors are optimized for dark backgrounds.

---

## Component Tokens

### Button

```css
/* Default */
background: hsl(var(--primary));
color: hsl(var(--primary-foreground));

/* Hover */
background: hsl(var(--primary) / 0.9);

/* Destructive */
background: hsl(var(--destructive));
color: hsl(var(--destructive-foreground));
```

### Input

```css
background: hsl(var(--background));
border: 1px solid hsl(var(--border));
color: hsl(var(--foreground));

/* Focus */
ring: 2px solid hsl(var(--ring));
```

### Card

```css
background: hsl(var(--card));
border: 1px solid hsl(var(--border));
border-radius: var(--radius);
box-shadow: var(--shadow-card);

/* Hover */
box-shadow: var(--shadow-card-hover);
```

---

## Responsive Breakpoints

```css
sm: 640px   /* Mobile landscape */
md: 768px   /* Tablet */
lg: 1024px  /* Desktop */
xl: 1280px  /* Large desktop */
2xl: 1400px /* Extra large */
```

### Container Widths

```css
--container-sm: 640px;
--container-md: 768px;
--container-lg: 1024px;
--container-xl: 1280px;
--container-2xl: 1400px;
```

---

## RTL Support

RTL support via `tailwindcss-rtl` plugin:

```html
<!-- RTL-aware margins -->
<div class="mr-4 rtl:ml-4 rtl:mr-0">Content</div>

<!-- RTL-aware text -->
<p class="text-left rtl:text-right">Text</p>
```

---

## Usage Examples

### Card Component

```html
<div class="
  bg-card
  border border-border
  rounded-lg
  p-6
  shadow-card
  hover:shadow-card-hover
  transition-shadow duration-base
">
  <h3 class="text-h3 text-foreground mb-2">Card Title</h3>
  <p class="text-body text-muted-foreground">Card content</p>
</div>
```

### Metric Display

```html
<div class="flex items-baseline gap-2">
  <span class="text-display font-bold text-foreground">$15,420</span>
  <span class="text-meta text-success">+12.5%</span>
</div>
```

### Platform Badge

```html
<span class="
  inline-flex items-center
  px-2 py-1
  rounded-md
  text-meta font-medium
  bg-meta/10 text-meta
">
  Meta
</span>
```
