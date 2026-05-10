# Analytics Dashboard User Flows

## Overview

Step-by-step user journeys for the Analytics Dashboard features.

---

## Flow 1: View Dashboard KPIs

**Actor**: Tenant User
**Goal**: Review current performance metrics at a glance

### Steps

1. User navigates to Analytics Dashboard
2. System loads default period (Last 7 Days)
3. KPI tiles display with current values and trends
4. User sees:
   - Total Spend with trend indicator
   - Total Revenue with trend indicator
   - ROAS with trend indicator
   - Impressions, Clicks, Conversions
5. User can hover over tile for sparkline detail

### UI States

```
┌─────────────────────────────────────────────────────────────┐
│  Analytics Dashboard                    [Today ▼] [7d ▼]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │  Spend    │ │  Revenue  │ │   ROAS    │ │   CTR     │  │
│  │  $45,230  │ │  $98,450  │ │   2.18x   │ │   3.2%    │  │
│  │  ↑ 12.5%  │ │  ↑ 18.3%  │ │  ↑ 5.2%   │ │  ↓ 0.8%  │  │
│  │  ▁▂▃▄▅▆▇█ │ │  ▁▂▄▅▆▇██ │ │  ▃▄▄▅▅▆▆▇ │ │  █▇▆▅▄▃▂▁ │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│  │Impressions│ │  Clicks   │ │Conversions│ │    CPA    │  │
│  │  2.4M     │ │   78.5K   │ │   1,245   │ │  $36.32   │  │
│  │  ↑ 8.2%   │ │  ↑ 6.1%   │ │  ↑ 22.4%  │ │  ↓ 8.1%   │  │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 2: Change Analysis Period

**Actor**: Tenant User
**Goal**: Compare performance across different time periods

### Steps

1. User clicks period selector dropdown
2. Options displayed: Today, 7d, 30d, 90d
3. User selects new period (e.g., "30d")
4. System fetches data for new period
5. All KPIs update with new values and trends
6. Trend percentages reflect comparison to previous 30 days

### Period Comparison Logic

| Selected | Current Period | Comparison Period |
|----------|----------------|-------------------|
| Today | Today | Yesterday |
| 7d | Last 7 days | Previous 7 days |
| 30d | Last 30 days | Previous 30 days |
| 90d | Last 90 days | Previous 90 days |

---

## Flow 3: View Demographics Breakdown

**Actor**: Tenant User
**Goal**: Understand audience composition and performance

### Steps

1. User navigates to Demographics tab
2. System loads demographic data
3. User views age group distribution chart
4. User switches to gender breakdown
5. User explores location performance
6. User checks device distribution

### UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Demographics          [Age ▼] [Gender] [Location] [Device]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Age Group Performance                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 18-24  ████████████░░░░░░░░░░  32%  $14,500  ROAS 1.8│   │
│  │ 25-34  ██████████████████████  48%  $21,700  ROAS 2.4│   │
│  │ 35-44  ████████░░░░░░░░░░░░░░  18%  $8,100   ROAS 2.1│   │
│  │ 45-54  ██░░░░░░░░░░░░░░░░░░░░   2%  $900     ROAS 1.2│   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Insights:                                                  │
│  • 25-34 age group drives 48% of spend with best ROAS      │
│  • Consider reducing 45-54 targeting (low ROAS)            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 4: Analyze Performance Heatmap

**Actor**: Tenant User
**Goal**: Identify optimal times for ad delivery

### Steps

1. User navigates to Heatmap view
2. Default metric (Conversions) displayed
3. 7×24 grid shows performance by day/hour
4. User hovers over cell for detailed metrics
5. User changes metric to CTR
6. Heatmap updates to show CTR distribution
7. User identifies best performing time slots

### Heatmap Visualization

```
┌─────────────────────────────────────────────────────────────┐
│  Performance Heatmap            [Conversions ▼] [7d ▼]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│       00  03  06  09  12  15  18  21                       │
│  Mon  ░░  ░░  ░▒  ▒▓  ▓█  ██  █▓  ▓▒                       │
│  Tue  ░░  ░░  ░▒  ▒▓  ▓█  ██  █▓  ▓▒                       │
│  Wed  ░░  ░░  ░▒  ▒▓  ▓█  ██  ██  ▓▒                       │
│  Thu  ░░  ░░  ░▒  ▒▓  ██  ██  █▓  ▓▒                       │
│  Fri  ░░  ░░  ░▒  ▒▓  ▓█  ██  ██  ██                       │
│  Sat  ░░  ░░  ░░  ▒▒  ▒▓  ▓█  ██  ██                       │
│  Sun  ░░  ░░  ░░  ▒▒  ▒▓  ▓▓  ▓▓  ▓▒                       │
│                                                             │
│  Legend: ░ Low  ▒ Medium  ▓ High  █ Peak                   │
│                                                             │
│  Best Times: Fri-Sat 18:00-21:00 (avg 42 conversions/hr)   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 5: Compare Platform Performance

