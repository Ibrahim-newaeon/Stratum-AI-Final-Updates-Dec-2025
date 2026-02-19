/**
 * Security Page
 */

import { usePublicPage } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { sanitizeHtml } from '@/lib/sanitize';
import {
  DocumentCheckIcon,
  EyeIcon,
  KeyIcon,
  LockClosedIcon,
  ServerIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

const securityFeatures = [
  {
    icon: LockClosedIcon,
    title: 'Encryption at Rest',
    description: 'All data is encrypted using AES-256 encryption when stored.',
  },
  {
    icon: ServerIcon,
    title: 'Encryption in Transit',
    description: 'TLS 1.3 encryption for all data transmission.',
  },
  {
    icon: KeyIcon,
    title: 'Access Controls',
    description: 'Role-based access control with multi-factor authentication.',
  },
  {
    icon: EyeIcon,
    title: 'Audit Logging',
    description: 'Comprehensive audit logs for all system activities.',
  },
  {
    icon: ShieldCheckIcon,
    title: 'SOC 2 Type II',
    description: 'Annual SOC 2 Type II certification for security controls.',
  },
  {
    icon: DocumentCheckIcon,
    title: 'GDPR Compliant',
    description: 'Full compliance with GDPR, CCPA, and other privacy regulations.',
  },
];

export default function Security() {
  const { data: page } = usePublicPage('security');
  const hasCMSContent = !!(page?.content && page.content.length > 0);

  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(52, 199, 89, 0.1)',
              border: '1px solid rgba(52, 199, 89, 0.3)',
              color: '#34c759',
            }}
          >
            <ShieldCheckIcon className="w-4 h-4" />
            Security
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Enterprise-Grade</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Security
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            Your data security is our top priority. We implement industry-leading security measures
            to protect your information.
          </p>
        </div>
      </section>

      {/* Content */}
      {hasCMSContent ? (
        <section className="py-12 px-6">
          <div className="max-w-4xl mx-auto prose prose-invert" dangerouslySetInnerHTML={{ __html: sanitizeHtml(page!.content!) }} />
        </section>
      ) : (
        <>
          {/* Security Features */}
          <section className="py-12 px-6">
            <div className="max-w-7xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {securityFeatures.map((feature) => (
                  <div
                    key={feature.title}
                    className="p-6 rounded-2xl"
                    style={{
                      background: 'rgba(255, 255, 255, 0.04)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                    }}
                  >
                    <feature.icon className="w-10 h-10 mb-4" style={{ color: '#34c759' }} />
                    <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                    <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                      {feature.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Security Practices */}
          <section className="py-20 px-6">
            <div className="max-w-4xl mx-auto">
              <div
                className="p-8 rounded-3xl"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <h2 className="text-2xl font-bold text-white mb-6">Our Security Practices</h2>
                <div className="space-y-6" style={{ color: 'rgba(255, 255, 255, 0.8)' }}>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">Infrastructure Security</h3>
                    <p>
                      Our infrastructure is hosted on AWS with multiple availability zones for high
                      availability. We use VPCs, security groups, and network ACLs to isolate and
                      protect our systems.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">Application Security</h3>
                    <p>
                      We follow secure development practices including code reviews, static analysis,
                      and regular penetration testing. All dependencies are continuously monitored for
                      vulnerabilities.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">Data Protection</h3>
                    <p>
                      Customer data is isolated using tenant-specific encryption keys. We implement data
                      minimization principles and retain data only as long as necessary.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">Incident Response</h3>
                    <p>
                      We maintain a 24/7 security operations team and have a documented incident
                      response plan. Customers are notified within 72 hours of any security incident
                      affecting their data.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-2">Employee Security</h3>
                    <p>
                      All employees undergo background checks and security training. Access to customer
                      data is limited to those who require it for their job function.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Certifications */}
          <section className="py-12 px-6">
            <div className="max-w-4xl mx-auto text-center">
              <h2 className="text-2xl font-bold text-white mb-8">Certifications & Compliance</h2>
              <div className="flex flex-wrap justify-center gap-6">
                {['SOC 2 Type II', 'GDPR', 'CCPA', 'ISO 27001', 'HIPAA Ready'].map((cert) => (
                  <div
                    key={cert}
                    className="px-6 py-3 rounded-xl"
                    style={{
                      background: 'rgba(52, 199, 89, 0.1)',
                      border: '1px solid rgba(52, 199, 89, 0.3)',
                      color: '#34c759',
                    }}
                  >
                    {cert}
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Contact */}
          <section className="py-20 px-6">
            <div className="max-w-4xl mx-auto text-center">
              <div
                className="p-12 rounded-3xl"
                style={{
                  background:
                    'linear-gradient(135deg, rgba(52, 199, 89, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                }}
              >
                <h2 className="text-3xl font-bold text-white mb-4">Security Questions?</h2>
                <p className="text-lg mb-6" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                  Contact our security team for questions, vulnerability reports, or to request our SOC
                  2 report.
                </p>
                <p style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                  <strong className="text-white">Email:</strong>{' '}
                  <a href="mailto:security@stratum.ai" className="text-orange-500 hover:underline">
                    security@stratum.ai
                  </a>
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </PageLayout>
  );
}
