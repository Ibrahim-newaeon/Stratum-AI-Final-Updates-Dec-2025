# STRATUM AI DASHBOARD ENHANCEMENT PROMPT

**Task:** Update existing dashboard with enhanced background nodes and colored shiny cards  
**Context:** Dark theme dashboard needs more visual depth and card prominence

---

## ENHANCEMENT 1: DENSE NEURAL NETWORK BACKGROUND

### Current Problem
- Only 1-2 nodes visible
- Background feels empty/static
- Doesn't communicate "AI intelligence"

### Target State
- 12-15 animated nodes
- 8-10 connection lines
- Layered depth with varying opacity

### Implementation

```css
/* NEURAL NETWORK CONTAINER */
.neural-network-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

/* NODES - 12-15 distributed across viewport */
.neural-node {
  position: absolute;
  width: 6px;
  height: 6px;
  background: rgba(10, 132, 255, 0.6);
  border-radius: 50%;
  box-shadow: 
    0 0 20px rgba(10, 132, 255, 0.4),
    0 0 40px rgba(10, 132, 255, 0.2);
  animation: nodePulse 3s ease-in-out infinite;
}

/* Node positions - spread across viewport */
.neural-node:nth-child(1)  { top: 8%;  left: 15%; animation-delay: 0s; }
.neural-node:nth-child(2)  { top: 12%; left: 45%; animation-delay: 0.3s; }
.neural-node:nth-child(3)  { top: 6%;  left: 75%; animation-delay: 0.6s; }
.neural-node:nth-child(4)  { top: 25%; left: 25%; animation-delay: 0.9s; }
.neural-node:nth-child(5)  { top: 20%; left: 60%; animation-delay: 1.2s; }
.neural-node:nth-child(6)  { top: 30%; left: 85%; animation-delay: 1.5s; }
.neural-node:nth-child(7)  { top: 45%; left: 10%; animation-delay: 1.8s; }
.neural-node:nth-child(8)  { top: 50%; left: 40%; animation-delay: 2.1s; }
.neural-node:nth-child(9)  { top: 55%; left: 70%; animation-delay: 2.4s; }
.neural-node:nth-child(10) { top: 65%; left: 20%; animation-delay: 0.2s; }
.neural-node:nth-child(11) { top: 70%; left: 55%; animation-delay: 0.5s; }
.neural-node:nth-child(12) { top: 75%; left: 90%; animation-delay: 0.8s; }
.neural-node:nth-child(13) { top: 85%; left: 30%; animation-delay: 1.1s; }
.neural-node:nth-child(14) { top: 90%; left: 65%; animation-delay: 1.4s; }
.neural-node:nth-child(15) { top: 95%; left: 80%; animation-delay: 1.7s; }

/* Vary node sizes for depth */
.neural-node:nth-child(odd) {
  width: 4px;
  height: 4px;
  opacity: 0.5;
}

.neural-node:nth-child(3n) {
  width: 8px;
  height: 8px;
  opacity: 0.8;
}

/* CONNECTION LINES */
.neural-line {
  position: absolute;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(10, 132, 255, 0.3), 
    transparent
  );
  transform-origin: left center;
  animation: linePulse 4s ease-in-out infinite;
}

/* Line positions - connect nearby nodes */
.neural-line:nth-child(1)  { top: 10%; left: 17%; width: 200px; transform: rotate(5deg); animation-delay: 0s; }
.neural-line:nth-child(2)  { top: 15%; left: 47%; width: 180px; transform: rotate(-10deg); animation-delay: 0.5s; }
.neural-line:nth-child(3)  { top: 22%; left: 27%; width: 220px; transform: rotate(15deg); animation-delay: 1s; }
.neural-line:nth-child(4)  { top: 35%; left: 12%; width: 190px; transform: rotate(25deg); animation-delay: 1.5s; }
.neural-line:nth-child(5)  { top: 48%; left: 42%; width: 200px; transform: rotate(-5deg); animation-delay: 2s; }
.neural-line:nth-child(6)  { top: 60%; left: 22%; width: 230px; transform: rotate(20deg); animation-delay: 0.3s; }
.neural-line:nth-child(7)  { top: 72%; left: 57%; width: 210px; transform: rotate(-15deg); animation-delay: 0.8s; }
.neural-line:nth-child(8)  { top: 80%; left: 32%; width: 200px; transform: rotate(10deg); animation-delay: 1.3s; }
.neural-line:nth-child(9)  { top: 88%; left: 67%; width: 150px; transform: rotate(-8deg); animation-delay: 1.8s; }
.neural-line:nth-child(10) { top: 40%; left: 62%; width: 180px; transform: rotate(30deg); animation-delay: 2.3s; }

@keyframes nodePulse {
  0%, 100% { 
    opacity: 0.4; 
    transform: scale(1);
    box-shadow: 0 0 20px rgba(10, 132, 255, 0.3);
  }
  50% { 
    opacity: 1; 
    transform: scale(1.5);
    box-shadow: 0 0 30px rgba(10, 132, 255, 0.6), 0 0 60px rgba(10, 132, 255, 0.3);
  }
}

@keyframes linePulse {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.5; }
}
```

### HTML Structure
```html
<div class="neural-network-bg">
  <!-- Nodes -->
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  
  <!-- Connection Lines -->
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
</div>
```

---

## ENHANCEMENT 2: COLORED SHINY CARDS

### Current Problem
- Cards too dark, blend into background
- No visual hierarchy between card types
- Missing premium/AI feel

### Target State
- Colored top gradient accent (4px)
- Shine/gloss highlight effect
- Subtle colored glow on hover
- Status-based color coding

### Card Color System

