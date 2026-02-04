/**
 * Terms of Service Page
 */

import { PageLayout } from '@/components/landing/PageLayout';
import { DocumentTextIcon } from '@heroicons/react/24/outline';

export default function Terms() {
  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(59, 130, 246, 0.1)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              color: '#3b82f6',
            }}
          >
            <DocumentTextIcon className="w-4 h-4" />
            Legal
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">Terms of Service</h1>
          <p style={{ color: 'rgba(255, 255, 255, 0.5)' }}>Last updated: January 15, 2026</p>
        </div>
      </section>

      {/* Content */}
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
                <h2 className="text-2xl font-bold text-white mb-4">1. Acceptance of Terms</h2>
                <p>
                  By accessing or using Stratum AI&apos;s services, you agree to be bound by these
                  Terms of Service. If you do not agree to these terms, please do not use our
                  services.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">2. Description of Services</h2>
                <p>
                  Stratum AI provides a revenue operating system with trust-gated automation,
                  customer data platform, and marketing intelligence capabilities. Our services
                  include but are not limited to signal health monitoring, audience synchronization,
                  predictive analytics, and automated campaign optimization.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">3. Account Registration</h2>
                <ul className="list-disc pl-6 space-y-2">
                  <li>You must provide accurate and complete registration information</li>
                  <li>You are responsible for maintaining the security of your account</li>
                  <li>You must notify us immediately of any unauthorized access</li>
                  <li>You may not share your account credentials with others</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">4. Acceptable Use</h2>
                <p>You agree not to:</p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Violate any applicable laws or regulations</li>
                  <li>Infringe on the rights of others</li>
                  <li>Transmit harmful code or interfere with our services</li>
                  <li>Attempt to gain unauthorized access to our systems</li>
                  <li>Use our services for spam or unsolicited communications</li>
                  <li>Reverse engineer or decompile our software</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">5. Payment Terms</h2>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Fees are billed in advance on a monthly or annual basis</li>
                  <li>All fees are non-refundable unless otherwise stated</li>
                  <li>We may change pricing with 30 days notice</li>
                  <li>You are responsible for all applicable taxes</li>
                </ul>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">6. Intellectual Property</h2>
                <p>
                  All intellectual property rights in our services remain with Stratum AI. You are
                  granted a limited, non-exclusive license to use our services for your internal
                  business purposes. You retain ownership of your data.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">7. Data Processing</h2>
                <p>
                  Our processing of personal data is governed by our Privacy Policy and Data
                  Processing Agreement. You represent that you have the right to provide us with any
                  data you submit and that such data complies with applicable laws.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">8. Limitation of Liability</h2>
                <p>
                  TO THE MAXIMUM EXTENT PERMITTED BY LAW, STRATUM AI SHALL NOT BE LIABLE FOR ANY
                  INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES. OUR TOTAL
                  LIABILITY SHALL NOT EXCEED THE AMOUNTS PAID BY YOU IN THE TWELVE MONTHS PRECEDING
                  THE CLAIM.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">9. Indemnification</h2>
                <p>
                  You agree to indemnify and hold harmless Stratum AI from any claims, damages, or
                  expenses arising from your use of our services or violation of these terms.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">10. Termination</h2>
                <p>
                  Either party may terminate this agreement with 30 days written notice. We may
                  suspend or terminate your access immediately for violation of these terms. Upon
                  termination, you may request export of your data within 30 days.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">11. Governing Law</h2>
                <p>
                  These terms are governed by the laws of the State of California. Any disputes
                  shall be resolved in the courts of San Francisco County, California.
                </p>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-white mb-4">12. Contact</h2>
                <p>
                  For questions about these terms, please contact us at:
                  <br />
                  <strong className="text-white">Email:</strong> legal@stratum.ai
                </p>
              </section>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
