/**
 * Role-Based Tour Definitions
 *
 * Each tour is designed for a specific user role to help them
 * understand their primary workflows and features.
 *
 * CONTENT GUIDELINES:
 * - Keep step content under 150 characters for readability
 * - Use concise, action-oriented language
 * - Focus on "what" and "why", not detailed "how"
 */

import { Step } from 'react-joyride'

export type TourRole = 'superadmin' | 'account_manager' | 'tenant_admin' | 'media_buyer' | 'data_team' | 'general'

export interface TourConfig {
  id: string
  role: TourRole
  name: string
  description: string
  steps: Step[]
}

/**
 * Super Admin Tour
 * Focus: Platform profitability, tenant health, systemic risk
 */
export const superAdminTour: TourConfig = {
  id: 'superadmin-tour',
  role: 'superadmin',
  name: 'Platform Control Tour',
  description: 'Learn how to monitor and manage your entire platform',
  steps: [
    {
      target: 'body',
      content: 'Welcome to the Super Admin Control Tower! This tour will show you how to monitor platform health and manage tenants.',
      placement: 'center',
      disableBeacon: true,
    },
    {
      target: '[data-tour="portfolio-kpis"]',
      content: 'These KPIs show your platform\'s financial health - MRR, ARR, churn risk, and total budget at risk across all tenants.',
      placement: 'bottom',
    },
    {
      target: '[data-tour="tenant-health"]',
      content: 'Monitor tenant health at a glance. Tenants are categorized by EMQ status - from healthy (green) to critical (red).',
      placement: 'bottom',
    },
    {
      target: '[data-tour="emq-benchmarks"]',
      content: 'EMQ Benchmarks show performance percentiles (P25/P50/P75) across all tenants, helping you spot systemic issues.',
      placement: 'left',
    },
    {
      target: '[data-tour="top-issues"]',
      content: 'Top Issues highlights the most common problems affecting your tenants - prioritize platform-wide fixes here.',
      placement: 'left',
    },
    {
      target: '[data-tour="autopilot-distribution"]',
      content: 'See how many tenants are in each autopilot mode. Too many in "frozen" or "cuts_only" may indicate platform issues.',
      placement: 'top',
    },
    {
      target: '[data-tour="tenant-actions"]',
      content: 'Click on any tenant to view their profile, override settings, or trigger support workflows.',
      placement: 'bottom',
    },
  ],
}

/**
 * Account Manager Tour
 * Focus: Reduce firefighting, explain performance, drive renewals
 */
export const accountManagerTour: TourConfig = {
  id: 'account-manager-tour',
  role: 'account_manager',
  name: 'Portfolio Management Tour',
  description: 'Learn how to manage your assigned tenants effectively',
  steps: [
    {
      target: 'body',
      content: 'Welcome to your Account Manager Portfolio! This tour will help you manage clients and explain performance to stakeholders.',
      placement: 'center',
      disableBeacon: true,
    },
    {
      target: '[data-tour="portfolio-list"]',
      content: 'Your portfolio shows all assigned tenants with their EMQ score, confidence band, autopilot mode, and budget at risk.',
      placement: 'bottom',
    },
    {
      target: '[data-tour="priority-alerts"]',
      content: 'Priority alerts highlight critical tenants that need immediate attention - don\'t let these wait!',
      placement: 'bottom',
    },
    {
      target: '[data-tour="tenant-narrative"]',
      content: 'Click any tenant to see their narrative - a client-friendly summary of what changed, what\'s at risk, and what you\'re doing about it.',
      placement: 'right',
    },
    {
      target: '[data-tour="fix-playbook"]',
      content: 'The Fix Playbook shows prioritized issues with estimated EMQ impact. Assign owners and track resolution.',
      placement: 'left',
    },
    {
      target: '[data-tour="export-pdf"]',
      content: 'Export a client-safe PDF report that explains performance in business terms - perfect for stakeholder meetings.',
      placement: 'bottom',
    },
  ],
}

/**
 * Tenant Admin Tour
 * Focus: Trust, control, decisions, reporting
 */
export const tenantAdminTour: TourConfig = {
  id: 'tenant-admin-tour',
  role: 'tenant_admin',
  name: 'Trust Dashboard Tour',
  description: 'Learn how to trust your data and make confident decisions',
  steps: [
    {
      target: 'body',
      content: 'Welcome to your Trust Dashboard! This tour will help you understand when you can trust your data and make confident decisions.',
      placement: 'center',
      disableBeacon: true,
    },
    {
      target: '[data-tour="trust-header"]',
      content: 'The Trust Header shows your EMQ score, confidence band, and autopilot mode at a glance. Green = reliable data!',
      placement: 'bottom',
    },
    {
      target: '[data-tour="confidence-band"]',
      content: 'Confidence bands: Reliable (use freely), Directional (use with caution), or Unsafe (investigate first).',
      placement: 'bottom',
    },
    {
      target: '[data-tour="autopilot-mode"]',
      content: 'Autopilot mode shows what automated actions are allowed today. When data quality drops, automation is automatically restricted.',
      placement: 'bottom',
    },
    {
      target: '[data-tour="kpi-strip"]',
      content: 'KPIs are stamped with your confidence level. Lower confidence = wider error bars on these numbers.',
      placement: 'bottom',
    },
    {
      target: '[data-tour="fix-playbook"]',
      content: 'The Fix Playbook shows what needs to be fixed to improve your EMQ. Assign tasks to your team from here.',
      placement: 'left',
    },
  ],
}