| Card Type | Accent Color | Use Case |
|-----------|--------------|----------|
| **Success/Positive** | `#22c55e` (Green) | ROAS up, CTR up, Active items |
| **Warning/Caution** | `#f59e0b` (Amber) | Needs attention, Medium priority |
| **Error/Critical** | `#ef4444` (Red) | Blocked, Failed, Critical issues |
| **Info/Neutral** | `#0a84ff` (Blue) | Totals, Counts, General metrics |
| **Premium/Special** | `#8b5cf6` (Purple) | Verified, Premium features |
| **Highlight** | `#06b6d4` (Cyan) | Active Rules, Selected items |

### Implementation

```css
/* BASE CARD - Solid with depth */
.metric-card {
  position: relative;
  background: #12121a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px 24px;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* TOP GRADIENT ACCENT (4px colored bar) */
.metric-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--card-accent);
  opacity: 0.9;
}

/* SHINE HIGHLIGHT (diagonal gloss) */
.metric-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 60%;
  height: 100%;
  background: linear-gradient(
    120deg,
    transparent,
    rgba(255, 255, 255, 0.03),
    rgba(255, 255, 255, 0.05),
    rgba(255, 255, 255, 0.03),
    transparent
  );
  transition: left 0.6s ease;
}

/* HOVER STATE - Shine sweep + glow */
.metric-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.4),
    0 0 20px var(--card-glow, rgba(10, 132, 255, 0.15));
}

.metric-card:hover::after {
  left: 100%;
}

/* ═══════════════════════════════════════════════════════════ */
/* COLOR VARIANTS                                               */
/* ═══════════════════════════════════════════════════════════ */

/* SUCCESS - Green (ROAS up, Active, Positive) */
.metric-card.success {
  --card-accent: linear-gradient(90deg, #22c55e, #16a34a);
  --card-glow: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.15);
}

/* WARNING - Amber (Needs attention) */
.metric-card.warning {
  --card-accent: linear-gradient(90deg, #f59e0b, #d97706);
  --card-glow: rgba(245, 158, 11, 0.2);
  border-color: rgba(245, 158, 11, 0.15);
}

/* ERROR - Red (Critical, Blocked) */
.metric-card.error {
  --card-accent: linear-gradient(90deg, #ef4444, #dc2626);
  --card-glow: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.15);
}

/* INFO - Blue (Neutral metrics, Totals) */
.metric-card.info {
  --card-accent: linear-gradient(90deg, #0a84ff, #0066cc);
  --card-glow: rgba(10, 132, 255, 0.2);
  border-color: rgba(10, 132, 255, 0.15);
}

/* PREMIUM - Purple (Verified, Special) */
.metric-card.premium {
  --card-accent: linear-gradient(90deg, #8b5cf6, #7c3aed);
  --card-glow: rgba(139, 92, 246, 0.2);
  border-color: rgba(139, 92, 246, 0.15);
}

/* ACTIVE - Cyan (Active rules, Selected) */
.metric-card.active {
  --card-accent: linear-gradient(90deg, #06b6d4, #0891b2);
  --card-glow: rgba(6, 182, 212, 0.2);
  border-color: rgba(6, 182, 212, 0.15);
}

/* ═══════════════════════════════════════════════════════════ */
/* INNER SHINE (Top edge highlight)                             */
/* ═══════════════════════════════════════════════════════════ */

.metric-card .card-content {
  position: relative;
}

.metric-card .card-content::before {
  content: '';
  position: absolute;
  top: 0;
  left: 10%;
  right: 10%;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent, 
    rgba(255, 255, 255, 0.15), 
    transparent
  );
}

/* ═══════════════════════════════════════════════════════════ */
/* METRIC VALUE COLORS (Match card accent)                      */
/* ═══════════════════════════════════════════════════════════ */

.metric-card.success .metric-value { color: #4ade80; }
.metric-card.warning .metric-value { color: #fbbf24; }
.metric-card.error .metric-value { color: #f87171; }
.metric-card.info .metric-value { color: #60a5fa; }
.metric-card.premium .metric-value { color: #a78bfa; }
.metric-card.active .metric-value { color: #22d3ee; }

/* ═══════════════════════════════════════════════════════════ */
/* PROGRESS BAR (Bottom of KPI cards)                           */
/* ═══════════════════════════════════════════════════════════ */

.progress-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  margin-top: 16px;
  overflow: hidden;
}

.progress-bar .fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

.metric-card.success .progress-bar .fill {
  background: linear-gradient(90deg, #22c55e, #4ade80);
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.5);
}

.metric-card.warning .progress-bar .fill {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
  box-shadow: 0 0 10px rgba(245, 158, 11, 0.5);
}

.metric-card.error .progress-bar .fill {
  background: linear-gradient(90deg, #ef4444, #f87171);
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
}

.metric-card.info .progress-bar .fill {
  background: linear-gradient(90deg, #0a84ff, #60a5fa);
  box-shadow: 0 0 10px rgba(10, 132, 255, 0.5);
}
```

### HTML Structure
```html
<!-- SUCCESS CARD (e.g., ROAS) -->
<div class="metric-card success">
  <div class="card-content">
    <span class="metric-label">ROAS</span>
    <span class="metric-badge">Top 25%</span>
    <div class="metric-value">3.50x</div>
    <div class="metric-subtext">Industry: 3.00x <span class="trend up">↗ 17%</span></div>
    <div class="progress-bar"><div class="fill" style="width: 85%"></div></div>
  </div>
</div>

<!-- INFO CARD (e.g., Total Rules) -->
<div class="metric-card info">
  <div class="card-content">
    <span class="metric-label">Total Rules</span>
    <div class="metric-value">6</div>
  </div>
</div>

<!-- ACTIVE CARD (e.g., Active Rules) -->
<div class="metric-card active">
  <div class="card-content">
    <span class="metric-label">Active Rules</span>
    <div class="metric-value">4</div>
  </div>
</div>

<!-- ERROR CARD (e.g., Blocked/Critical) -->
<div class="metric-card error">
  <div class="card-content">
    <span class="metric-label">Trust Gate</span>
    <span class="status-badge">BLOCK</span>
    <div class="metric-value">0/100</div>
  </div>
</div>
```