**Actor**: Tenant User
**Goal**: Evaluate performance across advertising platforms

### Steps

1. User navigates to Platform Breakdown
2. System displays comparison table
3. User sorts by ROAS (descending)
4. User identifies top performing platform
5. User clicks platform for drill-down
6. Detailed platform metrics displayed

### Platform Comparison Table

```
┌─────────────────────────────────────────────────────────────┐
│  Platform Performance                              [30d ▼] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Platform   Campaigns  Spend      Revenue    ROAS   CTR    │
│  ─────────────────────────────────────────────────────────  │
│  Meta          12      $18,500    $42,550    2.30x  3.4%   │
│  Google        8       $15,200    $38,000    2.50x  2.8%   │
│  TikTok        5       $8,500     $14,450    1.70x  4.2%   │
│  Snapchat      3       $3,030     $3,450     1.14x  5.1%   │
│  ─────────────────────────────────────────────────────────  │
│  Total         28      $45,230    $98,450    2.18x  3.2%   │
│                                                             │
│  [View Details] [Export CSV]                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 6: View Performance Trends

**Actor**: Tenant User
**Goal**: Analyze performance changes over time

### Steps

1. User navigates to Trends view
2. Default chart shows Spend and Revenue
3. User adds ROAS to comparison
4. Multi-line chart updates
5. User adjusts date range
6. User hovers for daily values
7. User identifies trend patterns

### Trends Chart

```
┌─────────────────────────────────────────────────────────────┐
│  Performance Trends    [Spend ✓] [Revenue ✓] [ROAS ✓]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  $                                                    ROAS  │
│  100K ┤                                              ┤ 3.0  │
│       │           ___----___                               │
│   80K ┤      ___--          ---___                   ┤ 2.5  │
│       │  ___-                     ---___                   │
│   60K ┤-                               ---           ┤ 2.0  │
│       │                                   ---___           │
│   40K ┤----___                                ---    ┤ 1.5  │
│       │       ---___                            ---        │
│   20K ┤            ---___                          - ┤ 1.0  │
│       │                  ---___                            │
│     0 ┼────┬────┬────┬────┬────┬────┬────┬────┬────  ┤ 0.0  │
│       Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep          │
│                                                             │
│  ── Spend  ── Revenue  ── ROAS                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 7: Generate Executive Summary

**Actor**: Tenant User / Manager
**Goal**: Get high-level performance overview with recommendations

### Steps

1. User navigates to Executive Summary
2. System generates summary for selected period
3. User reviews key metrics section
4. User checks top performers list
5. User reviews underperformers
6. User reads AI-generated recommendations
7. User exports summary as PDF

