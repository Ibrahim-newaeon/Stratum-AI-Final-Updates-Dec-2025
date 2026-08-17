# Dashboard Shell + Campaigns Exemplar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared page shell (`PageHeader`, `StatRow`, status mapping) and rewrite Campaigns on top of it, establishing the "operational list" archetype that ~12 further views will follow.

**Architecture:** Two new primitives plus one pure mapping module, then `views/Campaigns.tsx` is rewritten to compose them with the existing `DataTable` and `StatusPill`. No new dependencies, no backend changes, no API changes. Every piece is verifiable locally.

**Tech Stack:** React 18 + TypeScript, Tailwind with semantic theme tokens, vitest + @testing-library/react, lucide-react icons.

## Global Constraints

- Theme invariants: ink `#0B0B0B` bg, surface `#141414`, line `#1F1F1F`, ember `#FF5A1F` accent. Use **semantic Tailwind tokens** (`bg-card`, `text-foreground`, `text-muted-foreground`, `border-border`, `text-primary`) — never hardcoded hex.
- Geist (`font-sans`) for body and display; Geist Mono (`font-mono`) for labels, status, and all numerics.
- Hairline 1px borders only. No shadows, no gradients, no glassmorphism, no zebra striping.
- `rounded-2xl` on surfaces, `rounded-full` on every clickable affordance.
- **Ember appears once per screen: the primary action.** `StatusPill`'s own colours do not count against this.
- Table row height 52px. No density toggle.
- Dark and light are both first-class — every colour must come from a token that has both.
- Loading, empty, and error are explicit states. An empty table and a failed fetch must never look identical.
- Lint runs with `--max-warnings 0`. Warnings fail the build.
- Working directory for all commands: `frontend/`.

## File Structure

| File | Responsibility |
| --- | --- |
| `src/lib/statusVariant.ts` | **Create.** Pure mapping from domain status strings → `StatusPillVariant` + display label. No JSX. |
| `src/lib/statusVariant.test.ts` | **Create.** Unit tests for the mapping. |
| `src/components/primitives/PageHeader.tsx` | **Create.** Title + context line + right-aligned actions, with the hairline rule beneath. |
| `src/components/primitives/PageHeader.test.tsx` | **Create.** |
| `src/components/primitives/StatRow.tsx` | **Create.** Inline stat strip — mono figures, hairline dividers, no cards. |
| `src/components/primitives/StatRow.test.tsx` | **Create.** |
| `src/views/Campaigns.tsx` | **Rewrite.** Compose the above with `DataTable` + `StatusPill`. Delete the local `StatusBadge` and the hand-rolled `<table>`. |
| `src/views/Campaigns.test.tsx` | **Create.** Loading / empty / error / populated. |

---

### Task 1: Status mapping

**Files:**
- Create: `frontend/src/lib/statusVariant.ts`
- Test: `frontend/src/lib/statusVariant.test.ts`

**Interfaces:**
- Consumes: `StatusPillVariant` from `@/components/primitives/StatusPill` (exported type: `'healthy' | 'degraded' | 'unhealthy' | 'neutral'`).
- Produces: `campaignStatusVariant(status: string): StatusPillVariant` and `campaignStatusLabel(status: string): string`. Task 3 imports both.

Why this exists: `Campaigns.tsx` defines a local `StatusBadge` and `Rules.tsx` defines a local `getStatusBadge`, while `StatusPill` already exists as a tested primitive. Three independent colour vocabularies for the same concept. This module is the single source of truth; Rules migrates onto it in a later plan.

Mapping decision, deliberate: `paused` maps to `degraded` (amber), not `neutral`. Amber reads as "not currently delivering", which is the thing an operator scanning the list needs to catch. `draft` and `completed` are `neutral` because neither implies something is wrong. Unknown strings fall back to `neutral` rather than throwing — an unrecognised status from the API must not blank the screen.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/statusVariant.test.ts`:

```ts
import { describe, it, expect } from 'vitest';
import { campaignStatusVariant, campaignStatusLabel } from './statusVariant';