---

## ENHANCEMENT 3: APPLY TO SPECIFIC SCREENS

### Screen: Competitor Intelligence (Image 1)

| Card | Class | Reason |
|------|-------|--------|
| ROAS 3.50x | `.metric-card.success` | ↗ 17% positive |
| CTR 2.8% | `.metric-card.success` | ↗ 17% positive |
| CPC $1.2 | `.metric-card.success` | ↗ 8% (lower is better) |
| Conv. Rate 4.2% | `.metric-card.success` | ↗ 20% positive |

### Screen: Automation Rules (Image 2)

| Card | Class | Reason |
|------|-------|--------|
| Total Rules | `.metric-card.info` | Neutral count |
| Active Rules | `.metric-card.active` | Active state (cyan) |
| Triggers Today | `.metric-card.warning` | Activity metric |
| Actions Executed | `.metric-card.success` | Successful completions |

### Screen: User Management (Image 3)

| Card | Class | Reason |
|------|-------|--------|
| Total Users | `.metric-card.info` | Neutral count (white) |
| Active | `.metric-card.active` | Active state (cyan) |
| Admins | `.metric-card.premium` | Special role (purple) |
| Verified | `.metric-card.success` | Positive status (green) |

### Screen: Trust Gate Dashboard (Image 4)

| Card | Class | Reason |
|------|-------|--------|
| Trust Gate (Blocked) | `.metric-card.error` | Critical state |
| Signal Health (Empty) | `.metric-card.warning` | Needs attention |

---

## COMPLETE CSS BUNDLE

Copy this entire block to apply all enhancements:

