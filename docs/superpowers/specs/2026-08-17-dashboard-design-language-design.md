# Dashboard design language — exemplar screens

**Date:** 2026-08-17
**Status:** Approved, ready for implementation planning

## Why

The figma theme system exists and works. It reaches almost nothing.

- 10 primitives, each with a vitest: `Card`, `KPI`, `StatusPill`, `Chart`,
  `DataTable`, `ConfirmDrawer`, `InsightsPanel`, `Sidebar`, `Topbar`,
  `ThemeProvider` / `ThemeToggle`.
- The dashboard home (`views/dashboard/Overview.tsx`) is composed from them,
  routed, and live.
- **6 of 37 dashboard views import a primitive.** The other ~30, about 22,200
  lines, are on hand-rolled markup.

The brief for this work, in the product owner's words: *a look and feel that
reflects professionalism and expertise; simple and easy to navigate, not
crowded; and at the same time reflects that it is not easy to build.*

That is close to what `CLAUDE.md` already specifies — quiet authority,
information density without clutter, earn every pixel. The gap is not direction.
The gap is that the spec only ever proved itself on one screen, the home triage
view, and never defined what a **dense operational screen** looks like.

So this is not a re-theme. The invariants hold; the layer above them gets
defined, on three real screens, and each screen establishes an archetype the
remaining views can follow.

## Invariants (not open for revision)

From `backend/docs/03-frontend/figma-theme.md`:

- Ink `#0B0B0B` bg · surface `#141414` · line `#1F1F1F` · ember `#FF5A1F`
  accent · cyan `#06B6D4` info. Light mode per the token table.
- Geist (sans/display) + Geist Mono. No other families.
- Hairline 1px borders, `rounded-2xl` (`--radius: 1rem`), `rounded-full` on all
  clickable affordances.
- No glassmorphism, no drop shadows, no gradient fills.
- Semantic Tailwind tokens (`bg-card`, `text-muted-foreground`,
  `border-border`) over hardcoded hex.
- Dark and light are both first-class.

## What this work decides

The layer the theme spec never covered:

1. Page shell and header rhythm
2. Spacing and density for data-dense screens
3. Table row height, alignment, and separator treatment
4. Where ember is permitted to appear
5. Loading / empty / error treatment on data surfaces
6. How status reads at a glance, consistently

## Scope

Three exemplar screens, chosen because they are three genuinely different
layout problems and all three sit in the core journey.

| Screen | Route | Current state | Work |
| --- | --- | --- | --- |
| Campaigns | `/dashboard/campaigns` | `views/Campaigns.tsx`, 621 lines, no primitives. Local `StatusBadge`; hand-rolled `<table>`/`<td>`. | Rewrite |
| Rules | `/dashboard/rules` | `views/Rules.tsx`, 555 lines, no primitives. Local `getStatusBadge`; create/edit in a modal. | Rewrite |
| Trust Engine | `/dashboard/trust` | **No screen exists.** `/dashboard/trust-engine` redirects to `/dashboard/trust`, which renders `TenantAdminOverview` (`views/tenant/Overview.tsx`, 469 lines, no primitives) — a generic tenant admin page. | **Net-new design** |

The Trust Engine finding is the significant one: the sidebar's flagship
destination, for the feature the product is named around, currently points at a
generic overview. There is nothing to migrate. It has to be designed.

### Archetypes established

Each exemplar defines a pattern the remaining views inherit, so migration
becomes application rather than invention.

- **Operational list** (Campaigns) → ~12 views: Audiences, Segments, Profiles,
  Events, Reports, Tenants, API Keys, Assets, and similar.
- **Authoring** (Rules) → ~8 views: Custom Autopilot Rules, Drip Campaigns,
  Custom Report Builder, CAPI Setup, and similar.
- **Diagnostic** (Trust Engine) → ~6 views: Pacing, Attribution, Anomalies,
  Signal Health. `EMQ Diagnostics` is already migrated and serves as a
  reference point.

### Included because the exemplars cannot be done without it

**Consolidate three status-badge implementations onto `StatusPill`.**
`Campaigns.tsx` defines `StatusBadge`, `Rules.tsx` defines `getStatusBadge`,
and `StatusPill` exists as a tested primitive. Consistent status semantics
cannot be designed while three screens each define their own colours. This is a
precondition, not scope creep.

## The page shell

Applies to all three exemplars and to every view migrated afterwards.

```
┌─────────────────────────────────────────────────────────────┐
│  Campaigns                              [ + New campaign ]  │  h1 + primary action
│  6 active · 2 held by trust gate                            │  context line
├─────────────────────────────────────────────────────────────┤  hairline, full bleed
│  SPEND 24H      ROAS        PACING       TRUST              │  inline stat row
│  $12,480        3.42×       94%          HEALTHY            │
├─────────────────────────────────────────────────────────────┤
│  [search]   All | Active | Paused | Held      Platform ▾    │  filter bar
├─────────────────────────────────────────────────────────────┤
│  … content …                                                │
```

**Header.** `h1` at 28px display semibold. No eyebrow, no breadcrumb — the
sidebar already states location. Primary action right-aligned, `rounded-full`,
ember. At most one secondary action beside it, ghost style.

