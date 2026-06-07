/**
 * Terms of Service Page
 */

import { usePublicPage } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { MktHero, MktCard } from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';
import { sanitizeHtml } from '@/lib/sanitize';
import { DocumentTextIcon } from '@heroicons/react/24/outline';

export default function Terms() {
  const { data: page } = usePublicPage('terms');
  const hasCMSContent = !!(page?.content && page.content.length > 0);

  const seoTitle = page?.meta_title || pageSEO.terms.title;
  const seoDescription = page?.meta_description || pageSEO.terms.description;

  return (
    <PageLayout>
      <SEO {...pageSEO.terms} title={seoTitle} description={seoDescription} url="https://stratum-ai.com/terms" />
      {/* Hero Section */}
      <MktHero
        badge="Legal"
        badgeIcon={DocumentTextIcon}
        title="Terms of"
        highlight="Service"
        subtitle="Last updated: January 15, 2026"
      />

      {/* Content */}
      {hasCMSContent ? (
        <section className="pb-24">
          <div className="max-w-4xl mx-auto px-6">
            <MktCard className="p-8 md:p-10">
              <div
                className="space-y-4 text-body text-muted-foreground [&_h2]:text-h2 [&_h2]:text-foreground [&_h2]:font-semibold [&_h2]:mt-6 [&_h2]:mb-3 [&_h3]:text-h3 [&_h3]:text-foreground [&_h3]:font-semibold [&_ul]:list-disc [&_ul]:pl-6 [&_a]:text-secondary"
                dangerouslySetInnerHTML={{ __html: sanitizeHtml(page!.content!) }}
              />
            </MktCard>
          </div>
        </section>
      ) : (
        <section className="pb-24">
          <div className="max-w-4xl mx-auto px-6">
            <MktCard className="p-8 md:p-10">
              <div className="space-y-8">
                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">1. Acceptance of Terms</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    By accessing or using Stratum AI&apos;s services, you agree to be bound by these
                    Terms of Service. If you do not agree to these terms, please do not use our
                    services.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">2. Description of Services</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    Stratum AI provides a revenue operating system with trust-gated automation,
                    customer data platform, and marketing intelligence capabilities. Our services
                    include but are not limited to signal health monitoring, audience synchronization,
                    predictive analytics, and automated campaign optimization.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">3. Account Registration</h2>
                  <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                    <li>You must provide accurate and complete registration information</li>
                    <li>You are responsible for maintaining the security of your account</li>
                    <li>You must notify us immediately of any unauthorized access</li>
                    <li>You may not share your account credentials with others</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">4. Acceptable Use</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">You agree not to:</p>
                  <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                    <li>Violate any applicable laws or regulations</li>
                    <li>Infringe on the rights of others</li>
                    <li>Transmit harmful code or interfere with our services</li>
                    <li>Attempt to gain unauthorized access to our systems</li>
                    <li>Use our services for spam or unsolicited communications</li>
                    <li>Reverse engineer or decompile our software</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">5. Payment Terms</h2>
                  <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                    <li>Fees are billed in advance on a monthly or annual basis</li>
                    <li>All fees are non-refundable unless otherwise stated</li>
                    <li>We may change pricing with 30 days notice</li>
                    <li>You are responsible for all applicable taxes</li>
                  </ul>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">6. Intellectual Property</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    All intellectual property rights in our services remain with Stratum AI. You are
                    granted a limited, non-exclusive license to use our services for your internal
                    business purposes. You retain ownership of your data.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">7. Data Processing</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    Our processing of personal data is governed by our Privacy Policy and Data
                    Processing Agreement. You represent that you have the right to provide us with any
                    data you submit and that such data complies with applicable laws.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">8. Limitation of Liability</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    TO THE MAXIMUM EXTENT PERMITTED BY LAW, STRATUM AI SHALL NOT BE LIABLE FOR ANY
                    INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES. OUR TOTAL
                    LIABILITY SHALL NOT EXCEED THE AMOUNTS PAID BY YOU IN THE TWELVE MONTHS PRECEDING
                    THE CLAIM.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">9. Indemnification</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    You agree to indemnify and hold harmless Stratum AI from any claims, damages, or
                    expenses arising from your use of our services or violation of these terms.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">10. Termination</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    Either party may terminate this agreement with 30 days written notice. We may
                    suspend or terminate your access immediately for violation of these terms. Upon
                    termination, you may request export of your data within 30 days.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">11. Governing Law</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    These terms are governed by the laws of the State of California. Any disputes
                    shall be resolved in the courts of San Francisco County, California.
                  </p>
                </section>

                <section>
                  <h2 className="text-h2 text-foreground font-semibold mb-4">12. Contact</h2>
                  <p className="text-body text-muted-foreground leading-relaxed">
                    For questions about these terms, please contact us at:
                    <br />
                    <strong className="text-foreground">Email:</strong> legal@stratum.ai
                  </p>
                </section>
              </div>
            </MktCard>
          </div>
        </section>
      )}
    </PageLayout>
  );
}
