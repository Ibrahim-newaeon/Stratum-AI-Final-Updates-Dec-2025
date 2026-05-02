/**
 * dashboardNav — IA configuration for the dashboard sidebar.
 *
 * Three top-level groups that match the agency operator's mental model:
 *
 *   Operate       — what's running right now
 *   Intelligence  — what's being learned
 *   Account       — what's configured
 *
 * Each group's `items` array references the existing routes registered
 * in App.tsx. Adding a new route is a one-line append here; no Sidebar
 * primitive change required.
 *
 * Role-gated items (e.g., SuperAdmin) are filtered at the call site —
 * pass a different `groups` to <Sidebar> based on the current user's
 * role rather than embedding role logic into the config.
 */

import {
  Activity,
  AlertOctagon,
  BarChart3,
  Brain,
  CreditCard,
  Database,
  Funnel,
  LayoutDashboard,
  Plug,
  Rocket,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  Users,
} from 'lucide-react';
import type { SidebarGroup } from './Sidebar';

/** Default IA — covers the routes a typical agency operator uses. */
export const dashboardNavGroups: SidebarGroup[] = [
  {
    id: 'operate',
    label: 'Operate',
    items: [
      { label: 'Overview', href: '/dashboard/overview', icon: LayoutDashboard },
      { label: 'Campaigns', href: '/dashboard/campaigns', icon: Rocket },
      { label: 'Autopilot', href: '/dashboard/autopilot', icon: Sparkles },
      { label: 'Audiences', href: '/dashboard/audiences', icon: Users },
      { label: 'Trust Engine', href: '/dashboard/trust-engine', icon: ShieldCheck },
      { label: 'Pacing', href: '/dashboard/pacing', icon: Target },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    items: [
      { label: 'CDP', href: '/dashboard/cdp', icon: Database },
      { label: 'Attribution', href: '/dashboard/attribution', icon: Funnel },
      { label: 'Reporting', href: '/dashboard/reporting', icon: BarChart3 },
      { label: 'Insights', href: '/dashboard/insights', icon: Brain },
      { label: 'Anomalies', href: '/dashboard/anomalies', icon: AlertOctagon },
    ],
  },
  {
    id: 'account',
    label: 'Account',
    items: [
      { label: 'Integrations', href: '/dashboard/integrations', icon: Plug },
      { label: 'Settings', href: '/dashboard/settings', icon: Settings },
      { label: 'Plans', href: '/dashboard/plans', icon: Sparkles },
      { label: 'Billing', href: '/dashboard/billing', icon: CreditCard },
      { label: 'Team', href: '/dashboard/team', icon: Users },
    ],
  },
];

/** Add this group to `dashboardNavGroups` for users with role=superadmin. */
export const superadminGroup: SidebarGroup = {
  id: 'superadmin',
  label: 'Superadmin',
  items: [
    { label: 'Tenants', href: '/superadmin', icon: Activity },
    { label: 'Launch Readiness', href: '/superadmin/launch-readiness', icon: Sparkles },
  ],
};