**The context line states the decision the screen supports, not what the screen
is.** "6 active · 2 held by trust gate" tells the user whether they need to act.
"Manage your campaigns" tells them nothing. Every migrated view gets this
treatment, and writing it is part of migrating a view.

**KPIs are an inline stat row, not cards.** This is the primary anti-crowding
decision. Four bordered cards atop every list screen is what makes a dashboard
feel busy, and it dilutes `Card variant="glow"`, which the theme spec reserves
for emphasis on the home view. Figures are Geist Mono with `tabular-nums`,
labels are mono uppercase at 11px in `--muted-foreground`, separated by vertical
hairlines. Weight comes from typography, not containers.

**Ember appears once per screen: the primary action.** Status colour comes from
`StatusPill`'s own semantics and does not count against this. Threshold markers
on the Trust Engine chart are the one documented exception.

**Density.** Table row height 52px. A comfortable/compact toggle was considered
and cut — one correct row height beats a control the user has to reason about.

**Separators.** Hairlines only. No zebra striping, no shadows, no card-per-row.

## Archetype 1 — operational list (Campaigns)

Built on `DataTable`.

Columns: **Campaign** (name, platform as a mono sub-label) · **Status**
(`StatusPill`) · **Spend** · **Budget** · **ROAS** · **Conversions** · row
actions.

- Numeric columns right-aligned, Geist Mono, `tabular-nums`.
- Row actions (view / edit / pause-activate) are revealed on row hover and
  focus, and are always reachable by keyboard. This is how a row stays
  uncluttered without losing accessibility.
- Filter bar: search, status segmented control, platform dropdown. One row,
  hairline beneath.
- Existing data hooks are retained: `useCampaigns`, `usePauseCampaign`,
  `useActivateCampaign`, `useDeleteCampaign`, `usePriceMetrics`.

**A per-campaign Trust column was designed and cut.** It would have been the
product's differentiator expressed as a table column — no competitor's campaign
list says whether automation is allowed to touch a given row. But
`CampaignWithMetrics` (`frontend/src/api/campaigns.ts:49`) carries no trust or
pacing field, and both signals are tenant-level rather than per-campaign.
Shipping the column would have meant fabricating its values.

Adding it is backend work: per-campaign gate state on the campaigns list
response. Worth doing — it is the single highest-value addition to this screen —
but it needs its own spec, and the exemplar ships against real fields until then.
The column order above leaves room to insert it without redesigning the row.

## Archetype 2 — authoring (Rules)

Built on `DataTable` + `ConfirmDrawer`.

**Modal becomes a right-hand drawer.** `Rules.tsx` currently opens
`showCreateModal`. A modal blanks the context being edited against; a drawer
keeps the rule list visible while the rule is written. `ConfirmDrawer` already
establishes the drawer pattern, so this is reuse.

- Form is single-column, grouped by mono uppercase section labels, with inline
  validation and a sticky footer (Cancel / Save).
- Saving a rule that changes automation behaviour routes through
  `ConfirmDrawer`: preview the change, then confirm.
- Existing hooks retained: `useRules`, `useToggleRule`, `useDuplicateRule`,
  `useUpdateRule`.

## Archetype 3 — diagnostic (Trust Engine)

Net-new. This screen carries the "not easy to build" weight.

### Designed against the data that exists, not the data that is documented

`CLAUDE.md` describes signal health as a weighted composite — EMQ 35%, API
health 25%, event loss 20%, platform stability 10%, data quality 10%. **That
model is not implemented.** `backend/app/analytics/logic/signal_health.py`
computes status from three inputs against thresholds:

- `emq_score` vs `params.emq_healthy` / `params.emq_risk`
- `event_loss_pct` vs `params.event_loss_risk`
- `api_health` (boolean)

There is no `platform_stability`, no `data_quality`, and no 35/25/20/10/10
weighting anywhere in `analytics/logic/`. (EMQ itself *is* internally weighted,
in `emq_calculation.py`, but that produces the EMQ score — not the signal-health
composite.)

The first draft of this screen was designed around the documented five-component
table. Building it would have meant inventing four numbers in the UI. The screen
below is designed against the real calculator instead.

What the calculator does emit is better material anyway: **human-readable reason
strings carrying the value and the target** — e.g. `"EMQ score below target:
78.0 (target: 90)"`. That is the product showing its work, generated by the
system rather than drawn by a designer.

```
┌──────────────────────────────────────────────────────────────┐
│  Trust Engine                                                │
│  Autopilot enabled — signals healthy                         │
├──────────────────────────────────────────────────────────────┤
│                                    │                         │
│    ● HEALTHY                       │   30-day signal health  │
│    gate: PASS                      │   ╭─────────────╮       │
│    unchanged for 6 days            │   │      ∙∙∙∙∙∙∙│       │
│                                    │   │∙∙∙∙∙∙  ─────│ risk  │
│                                    │   ╰─────────────╯       │
├────────────────────────────────────┴─────────────────────────┤
│  INPUT                     VALUE      TARGET        STATUS   │
│  Event match quality        78.0        90          ● below  │
│  Event loss                  2.1%      < 5%         ● ok     │
│  API health                 all ok      —           ● ok     │
│                                                              │
│  “EMQ score below target: 78.0 (target: 90)”                 │
├──────────────────────────────────────────────────────────────┤
│  RECENT GATE DECISIONS                                       │
│  09:42  Increase budget · Meta      HELD    EMQ below target │
│  09:15  Pause campaign · Google     PASS    —                │
└──────────────────────────────────────────────────────────────┘
```

