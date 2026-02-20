/**
 * Privacy Policy Page
 */

import { usePublicPage } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { pageSEO, SEO } from '@/components/common/SEO';
import { sanitizeHtml } from '@/lib/sanitize';
import { ShieldCheckIcon } from '@heroicons/react/24/outline';

export default function Privacy() {
  const { data: page } = usePublicPage('privacy');
  const hasCMSContent = !!(page?.content && page.content.length > 0);

  const seoTitle = page?.meta_title || pageSEO.privacy.title;
  const seoDescription = page?.meta_description || pageSEO.privacy.description;

  return (
    <PageLayout>
      <SEO {...pageSEO.privacy} title={seoTitle} description={seoDescription} url="https://stratum-ai.com/privacy" />
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(52, 199, 89, 0.1)',
              border: '1px solid rgba(52, 199, 89, 0.3)',
              color: '#34c759',
            }}
          >
            <ShieldCheckIcon className="w-4 h-4" />
            Legal
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">Privacy Policy</h1>
          <p style={{ color: 'rgba(255, 255, 255, 0.5)' }}>Last updated: January 15, 2026</p>
        </div>
      </section>

      {/* Content */}
      {hasCMSContent ? (
        <section className="py-12 px-6">
          <div className="max-w-4xl mx-auto prose prose-invert" dangerouslySetInnerHTML={{ __html: sanitizeHtml(page!.content!) }} />
        </section>
      ) : (
        <section className="py-12 px-6">
          <div className="max-w-4xl mx-auto">
            <div
              className="prose prose-invert max-w-none p-8 rounded-3xl"
              style={{
                background: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <div className="space-y-8" style={{ color: 'rgba(255, 255, 255, 0.8)' }}>
                <section>
                  <h2 className="text-2xl font-bold text-white mb-4">1. Introduction</h2>
                  <p>
                    Stratum AI, Inc. (&quot;Stratum AI,&quot; &quot;we,&quot; &quot;us,&quot; or
                    &quot;our&quot;) respects your privacy and is committed to protecting your
                    personal data. This privacy policy explains how we collect, use, disclose, and
                    safeguard your information when you use our services.
                  </p>
                </section>

                <section>
                  <h2 className="text-2xl font-bold text-white mb-4">2. Information We Collect</h2>
                  <h3 className="text-lg font-semibold text-white mb-2">
                    2.1 Information You Provide
                  </h3>
                  <ul className="list-disc pl-6 space-y-2">
                    <li>Account registration information (name, email, company)</li>
                    <li>Payment and billing information</li>
                    <li>Communications with our support team</li>
                    <li>Survey responses and feedback</li>
                  </ul>
                  <h3 className="text-lg font-semibold text-white mb-2 mt-4">
                    2.2 Information Collected Automatically
                  </h3>
                  <ul className="list-disc pl-6 space-y-2">
                    <li>Device and browser information</li>
                    <li>IP address and location data</li>
                    <li>Usage data and analytics</li>
                    <li>Cookies and similar technologies</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-2xl font-bold text-white mb-4">
                    3. How We Use Your Information
                  </h2>
                  <ul className="list-disc pl-6 space-y-2">
                    <li>Provide and maintain our services</li>
                    <li>Process transactions and send billing information</li>
                    <li>Send technical notices and security alerts</li>
                    <li>Respond to your comments and questions</li>
                    <li>Analyze usage patterns to improve our services</li>
                    <li>Detect and prevent fraud and abuse</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-2xl font-bold text-white mb-4">4. Data Sharing</h2>
                  <p>We may share your information with:</p>
                  <ul className="list-disc pl-6 space-y-2">
                    <li>Service providers who assist in our operations</li>
                    <li>Business partners with your consent</li>
                    <li>Legal authorities when required by law</li>
                    <li>Parties involved in a business transaction (merger, acquisition)</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-2xl font-bold text-white mb-4">5. Data Security</h2>
                  <p>
                    We implement industry-standard security measures to protect your data, including
                    encryption at rest and in transit, access controls, and regular security audits.
                    However, no method of transmission over the internet is 100% secure.
                  </p>
                </section>

                <section>
                  <h2 className="text-2xl font-bold text-white mb-4">6. Your Rights</h2>
                  <p>Depending on your location, you may have the right to:</p>
                  <ul className="list-disc pl-6 space-y-2">
                    <li>Access your personal data</li>
                    <li>Correct inaccurate data</li>
                    <li>Delete your data</li>
                    <li>Object to or restrict processing</li>
                    <li>Data portability</li>
                    <li>Withdraw consent</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-2xl font-bold text-white mb-4">7. International Transfers</h2>
                  <p>
                    Your data may be transferred to and processed in countries other than your own. We
                    ensure appropriate safeguards are in place, including Standard Contractual Clauses
                    approved by the European Commission.
                  </p>
                </section>

                <section>
                  <h2 className="text-2xl font-bold text-white mb-4">8. Data Retention</h2>
                  <p>
                    We retain your data for as long as your account is active or as needed to provide
                    services. We may retain certain information as required by law or for legitimate
                    business purposes.
                  </p>
                </section>

                <section>
                  <h2 className="text-2xl font-bold text-white mb-4">9. Contact Us</h2>
                  <p>
                    For questions about this privacy policy or our data practices, please contact our
                    Data Protection Officer at:
                  </p>
                  <p className="mt-4">
                    <strong className="text-white">Email:</strong> privacy@stratum.ai
                    <br />
                    <strong className="text-white">Address:</strong> 548 Market Street, Suite 35000,
                    San Francisco, CA 94104
                  </p>
                </section>
              </div>
            </div>
          </div>
        </section>
      )}
    </PageLayout>
  );
}
