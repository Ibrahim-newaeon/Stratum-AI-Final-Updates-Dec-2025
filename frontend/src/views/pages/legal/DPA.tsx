/**
 * Data Processing Agreement Page
 */

import { usePublicPage } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { sanitizeHtml } from '@/lib/sanitize';
import { DocumentCheckIcon } from '@heroicons/react/24/outline';

export default function DPA() {
  const { data: page } = usePublicPage('dpa');
  const hasCMSContent = !!(page?.content && page.content.length > 0);

  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(168, 85, 247, 0.1)',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              color: '#a855f7',
            }}
          >
            <DocumentCheckIcon className="w-4 h-4" />
            Legal
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Data Processing Agreement
          </h1>
          <p style={{ color: 'rgba(255, 255, 255, 0.5)' }}>Last updated: January 15, 2026</p>
        </div>
      </section>

      {/* Content */}
      {hasCMSContent ? (
        <section className="py-12 px-6">
          <div className="max-w-4xl mx-auto prose prose-invert" dangerouslySetInnerHTML={{ __html: sanitizeHtml(page!.content!) }} />
        </section>
      ) : (
        <>
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
                      This Data Processing Agreement (&quot;DPA&quot;) forms part of the Terms of
                      Service between Stratum AI, Inc. (&quot;Processor&quot;) and the Customer
                      (&quot;Controller&quot;) and governs the processing of personal data by Processor
                      on behalf of Controller.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">2. Definitions</h2>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>
                        <strong className="text-white">&quot;Personal Data&quot;</strong> means any
                        information relating to an identified or identifiable natural person.
                      </li>
                      <li>
                        <strong className="text-white">&quot;Processing&quot;</strong> means any
                        operation performed on Personal Data.
                      </li>
                      <li>
                        <strong className="text-white">&quot;Data Subject&quot;</strong> means the
                        individual to whom Personal Data relates.
                      </li>
                      <li>
                        <strong className="text-white">&quot;Sub-processor&quot;</strong> means any
                        third party engaged by Processor to process Personal Data.
                      </li>
                    </ul>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">3. Scope of Processing</h2>
                    <h3 className="text-lg font-semibold text-white mb-2">3.1 Subject Matter</h3>
                    <p>
                      Processor processes Personal Data to provide the services described in the Terms
                      of Service, including customer data platform, audience synchronization, and
                      marketing automation.
                    </p>
                    <h3 className="text-lg font-semibold text-white mb-2 mt-4">
                      3.2 Categories of Data
                    </h3>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>Contact information (name, email, phone)</li>
                      <li>Identifiers (customer IDs, device IDs)</li>
                      <li>Behavioral data (events, page views, purchases)</li>
                      <li>Marketing data (campaign interactions, conversions)</li>
                    </ul>
                    <h3 className="text-lg font-semibold text-white mb-2 mt-4">
                      3.3 Categories of Data Subjects
                    </h3>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>Controller&apos;s customers and prospects</li>
                      <li>Controller&apos;s website visitors</li>
                      <li>Controller&apos;s employees (if applicable)</li>
                    </ul>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">4. Processor Obligations</h2>
                    <ul className="list-disc pl-6 space-y-2">
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
                    <h2 className="text-2xl font-bold text-white mb-4">5. Sub-processors</h2>
                    <p>
                      Controller provides general authorization for Processor to engage Sub-processors.
                      Processor maintains a list of current Sub-processors at
                      stratum.ai/legal/subprocessors. Processor will notify Controller of any new
                      Sub-processors 30 days in advance.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">6. International Transfers</h2>
                    <p>
                      For transfers of Personal Data outside the EEA, Processor ensures appropriate
                      safeguards through:
                    </p>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>Standard Contractual Clauses (SCCs)</li>
                      <li>Data Privacy Framework certification (where applicable)</li>
                      <li>Other lawful transfer mechanisms</li>
                    </ul>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">7. Security Measures</h2>
                    <p>Processor implements the following security measures:</p>
                    <ul className="list-disc pl-6 space-y-2">
                      <li>Encryption of data at rest and in transit</li>
                      <li>Access controls and authentication</li>
                      <li>Regular security testing and audits</li>
                      <li>Incident response procedures</li>
                      <li>Employee security training</li>
                      <li>Physical security of data centers</li>
                    </ul>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">8. Data Subject Rights</h2>
                    <p>
                      Processor will assist Controller in responding to Data Subject requests for
                      access, rectification, erasure, restriction, portability, and objection, taking
                      into account the nature of the processing.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">9. Data Breach Notification</h2>
                    <p>
                      Processor will notify Controller without undue delay, and in any event within 48
                      hours, after becoming aware of a Personal Data breach. Notification will include
                      the nature of the breach, categories of data affected, and recommended mitigation
                      measures.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">10. Audit Rights</h2>
                    <p>
                      Controller may audit Processor&apos;s compliance with this DPA once per year with
                      reasonable notice. Processor will provide SOC 2 Type II reports and other
                      compliance documentation upon request.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">11. Term and Termination</h2>
                    <p>
                      This DPA remains in effect for the duration of the Terms of Service. Upon
                      termination, Processor will delete all Personal Data within 90 days unless
                      retention is required by law.
                    </p>
                  </section>

                  <section>
                    <h2 className="text-2xl font-bold text-white mb-4">12. Contact</h2>
                    <p>For questions about this DPA, please contact our Data Protection Officer at:</p>
                    <p className="mt-4">
                      <strong className="text-white">Email:</strong> dpo@stratum.ai
                      <br />
                      <strong className="text-white">Address:</strong> 548 Market Street, Suite 35000,
                      San Francisco, CA 94104
                    </p>
                  </section>
                </div>
              </div>
            </div>
          </section>

          {/* Download CTA */}
          <section className="py-12 px-6">
            <div className="max-w-4xl mx-auto text-center">
              <div
                className="p-8 rounded-3xl"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <h2 className="text-2xl font-bold text-white mb-4">Need a Signed Copy?</h2>
                <p className="mb-6" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                  Request a pre-signed DPA for your records or contact us for a custom agreement.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                  <button
                    className="px-6 py-3 rounded-xl font-semibold text-white transition-all hover:opacity-90"
                    style={{
                      background: '#f97316',
                      boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
                    }}
                  >
                    Download DPA (PDF)
                  </button>
                  <button
                    className="px-6 py-3 rounded-xl font-semibold text-white transition-all hover:bg-white/10"
                    style={{
                      background: 'rgba(255, 255, 255, 0.06)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                    }}
                  >
                    Contact Legal Team
                  </button>
                </div>
              </div>
            </div>
          </section>
        </>
      )}
    </PageLayout>
  );
}
