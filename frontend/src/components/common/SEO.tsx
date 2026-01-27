/**
 * SEO Component
 * Manages document head meta tags for SEO and social sharing
 */

import { Helmet } from 'react-helmet-async';

interface SEOProps {
  title?: string;
  description?: string;
  keywords?: string;
  image?: string;
  url?: string;
  type?: 'website' | 'article' | 'product';
  twitterCard?: 'summary' | 'summary_large_image';
  noIndex?: boolean;
  structuredData?: object;
}

const defaultMeta = {
  siteName: 'Stratum AI',
  title: 'Stratum AI - Revenue Operating System',
  description:
    'AI-powered marketing intelligence with Trust-Gated Autopilot. Real-time attribution, signal health monitoring, and automated optimization across Meta, Google, TikTok, and Snapchat.',
  image: '/og-image.png',
  url: 'https://stratum-ai.com',
  keywords:
    'marketing intelligence, CDP, customer data platform, ad optimization, ROAS, attribution, Meta ads, Google ads, TikTok ads',
};

export function SEO({
  title,
  description = defaultMeta.description,
  keywords = defaultMeta.keywords,
  image = defaultMeta.image,
  url = defaultMeta.url,
  type = 'website',
  twitterCard = 'summary_large_image',
  noIndex = false,
  structuredData,
}: SEOProps) {
  const fullTitle = title ? `${title} | ${defaultMeta.siteName}` : defaultMeta.title;

  const fullImageUrl = image.startsWith('http') ? image : `${defaultMeta.url}${image}`;

  return (
    <Helmet>
      {/* Primary Meta Tags */}
      <title>{fullTitle}</title>
      <meta name="title" content={fullTitle} />
      <meta name="description" content={description} />
      <meta name="keywords" content={keywords} />

      {/* Robots */}
      {noIndex && <meta name="robots" content="noindex, nofollow" />}

      {/* Open Graph / Facebook */}
      <meta property="og:type" content={type} />
      <meta property="og:url" content={url} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={fullImageUrl} />
      <meta property="og:site_name" content={defaultMeta.siteName} />

      {/* Twitter Card */}
      <meta name="twitter:card" content={twitterCard} />
      <meta name="twitter:url" content={url} />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={fullImageUrl} />

      {/* Canonical URL */}
      <link rel="canonical" href={url} />

      {/* Structured Data / JSON-LD */}
      {structuredData && (
        <script type="application/ld+json">{JSON.stringify(structuredData)}</script>
      )}
    </Helmet>
  );
}

/**
 * Page-specific SEO configurations
 */
export const pageSEO = {
  landing: {
    title: undefined, // Uses default
    description:
      'Transform your marketing with AI-powered intelligence. Trust-Gated Autopilot ensures automations only execute when data is reliable.',
  },
  pricing: {
    title: 'Pricing',
    description:
      'Simple, transparent pricing for Stratum AI. Start with a 14-day free trial. Plans from $499/month for growing teams.',
  },
  features: {
    title: 'Features',
    description:
      'Explore Stratum AI features: Trust Engine, Signal Health monitoring, CDP with audience sync, predictive analytics, and more.',
  },
  faq: {
    title: 'FAQ',
    description:
      'Frequently asked questions about Stratum AI. Learn about pricing, features, integrations, data security, and support.',
  },
  login: {
    title: 'Sign In',
    description:
      'Sign in to your Stratum AI account to access your marketing intelligence dashboard.',
    noIndex: true,
  },
  signup: {
    title: 'Sign Up',
    description:
      'Create your Stratum AI account and start your 14-day free trial. No credit card required.',
  },
  contact: {
    title: 'Contact Us',
    description:
      "Get in touch with the Stratum AI team. We're here to help with sales inquiries, support, and partnerships.",
  },
  about: {
    title: 'About Us',
    description:
      "Learn about Stratum AI's mission to bring trust and transparency to marketing automation.",
  },
  cdp: {
    title: 'Customer Data Platform',
    description:
      'Unify customer profiles, sync audiences to ad platforms, and build smart segments with Stratum AI CDP.',
  },
  docs: {
    title: 'Documentation',
    description:
      'Stratum AI documentation. Learn how to integrate, configure, and get the most out of the platform.',
  },
};

export default SEO;
