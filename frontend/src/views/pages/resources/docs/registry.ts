/**
 * Documentation registry — single source of truth for both the `/docs`
 * portal navigation and the dynamic `/docs/*` article pages.
 *
 * `docsNav` drives the category cards on the portal; `docArticles` maps a
 * slug to its authored content. The two are kept in sync here: every
 * internal nav link (one starting `/docs/`) must resolve to an article.
 */

import {
  AcademicCapIcon,
  CloudIcon,
  CodeBracketIcon,
  CpuChipIcon,
  PlayIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import type { DocArticle, DocNavCategory } from './types';

import { gettingStartedArticles } from './content/gettingStarted';
import { apiReferenceArticles } from './content/apiReference';
import { trustEngineArticles } from './content/trustEngine';
import { cdpArticles } from './content/cdp';
import { integrationsArticles } from './content/integrations';
import { tutorialsArticles } from './content/tutorials';

export const docsNav: DocNavCategory[] = [
  {
    title: 'Getting Started',
    description: 'Quick start guides to get you up and running',
    icon: PlayIcon,
    links: [
      { name: 'Quick Start Guide', href: '/docs/quickstart' },
      { name: 'Installation', href: '/docs/installation' },
      { name: 'Authentication', href: '/docs/auth' },
      { name: 'First Campaign', href: '/docs/first-campaign' },
    ],
  },
  {
    title: 'API Reference',
    description: 'Complete API documentation with examples',
    icon: CodeBracketIcon,
    links: [
      { name: 'REST API', href: '/api-docs' },
      { name: 'Webhooks', href: '/docs/webhooks' },
      { name: 'SDKs', href: '/docs/sdks' },
      { name: 'Rate Limits', href: '/docs/rate-limits' },
    ],
  },
  {
    title: 'Trust Engine',
    description: 'Learn about our trust-gated automation',
    icon: ShieldCheckIcon,
    links: [
      { name: 'Signal Health', href: '/docs/signal-health' },
      { name: 'Trust Gates', href: '/docs/trust-gates' },
      { name: 'Autopilot Rules', href: '/docs/autopilot' },
      { name: 'Thresholds', href: '/docs/thresholds' },
    ],
  },
  {
    title: 'CDP',
    description: 'Customer Data Platform documentation',
    icon: CpuChipIcon,
    links: [
      { name: 'Profiles', href: '/docs/cdp/profiles' },
      { name: 'Segments', href: '/docs/cdp/segments' },
      { name: 'Identity Resolution', href: '/docs/cdp/identity' },
      { name: 'Audience Sync', href: '/docs/cdp/audience-sync' },
    ],
  },
  {
    title: 'Integrations',
    description: 'Connect with ad platforms and tools',
    icon: CloudIcon,
    links: [
      { name: 'Meta Ads', href: '/docs/integrations/meta' },
      { name: 'Google Ads', href: '/docs/integrations/google' },
      { name: 'TikTok Ads', href: '/docs/integrations/tiktok' },
      { name: 'CRM Systems', href: '/docs/integrations/crm' },
    ],
  },
  {
    title: 'Tutorials',
    description: 'Step-by-step guides and best practices',
    icon: AcademicCapIcon,
    links: [
      { name: 'Video Tutorials', href: '/docs/tutorials/videos' },
      { name: 'Use Cases', href: '/docs/tutorials/use-cases' },
      { name: 'Best Practices', href: '/docs/tutorials/best-practices' },
      { name: 'Troubleshooting', href: '/docs/tutorials/troubleshooting' },
    ],
  },
];

const allArticles: DocArticle[] = [
  ...gettingStartedArticles,
  ...apiReferenceArticles,
  ...trustEngineArticles,
  ...cdpArticles,
  ...integrationsArticles,
  ...tutorialsArticles,
];

export const docArticles: Record<string, DocArticle> = Object.fromEntries(
  allArticles.map((article) => [article.slug, article])
);

export function getDocArticle(slug: string | undefined): DocArticle | undefined {
  if (!slug) return undefined;
  return docArticles[slug.replace(/^\/+|\/+$/g, '')];
}

/** Ordered flat list of internal article slugs, for prev/next navigation. */
export const docArticleOrder: string[] = docsNav
  .flatMap((cat) => cat.links)
  .filter((l) => l.href.startsWith('/docs/'))
  .map((l) => l.href.replace(/^\/docs\//, ''));
