/**
 * Integrations Page
 * Showcases all platform integrations
 */

import { Link } from 'react-router-dom';
import { usePageContent, type IntegrationsPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { SEO } from '@/components/common/SEO';

const categoryColors: Record<string, string> = {
  'Ad Platforms': '#f97316',
  'Analytics & Attribution': '#06b6d4',
  'CRM & Sales': '#a855f7',
  'E-commerce': '#34c759',
  Communication: '#3b82f6',
};

const fallbackIntegrations = {
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

  // Use CMS data if available, otherwise fallback
  const integrations: Record<string, { name: string; description: string; logo: string }[]> =
    content?.categories?.length
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
      <SEO title="Integrations" description="Connect Stratum AI with Meta, Google, TikTok, Snapchat, and 30+ marketing platforms. Unified data, one dashboard." url="https://stratum-ai.com/integrations" />
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Connect Your</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Entire Stack
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto mb-10"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            Stratum AI integrates with 50+ platforms to unify your marketing data and automate
            across channels.
          </p>
          <Link
            to="/signup"
            className="inline-flex px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:opacity-90"
            style={{
              background: '#f97316',
              boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
            }}
          >
            Start Free Trial
          </Link>
        </div>
      </section>

      {/* Integrations Grid */}
      <section className="py-12 px-6">
        <div className="max-w-7xl mx-auto">
          {Object.entries(integrations).map(([category, items]) => {
            const color = categoryColors[category] || '#a855f7';
            return (
              <div key={category} className="mb-16">
                <h2 className="text-2xl font-bold text-white mb-8">{category}</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map((integration) => (
                    <div
                      key={integration.name}
                      className="p-6 rounded-2xl transition-all hover:scale-[1.02] group backdrop-blur-xl"
                      style={{
                        background: `${color}15`,
                        border: `1px solid ${color}30`,
                        boxShadow: `0 8px 32px ${color}10`,
                      }}
                    >
                      <div className="flex items-center gap-4">
                        <div
                          className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold"
                          style={{
                            background: `${color}40`,
                            border: `1px solid ${color}60`,
                          }}
                        >
                          {integration.logo}
                        </div>
                        <div>
                          <h3 className="font-semibold text-white">{integration.name}</h3>
                          <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                            {integration.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Custom Integration CTA */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="p-12 rounded-3xl"
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">Need a Custom Integration?</h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              Our API allows you to connect any data source. Contact us to discuss your needs.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                to="/api-docs"
                className="px-8 py-4 rounded-xl font-semibold text-white transition-all hover:bg-white/10"
                style={{
                  background: 'rgba(255, 255, 255, 0.06)',
                  border: '1px solid rgba(255, 255, 255, 0.12)',
                }}
              >
                View API Docs
              </Link>
              <Link
                to="/contact"
                className="px-8 py-4 rounded-xl font-semibold text-white transition-all hover:opacity-90"
                style={{
                  background: '#f97316',
                  boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
                }}
              >
                Contact Sales
              </Link>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