/**
 * Media Buyer Tour
 * Focus: Optimize fast but safely; know what's allowed today
 */
export const mediaBuyerTour: TourConfig = {
  id: 'media-buyer-tour',
  role: 'media_buyer',
  name: 'Daily Console Tour',
  description: 'Learn how to optimize campaigns while staying safe',
  steps: [
    {
      target: 'body',
      content: 'Welcome to your Daily Console! This tour will show you how to optimize campaigns while staying within safe limits.',
      placement: 'center',
      disableBeacon: true,
    },
    {
      target: '[data-tour="console-header"]',
      content: 'The header always shows your EMQ, confidence, and what actions are allowed today. Check this before making changes!',
      placement: 'bottom',
    },
    {
      target: '[data-tour="allowed-actions"]',
      content: 'Allowed Actions tells you exactly what you can and can\'t do today based on data quality. Follow these guidelines!',
      placement: 'bottom',
    },
    {
      target: '[data-tour="action-cards"]',
      content: 'Action cards show opportunities, risks, and fixes. Each has a confidence score - higher confidence = safer to act.',
      placement: 'left',
    },
    {
      target: '[data-tour="apply-action"]',
      content: 'Apply actions directly from here. Disabled buttons mean the action is blocked due to low data quality.',
      placement: 'left',
    },
    {
      target: '[data-tour="fix-first"]',
      content: 'When data quality is low, "Fix First" tasks appear. Address these before making optimization changes.',
      placement: 'top',
    },
  ],
}

/**
 * Data Team Tour
 * Focus: Diagnose signal issues, recover fast, reduce volatility
 */
export const dataTeamTour: TourConfig = {
  id: 'data-team-tour',
  role: 'data_team',
  name: 'Signal Hub Tour',
  description: 'Learn how to diagnose and fix signal issues',
  steps: [
    {
      target: 'body',
      content: 'Welcome to the Signal Hub! This tour will help you diagnose signal issues and recover data quality fast.',
      placement: 'center',
      disableBeacon: true,
    },
    {
      target: '[data-tour="platform-signals"]',
      content: 'Platform Signal Cards show health by platform. Click to drill down into freshness, data loss, variance, and errors.',
      placement: 'bottom',
    },
    {
      target: '[data-tour="emq-drivers"]',
      content: 'EMQ Drivers break down your score into components. Find the weakest driver to focus your efforts.',
      placement: 'left',
    },
    {
      target: '[data-tour="active-incidents"]',
      content: 'Active Incidents shows open issues that need resolution. Click to see resolution steps and add notes.',
      placement: 'left',
    },
    {
      target: '[data-tour="resolution-steps"]',
      content: 'Each incident has resolution steps. Check them off as you complete them to track progress.',
      placement: 'right',
    },
    {
      target: '[data-tour="recovery-metrics"]',
      content: 'Recovery Metrics show your MTTR (Mean Time to Recover) and resolution rate. Track improvement over time.',
      placement: 'left',
    },
    {
      target: '[data-tour="volatility-badge"]',
      content: 'The Volatility Badge shows signal stability. High volatility means frequent incidents - focus on root causes.',
      placement: 'bottom',
    },
  ],
}

/**
 * General Tour (for users without specific role)
 */
export const generalTour: TourConfig = {
  id: 'general-tour',
  role: 'general',
  name: 'Platform Overview',
  description: 'Get familiar with the Stratum AI platform',
  steps: [
    {
      target: 'body',
      content: 'Welcome to Stratum AI! Let\'s take a quick tour of the platform.',
      placement: 'center',
      disableBeacon: true,
    },
    {
      target: '[data-tour="sidebar"]',
      content: 'The sidebar gives you access to all major features. Your available options depend on your role.',
      placement: 'right',
    },
    {
      target: '[data-tour="overview"]',
      content: 'The Overview page shows your key metrics and performance at a glance.',
      placement: 'bottom',
    },
    {
      target: '[data-tour="settings"]',
      content: 'Access your settings, integrations, and preferences from here.',
      placement: 'left',
    },
  ],
}

/**
 * Get tour by role
 */
export function getTourByRole(role: TourRole): TourConfig {
  switch (role) {
    case 'superadmin':
      return superAdminTour
    case 'account_manager':
      return accountManagerTour
    case 'tenant_admin':
      return tenantAdminTour
    case 'media_buyer':
      return mediaBuyerTour
    case 'data_team':
      return dataTeamTour
    default:
      return generalTour
  }
}

/**
 * Get all available tours
 */
export function getAllTours(): TourConfig[] {
  return [
    superAdminTour,
    accountManagerTour,
    tenantAdminTour,
    mediaBuyerTour,
    dataTeamTour,
    generalTour,
  ]
}

/**
 * Check if user has completed a specific tour
 */
export function hasTourCompleted(tourId: string): boolean {
  return localStorage.getItem(`stratum_tour_${tourId}_completed`) === 'true'
}

/**
 * Mark tour as completed
 */
export function markTourCompleted(tourId: string): void {
  localStorage.setItem(`stratum_tour_${tourId}_completed`, 'true')
}

/**
 * Reset tour completion status
 */
export function resetTour(tourId: string): void {
  localStorage.removeItem(`stratum_tour_${tourId}_completed`)
}

/**
 * Reset all tours
 */
export function resetAllTours(): void {
  getAllTours().forEach(tour => resetTour(tour.id))
}
