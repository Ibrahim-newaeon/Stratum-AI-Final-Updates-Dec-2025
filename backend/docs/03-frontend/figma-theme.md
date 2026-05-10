# Figma Theme — Stratum AI

The dashboard, auth flow, and marketing surfaces all read from the figma
theme system, designed dual-mode with semantic CSS variables in
`frontend/src/index.css` and Tailwind aliases in
`frontend/tailwind.config.js`.

## Tokens

### Surfaces

| Token                  | Dark              | Light                    | Use              |
| ---------------------- | ----------------- | ------------------------ | ---------------- |
| `--background`         | `#0B0B0B` ink     | `#FAFAF7` warm off-white | Page bg          |
| `--card` / `--popover` | `#141414` surface | `#FFFFFF`                | Card / panel bg  |
| `--surface-tertiary`   | `#1A1A1A`         | `#F0EFE8`                | Elevated card    |
| `--muted`              | `#262626` line2   | `#F0EFE8`                | Subtle fills     |
| `--border` / `--input` | `#1F1F1F` line    | `#E8E8E0`                | Hairline borders |

### Typography

| Token                   | Dark       | Light              | Use                     |
| ----------------------- | ---------- | ------------------ | ----------------------- |
| `--foreground`          | `#FFFFFF`  | `#1A1A1A` charcoal | Primary text            |
| `--muted-foreground`    | `#9A9A9A`  | `#5A5A55`          | Secondary text          |
| Font family `font-sans` | Geist      | Geist              | Body + display          |
| Font family `font-mono` | Geist Mono | Geist Mono         | Labels, status, tabular |

### Brand & status

| Token                        | Dark              | Light                       | Use                                |
| ---------------------------- | ----------------- | --------------------------- | ---------------------------------- |
| `--primary`                  | `#FF5A1F` ember   | `#E84F1F` desaturated ember | CTA, accent, focus ring            |
| `--secondary` / `--insight`  | `#FF8A4A` ember-2 | `#FF8A4A`                   | Gradient stop, hover               |
| `--accent` / `--info`        | `#06B6D4` cyan    | `#0891B2`                   | Multi-series chart, neutral signal |
| `--success`                  | `#10B981`         | `#059669`                   | Healthy / pass                     |
| `--warning`                  | `#F59E0B`         | `#D97706`                   | Hold / degraded                    |
| `--danger` / `--destructive` | `#EF4444`         | `#DC2626`                   | Block / unhealthy                  |

### Geometry

| Token           | Value                    | Use                          |
| --------------- | ------------------------ | ---------------------------- |
| `--radius`      | `1rem` (16px)            | `rounded-2xl` cards, default |
| Radii           | 8 / 12 / 14 / 16 / 18 px | Sm → 2xl                     |
| Card padding    | `p-6` minimum            | Surfaces                     |
| Buttons / pills | `rounded-full`           | All clickable affordances    |

## Theme system

`frontend/src/components/primitives/theme/ThemeProvider.tsx` wraps the
app and exposes:

- `theme: 'dark' | 'light' | 'system'`
- `resolvedTheme: 'dark' | 'light'` (what's actually applied)
- `setTheme(theme)`

Persists to `localStorage('stratum-theme')`. Defaults to `'system'`,
which resolves via `window.matchMedia('(prefers-color-scheme: dark)')`.

The initial paint is handled by an inline `<script>` in
`frontend/index.html` that applies the correct class to `<html>` before
React mounts — this avoids the dreaded theme flash. A
`theme-no-transition` guard on the root suppresses the cross-fade
transition during that initial swap, then is removed on the next
animation frame so user-driven toggles animate smoothly.

`ThemeToggle` (in `primitives/theme/ThemeToggle.tsx`) renders a
segmented sun / moon / system control; lives in the topbar.

## Primitive library

```
frontend/src/components/primitives/
├── Card.tsx              ← rounded-2xl surface, default/elevated/glow variants
├── KPI.tsx               ← composed Card + label + value + delta + status
├── StatusPill.tsx        ← figma signature pill (healthy/degraded/unhealthy/neutral)
├── Chart.tsx             ← themed recharts wrapper (LineChart, AreaChart)
├── DataTable.tsx         ← headless table with sort + loading + empty
├── ConfirmDrawer.tsx     ← destructive-action preview-then-confirm gate
├── nav/
│   ├── Sidebar.tsx           ← collapsible-group nav (Operate/Intelligence/Account)
│   ├── Topbar.tsx            ← search + theme toggle + profile
│   └── dashboardNav.ts       ← IA config (typed group definition)
└── theme/
    ├── ThemeProvider.tsx     ← dark/light/system + localStorage + matchMedia
    └── ThemeToggle.tsx       ← sun/moon/system segmented control
```

Every primitive ships with a vitest at `*.test.tsx`. ARIA + keyboard
support are first-class. Loading / empty / error states are explicit
props on every data-bearing primitive — no caller-side branching
required.

## Dashboard home

`frontend/src/views/dashboard/Overview.tsx` is the post-login
"what needs my attention" surface composed entirely from primitives.

Composition (top → bottom):

1. **KpiStrip** — 4 compact cards (Trust Gate / Signal Health / ROAS /
   Pacing). The most-attention-needing card uses `Card variant="glow"`
   for emphasis.
2. **SignalStrip** — alert chips per severity bucket; click drives
   the FocusPane. Collapses to "All clear" when alerts = 0.
3. **FocusPane** — URL-driven adaptive surface. `?focus=trust-holds`
   renders a DataTable with per-row CTAs; `signal-drops` shows the EMQ
   pipeline view; `pacing-breaches` shows a budget-burn table;
   `autopilot-pending` filters the autopilot stream; `all-clear`
   shows a 30d revenue/spend chart.
4. **RecentAutopilot** — last 24h decisions DataTable, always present.

Data flows through `views/dashboard/overview/useOverviewData.ts` —
the single seam between primitives and the API. It calls the existing
React Query hooks (`useDashboardOverview`, `useTrustStatus`,
`useDashboardSignalHealth`, `usePacingSummary`, `useAutopilotActions`)
in parallel and falls back to deterministic mocks
(`overview/mockData.ts`) when tenant context is missing or a single
endpoint is unavailable. The `isMock` flag drives a "Demo data" pill
in the page header so testers can tell at a glance.

## Sidebar IA

The product has 25 dashboard routes; the figma brief asks for 3 sidebar
items. `dashboardNavGroups` (in `nav/dashboardNav.ts`) reconciles by
splitting the routes into 3 collapsible groups:

```
Operate       Overview · Campaigns · Autopilot · Audiences ·
              Trust Engine · Pacing
Intelligence  CDP · Attribution · Reporting · Insights · Anomalies
Account       Integrations · Settings · Billing · Team · (Superadmin)
```

The Sidebar primitive auto-expands the group containing the active
route on mount and on route changes — no manual expand needed when
navigating from an Overview into a CDP sub-page. Collapse state
persists per-user via `localStorage('stratum-sidebar-groups')`.

## Migrations

The legacy "Nebula Aurora" theme (cyber-pink `#FF1F6D`, midnight
`#080C14`, Satoshi + Clash Display) is fully retired across the
codebase via the 6-phase commit chain
`a189ff6 → 36a86c0`. The `frontend/scripts/sweep-hex.sh` script remains
in the repo for catching future palette stragglers. The doc
`nebula-aurora-design.md` is now historical reference only.

## When in doubt

- **Use semantic Tailwind tokens** (`bg-card`, `text-foreground`,
  `border-border`, `text-primary`) over hardcoded hex.
- **Use `text-muted-foreground`** instead of `text-gray-400 dark:text-gray-300`.
- **Compose primitives** before building bespoke surfaces.
- **Glow only for primary KPI** — overuse cheapens the effect.
- **Mono for labels and status**, Geist for body and display.