```css
/* ═══════════════════════════════════════════════════════════════════════════
   STRATUM AI DASHBOARD ENHANCEMENTS
   - Dense Neural Network Background (15 nodes, 10 lines)
   - Colored Shiny Cards with Hover Effects
   ═══════════════════════════════════════════════════════════════════════════ */

/* ─────────────────────────────────────────────────────────────────────────────
   1. NEURAL NETWORK BACKGROUND
   ───────────────────────────────────────────────────────────────────────────── */

.neural-network-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.neural-node {
  position: absolute;
  width: 6px;
  height: 6px;
  background: rgba(10, 132, 255, 0.6);
  border-radius: 50%;
  box-shadow: 
    0 0 20px rgba(10, 132, 255, 0.4),
    0 0 40px rgba(10, 132, 255, 0.2);
  animation: nodePulse 3s ease-in-out infinite;
}

.neural-node:nth-child(1)  { top: 8%;  left: 15%; animation-delay: 0s; }
.neural-node:nth-child(2)  { top: 12%; left: 45%; animation-delay: 0.3s; }
.neural-node:nth-child(3)  { top: 6%;  left: 75%; animation-delay: 0.6s; }
.neural-node:nth-child(4)  { top: 25%; left: 25%; animation-delay: 0.9s; }
.neural-node:nth-child(5)  { top: 20%; left: 60%; animation-delay: 1.2s; }
.neural-node:nth-child(6)  { top: 30%; left: 85%; animation-delay: 1.5s; }
.neural-node:nth-child(7)  { top: 45%; left: 10%; animation-delay: 1.8s; }
.neural-node:nth-child(8)  { top: 50%; left: 40%; animation-delay: 2.1s; }
.neural-node:nth-child(9)  { top: 55%; left: 70%; animation-delay: 2.4s; }
.neural-node:nth-child(10) { top: 65%; left: 20%; animation-delay: 0.2s; }
.neural-node:nth-child(11) { top: 70%; left: 55%; animation-delay: 0.5s; }
.neural-node:nth-child(12) { top: 75%; left: 90%; animation-delay: 0.8s; }
.neural-node:nth-child(13) { top: 85%; left: 30%; animation-delay: 1.1s; }
.neural-node:nth-child(14) { top: 90%; left: 65%; animation-delay: 1.4s; }
.neural-node:nth-child(15) { top: 95%; left: 80%; animation-delay: 1.7s; }

.neural-node:nth-child(odd) { width: 4px; height: 4px; opacity: 0.5; }
.neural-node:nth-child(3n) { width: 8px; height: 8px; opacity: 0.8; }

.neural-line {
  position: absolute;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(10, 132, 255, 0.3), transparent);
  transform-origin: left center;
  animation: linePulse 4s ease-in-out infinite;
}

.neural-line:nth-child(16) { top: 10%; left: 17%; width: 200px; transform: rotate(5deg); animation-delay: 0s; }
.neural-line:nth-child(17) { top: 15%; left: 47%; width: 180px; transform: rotate(-10deg); animation-delay: 0.5s; }
.neural-line:nth-child(18) { top: 22%; left: 27%; width: 220px; transform: rotate(15deg); animation-delay: 1s; }
.neural-line:nth-child(19) { top: 35%; left: 12%; width: 190px; transform: rotate(25deg); animation-delay: 1.5s; }
.neural-line:nth-child(20) { top: 48%; left: 42%; width: 200px; transform: rotate(-5deg); animation-delay: 2s; }
.neural-line:nth-child(21) { top: 60%; left: 22%; width: 230px; transform: rotate(20deg); animation-delay: 0.3s; }
.neural-line:nth-child(22) { top: 72%; left: 57%; width: 210px; transform: rotate(-15deg); animation-delay: 0.8s; }
.neural-line:nth-child(23) { top: 80%; left: 32%; width: 200px; transform: rotate(10deg); animation-delay: 1.3s; }
.neural-line:nth-child(24) { top: 88%; left: 67%; width: 150px; transform: rotate(-8deg); animation-delay: 1.8s; }
.neural-line:nth-child(25) { top: 40%; left: 62%; width: 180px; transform: rotate(30deg); animation-delay: 2.3s; }

@keyframes nodePulse {
  0%, 100% { 
    opacity: 0.4; 
    transform: scale(1);
    box-shadow: 0 0 20px rgba(10, 132, 255, 0.3);
  }
  50% { 
    opacity: 1; 
    transform: scale(1.5);
    box-shadow: 0 0 30px rgba(10, 132, 255, 0.6), 0 0 60px rgba(10, 132, 255, 0.3);
  }
}

@keyframes linePulse {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.5; }
}

/* ─────────────────────────────────────────────────────────────────────────────
   2. COLORED SHINY CARDS
   ───────────────────────────────────────────────────────────────────────────── */

.metric-card {
  position: relative;
  background: #12121a;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px 24px;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--card-accent, linear-gradient(90deg, #0a84ff, #0066cc));
  opacity: 0.9;
}

.metric-card::after {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 60%;
  height: 100%;
  background: linear-gradient(120deg, transparent, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.03), transparent);
  transition: left 0.6s ease;
}

.metric-card:hover {
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px var(--card-glow, rgba(10, 132, 255, 0.15));
}

.metric-card:hover::after { left: 100%; }

/* Color Variants */
.metric-card.success {
  --card-accent: linear-gradient(90deg, #22c55e, #16a34a);
  --card-glow: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.15);
}

.metric-card.warning {
  --card-accent: linear-gradient(90deg, #f59e0b, #d97706);
  --card-glow: rgba(245, 158, 11, 0.2);
  border-color: rgba(245, 158, 11, 0.15);
}

.metric-card.error {
  --card-accent: linear-gradient(90deg, #ef4444, #dc2626);
  --card-glow: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.15);
}

.metric-card.info {
  --card-accent: linear-gradient(90deg, #0a84ff, #0066cc);
  --card-glow: rgba(10, 132, 255, 0.2);
  border-color: rgba(10, 132, 255, 0.15);
}

.metric-card.premium {
  --card-accent: linear-gradient(90deg, #8b5cf6, #7c3aed);
  --card-glow: rgba(139, 92, 246, 0.2);
  border-color: rgba(139, 92, 246, 0.15);
}

.metric-card.active {
  --card-accent: linear-gradient(90deg, #06b6d4, #0891b2);
  --card-glow: rgba(6, 182, 212, 0.2);
  border-color: rgba(6, 182, 212, 0.15);
}

/* Metric Value Colors */
.metric-card.success .metric-value { color: #4ade80; }
.metric-card.warning .metric-value { color: #fbbf24; }
.metric-card.error .metric-value { color: #f87171; }
.metric-card.info .metric-value { color: #60a5fa; }
.metric-card.premium .metric-value { color: #a78bfa; }
.metric-card.active .metric-value { color: #22d3ee; }

/* Progress Bar */
.progress-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  margin-top: 16px;
  overflow: hidden;
}

.progress-bar .fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

.metric-card.success .progress-bar .fill {
  background: linear-gradient(90deg, #22c55e, #4ade80);
  box-shadow: 0 0 10px rgba(34, 197, 94, 0.5);
}

.metric-card.warning .progress-bar .fill {
  background: linear-gradient(90deg, #f59e0b, #fbbf24);
  box-shadow: 0 0 10px rgba(245, 158, 11, 0.5);
}

.metric-card.error .progress-bar .fill {
  background: linear-gradient(90deg, #ef4444, #f87171);
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
}

.metric-card.info .progress-bar .fill {
  background: linear-gradient(90deg, #0a84ff, #60a5fa);
  box-shadow: 0 0 10px rgba(10, 132, 255, 0.5);
}

/* ─────────────────────────────────────────────────────────────────────────────
   3. TAB BAR / HORIZONTAL TAB NAVIGATION
   ───────────────────────────────────────────────────────────────────────────── */

.tab-bar {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #888;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab:hover {
  color: #ccc;
  background: rgba(255, 255, 255, 0.03);
}

.tab.active {
  background: #0a84ff;
  color: #fff;
  box-shadow: 0 2px 8px rgba(10, 132, 255, 0.3);
}

/* Tab with icon */
.tab svg,
.tab .icon {
  width: 16px;
  height: 16px;
  opacity: 0.7;
}

.tab.active svg,
.tab.active .icon {
  opacity: 1;
}

/* Tab Bar Color Variants */
.tab-bar.success .tab.active {
  background: #22c55e;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
}

.tab-bar.warning .tab.active {
  background: #f59e0b;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
}

.tab-bar.error .tab.active {
  background: #ef4444;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
}

.tab-bar.premium .tab.active {
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.3);
}

/* ─────────────────────────────────────────────────────────────────────────────
   4. ONBOARDING STEPPER / GETTING STARTED
   ───────────────────────────────────────────────────────────────────────────── */

.onboarding-stepper {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #12121a;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
}

/* Left side - Icon + Title + Progress */
.onboarding-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-right: 16px;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.onboarding-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}

.onboarding-icon svg {
  width: 24px;
  height: 24px;
  color: #fff;
}

.onboarding-title {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.onboarding-progress {
  font-size: 13px;
  font-weight: 500;
  color: #888;
  margin-left: 8px;
}

/* Right side - Step tabs */
.onboarding-steps {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.onboarding-step {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #888;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.onboarding-step svg {
  width: 16px;
  height: 16px;
  opacity: 0.6;
}

.onboarding-step:hover {
  color: #ccc;
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.03);
}

/* Completed step */
.onboarding-step.completed {
  border-color: rgba(34, 197, 94, 0.3);
  color: #4ade80;
}

.onboarding-step.completed svg {
  opacity: 1;
  color: #22c55e;
}

/* Active/Current step */
.onboarding-step.active {
  border-color: rgba(10, 132, 255, 0.5);
  background: rgba(10, 132, 255, 0.1);
  color: #60a5fa;
}

.onboarding-step.active svg {
  opacity: 1;
  color: #0a84ff;
}

/* Locked/Disabled step */
.onboarding-step.locked {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Step with checkmark (completed) */
.onboarding-step.completed::before {
  content: '✓';
  margin-right: 4px;
  color: #22c55e;
  font-weight: 700;
}

/* ─────────────────────────────────────────────────────────────────────────────
   5. BUTTONS
   ───────────────────────────────────────────────────────────────────────────── */

/* Base Button */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.btn svg {
  width: 16px;
  height: 16px;
}

/* Primary Button (Blue) */
.btn-primary {
  background: #0a84ff;
  color: #fff;
  box-shadow: 0 2px 8px rgba(10, 132, 255, 0.3);
}

.btn-primary:hover {
  background: #0070e0;
  box-shadow: 0 4px 12px rgba(10, 132, 255, 0.4);
  transform: translateY(-1px);
}

/* Secondary Button (Outline) */
.btn-secondary {
  background: transparent;
  color: #ccc;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.25);
  color: #fff;
}

/* Ghost Button (Text only) */
.btn-ghost {
  background: transparent;
  color: #888;
  padding: 8px 12px;
}

.btn-ghost:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
}

/* Danger Button (Red) */
.btn-danger {
  background: #ef4444;
  color: #fff;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
}

.btn-danger:hover {
  background: #dc2626;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
}

/* Success Button (Green) */
.btn-success {
  background: #22c55e;
  color: #fff;
  box-shadow: 0 2px 8px rgba(34, 197, 94, 0.3);
}

.btn-success:hover {
  background: #16a34a;
}

/* Icon Button (Square) */
.btn-icon {
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 8px;
}

/* Button Sizes */
.btn-sm { padding: 6px 12px; font-size: 12px; }
.btn-lg { padding: 14px 28px; font-size: 16px; }

/* Button Loading State */
.btn.loading {
  pointer-events: none;
  opacity: 0.7;
}

.btn.loading::after {
  content: '';
  width: 14px;
  height: 14px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Button Disabled */
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

/* ─────────────────────────────────────────────────────────────────────────────
   6. INPUTS & FORM FIELDS
   ───────────────────────────────────────────────────────────────────────────── */

/* Text Input */
.input {
  width: 100%;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  transition: all 0.2s ease;
}

.input::placeholder {
  color: #666;
}

.input:hover {
  border-color: rgba(255, 255, 255, 0.2);
}

.input:focus {
  outline: none;
  border-color: #0a84ff;
  box-shadow: 0 0 0 3px rgba(10, 132, 255, 0.15);
}

/* Input with icon (search) */
.input-wrapper {
  position: relative;
}

.input-wrapper .input-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  color: #666;
  pointer-events: none;
}

.input-wrapper .input {
  padding-left: 44px;
}

/* Input Error State */
.input.error {
  border-color: #ef4444;
}

.input.error:focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15);
}

.input-error-text {
  color: #f87171;
  font-size: 12px;
  margin-top: 6px;
}

/* Input Success State */
.input.success {
  border-color: #22c55e;
}

/* Label */
.label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #ccc;
  margin-bottom: 8px;
}

.label.required::after {
  content: ' *';
  color: #ef4444;
}

/* ─────────────────────────────────────────────────────────────────────────────
   7. SELECT / DROPDOWN
   ───────────────────────────────────────────────────────────────────────────── */

.select-wrapper {
  position: relative;
}

.select {
  width: 100%;
  padding: 12px 40px 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  appearance: none;
  transition: all 0.2s ease;
}

.select-wrapper::after {
  content: '';
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 5px solid #888;
  pointer-events: none;
}

.select:hover {
  border-color: rgba(255, 255, 255, 0.2);
}

.select:focus {
  outline: none;
  border-color: #0a84ff;
}

/* Dropdown Menu (Custom) */
.dropdown {
  position: relative;
  display: inline-block;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 200px;
  background: #1a1a24;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  padding: 6px;
  z-index: 100;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-8px);
  transition: all 0.2s ease;
}

.dropdown.open .dropdown-menu {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-radius: 6px;
  color: #ccc;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.dropdown-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
}

.dropdown-item.active {
  background: rgba(10, 132, 255, 0.15);
  color: #60a5fa;
}

.dropdown-item.danger {
  color: #f87171;
}

.dropdown-item.danger:hover {
  background: rgba(239, 68, 68, 0.1);
}

.dropdown-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.08);
  margin: 6px 0;
}

/* ─────────────────────────────────────────────────────────────────────────────
   8. TOGGLE / SWITCH
   ───────────────────────────────────────────────────────────────────────────── */

.toggle {
  position: relative;
  width: 44px;
  height: 24px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.toggle::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.toggle.active {
  background: #0a84ff;
}

.toggle.active::after {
  transform: translateX(20px);
}

/* Toggle with label */
.toggle-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toggle-label {
  font-size: 14px;
  color: #ccc;
}

/* ─────────────────────────────────────────────────────────────────────────────
   9. CHECKBOX & RADIO
   ───────────────────────────────────────────────────────────────────────────── */

/* Checkbox */
.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.checkbox {
  width: 18px;
  height: 18px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.checkbox.checked {
  background: #0a84ff;
  border-color: #0a84ff;
}

.checkbox.checked::after {
  content: '✓';
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.checkbox-label {
  font-size: 14px;
  color: #ccc;
}

/* Radio */
.radio {
  width: 18px;
  height: 18px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.radio.checked {
  border-color: #0a84ff;
}

.radio.checked::after {
  content: '';
  width: 8px;
  height: 8px;
  background: #0a84ff;
  border-radius: 50%;
}

/* ─────────────────────────────────────────────────────────────────────────────
   10. MODAL / DIALOG
   ───────────────────────────────────────────────────────────────────────────── */

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s ease;
}

.modal-overlay.open {
  opacity: 1;
  visibility: visible;
}

.modal {
  width: 100%;
  max-width: 500px;
  background: #1a1a24;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  box-shadow: 0 16px 64px rgba(0, 0, 0, 0.5);
  transform: scale(0.95) translateY(20px);
  transition: transform 0.2s ease;
}

.modal-overlay.open .modal {
  transform: scale(1) translateY(0);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.modal-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #888;
  cursor: pointer;
  transition: all 0.15s ease;
}

.modal-close:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
}

.modal-body {
  padding: 24px;
  color: #ccc;
  font-size: 14px;
  line-height: 1.6;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

/* Modal Sizes */
.modal.sm { max-width: 400px; }
.modal.lg { max-width: 700px; }
.modal.xl { max-width: 900px; }

/* ─────────────────────────────────────────────────────────────────────────────
   11. BADGES / TAGS
   ───────────────────────────────────────────────────────────────────────────── */

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-radius: 6px;
}

.badge-default {
  background: rgba(255, 255, 255, 0.1);
  color: #ccc;
}

.badge-primary {
  background: rgba(10, 132, 255, 0.15);
  color: #60a5fa;
}

.badge-success {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.badge-warning {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
}

.badge-error {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.badge-premium {
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
}

/* Pill Badge (Rounded) */
.badge-pill {
  border-radius: 100px;
  padding: 4px 12px;
}

/* Badge with dot */
.badge-dot::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

/* ─────────────────────────────────────────────────────────────────────────────
   12. ALERTS / TOAST NOTIFICATIONS
   ───────────────────────────────────────────────────────────────────────────── */

.alert {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  border-left: 4px solid;
}

.alert-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.alert-message {
  font-size: 13px;
  color: #aaa;
}

.alert-info {
  background: rgba(10, 132, 255, 0.1);
  border-color: #0a84ff;
}
.alert-info .alert-icon,
.alert-info .alert-title { color: #60a5fa; }

.alert-success {
  background: rgba(34, 197, 94, 0.1);
  border-color: #22c55e;
}
.alert-success .alert-icon,
.alert-success .alert-title { color: #4ade80; }

.alert-warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: #f59e0b;
}
.alert-warning .alert-icon,
.alert-warning .alert-title { color: #fbbf24; }

.alert-error {
  background: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
}
.alert-error .alert-icon,
.alert-error .alert-title { color: #f87171; }

/* Toast (Floating notification) */
.toast-container {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: #1a1a24;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  min-width: 300px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.toast-success { border-left: 4px solid #22c55e; }
.toast-error { border-left: 4px solid #ef4444; }
.toast-warning { border-left: 4px solid #f59e0b; }
.toast-info { border-left: 4px solid #0a84ff; }

/* ─────────────────────────────────────────────────────────────────────────────
   13. TOOLTIP
   ───────────────────────────────────────────────────────────────────────────── */

.tooltip-wrapper {
  position: relative;
  display: inline-block;
}

.tooltip {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 12px;
  background: #2a2a36;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: #fff;
  font-size: 12px;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: all 0.15s ease;
  z-index: 100;
}

.tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: #2a2a36;
}

.tooltip-wrapper:hover .tooltip {
  opacity: 1;
  visibility: visible;
}

/* ─────────────────────────────────────────────────────────────────────────────
   14. AVATAR
   ───────────────────────────────────────────────────────────────────────────── */

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0a84ff, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-sm { width: 32px; height: 32px; font-size: 12px; }
.avatar-lg { width: 56px; height: 56px; font-size: 18px; }
.avatar-xl { width: 80px; height: 80px; font-size: 24px; }

/* Avatar with status */
.avatar-wrapper {
  position: relative;
  display: inline-block;
}

.avatar-status {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #12121a;
}

.avatar-status.online { background: #22c55e; }
.avatar-status.offline { background: #888; }
.avatar-status.busy { background: #ef4444; }

/* Avatar Group */
.avatar-group {
  display: flex;
}

.avatar-group .avatar {
  margin-left: -12px;
  border: 2px solid #12121a;
}

.avatar-group .avatar:first-child {
  margin-left: 0;
}

/* ─────────────────────────────────────────────────────────────────────────────
   15. TABLE
   ───────────────────────────────────────────────────────────────────────────── */

.table-wrapper {
  overflow-x: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.table th {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #888;
  background: rgba(255, 255, 255, 0.02);
}

.table td {
  font-size: 14px;
  color: #ccc;
}

.table tbody tr {
  transition: background 0.15s ease;
}

.table tbody tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

/* Table row selection */
.table tbody tr.selected {
  background: rgba(10, 132, 255, 0.1);
}

/* ─────────────────────────────────────────────────────────────────────────────
   16. LOADING STATES
   ───────────────────────────────────────────────────────────────────────────── */

/* Spinner */
.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: #0a84ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-sm { width: 16px; height: 16px; border-width: 2px; }
.spinner-lg { width: 40px; height: 40px; border-width: 4px; }

/* Skeleton Loader */
.skeleton {
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.03) 0%,
    rgba(255, 255, 255, 0.08) 50%,
    rgba(255, 255, 255, 0.03) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 6px;
}

.skeleton-text {
  height: 14px;
  margin-bottom: 8px;
}

.skeleton-title {
  height: 24px;
  width: 60%;
  margin-bottom: 12px;
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.skeleton-card {
  height: 120px;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* ─────────────────────────────────────────────────────────────────────────────
   17. EMPTY STATE
   ───────────────────────────────────────────────────────────────────────────── */

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.empty-state-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: #555;
}

.empty-state-title {
  font-size: 16px;
  font-weight: 600;
  color: #ccc;
  margin-bottom: 8px;
}

.empty-state-message {
  font-size: 14px;
  color: #888;
  margin-bottom: 20px;
  max-width: 300px;
}

/* ─────────────────────────────────────────────────────────────────────────────
   18. SIDEBAR NAVIGATION
   ───────────────────────────────────────────────────────────────────────────── */

.sidebar {
  width: 260px;
  height: 100vh;
  background: #0d0d12;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: 20px 0;
  position: fixed;
  left: 0;
  top: 0;
  display: flex;
  flex-direction: column;
}

.sidebar-logo {
  padding: 0 20px;
  margin-bottom: 24px;
}

.sidebar-section {
  padding: 0 12px;
  margin-bottom: 24px;
}

.sidebar-section-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #555;
  padding: 0 12px;
  margin-bottom: 8px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #888;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.15s ease;
}

.sidebar-link svg {
  width: 18px;
  height: 18px;
  opacity: 0.6;
}

.sidebar-link:hover {
  background: rgba(255, 255, 255, 0.03);
  color: #ccc;
}

.sidebar-link.active {
  background: rgba(10, 132, 255, 0.1);
  color: #60a5fa;
}

.sidebar-link.active svg {
  opacity: 1;
  color: #0a84ff;
}

/* Sidebar badge (notification count) */
.sidebar-link .badge {
  margin-left: auto;
  padding: 2px 8px;
  font-size: 10px;
}

/* ─────────────────────────────────────────────────────────────────────────────
   19. CIRCUIT GRID (Optional - adds tech feel)
   ───────────────────────────────────────────────────────────────────────────── */

.circuit-grid {
  position: fixed;
  inset: 0;
  background-image: 
    linear-gradient(rgba(10, 132, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(10, 132, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 1;
}
```