describe('campaignStatusVariant', () => {
  it.each([
    ['active', 'healthy'],
    ['paused', 'degraded'],
    ['draft', 'neutral'],
    ['completed', 'neutral'],
  ] as const)('maps %s to %s', (status, expected) => {
    expect(campaignStatusVariant(status)).toBe(expected);
  });

  it('is case-insensitive', () => {
    expect(campaignStatusVariant('ACTIVE')).toBe('healthy');
  });

  it('falls back to neutral for an unknown status', () => {
    expect(campaignStatusVariant('archived_by_platform')).toBe('neutral');
  });
});

describe('campaignStatusLabel', () => {
  it('capitalises a known status', () => {
    expect(campaignStatusLabel('active')).toBe('Active');
  });

  it('returns unknown statuses unchanged rather than blanking them', () => {
    expect(campaignStatusLabel('archived_by_platform')).toBe('archived_by_platform');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- src/lib/statusVariant.test.ts`
Expected: FAIL — `Failed to resolve import "./statusVariant"`.

- [ ] **Step 3: Write the minimal implementation**

Create `frontend/src/lib/statusVariant.ts`:

```ts
/**
 * Domain status -> StatusPill variant.
 *
 * Campaigns.tsx and Rules.tsx each grew their own status badge with their own
 * colours, while StatusPill already existed as a tested primitive. This is the
 * single vocabulary they collapse onto.
 *
 * `paused` is degraded (amber) rather than neutral on purpose: amber reads as
 * "not currently delivering", which is what an operator scanning a list needs
 * to catch. draft/completed are neutral — neither implies something is wrong.
 */
import type { StatusPillVariant } from '@/components/primitives/StatusPill';

const CAMPAIGN_STATUS_VARIANT: Record<string, StatusPillVariant> = {
  active: 'healthy',
  paused: 'degraded',
  draft: 'neutral',
  completed: 'neutral',
};

const CAMPAIGN_STATUS_LABEL: Record<string, string> = {
  active: 'Active',
  paused: 'Paused',
  draft: 'Draft',
  completed: 'Completed',
};

/** Unknown statuses fall back to neutral — never throw, never blank the row. */
export function campaignStatusVariant(status: string): StatusPillVariant {
  return CAMPAIGN_STATUS_VARIANT[status?.toLowerCase()] ?? 'neutral';
}

/** Unknown statuses are shown verbatim so the operator sees the real value. */
export function campaignStatusLabel(status: string): string {
  return CAMPAIGN_STATUS_LABEL[status?.toLowerCase()] ?? status;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -- src/lib/statusVariant.test.ts`
Expected: PASS, 8 assertions.

- [ ] **Step 5: Commit**

```bash
git add src/lib/statusVariant.ts src/lib/statusVariant.test.ts
git commit -m "feat(frontend): one status vocabulary for StatusPill

Campaigns and Rules each defined their own status badge with their own
colours while StatusPill already existed. This is the module they collapse
onto. paused maps to degraded deliberately: amber reads as 'not currently
delivering', which is what matters when scanning a list."
```

---

### Task 2: Page shell primitives

**Files:**
- Create: `frontend/src/components/primitives/PageHeader.tsx`
- Create: `frontend/src/components/primitives/PageHeader.test.tsx`
- Create: `frontend/src/components/primitives/StatRow.tsx`
- Create: `frontend/src/components/primitives/StatRow.test.tsx`

**Interfaces:**
- Consumes: `cn` from `@/lib/utils`.
- Produces:
  - `<PageHeader title={string} context?={ReactNode} actions?={ReactNode} />`
  - `<StatRow items={StatRowItem[]} />` where `export interface StatRowItem { label: string; value: ReactNode; }`

  Task 3 imports both. Later plans reuse them for every migrated view.

Why `StatRow` and not `KPI` cards: four bordered cards atop every list screen is what makes a dashboard read as crowded, and it dilutes `Card variant="glow"`, which the theme spec reserves for emphasis on the home view. Weight comes from typography — mono figures, `tabular-nums` — not from containers.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/primitives/PageHeader.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PageHeader } from './PageHeader';

describe('PageHeader', () => {
  it('renders the title as a level-1 heading', () => {
    render(<PageHeader title="Campaigns" />);
    expect(screen.getByRole('heading', { level: 1, name: 'Campaigns' })).toBeInTheDocument();
  });

  it('renders the context line when given', () => {
    render(<PageHeader title="Campaigns" context="6 active · 2 held" />);
    expect(screen.getByText('6 active · 2 held')).toBeInTheDocument();
  });

  it('omits the context line entirely when not given', () => {
    const { container } = render(<PageHeader title="Campaigns" />);
    expect(container.querySelector('[data-slot="context"]')).toBeNull();
  });

  it('renders actions', () => {
    render(<PageHeader title="Campaigns" actions={<button>New campaign</button>} />);
    expect(screen.getByRole('button', { name: 'New campaign' })).toBeInTheDocument();
  });
});
```

Create `frontend/src/components/primitives/StatRow.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatRow } from './StatRow';

describe('StatRow', () => {
  const items = [
    { label: 'Spend 24h', value: '$12,480' },
    { label: 'ROAS', value: '3.42×' },
  ];

  it('renders every label and value', () => {
    render(<StatRow items={items} />);
    expect(screen.getByText('Spend 24h')).toBeInTheDocument();
    expect(screen.getByText('$12,480')).toBeInTheDocument();
    expect(screen.getByText('ROAS')).toBeInTheDocument();
    expect(screen.getByText('3.42×')).toBeInTheDocument();
  });

  it('renders figures in the mono face with tabular numerals', () => {
    const { container } = render(<StatRow items={items} />);
    const figure = container.querySelector('[data-slot="stat-value"]');
    expect(figure?.className).toContain('font-mono');
    expect(figure?.className).toContain('tabular-nums');
  });

  it('renders nothing when given no items', () => {
    const { container } = render(<StatRow items={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -- src/components/primitives/PageHeader.test.tsx src/components/primitives/StatRow.test.tsx`
Expected: FAIL — both fail to resolve their imports.

- [ ] **Step 3: Write the minimal implementations**

Create `frontend/src/components/primitives/PageHeader.tsx`:

```tsx
/**
 * Page shell header: title, a context line, and right-aligned actions.
 *
 * The context line states the decision the screen supports, not what the
 * screen is. "6 active · 2 held by trust gate" tells the operator whether they
 * need to act; "Manage your campaigns" tells them nothing. Writing that line is
 * part of migrating a view.
 */
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PageHeaderProps {
  title: string;
  context?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({ title, context, actions, className }: PageHeaderProps) {
  return (
    <header className={cn('border-b border-border pb-5', className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-[28px] font-semibold leading-tight text-foreground">{title}</h1>
          {context ? (
            <p data-slot="context" className="mt-1 text-sm text-muted-foreground">
              {context}
            </p>
          ) : null}
        </div>
        {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
      </div>
    </header>
  );
}

export default PageHeader;
```

Create `frontend/src/components/primitives/StatRow.tsx`:

```tsx
/**
 * Inline stat strip — deliberately NOT cards.
 *
 * Four bordered cards atop every list screen is what makes a dashboard read as
 * crowded, and it dilutes Card variant="glow", which the theme reserves for
 * emphasis on the home view. Weight here comes from typography: mono figures
 * with tabular numerals, mono uppercase labels, hairline dividers.
 */
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface StatRowItem {
  label: string;
  value: ReactNode;
}

interface StatRowProps {
  items: StatRowItem[];
  className?: string;
}

export function StatRow({ items, className }: StatRowProps) {
  if (items.length === 0) return null;

  return (
    <dl className={cn('flex flex-wrap items-stretch border-b border-border', className)}>
      {items.map((item) => (
        <div
          key={item.label}
          className="flex min-w-[9rem] flex-col gap-1 border-r border-border py-4 pr-8 pl-0 last:border-r-0 first:pl-0 [&:not(:first-child)]:pl-8"
        >
          <dt className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
            {item.label}
          </dt>
          <dd
            data-slot="stat-value"
            className="font-mono text-xl tabular-nums text-foreground"
          >
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default StatRow;
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm test -- src/components/primitives/PageHeader.test.tsx src/components/primitives/StatRow.test.tsx`
Expected: PASS, 7 tests.

- [ ] **Step 5: Typecheck and lint**

Run: `npx tsc --noEmit && npm run lint`
Expected: no output from tsc; eslint exits 0. Lint runs with `--max-warnings 0`, so any warning is a failure.

- [ ] **Step 6: Commit**

```bash
git add src/components/primitives/PageHeader.tsx src/components/primitives/PageHeader.test.tsx \
        src/components/primitives/StatRow.tsx src/components/primitives/StatRow.test.tsx
git commit -m "feat(frontend): page shell primitives — PageHeader and StatRow

StatRow is an inline stat strip rather than KPI cards. Cards atop every list
screen are what make a dashboard read as crowded, and they dilute
Card variant=glow, which the theme reserves for the home view. Weight comes
from typography: mono figures with tabular numerals, hairline dividers."
```

---

### Task 3: Rewrite Campaigns on the shell

**Files:**
- Modify: `frontend/src/views/Campaigns.tsx` (full rewrite of the render layer; keep the existing data hooks)
- Create: `frontend/src/views/Campaigns.test.tsx`

**Interfaces:**
- Consumes: `campaignStatusVariant`, `campaignStatusLabel` (Task 1); `PageHeader`, `StatRow`, `StatRowItem` (Task 2); `DataTable`, `DataTableColumn` from `@/components/primitives/DataTable`; `StatusPill` from `@/components/primitives/StatusPill`.
- Produces: nothing imported elsewhere. This is a route leaf.

Keep these existing hooks exactly as they are — this task changes presentation, not data: `useCampaigns`, `usePauseCampaign`, `useActivateCampaign`, `useDeleteCampaign` (from `@/api/hooks`), `usePriceMetrics` (from `@/hooks/usePriceMetrics`).

Delete on sight: the local `StatusBadge` component and the hand-rolled `<table>` / `<td>` markup.

`DataTable`'s real API, for reference while writing columns:

```ts
interface DataTableColumn<T> {
  id?: string;
  header: ReactNode;
  cell: (row: T, rowIndex: number) => ReactNode;
  sortable?: boolean;
  sortAccessor?: (row: T) => string | number;
  className?: string;
  headerClassName?: string;
  cellClassName?: string;
  hideOnMobile?: boolean;
}
// <DataTable data columns rowKey onRowClick loading loadingRows
//            emptyMessage error className ariaLabel />
```

Columns are **Campaign · Status · Spend · Budget · ROAS · Conversions · actions**. There is deliberately no Trust or Pacing column: `CampaignWithMetrics` carries no such field, and both signals are tenant-level. See the spec.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/views/Campaigns.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

const mockUseCampaigns = vi.fn();

vi.mock('@/api/hooks', () => ({
  useCampaigns: (...args: unknown[]) => mockUseCampaigns(...args),
  usePauseCampaign: () => ({ mutate: vi.fn(), isPending: false }),
  useActivateCampaign: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteCampaign: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock('@/hooks/usePriceMetrics', () => ({
  usePriceMetrics: () => ({ showPriceMetrics: true }),
}));

import Campaigns from './Campaigns';

function renderView() {
  return render(
    <MemoryRouter>
      <Campaigns />
    </MemoryRouter>,
  );
}

const row = {
  id: 'c-1',
  name: 'Summer Prospecting',
  platform: 'meta',
  status: 'active',
  budget: 5000,
  metrics: { spend: 1240.5, roas: 3.42, conversions: 87 },
};

describe('Campaigns', () => {
  it('renders the page title', () => {
    mockUseCampaigns.mockReturnValue({ data: { campaigns: [] }, isLoading: false, error: null });
    renderView();
    expect(screen.getByRole('heading', { level: 1, name: 'Campaigns' })).toBeInTheDocument();
  });

  it('shows an empty message distinct from an error', () => {
    mockUseCampaigns.mockReturnValue({ data: { campaigns: [] }, isLoading: false, error: null });
    renderView();
    expect(screen.getByText(/no campaigns yet/i)).toBeInTheDocument();
  });

  it('surfaces a fetch failure rather than showing an empty table', () => {
    mockUseCampaigns.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('boom'),
    });
    renderView();
    expect(screen.getByText(/could not load campaigns/i)).toBeInTheDocument();
    expect(screen.queryByText(/no campaigns yet/i)).toBeNull();
  });

  it('renders a campaign row with its status pill', () => {
    mockUseCampaigns.mockReturnValue({
      data: { campaigns: [row] },
      isLoading: false,
      error: null,
    });
    renderView();
    expect(screen.getByText('Summer Prospecting')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- src/views/Campaigns.test.tsx`
Expected: FAIL. The current view renders its own markup, so the heading-level query and the distinct empty/error copy will not match.

- [ ] **Step 3: Rewrite the view**

Replace the render layer of `frontend/src/views/Campaigns.tsx`. Keep the existing imports for the data hooks and the create-modal, and keep any existing filter state. The presentation becomes:

```tsx
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Pause, Pencil, Eye } from 'lucide-react';
import { PageHeader } from '@/components/primitives/PageHeader';
import { StatRow, type StatRowItem } from '@/components/primitives/StatRow';
import { StatusPill } from '@/components/primitives/StatusPill';
import { DataTable, type DataTableColumn } from '@/components/primitives/DataTable';
import { campaignStatusVariant, campaignStatusLabel } from '@/lib/statusVariant';
import { formatCurrency, formatCompactNumber } from '@/lib/utils';

// ... existing hooks: useCampaigns, usePauseCampaign, useActivateCampaign,
// useDeleteCampaign, usePriceMetrics

const columns: DataTableColumn<CampaignRow>[] = [
  {
    id: 'name',
    header: 'Campaign',
    sortable: true,
    sortAccessor: (c) => c.name,
    cell: (c) => (
      <div className="min-w-0">
        <div className="truncate font-medium text-foreground">{c.name}</div>
        <div className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
          {c.platform}
        </div>
      </div>
    ),
  },
  {
    id: 'status',
    header: 'Status',
    cell: (c) => (
      <StatusPill size="sm" variant={campaignStatusVariant(c.status)}>
        {campaignStatusLabel(c.status)}
      </StatusPill>
    ),
  },
  {
    id: 'spend',
    header: 'Spend',
    sortable: true,
    sortAccessor: (c) => c.metrics?.spend ?? 0,
    headerClassName: 'text-right',
    cellClassName: 'text-right font-mono tabular-nums',
    cell: (c) => formatCurrency(c.metrics?.spend ?? 0),
  },
  {
    id: 'budget',
    header: 'Budget',
    sortable: true,
    sortAccessor: (c) => c.budget ?? 0,
    headerClassName: 'text-right',
    cellClassName: 'text-right font-mono tabular-nums',
    cell: (c) => formatCurrency(c.budget ?? 0),
  },
  {
    id: 'roas',
    header: 'ROAS',
    sortable: true,
    sortAccessor: (c) => c.metrics?.roas ?? 0,
    headerClassName: 'text-right',
    cellClassName: 'text-right font-mono tabular-nums',
    cell: (c) => `${(c.metrics?.roas ?? 0).toFixed(2)}×`,
  },
  {
    id: 'conversions',
    header: 'Conv.',
    sortable: true,
    sortAccessor: (c) => c.metrics?.conversions ?? 0,
    headerClassName: 'text-right',
    cellClassName: 'text-right font-mono tabular-nums',
    cell: (c) => formatCompactNumber(c.metrics?.conversions ?? 0),
  },
];
```

Row actions are appended as a final column whose cell wraps the buttons in
`opacity-0 transition-opacity group-hover/row:opacity-100 focus-within:opacity-100`,
so they are hidden until hover **but always reachable by keyboard**. Each button
carries an explicit `aria-label` (`Pause campaign` / `Activate campaign`,
`Edit campaign`, `View campaign`).

The page body:

```tsx
return (
  <div className="px-8 py-6">
    <PageHeader
      title="Campaigns"
      context={contextLine}
      actions={
        <button
          type="button"
          onClick={() => setShowCreate(true)}
          className="rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          New campaign
        </button>
      }
    />
    <StatRow items={stats} />
    {/* existing filter bar goes here, one row, border-b border-border */}
    <DataTable
      data={campaigns}
      columns={columns}
      rowKey={(c) => c.id}
      loading={isLoading}
      emptyMessage="No campaigns yet. Connect a platform to import them."
      error={error ? 'Could not load campaigns. Retry, or check the integration.' : undefined}
      ariaLabel="Campaigns"
      className="mt-4"
    />
    {/* existing CampaignCreateModal */}
  </div>
);
```

`contextLine` is derived, not hardcoded — e.g.
``const contextLine = `${activeCount} active · ${pausedCount} paused`;``

`stats` is built with `useMemo` from the loaded campaigns:

```tsx
const stats: StatRowItem[] = useMemo(
  () => [
    { label: 'Spend 24h', value: formatCurrency(totalSpend) },
    { label: 'ROAS', value: `${avgRoas.toFixed(2)}×` },
    { label: 'Active', value: String(activeCount) },
    { label: 'Budget', value: formatCurrency(totalBudget) },
  ],
  [totalSpend, avgRoas, activeCount, totalBudget],
);
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `npm test -- src/views/Campaigns.test.tsx`
Expected: PASS, 4 tests.

- [ ] **Step 5: Verify nothing else regressed**

Run: `npm test -- --run`
Expected: the full suite passes. If a snapshot or an existing Campaigns-related test fails, read it before changing it — it may be asserting behaviour worth keeping.

- [ ] **Step 6: Typecheck, lint, build**

Run: `npx tsc --noEmit && npm run lint && npm run build`
Expected: all three clean. `npm run build` requires `VITE_API_URL` to be set since #670 — export it first if the build complains:
`VITE_API_URL=https://api.stratumai.app/api/v1 npm run build`

- [ ] **Step 7: Confirm the local dev server renders it**

Run: `npm run dev`, open `/dashboard/campaigns`, and check by eye:
- exactly one ember element (the "New campaign" button),
- numerics right-aligned and mono,
- hairline separators, no zebra, no shadows,
- row actions appear on hover **and** on keyboard tab,
- toggle the theme — light mode must be equally correct.

- [ ] **Step 8: Commit**

```bash
git add src/views/Campaigns.tsx src/views/Campaigns.test.tsx
git commit -m "feat(frontend): rewrite Campaigns on the page shell

Establishes the operational-list archetype: PageHeader with a context line
stating the decision the screen supports, StatRow instead of KPI cards,
DataTable + StatusPill instead of a hand-rolled table and a local StatusBadge.

Row actions are hidden until hover but stay keyboard-reachable. Empty and
error states are distinct — an empty table and a failed fetch must not look
identical.

No Trust or Pacing column: CampaignWithMetrics carries neither field and both
signals are tenant-level. Adding it is backend work, specced separately."
```

---

## Self-Review

**Spec coverage.** Page shell → Task 2. Inline stat row over cards → Task 2. Status consolidation → Task 1 (Campaigns call site in Task 3; Rules migrates in the next plan, as the spec's scope note says). Operational-list archetype → Task 3. Explicit loading/empty/error → Task 3 Step 1 tests. Accessibility (keyboard-reachable row actions, aria-labels, aria-sort via `DataTable`) → Task 3. Testing strategy → every task.

**Not covered here, by design:** Rules (authoring archetype) and Trust Engine (diagnostic archetype) are separate plans. Designing their tasks before the first archetype has landed and been reviewed would be guessing at patterns this plan exists to establish. The spec's remaining sections map to those two plans.

**Placeholder scan.** No TBD/TODO. Every code step carries real code. The one prose-only instruction — "existing filter bar goes here" — refers to code already in the file being modified, not to something unwritten.

**Type consistency.** `StatusPillVariant` is imported as a type in Task 1 and used in Tasks 1 and 3. `StatRowItem` is exported by Task 2 and imported by Task 3. `DataTableColumn<T>` matches the real signature read from `DataTable.tsx:23-41`. `campaignStatusVariant` / `campaignStatusLabel` keep the same names across Tasks 1 and 3.

**Known gap the implementer will hit.** The test in Task 3 mocks `@/api/hooks` with a `{ campaigns: [...] }` shape. Verify the real `useCampaigns` return shape in `frontend/src/api/campaigns.ts:197` before writing the mock and match it — if it differs, fix the mock, not the view.
