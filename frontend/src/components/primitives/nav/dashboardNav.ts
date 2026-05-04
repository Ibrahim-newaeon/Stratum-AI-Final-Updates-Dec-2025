/**
 * dashboardNav — IA configuration for the operator dashboard sidebar.
 *
 * Three top-level groups that match the agency operator's mental model:
 *
 *   Operate       — what's running right now
 *   Intelligence  — what's being learned
 *   Workspace     — what's configured (agency-scoped)
 *
 * Platform-owner concerns (cross-tenant tooling, feature flags, ops)
 * live in a separate shell at `/console/*` — see `consoleNav.ts`. The
 * operator dashboard intentionally never surfaces those, so non-owner
 * users (admin / manager / analyst / viewer) never see them.
 *
 * Each group's `items` array references the existing routes registered
 * in App.tsx. Adding a new route is a one-line append here; no Sidebar
 * primitive change required.
 *
 * Role-gated items are filtered by the section-visibility map below
 * (mirrors backend SIDEBAR_VISIBILITY). Call `buildDashboardNav(role)`
 * to get a `SidebarGroup[]` that has invisible items removed and
 * empty groups stripped.
 */

import {
  AlertOctagon,
  BarChart3,
  Brain,
  Calculator,
  Clock,
  CreditCard,
  Database,
  FileText,
  Funnel,
  LayoutDashboard,
  Mail,
  MessageSquareText,
  Plug,
  Rocket,
  Settings,
  Share2,
  ShieldCheck,
  Sparkles,
  Tag,
  Target,
  TrendingUp,
  UserMinus,
  Users,
  Zap,
} from 'lucide-react';
import type { SidebarGroup, SidebarItem } from './Sidebar';
import type { AppRole } from '@/components/auth/ProtectedRoute';

/**
 * Section-visibility map — mirrors backend `SIDEBAR_VISIBILITY`.
 * If a role lists a section here, items tagged with that section
 * appear in the sidebar.
 */
const SIDEBAR_VISIBILITY: Record<AppRole, ReadonlySet<string>> = {
  // Owner sees the operator dashboard the same as admin (so they can
  // QA what their customers see). Owner-only platform tooling lives at
  // /console/* — not surfaced here.
  superadmin: new Set([
    'dashboard',
    'campaigns',
    'autopilot',
    'audiences',
    'trust',
    'pacing',
    'cdp',
    'attribution',
    'reporting',
    'insights',
    'anomalies',
    'rules',
    'integrations',
    'settings',
    'billing',
    'team',
    'whatsapp',
    'newsletter',
    'predictions',
    'benchmarks',
    'simulator',
    'audit',
  ]),
  admin: new Set([
    'dashboard',
    'campaigns',
    'autopilot',
    'audiences',
    'trust',
    'pacing',
    'cdp',
    'attribution',
    'reporting',
    'insights',
    'anomalies',
    'rules',
    'integrations',
    'settings',
    'billing',
    'team',
    'whatsapp',
    'newsletter',
    'predictions',
    'benchmarks',
    'simulator',
    'audit',
  ]),
  manager: new Set([
    'dashboard',
    'campaigns',
    'autopilot',
    'audiences',
    'trust',
    'pacing',
    'cdp',
    'attribution',
    'reporting',
    'insights',
    'anomalies',
    'rules',
    'whatsapp',
    'newsletter',
    'predictions',
    'benchmarks',
  ]),
  analyst: new Set([
    'dashboard',
    'campaigns',
    'audiences',
    'trust',
    'pacing',
    'cdp',
    'attribution',
    'reporting',
    'insights',
    'anomalies',
    'rules',
    'newsletter',
    'predictions',
    'benchmarks',
  ]),
  viewer: new Set(['dashboard', 'campaigns', 'reporting', 'insights']),
};

/** Internal item type — adds a `section` tag for role-gating. */
interface NavItem extends SidebarItem {
  section: string;
  children?: NavItem[];
}

interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
}

