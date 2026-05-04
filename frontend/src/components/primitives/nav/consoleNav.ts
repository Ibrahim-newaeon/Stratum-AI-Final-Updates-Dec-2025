/**
 * consoleNav — IA configuration for the Platform Owner console.
 *
 * Reserved for `superadmin` only. Lives at `/console/*`, separate
 * shell from the operator dashboard so platform-level concerns don't
 * clutter the agency operator's mental model.
 *
 * Three top-level groups:
 *
 *   Platform     — what the owner manages (tenants, users, flags)
 *   Operations   — runtime tooling (queues, control tower, logs)
 *   Health       — visibility (readiness, analytics, cross-tenant audit)
 */

import {
  Activity,
  AlertOctagon,
  BarChart3,
  Briefcase,
  Building2,
  Cog,
  Database,
  Flag,
  Gauge,
  Inbox,
  Rocket,
  ScrollText,
  ShieldCheck,
  Users,
} from 'lucide-react';
import type { SidebarGroup } from './Sidebar';

/** Owner-only IA. No role gating needed at config time — the entire
 *  /console/* prefix is gated at the route level (superadmin only). */
export const consoleNavGroups: SidebarGroup[] = [
  {
    id: 'platform',
    label: 'Platform',
    items: [
      { label: 'Overview', href: '/console', icon: Gauge },
      { label: 'Tenants', href: '/console/tenants', icon: Building2 },
      { label: 'Users', href: '/console/users', icon: Users },
      { label: 'Feature Flags', href: '/console/feature-flags', icon: Flag },
      { label: 'Billing Plans', href: '/console/billing', icon: Briefcase },
    ],
  },
  {
    id: 'operations',
    label: 'Operations',
    items: [
      { label: 'Control Tower', href: '/console/control-tower', icon: Activity },
      { label: 'Dead Letter Queue', href: '/console/dead-letter-queue', icon: Inbox },
      { label: 'Publish Logs', href: '/console/publish-logs', icon: ScrollText },
      { label: 'System', href: '/console/system', icon: Cog },
    ],
  },
  {
    id: 'health',
    label: 'Health',
    items: [
      { label: 'Launch Readiness', href: '/console/launch-readiness', icon: Rocket },
      { label: 'Platform Analytics', href: '/console/analytics', icon: BarChart3 },
      { label: 'Benchmarks', href: '/console/benchmarks', icon: Database },
      { label: 'Cross-Tenant Audit', href: '/console/audit', icon: ShieldCheck },
      { label: 'Anomalies', href: '/console/anomalies', icon: AlertOctagon },
    ],
  },
];
