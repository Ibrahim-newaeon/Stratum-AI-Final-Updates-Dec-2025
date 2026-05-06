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
  AlertCircle,
  AlertOctagon,
  BarChart3,
  Bell,
  Brain,
  Cable,
  Calculator,
  Clock,
  Code,
  Code2,
  CreditCard,
  Database,
  DollarSign,
  FileBarChart,
  FileText,
  Filter,
  FlaskConical,
  Funnel,
  GitBranch,
  KeyRound,
  LayoutDashboard,
  LayoutGrid,
  LineChart,
  Mail,
  MessageSquareText,
  Microscope,
  Plug,
  Rocket,
  Send,
  Settings,
  Share2,
  Shield,
  ShieldCheck,
  Sparkles,
  Tag,
  Target,
  Terminal,
  TrendingUp,
  UserMinus,
  Users,
  Wallet,
  Webhook,
  Workflow,
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
    'ab-testing',
    'profit',
    'custom-reports',
    'custom-dashboard',
    'ai-insights',
    'cohort',
    'funnel-analysis',
    'explainability',
    'sql-editor',
    'compliance',
    'gdpr',
    'api-keys',
    'drip-campaigns',
    'push-notifications',
    'embed-widgets',
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
    'ab-testing',
    'profit',
    'custom-reports',
    'custom-dashboard',
    'ai-insights',
    'cohort',
    'funnel-analysis',
    'explainability',
    'sql-editor',
    'compliance',
    'gdpr',
    'api-keys',
    'drip-campaigns',
    'push-notifications',
    'embed-widgets',
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
    'ai-insights',
    'cohort',
    'funnel-analysis',
    'drip-campaigns',
    'push-notifications',
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
    'ai-insights',
    'cohort',
    'funnel-analysis',
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
      { label: 'Autopilot', href: '/dashboard/rules', icon: Sparkles, section: 'autopilot' },
      {
        label: 'Audiences',
        href: '/dashboard/cdp/audience-sync',
        icon: Users,
        section: 'audiences',
      },
      {
        label: 'Trust Engine',
        href: '/dashboard/trust',
        icon: ShieldCheck,
        section: 'trust',
      },
      { label: 'Pacing', href: '/dashboard/pacing', icon: Target, section: 'pacing' },
      { label: 'Rules', href: '/dashboard/rules', icon: Zap, section: 'rules' },
      {
        label: 'AB Testing',
        href: '/dashboard/ab-testing',
        icon: FlaskConical,
        section: 'ab-testing',
      },
      {
        label: 'Profit & ROAS',
        href: '/dashboard/profit',
        icon: DollarSign,
        section: 'profit',
      },
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
      {
        label: 'Reporting',
        href: '/dashboard/reporting',
        icon: BarChart3,
        section: 'reporting',
        children: [
          { label: 'Reports', href: '/dashboard/reporting', icon: BarChart3, section: 'reporting' },
          {
            label: 'Custom Reports',
            href: '/dashboard/custom-reports',
            icon: FileBarChart,
            section: 'custom-reports',
          },
          {
            label: 'Custom Dashboard',
            href: '/dashboard/custom-dashboard',
            icon: LayoutGrid,
            section: 'custom-dashboard',
          },
        ],
      },
      {
        label: 'Knowledge Graph',
        href: '/dashboard/knowledge-graph/insights',
        icon: Brain,
        section: 'insights',
        children: [
          {
            label: 'Insights',
            href: '/dashboard/knowledge-graph/insights',
            icon: Brain,
            section: 'insights',
          },
          {
            label: 'Problems',
            href: '/dashboard/knowledge-graph/problems',
            icon: AlertCircle,
            section: 'insights',
          },
          {
            label: 'Revenue Attribution',
            href: '/dashboard/knowledge-graph/revenue',
            icon: LineChart,
            section: 'insights',
          },
        ],
      },
      {
        label: 'AI Insights',
        href: '/dashboard/ai-insights',
        icon: Sparkles,
        section: 'ai-insights',
      },
      {
        label: 'Cohort Analysis',
        href: '/dashboard/cohort-analysis',
        icon: GitBranch,
        section: 'cohort',
      },
      {
        label: 'Funnel Analysis',
        href: '/dashboard/funnel-analysis',
        icon: Filter,
        section: 'funnel-analysis',
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
      {
        label: 'Model Explainability',
        href: '/dashboard/explainability',
        icon: Microscope,
        section: 'explainability',
      },
      {
        label: 'SQL Editor',
        href: '/dashboard/sql-editor',
        icon: Terminal,
        section: 'sql-editor',
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
        children: [
          {
            label: 'Hub',
            href: '/dashboard/integrations',
            icon: Plug,
            section: 'integrations',
          },
          {
            label: 'Connect Platforms',
            href: '/dashboard/campaigns/connect',
            icon: Cable,
            section: 'integrations',
          },
          {
            label: 'Ad Accounts',
            href: '/dashboard/campaigns/accounts',
            icon: Wallet,
            section: 'integrations',
          },
          {
            label: 'CAPI Setup',
            href: '/dashboard/capi-setup',
            icon: Webhook,
            section: 'integrations',
          },
          {
            label: 'Developer Portal',
            href: '/dashboard/developer',
            icon: Code,
            section: 'integrations',
          },
        ],
      },
      {
        label: 'WhatsApp',
        href: '/dashboard/whatsapp',
        icon: MessageSquareText,
        section: 'whatsapp',
      },
      {
        label: 'Newsletter',
        href: '/dashboard/newsletter',
        icon: Mail,
        section: 'newsletter',
        children: [
          { label: 'Dashboard', href: '/dashboard/newsletter', icon: Mail, section: 'newsletter' },
          {
            label: 'Campaigns',
            href: '/dashboard/newsletter/campaigns',
            icon: Send,
            section: 'newsletter',
          },
          {
            label: 'Subscribers',
            href: '/dashboard/newsletter/subscribers',
            icon: Users,
            section: 'newsletter',
          },
          {
            label: 'Templates',
            href: '/dashboard/newsletter/templates',
            icon: FileText,
            section: 'newsletter',
          },
        ],
      },
      {
        label: 'Drip Campaigns',
        href: '/dashboard/drip-campaigns',
        icon: Workflow,
        section: 'drip-campaigns',
      },
      {
        label: 'Push Notifications',
        href: '/dashboard/push-notifications',
        icon: Bell,
        section: 'push-notifications',
      },
      {
        label: 'Embed Widgets',
        href: '/dashboard/embed-widgets',
        icon: Code2,
        section: 'embed-widgets',
      },
      { label: 'Audit Log', href: '/dashboard/audit-log', icon: FileText, section: 'audit' },
      {
        label: 'Compliance',
        href: '/dashboard/compliance',
        icon: Shield,
        section: 'compliance',
      },
      {
        label: 'Data & Privacy',
        href: '/dashboard/gdpr',
        icon: ShieldCheck,
        section: 'gdpr',
      },
      {
        label: 'API Keys',
        href: '/dashboard/api-keys',
        icon: KeyRound,
        section: 'api-keys',
      },
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
