/**
 * Integrations Page — landing-themed (ink + ember).
 */

import { usePageContent, type IntegrationsPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { MktHero, MktCard } from '@/components/landing/marketing';
import { SEO } from '@/components/common/SEO';

const fallbackIntegrations: Record<
  string,
  { name: string; description: string; logo: string }[]
> = {
  'Ad Platforms': [
    { name: 'Meta Ads', description: 'Facebook & Instagram advertising', logo: 'M' },
    { name: 'Google Ads', description: 'Search, Display & YouTube', logo: 'G' },
    { name: 'TikTok Ads', description: 'TikTok advertising platform', logo: 'T' },
    { name: 'Snapchat Ads', description: 'Snapchat marketing API', logo: 'S' },
    { name: 'LinkedIn Ads', description: 'B2B advertising', logo: 'L' },
    { name: 'Twitter/X Ads', description: 'Twitter advertising', logo: 'X' },
  ],
  'Analytics & Attribution': [
    { name: 'Google Analytics', description: 'Web analytics', logo: 'GA' },
    { name: 'Mixpanel', description: 'Product analytics', logo: 'MP' },
    { name: 'Amplitude', description: 'Digital analytics', logo: 'A' },
    { name: 'Segment', description: 'Customer data platform', logo: 'SG' },
  ],
  'CRM & Sales': [
    { name: 'Salesforce', description: 'CRM platform', logo: 'SF' },
    { name: 'HubSpot', description: 'Marketing & sales', logo: 'HS' },
    { name: 'Pipedrive', description: 'Sales CRM', logo: 'PD' },
  ],
  'E-commerce': [
    { name: 'Shopify', description: 'E-commerce platform', logo: 'SH' },
    { name: 'WooCommerce', description: 'WordPress commerce', logo: 'WC' },
    { name: 'Magento', description: 'Adobe Commerce', logo: 'MG' },
  ],
  Communication: [
    { name: 'Slack', description: 'Team messaging', logo: 'SL' },
    { name: 'WhatsApp Business', description: 'Customer messaging', logo: 'WA' },
    { name: 'Intercom', description: 'Customer messaging', logo: 'IC' },
  ],
};

export default function Integrations() {
  const { content } = usePageContent<IntegrationsPageContent>('integrations');

  const integrations: Record<
    string,
    { name: string; description: string; logo: string }[]
  > = content?.categories?.length
    ? content.categories.reduce(
        (acc, cat) => {
          acc[cat.name] = cat.platforms.map((p) => ({
            name: p.name,
            description: p.description,
            logo: p.iconName,
          }));
          return acc;
        },
        {} as Record<string, { name: string; description: string; logo: string }[]>
      )
    : fallbackIntegrations;

  return (
    <PageLayout>
      <SEO
        title="Integrations"
        description="Connect Stratum AI with Meta, Google, TikTok, Snapchat, and 30+ marketing platforms. Unified data, one dashboard."
        url="https://stratumai.app/integrations"
      />

      <MktHero
        badge="Integrations"
        title="Connect your"
        highlight="entire stack"
        subtitle="Stratum AI integrates with 30+ platforms to unify your marketing data and automate across every channel."
        primary={{ label: 'Start Free Trial', href: '/signup' }}
        secondary={{ label: 'Read the API docs', href: '/api-docs' }}
      />

      <section className="pb-24 lg:pb-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8 space-y-16">
          {Object.entries(integrations).map(([category, items]) => (
            <div key={category}>
              <h2 className="text-h1 text-foreground font-semibold mb-8">{category}</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {items.map((integration, i) => (
                  <MktCard
                    key={integration.name}
                    delay={(i % 3) * 0.05}
                    className="p-6 flex items-center gap-4"
                  >
                    <div className="w-12 h-12 flex-shrink-0 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center">
                      <span className="text-body font-semibold text-secondary">
                        {integration.logo}
                      </span>
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-h3 text-foreground font-semibold truncate">
                        {integration.name}
                      </h3>
                      <p className="text-body text-muted-foreground truncate">
                        {integration.description}
                      </p>
                    </div>
                  </MktCard>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
