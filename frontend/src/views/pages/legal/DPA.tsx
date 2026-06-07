/**
 * Data Processing Agreement Page
 */

import { usePublicPage } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { MktHero, MktCard, MktPrimaryButton, MktSecondaryButton } from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';
import { sanitizeHtml } from '@/lib/sanitize';
import { DocumentCheckIcon } from '@heroicons/react/24/outline';

export default function DPA() {
  const { data: page } = usePublicPage('dpa');
  const hasCMSContent = !!(page?.content && page.content.length > 0);

  const seoTitle = page?.meta_title || pageSEO.dpa.title;
  const seoDescription = page?.meta_description || pageSEO.dpa.description;

  return (
    <PageLayout>
      <SEO {...pageSEO.dpa} title={seoTitle} description={seoDescription} url="https://stratum-ai.com/dpa" />
      {/* Hero Section */}
      <MktHero
        badge="Legal"
        badgeIcon={DocumentCheckIcon}
        title="Data Processing"
        highlight="Agreement"
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
        <>
          <section className="pb-12 px-6">
            <div className="max-w-4xl mx-auto">
              <MktCard className="p-8 md:p-10">
                <div className="space-y-8">
                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">1. Introduction</h2>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      This Data Processing Agreement (&quot;DPA&quot;) forms part of the Terms of
                      Service between Stratum AI, Inc. (&quot;Processor&quot;) and the Customer
                      (&quot;Controller&quot;) and governs the processing of personal data by Processor
                      on behalf of Controller.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">2. Definitions</h2>
                    <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                      <li>
                        <strong className="text-foreground">&quot;Personal Data&quot;</strong> means any
                        information relating to an identified or identifiable natural person.
                      </li>
                      <li>
                        <strong className="text-foreground">&quot;Processing&quot;</strong> means any
                        operation performed on Personal Data.
                      </li>
                      <li>
                        <strong className="text-foreground">&quot;Data Subject&quot;</strong> means the
                        individual to whom Personal Data relates.
                      </li>
                      <li>
                        <strong className="text-foreground">&quot;Sub-processor&quot;</strong> means any
                        third party engaged by Processor to process Personal Data.
                      </li>
                    </ul>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">3. Scope of Processing</h2>
                    <h3 className="text-h3 text-foreground font-semibold mb-2 mt-4">3.1 Subject Matter</h3>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      Processor processes Personal Data to provide the services described in the Terms
                      of Service, including customer data platform, audience synchronization, and
                      marketing automation.
                    </p>
                    <h3 className="text-h3 text-foreground font-semibold mb-2 mt-4">
                      3.2 Categories of Data
                    </h3>
                    <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                      <li>Contact information (name, email, phone)</li>
                      <li>Identifiers (customer IDs, device IDs)</li>
                      <li>Behavioral data (events, page views, purchases)</li>
                      <li>Marketing data (campaign interactions, conversions)</li>
                    </ul>
                    <h3 className="text-h3 text-foreground font-semibold mb-2 mt-4">
                      3.3 Categories of Data Subjects
                    </h3>
                    <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                      <li>Controller&apos;s customers and prospects</li>
                      <li>Controller&apos;s website visitors</li>
                      <li>Controller&apos;s employees (if applicable)</li>
                    </ul>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">4. Processor Obligations</h2>
                    <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                      <li>Process Personal Data only on documented instructions from Controller</li>
                      <li>Ensure personnel are bound by confidentiality obligations</li>
                      <li>Implement appropriate technical and organizational security measures</li>
                      <li>Assist Controller with Data Subject requests</li>
                      <li>Assist Controller with security incident notifications</li>
                      <li>Delete or return Personal Data upon termination</li>
                      <li>Make available information necessary for compliance audits</li>
                    </ul>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">5. Sub-processors</h2>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      Controller provides general authorization for Processor to engage Sub-processors.
                      Processor maintains a list of current Sub-processors at
                      stratum.ai/legal/subprocessors. Processor will notify Controller of any new
                      Sub-processors 30 days in advance.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">6. International Transfers</h2>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      For transfers of Personal Data outside the EEA, Processor ensures appropriate
                      safeguards through:
                    </p>
                    <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                      <li>Standard Contractual Clauses (SCCs)</li>
                      <li>Data Privacy Framework certification (where applicable)</li>
                      <li>Other lawful transfer mechanisms</li>
                    </ul>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">7. Security Measures</h2>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      Processor implements the following security measures:
                    </p>
                    <ul className="list-disc pl-6 space-y-2 text-body text-muted-foreground">
                      <li>Encryption of data at rest and in transit</li>
                      <li>Access controls and authentication</li>
                      <li>Regular security testing and audits</li>
                      <li>Incident response procedures</li>
                      <li>Employee security training</li>
                      <li>Physical security of data centers</li>
                    </ul>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">8. Data Subject Rights</h2>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      Processor will assist Controller in responding to Data Subject requests for
                      access, rectification, erasure, restriction, portability, and objection, taking
                      into account the nature of the processing.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">9. Data Breach Notification</h2>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      Processor will notify Controller without undue delay, and in any event within 48
                      hours, after becoming aware of a Personal Data breach. Notification will include
                      the nature of the breach, categories of data affected, and recommended mitigation
                      measures.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">10. Audit Rights</h2>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      Controller may audit Processor&apos;s compliance with this DPA once per year with
                      reasonable notice. Processor will provide SOC 2 Type II reports and other
                      compliance documentation upon request.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">11. Term and Termination</h2>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      This DPA remains in effect for the duration of the Terms of Service. Upon
                      termination, Processor will delete all Personal Data within 90 days unless
                      retention is required by law.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-h2 text-foreground font-semibold mb-4">12. Contact</h2>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      For questions about this DPA, please contact our Data Protection Officer at:
                    </p>
                    <p className="mt-4 text-body text-muted-foreground leading-relaxed">
                      <strong className="text-foreground">Email:</strong> dpo@stratum.ai
                      <br />
                      <strong className="text-foreground">Address:</strong> 548 Market Street, Suite 35000,
                      San Francisco, CA 94104
                    </p>
                  </section>
                </div>
              </MktCard>
            </div>
          </section>

          {/* Download CTA */}
          <section className="py-12 pb-24 px-6">
            <div className="max-w-4xl mx-auto text-center">
              <MktCard className="p-8 md:p-12">
                <h2 className="text-h2 text-foreground font-semibold mb-4">Need a Signed Copy?</h2>
                <p className="text-body text-muted-foreground leading-relaxed mb-6">
                  Request a pre-signed DPA for your records or contact us for a custom agreement.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  <MktPrimaryButton label="Download DPA (PDF)" href="/dpa" />
                  <MktSecondaryButton label="Contact Legal Team" href="/contact" />
                </div>
              </MktCard>
            </div>
          </section>
        </>
      )}
    </PageLayout>
  );
}