---

## QUICK REFERENCE

### Card Class Decision

```
Is metric positive/up?     → .metric-card.success (green)
Is metric negative/down?   → .metric-card.error (red)
Needs attention?           → .metric-card.warning (amber)
Neutral count/total?       → .metric-card.info (blue)
Special/verified status?   → .metric-card.premium (purple)
Active/selected state?     → .metric-card.active (cyan)
```

### Copy-Paste HTML for Buttons

```html
<!-- Primary -->
<button class="btn btn-primary">
  <svg><!-- icon --></svg>
  Create Rule
</button>

<!-- Secondary (Outline) -->
<button class="btn btn-secondary">Cancel</button>

<!-- Danger -->
<button class="btn btn-danger">Delete</button>

<!-- Ghost -->
<button class="btn btn-ghost">View Details</button>

<!-- Icon Button -->
<button class="btn btn-icon btn-secondary">
  <svg><!-- refresh icon --></svg>
</button>

<!-- Loading -->
<button class="btn btn-primary loading">Saving...</button>
```

### Copy-Paste HTML for Inputs

```html
<!-- Basic Input -->
<div>
  <label class="label required">Email Address</label>
  <input type="email" class="input" placeholder="you@example.com">
</div>

<!-- Search Input with Icon -->
<div class="input-wrapper">
  <svg class="input-icon"><!-- search icon --></svg>
  <input type="text" class="input" placeholder="Search...">
</div>

<!-- Input with Error -->
<div>
  <label class="label">Password</label>
  <input type="password" class="input error">
  <p class="input-error-text">Password must be at least 8 characters</p>
</div>
```