const navConfig: NavGroup[] = [
  {
    id: 'operate',
    label: 'Operate',
    items: [
      {
        label: 'Overview',
        href: '/dashboard/overview',
        icon: LayoutDashboard,
        section: 'dashboard',
      },
      { label: 'Campaigns', href: '/dashboard/campaigns', icon: Rocket, section: 'campaigns' },
      { label: 'Autopilot', href: '/dashboard/autopilot', icon: Sparkles, section: 'autopilot' },
      { label: 'Audiences', href: '/dashboard/audiences', icon: Users, section: 'audiences' },
      {
        label: 'Trust Engine',
        href: '/dashboard/trust-engine',
        icon: ShieldCheck,
        section: 'trust',
      },
      { label: 'Pacing', href: '/dashboard/pacing', icon: Target, section: 'pacing' },
      { label: 'Rules', href: '/dashboard/rules', icon: Zap, section: 'rules' },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    items: [
      {
        label: 'CDP',
        href: '/dashboard/cdp',
        icon: Database,
        section: 'cdp',
        children: [
          { label: 'Overview', href: '/dashboard/cdp', icon: Database, section: 'cdp' },
          { label: 'Profiles', href: '/dashboard/cdp/profiles', icon: Users, section: 'cdp' },
          { label: 'Segments', href: '/dashboard/cdp/segments', icon: Tag, section: 'cdp' },
          { label: 'Events', href: '/dashboard/cdp/events', icon: Clock, section: 'cdp' },
          {
            label: 'Identity Graph',
            href: '/dashboard/cdp/identity',
            icon: Share2,
            section: 'cdp',
          },
          { label: 'Funnels', href: '/dashboard/cdp/funnels', icon: Funnel, section: 'cdp' },
          {
            label: 'Computed Traits',
            href: '/dashboard/cdp/computed-traits',
            icon: Calculator,
            section: 'cdp',
          },
          {
            label: 'Predictive Churn',
            href: '/dashboard/cdp/predictive-churn',
            icon: UserMinus,
            section: 'cdp',
          },
        ],
      },
      {
        label: 'Attribution',
        href: '/dashboard/attribution',
        icon: Funnel,
        section: 'attribution',
      },
      { label: 'Reporting', href: '/dashboard/reporting', icon: BarChart3, section: 'reporting' },
      {
        label: 'Insights',
        href: '/dashboard/knowledge-graph/insights',
        icon: Brain,
        section: 'insights',
      },
      {
        label: 'Predictions',
        href: '/dashboard/stratum',
        icon: TrendingUp,
        section: 'predictions',
      },
      {
        label: 'Benchmarks',
        href: '/dashboard/benchmarks',
        icon: BarChart3,
        section: 'benchmarks',
      },
      {
        label: 'Anomalies',
        href: '/dashboard/anomalies',
        icon: AlertOctagon,
        section: 'anomalies',
      },
    ],
  },
  {
    id: 'workspace',
    label: 'Workspace',
    items: [
      {
        label: 'Integrations',
        href: '/dashboard/integrations',
        icon: Plug,
        section: 'integrations',
      },
      {
        label: 'WhatsApp',
        href: '/dashboard/whatsapp',
        icon: MessageSquareText,
        section: 'whatsapp',
      },
      { label: 'Newsletter', href: '/dashboard/newsletter', icon: Mail, section: 'newsletter' },
      { label: 'Audit Log', href: '/dashboard/audit-log', icon: FileText, section: 'audit' },
      { label: 'Settings', href: '/dashboard/settings', icon: Settings, section: 'settings' },
      { label: 'Team', href: '/dashboard/tenants', icon: Users, section: 'team' },
      { label: 'Billing', href: '/dashboard/ml-training', icon: CreditCard, section: 'billing' },
    ],
  },
];

function visibleSections(role: AppRole | undefined): ReadonlySet<string> {
  if (!role) return new Set();
  return SIDEBAR_VISIBILITY[role] ?? new Set();
}

function filterItems(items: NavItem[], visible: ReadonlySet<string>): SidebarItem[] {
  const result: SidebarItem[] = [];
  for (const item of items) {
    if (!visible.has(item.section)) continue;
    const filteredChildren = item.children ? filterItems(item.children, visible) : undefined;
    const { section: _section, children: _children, ...rest } = item;
    result.push({
      ...rest,
      ...(filteredChildren && filteredChildren.length > 0 ? { children: filteredChildren } : {}),
    });
  }
  return result;
}

/**
 * Build the operator-dashboard sidebar groups for a given role. Items
 * the role can't see are filtered out; groups that end up empty are
 * stripped. Platform-owner items are NOT here — they live in
 * `consoleNav.ts` and render in the separate /console/* shell.
 */
export function buildDashboardNav(role: AppRole | undefined): SidebarGroup[] {
  const visible = visibleSections(role);
  return navConfig
    .map<SidebarGroup>((g) => ({ id: g.id, label: g.label, items: filterItems(g.items, visible) }))
    .filter((g) => g.items.length > 0);
}

/** Default IA — matches the previous static export. Used when no role
 *  context is available (story tests, etc.). */
export const dashboardNavGroups: SidebarGroup[] = buildDashboardNav('admin');
