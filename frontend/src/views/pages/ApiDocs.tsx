/**
 * API Docs Page — landing-themed (ink + ember).
 */

import { usePageContent, type ApiDocsPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import {
  MktHero,
  MktSectionHeader,
  MktFeatureCard,
  MktCard,
} from '@/components/landing/marketing';
import { SEO } from '@/components/common/SEO';
import {
  BookOpenIcon,
  CodeBracketIcon,
  CommandLineIcon,
  CubeIcon,
} from '@heroicons/react/24/outline';

const iconMap: Record<string, typeof BookOpenIcon> = {
  BookOpenIcon,
  CodeBracketIcon,
  CommandLineIcon,
  CubeIcon,
};

const fallbackSections = [
  {
    icon: BookOpenIcon,
    title: 'Getting Started',
    description: 'Learn the basics and set up your first integration.',
    href: '#getting-started',
  },
  {
    icon: CodeBracketIcon,
    title: 'API Reference',
    description: 'Complete reference for all API endpoints.',
    href: '#api-reference',
  },
  {
    icon: CommandLineIcon,
    title: 'SDKs & Libraries',
    description: 'Official SDKs for JavaScript, Python, and more.',
    href: '#sdks',
  },
  {
    icon: CubeIcon,
    title: 'Webhooks',
    description: 'Real-time event notifications for your app.',
    href: '#webhooks',
  },
];

const fallbackEndpoints = [
  { method: 'GET', path: '/api/v1/signals', description: 'List all signals' },
  { method: 'POST', path: '/api/v1/signals', description: 'Create a new signal' },
  { method: 'GET', path: '/api/v1/signals/:id/health', description: 'Get signal health score' },
  { method: 'GET', path: '/api/v1/automations', description: 'List all automations' },
  { method: 'POST', path: '/api/v1/automations/execute', description: 'Execute automation' },
  { method: 'GET', path: '/api/v1/cdp/profiles', description: 'Search customer profiles' },
  { method: 'POST', path: '/api/v1/cdp/segments', description: 'Create a segment' },
  { method: 'POST', path: '/api/v1/audience-sync', description: 'Sync audience to platform' },
];

function methodClasses(method: string): string {
  switch (method.toUpperCase()) {
    case 'GET':
      return 'bg-accent/10 text-accent border-accent/20';
    case 'POST':
      return 'bg-secondary/10 text-secondary border-secondary/20';
    case 'DELETE':
      return 'bg-destructive/10 text-destructive border-destructive/20';
    default:
      return 'bg-warning/10 text-warning border-warning/20';
  }
}

export default function ApiDocs() {
  const { content } = usePageContent<ApiDocsPageContent>('api-docs');

  const quickLinks = content?.sections?.length
    ? content.sections.map((s) => ({
        icon: iconMap[s.iconName] || BookOpenIcon,
        title: s.title,
        description: s.description,
        href: s.href,
      }))
    : fallbackSections;

  const endpoints = content?.endpoints?.length
    ? content.endpoints.map((e) => ({
        method: e.method,
        path: e.path,
        description: e.description,
      }))
    : fallbackEndpoints;

  return (
    <PageLayout>
      <SEO
        title="API Documentation"
        description="Build on the Stratum API — REST endpoints for signals, automations, the CDP, and audience sync, with SDKs and real-time webhooks."
        url="https://stratumai.app/api-docs"
      />

      <MktHero
        badge="API Documentation"
        badgeIcon={CodeBracketIcon}
        title="Build on the"
        highlight="Stratum API"
        subtitle="A clean, predictable REST API for signals, automations, the CDP, and audience sync — with SDKs and real-time webhooks."
        primary={{ label: 'Start Free Trial', href: '/signup' }}
        secondary={{ label: 'View integrations', href: '/integrations' }}
      />

      {/* Quick links */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {quickLinks.map((link, i) => (
              <MktFeatureCard
                key={link.title}
                icon={link.icon}
                title={link.title}
                description={link.description}
                delay={(i % 4) * 0.05}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Endpoints */}
      <section className="py-24 lg:py-28">
        <div className="max-w-4xl mx-auto px-6 lg:px-8">
          <MktSectionHeader
            eyebrow="API Reference"
            title="Popular"
            highlight="endpoints"
            subtitle="A taste of what you can do. See the full reference for every route, parameter, and response."
          />
          <MktCard className="divide-y divide-border overflow-hidden">
            {endpoints.map((endpoint) => (
              <div
                key={`${endpoint.method}-${endpoint.path}`}
                className="flex flex-col sm:flex-row sm:items-center gap-3 p-5 hover:bg-foreground/[0.02] transition-colors"
              >
                <span
                  className={`inline-flex w-fit items-center px-2.5 py-1 rounded-md border text-micro font-semibold uppercase tracking-wide ${methodClasses(
                    endpoint.method
                  )}`}
                >
                  {endpoint.method}
                </span>
                <code className="font-mono text-body text-foreground sm:flex-1 break-all">
                  {endpoint.path}
                </code>
                <span className="text-body text-muted-foreground sm:text-right">
                  {endpoint.description}
                </span>
              </div>
            ))}
          </MktCard>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