### Copy-Paste HTML for Select/Dropdown

```html
<!-- Native Select -->
<div class="select-wrapper">
  <select class="select">
    <option>All Platforms</option>
    <option>Meta</option>
    <option>Google</option>
    <option>TikTok</option>
  </select>
</div>

<!-- Custom Dropdown -->
<div class="dropdown open">
  <button class="btn btn-secondary">Options</button>
  <div class="dropdown-menu">
    <div class="dropdown-item">Edit</div>
    <div class="dropdown-item">Duplicate</div>
    <div class="dropdown-divider"></div>
    <div class="dropdown-item danger">Delete</div>
  </div>
</div>
```

### Copy-Paste HTML for Toggle/Switch

```html
<div class="toggle-wrapper">
  <div class="toggle active"></div>
  <span class="toggle-label">Enable Automation</span>
</div>
```

### Copy-Paste HTML for Checkbox/Radio

```html
<!-- Checkbox -->
<label class="checkbox-wrapper">
  <div class="checkbox checked"></div>
  <span class="checkbox-label">Remember me</span>
</label>

<!-- Radio -->
<label class="checkbox-wrapper">
  <div class="radio checked"></div>
  <span class="checkbox-label">Option A</span>
</label>
```

### Copy-Paste HTML for Modal

```html
<div class="modal-overlay open">
  <div class="modal">
    <div class="modal-header">
      <h3 class="modal-title">Confirm Action</h3>
      <button class="modal-close">✕</button>
    </div>
    <div class="modal-body">
      Are you sure you want to delete this automation rule? This action cannot be undone.
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary">Cancel</button>
      <button class="btn btn-danger">Delete Rule</button>
    </div>
  </div>
</div>
```

