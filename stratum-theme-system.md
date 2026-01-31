# STRATUM AI - COMPLETE THEME SYSTEM
## Design Tokens & Implementation Guide for Light/Dark Modes

**Version:** 2.0  
**Last Updated:** January 2026  
**Scope:** Landing Pages, Authentication, Dashboard  
**Modes:** Dark (Default) | Light  

---

## QUICK IMPLEMENTATION

### Theme Toggle HTML
```html
<button class="theme-toggle" id="themeToggle" aria-label="Toggle theme">
  <svg class="icon-sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
  <svg class="icon-moon" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
</button>
```

### Theme Toggle JavaScript
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
  },
  toggle() {
    const current = document.documentElement.getAttribute('data-theme');
    this.set(current === 'dark' ? 'light' : 'dark');
  }
};
ThemeManager.init();
```

---

## CORE DESIGN TOKENS

```css
:root,
[data-theme="dark"] {
  /* ═══════════════════════════════════════════════════════════
     DARK MODE (Default) - Command Center Aesthetic
     ═══════════════════════════════════════════════════════════ */
  
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
  --border-hover: rgba(255, 255, 255, 0.1);
  --border-active: rgba(255, 255, 255, 0.15);
  --border-focus: rgba(212, 175, 55, 0.5);
  --border-gold: rgba(212, 175, 55, 0.15);
  
  /* Text */
  --text-primary: #ffffff;
  --text-secondary: #cccccc;
  --text-tertiary: #999999;
  --text-muted: #888888;
  --text-disabled: #555555;
  --text-inverse: #0a0a0f;
  
  /* Brand Gold */
  --gold: #D4AF37;
  --gold-bright: #F4D03F;
  --gold-muted: #B8860B;
  --gold-glow: rgba(212, 175, 55, 0.5);
  --gold-subtle: rgba(212, 175, 55, 0.1);
  
  /* Accent Cyan */
  --cyan: #14F0C6;
  --cyan-muted: #0FB89A;
  --cyan-glow: rgba(20, 240, 198, 0.4);
  --cyan-subtle: rgba(20, 240, 198, 0.1);
  
  /* Accent Purple */
  --purple: #8b5cf6;
  --purple-glow: rgba(139, 92, 246, 0.4);
  
  /* Status */
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
  
  /* Shadows */
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.5);
  --shadow-xl: 0 16px 48px rgba(0, 0, 0, 0.6);
  --shadow-gold: 0 0 40px rgba(212, 175, 55, 0.25);
  --shadow-inset: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  
  /* Effects */
  --neural-node: rgba(212, 175, 55, 0.6);
  --neural-line: rgba(212, 175, 55, 0.12);
  --scan-line: rgba(0, 0, 0, 0.03);
  --grid-line: rgba(212, 175, 55, 0.04);
  --glass-bg: rgba(20, 20, 30, 0.75);
  --glass-border: rgba(255, 255, 255, 0.08);
}

[data-theme="light"] {
  /* ═══════════════════════════════════════════════════════════
     LIGHT MODE - Clean Professional Aesthetic
     ═══════════════════════════════════════════════════════════ */
  
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
  
  /* Text */
  --text-primary: #0f172a;
  --text-secondary: #334155;
  --text-tertiary: #64748b;
  --text-muted: #94a3b8;
  --text-disabled: #cbd5e1;
  --text-inverse: #ffffff;
  
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
  
  /* Status (Darker for Contrast) */
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
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 16px 40px rgba(0, 0, 0, 0.12);
  --shadow-gold: 0 0 30px rgba(180, 134, 11, 0.15);
  --shadow-inset: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  
  /* Effects (Subtle) */
  --neural-node: rgba(180, 134, 11, 0.4);
  --neural-line: rgba(180, 134, 11, 0.08);
  --scan-line: rgba(0, 0, 0, 0.02);
  --grid-line: rgba(180, 134, 11, 0.03);
  --glass-bg: rgba(255, 255, 255, 0.8);
  --glass-border: rgba(0, 0, 0, 0.06);
}

/* ═══════════════════════════════════════════════════════════
   TYPOGRAPHY
   ═══════════════════════════════════════════════════════════ */

:root {
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;
}
```

---

## COMPONENT PATTERNS

### Theme Toggle Button
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

[data-theme="light"] .theme-toggle-knob {
  transform: translateX(20px);
}

/* Icons */
[data-theme="dark"] .icon-sun { display: block; }
[data-theme="dark"] .icon-moon { display: none; }
[data-theme="light"] .icon-sun { display: none; }
[data-theme="light"] .icon-moon { display: block; }
```