Four elements carry the weight, none decorative:

1. **The status is shown with its inputs and their targets.** A status word is a
   claim; a status word beside the three values that produced it and the
   thresholds they were tested against is a method. It is immediately visible
   *which* input is failing and by how much.
2. **The calculator's own reason strings are surfaced verbatim.** They already
   state value and target. Rendering them rather than re-deriving the sentence
   in the frontend means the UI cannot drift from the logic.
3. **Recent gate decisions, including the ones that did nothing.** A `HELD` row
   with a stated reason is the most credible artifact the product has: it proves
   the gate is real. Sourced from `useAutopilotActions`.
4. **Deltas and thresholds, gradients nowhere.** Ember is used only for the
   threshold marker on the history chart.

Thresholds come from the tenant's configured params, never hardcoded — the
screen renders whatever that tenant is actually configured with.

**Data sources, all existing:** `useSignalHealth` and `useSignalHealthHistory`
(`/trust-layer/signal-health`, `/signal-health/history`), `useTrustStatus`
(`/trust-layer/trust-status`), `useAutopilotActions`.

If the documented five-component weighted model is the intended direction, that
is backend work — implementing `platform_stability` and `data_quality`
collectors and the weighting — and it needs its own spec. This screen is
designed so that adding contributors later extends the input table rather than
redesigning the page.

## States

Explicit on every data surface. `DataTable` and `Chart` already take these as
props, so callers must not branch.

- **Loading** — skeleton rows at the real row height, so layout does not shift.
- **Empty** — one line of what is absent plus the action that resolves it. Not
  an illustration.
- **Error** — what failed and a retry affordance. Never a silent empty state; an
  empty table and a failed fetch must not look identical.

That last point is the repo's dominant failure mode expressed in UI: a surface
that cannot distinguish "no data" from "broken" is a check whose failure is
indistinguishable from success.

## Accessibility

First-class, per the existing primitive contract.

- Row actions reachable by keyboard even though revealed on hover.
- Visible focus ring using `--primary`.
- Status never encoded by colour alone — `StatusPill` carries a text label.
- Semantic table markup; sortable headers expose `aria-sort`.
- Drawer traps focus and restores it to the trigger on close.

## Testing

Frontend is fully verifiable locally (`npm run lint`, `npx tsc --noEmit`,
`npm run build`, `npm run test:coverage` in `frontend/`), unlike the backend.
There is no excuse for shipping this unverified.

- A vitest per new or changed component, following the existing primitive test
  style.
- Each exemplar screen: renders loading, empty, error, and populated states.
- Trust Engine: the input table renders the tenant's configured thresholds, not
  the defaults, when a tenant config differs; and the calculator's reason
  strings are rendered verbatim rather than re-derived in the frontend.
- `StatusPill` consolidation: assert no view defines its own status badge —
  a guard test enumerating the three former call sites.

## Out of scope

- The other ~27 views. They follow in batches, each against an established
  archetype, planned separately.
- **Sidebar IA.** 53 destinations under Operate / Intelligence / Account is what
  will read as crowded regardless of styling, and `Autopilot` and `Rules` are
  two entries pointing at the same route (`dashboardNav.ts:232` and `:255`).
  This is an information-architecture problem, not a visual one, and it deserves
  its own pass.
- **"This rule would have fired 4× in the last 7 days"** on the Rules authoring
  drawer. The strongest available expression of the brief, and it needs a
  backend endpoint that does not exist. Spec separately if wanted.
- Marketing/landing surfaces. Already coherent.

## Documentation defect found while writing this spec

`CLAUDE.md` states, under Trust Engine Rules:

```
# Signal Health Components (weighted):
# EMQ: 35%, API Health: 25%, Event Loss: 20%,
# Platform Stability: 10%, Data Quality: 10%
```

No part of that is implemented. It should be corrected to describe the
three-input threshold model that `signal_health.py` actually applies, or marked
explicitly as an intended future model. Leaving it as-is will cause the next
person to design or build against it, exactly as nearly happened here — the
first draft of the Trust Engine screen was a five-row weighted table, and
shipping it would have meant inventing four numbers in the UI.

Not fixed in this spec's branch because it is a `CLAUDE.md` change with
implications beyond the frontend; raised for a decision.

## Open question, non-blocking

`/dashboard/trust` currently renders `TenantAdminOverview`, which is also
rendered at two other routes. Building the Trust Engine screen means changing
what `/dashboard/trust` resolves to. Whether `TenantAdminOverview` remains
reachable elsewhere needs confirming by clicking through the app while
authenticated — a static read of `App.tsx` could not settle which route block
owns which path.