### Copy-Paste HTML for Badges

```html
<span class="badge badge-success">Active</span>
<span class="badge badge-warning">Pending</span>
<span class="badge badge-error">Failed</span>
<span class="badge badge-primary">New</span>
<span class="badge badge-premium badge-pill">Pro</span>
<span class="badge badge-success badge-dot">Online</span>
```

### Copy-Paste HTML for Alerts

```html
<!-- Success Alert -->
<div class="alert alert-success">
  <svg class="alert-icon"><!-- check icon --></svg>
  <div class="alert-content">
    <div class="alert-title">Rule Created Successfully</div>
    <div class="alert-message">Your automation rule is now active and monitoring.</div>
  </div>
</div>

<!-- Error Alert -->
<div class="alert alert-error">
  <svg class="alert-icon"><!-- x icon --></svg>
  <div class="alert-content">
    <div class="alert-title">Connection Failed</div>
    <div class="alert-message">Unable to connect to Meta Ads. Please try again.</div>
  </div>
</div>
```

### Copy-Paste HTML for Toast

```html
<div class="toast-container">
  <div class="toast toast-success">
    <svg><!-- check icon --></svg>
    <span>Settings saved successfully</span>
  </div>
</div>
```

### Copy-Paste HTML for Tooltip

```html
<div class="tooltip-wrapper">
  <button class="btn btn-icon btn-secondary">
    <svg><!-- info icon --></svg>
  </button>
  <div class="tooltip">Click to refresh data</div>
</div>
```