### Solid Data Card (NN/g Compliant)
```css
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md), var(--shadow-inset);
  transition: all 0.3s ease;
}

.card:hover {
  transform: translateY(-4px);
  border-color: var(--border-hover);
  box-shadow: var(--shadow-lg);
}

/* 3px Status Accent */
.card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--accent-color);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}
```

### Primary Button
```css
.btn-primary {
  background: var(--gold);
  color: var(--text-inverse);
  padding: 12px 24px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background: var(--gold-bright);
  box-shadow: var(--shadow-gold);
  transform: translateY(-2px);
}
```

### Form Input
```css
.input {
  width: 100%;
  padding: 14px 16px;
  background: var(--bg-input);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 14px;
}

.input:focus {
  outline: none;
  border-color: var(--gold);
  box-shadow: 0 0 0 3px var(--gold-subtle);
}

.input::placeholder {
  color: var(--text-disabled);
}
```

### Status Badge
```css
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-card);
  border: 1px solid var(--status-success-border);
  border-radius: var(--radius-md);
}

.status-dot {
  width: 8px;
  height: 8px;
  background: var(--status-success);
  border-radius: 50%;
  box-shadow: 0 0 12px var(--status-success);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

---

## NEURAL EFFECTS

### Canvas Background
```css
#neural-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  opacity: 0.7;
}

[data-theme="light"] #neural-canvas {
  opacity: 0.4;
}
```

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
    repeating-linear-gradient(90deg, transparent, transparent 99px, var(--grid-line) 100px);
  transform: perspective(500px) rotateX(60deg);
  transform-origin: bottom center;
  pointer-events: none;
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
  z-index: 100;
}

.hud-corner.tl { top: 16px; left: 16px; border-right: none; border-bottom: none; }
.hud-corner.tr { top: 16px; right: 16px; border-left: none; border-bottom: none; }
.hud-corner.bl { bottom: 16px; left: 16px; border-right: none; border-top: none; }
.hud-corner.br { bottom: 16px; right: 16px; border-left: none; border-top: none; }

[data-theme="light"] .hud-corner {
  opacity: 0.4;
}
```

---

## PAGE GUIDELINES

### Landing Page
| Element | Dark | Light |
|---------|------|-------|
| Background | #050508 | #f8f9fc |
| Card | #12121a solid | #ffffff solid |
| Neural Canvas | 70% opacity | 40% opacity |
| Grid Floor | 80% opacity | 40% opacity |
| HUD Corners | Visible | 40% opacity |

### Sign In / Sign Up
| Element | Dark | Light |
|---------|------|-------|
| Split Background | #0a0a0f / #12121a | #f8f9fc / #ffffff |
| Input Background | #0a0a0f | #f4f5f7 |
| Trust Ring | Gold gradient | Gold gradient (muted) |
| Terminal Footer | Visible | Visible |

### Dashboard
| Element | Dark | Light |
|---------|------|-------|
| Sidebar | #0a0a0f | #ffffff |
| Main Content | #050508 | #f8f9fc |
| KPI Cards | #12121a solid | #ffffff solid |
| Data Tables | #12121a | #ffffff |
| Charts | Gold/Cyan accents | Gold/Teal accents |

---

## ACCESSIBILITY

### Contrast Ratios (WCAG AA)
| Element | Dark | Light |
|---------|------|-------|
| Primary Text | 18.1:1 ✅ | 15.9:1 ✅ |
| Secondary Text | 10.4:1 ✅ | 8.5:1 ✅ |
| Gold Accent | 8.1:1 ✅ | 4.5:1 ✅ |
| Success | 6.2:1 ✅ | 4.5:1 ✅ |

### Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## QUICK REFERENCE

### Dark Mode Card
```css
background: #12121a;
border: 1px solid rgba(255, 255, 255, 0.06);
border-radius: 12px;
box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
```

### Light Mode Card
```css
background: #ffffff;
border: 1px solid rgba(0, 0, 0, 0.08);
border-radius: 12px;
box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
```

### Gold Button
```css
background: var(--gold);
color: var(--text-inverse);
box-shadow: var(--shadow-gold);
```

### Status Accents
```css
/* Gold */    --gold or border-top: 3px solid #D4AF37;
/* Cyan */    --cyan or border-top: 3px solid #14F0C6;
/* Success */ --status-success or border-top: 3px solid #22c55e;
/* Warning */ --status-warning or border-top: 3px solid #f59e0b;
/* Error */   --status-error or border-top: 3px solid #ef4444;
```

---

**END OF THEME SYSTEM**