### Executive Summary Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Executive Summary                    [30d ▼] [Export PDF] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Overall Performance         Account Health: 85/100 ●●●●○  │
│  ─────────────────────────────────────────────────────────  │
│  Total Spend: $45,230 (↑12.5%)    ROAS: 2.18x (↑5.2%)     │
│  Total Revenue: $98,450 (↑18.3%)  Conversions: 1,245       │
│                                                             │
│  Top Performers                                             │
│  ─────────────────────────────────────────────────────────  │
│  1. Summer Sale 2024 - $28,500 revenue, 3.2x ROAS          │
│  2. Q1 Promo Meta - $18,200 revenue, 2.8x ROAS             │
│  3. Brand Awareness - $12,100 revenue, 2.4x ROAS           │
│                                                             │
│  Needs Attention                                            │
│  ─────────────────────────────────────────────────────────  │
│  1. Winter Campaign - $1,200 revenue, 0.8x ROAS ⚠️         │
│  2. Test Campaign TT - $450 revenue, 0.6x ROAS ⚠️          │
│                                                             │
│  Recommendations                                            │
│  ─────────────────────────────────────────────────────────  │
│  • Pause "Winter Campaign" - ROAS below threshold          │
│  • Increase budget on "Summer Sale" - strong performer     │
│  • Review TikTok targeting - CTR high but ROAS low         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 8: Schedule Automated Reports

**Actor**: Tenant Admin
**Goal**: Set up recurring performance reports

### Steps

1. User clicks "Schedule Report" button
2. Modal opens with report configuration
3. User selects report type (Executive/Detailed)
4. User sets schedule (Daily/Weekly/Monthly)
5. User adds recipient email addresses
6. User chooses export format (PDF/Excel)
7. User configures filters (optional)
8. User saves scheduled report
9. Confirmation displayed with next send date

### Schedule Report Modal

```
┌─────────────────────────────────────────────────────────────┐
│  Schedule Report                                     [×]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Report Type                                                │
│  ○ Executive Summary                                        │
│  ● Detailed Performance                                     │
│  ○ Platform Comparison                                      │
│                                                             │
│  Schedule                                                   │
│  ○ Daily at [09:00 ▼]                                      │
│  ● Weekly on [Monday ▼] at [09:00 ▼]                       │
│  ○ Monthly on [1st ▼] at [09:00 ▼]                         │
│                                                             │
│  Recipients                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ manager@company.com                           [×]   │   │
│  │ cmo@company.com                               [×]   │   │
│  │ [+ Add recipient]                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Format: [PDF ▼]                                           │
│                                                             │
│  [Cancel]                                [Save Schedule]    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 9: Export Analytics Data

**Actor**: Tenant User
**Goal**: Download analytics data for external analysis

### Steps

1. User clicks "Export" button on any analytics view
2. Export options modal appears
3. User selects format (CSV/Excel/PDF)
4. User selects date range
5. User selects metrics to include
6. User clicks "Export"
7. Download starts automatically
8. Success notification displayed

---

## Flow 10: Superadmin Tenant Overview (Admin Only)

**Actor**: Platform Administrator
**Goal**: Monitor performance across all tenants

### Steps

1. Superadmin navigates to Admin Analytics
2. Tenant overview table displayed
3. Admin sorts by various metrics
4. Admin filters by health status
5. Admin clicks tenant for details
6. Detailed tenant analytics displayed
7. Admin can impersonate tenant if needed

### Tenant Overview Table

```
┌─────────────────────────────────────────────────────────────┐
│  Tenant Overview                        [Filter ▼] [Export]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Tenant         Campaigns  Spend(30d)  ROAS   Health       │
│  ─────────────────────────────────────────────────────────  │
│  Acme Corp          28     $45,230     2.18x  ● Healthy    │
│  TechStart Inc      15     $28,100     1.95x  ● Healthy    │
│  Fashion Brand      22     $52,000     1.45x  ◐ Degraded   │
│  Local Shop          5     $2,500      0.82x  ○ Unhealthy  │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Platform Totals                                            │
│  Active Tenants: 156   Total Spend: $1.2M   Avg ROAS: 1.85 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