### Copy-Paste HTML for Avatar

```html
<!-- Basic Avatar -->
<div class="avatar">JD</div>

<!-- Avatar with Image -->
<div class="avatar">
  <img src="user.jpg" alt="John Doe">
</div>

<!-- Avatar with Status -->
<div class="avatar-wrapper">
  <div class="avatar">JD</div>
  <span class="avatar-status online"></span>
</div>

<!-- Avatar Group -->
<div class="avatar-group">
  <div class="avatar">JD</div>
  <div class="avatar">AB</div>
  <div class="avatar">+3</div>
</div>
```

### Copy-Paste HTML for Table

```html
<div class="table-wrapper">
  <table class="table">
    <thead>
      <tr>
        <th>Name</th>
        <th>Status</th>
        <th>Platform</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Campaign Alpha</td>
        <td><span class="badge badge-success">Active</span></td>
        <td>Meta</td>
        <td><button class="btn btn-ghost btn-sm">Edit</button></td>
      </tr>
    </tbody>
  </table>
</div>
```

### Copy-Paste HTML for Loading States

```html
<!-- Spinner -->
<div class="spinner"></div>
<div class="spinner spinner-lg"></div>

<!-- Skeleton -->
<div class="skeleton skeleton-title"></div>
<div class="skeleton skeleton-text"></div>
<div class="skeleton skeleton-text" style="width: 80%"></div>
<div class="skeleton skeleton-card"></div>
```

### Copy-Paste HTML for Empty State

```html
<div class="empty-state">
  <svg class="empty-state-icon"><!-- inbox icon --></svg>
  <h3 class="empty-state-title">No signal health data available</h3>
  <p class="empty-state-message">Connect an ad platform to start monitoring your signal health.</p>
  <button class="btn btn-primary">Connect Platform</button>
</div>
```

### Copy-Paste HTML for Sidebar

```html
<aside class="sidebar">
  <div class="sidebar-logo">
    <img src="logo.svg" alt="Stratum AI">
  </div>
  
  <div class="sidebar-section">
    <div class="sidebar-section-title">Main</div>
    <nav class="sidebar-nav">
      <a href="#" class="sidebar-link active">
        <svg><!-- dashboard icon --></svg>
        Dashboard
      </a>
      <a href="#" class="sidebar-link">
        <svg><!-- chart icon --></svg>
        Analytics
        <span class="badge badge-primary">3</span>
      </a>
      <a href="#" class="sidebar-link">
        <svg><!-- zap icon --></svg>
        Automation
      </a>
    </nav>
  </div>
  
  <div class="sidebar-section">
    <div class="sidebar-section-title">Settings</div>
    <nav class="sidebar-nav">
      <a href="#" class="sidebar-link">
        <svg><!-- settings icon --></svg>
        Settings
      </a>
    </nav>
  </div>
</aside>
```

### Copy-Paste HTML for Onboarding Stepper

```html
<div class="onboarding-stepper">
  <!-- Left: Icon + Title + Progress -->
  <div class="onboarding-header">
    <div class="onboarding-icon">
      <svg><!-- rocket/star icon --></svg>
    </div>
    <span class="onboarding-title">Getting Started</span>
    <span class="onboarding-progress">0/6</span>
  </div>
  
  <!-- Right: Step Tabs -->
  <div class="onboarding-steps">
    <button class="onboarding-step completed">
      <svg><!-- link icon --></svg>
      Connect an Ad Platform
    </button>
    <button class="onboarding-step active">
      <svg><!-- users icon --></svg>
      Create a CDP Segment
    </button>
    <button class="onboarding-step">
      <svg><!-- zap icon --></svg>
      Configure an Automation Rule
    </button>
    <button class="onboarding-step locked">
      <svg><!-- chart icon --></svg>
      Review Signal Health
    </button>
  </div>
</div>
```

### Copy-Paste HTML for Tab Bar

```html
<nav class="tab-bar">
  <button class="tab">
    <svg><!-- icon --></svg>
    Posts
  </button>
  <button class="tab active">
    <svg><!-- icon --></svg>
    Pages
  </button>
  <button class="tab">
    <svg><!-- icon --></svg>
    Categories
  </button>
  <button class="tab">
    <svg><!-- icon --></svg>
    Tags
  </button>
  <button class="tab">
    <svg><!-- icon --></svg>
    Authors
  </button>
  <button class="tab">
    <svg><!-- icon --></svg>
    Contact Inbox
  </button>
</nav>
```

### Copy-Paste HTML for Neural Background

```html
<div class="neural-network-bg">
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-node"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
  <div class="neural-line"></div>
</div>
<div class="circuit-grid"></div>
```

---

**Version:** 1.0  
**For:** Stratum AI Dashboard Updates  
**Maintains:** NN/g compliance (solid cards, no transparency on data)
