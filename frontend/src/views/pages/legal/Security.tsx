/**
 * Security Page
 */

import { usePublicPage } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { MktHero, MktCard, MktFeatureCard, MktBadge } from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';
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

  const seoTitle = page?.meta_title || pageSEO.security.title;
  const seoDescription = page?.meta_description || pageSEO.security.description;

  return (
    <PageLayout>
      <SEO {...pageSEO.security} title={seoTitle} description={seoDescription} url="https://stratum-ai.com/security" />
      {/* Hero Section */}
      <MktHero
        badge="Security"
        badgeIcon={ShieldCheckIcon}
        title="Security at"
        highlight="Stratum"
        subtitle="Your data security is our top priority. We implement industry-leading security measures to protect your information."
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
          {/* Security Features */}
          <section className="pb-12 px-6">
            <div className="max-w-7xl mx-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {securityFeatures.map((feature) => (
                  <MktFeatureCard
                    key={feature.title}
                    icon={feature.icon}
                    title={feature.title}
                    description={feature.description}
                  />
                ))}
              </div>
            </div>
          </section>

          {/* Security Practices */}
          <section className="py-12 px-6">
            <div className="max-w-4xl mx-auto">
              <MktCard className="p-8 md:p-10">
                <h2 className="text-h2 text-foreground font-semibold mb-6">Our Security Practices</h2>
                <div className="space-y-6">
                  <div>
                    <h3 className="text-h3 text-foreground font-semibold mb-2">Infrastructure Security</h3>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      Our infrastructure is hosted on AWS with multiple availability zones for high
                      availability. We use VPCs, security groups, and network ACLs to isolate and
                      protect our systems.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-h3 text-foreground font-semibold mb-2">Application Security</h3>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      We follow secure development practices including code reviews, static analysis,
                      and regular penetration testing. All dependencies are continuously monitored for
                      vulnerabilities.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-h3 text-foreground font-semibold mb-2">Data Protection</h3>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      Customer data is isolated using tenant-specific encryption keys. We implement data
                      minimization principles and retain data only as long as necessary.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-h3 text-foreground font-semibold mb-2">Incident Response</h3>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      We maintain a 24/7 security operations team and have a documented incident
                      response plan. Customers are notified within 72 hours of any security incident
                      affecting their data.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-h3 text-foreground font-semibold mb-2">Employee Security</h3>
                    <p className="text-body text-muted-foreground leading-relaxed">
                      All employees undergo background checks and security training. Access to customer
                      data is limited to those who require it for their job function.
                    </p>
                  </div>
                </div>
              </MktCard>
            </div>
          </section>

          {/* Certifications */}
          <section className="py-12 px-6">
            <div className="max-w-4xl mx-auto text-center">
              <h2 className="text-h2 text-foreground font-semibold mb-8">Certifications &amp; Compliance</h2>
              <div className="flex flex-wrap justify-center gap-6">
                {['SOC 2 Type II', 'GDPR', 'CCPA', 'ISO 27001', 'HIPAA Ready'].map((cert) => (
                  <MktBadge key={cert}>{cert}</MktBadge>
                ))}
              </div>
            </div>
          </section>

          {/* Contact */}
          <section className="py-12 pb-24 px-6">
            <div className="max-w-4xl mx-auto text-center">
              <MktCard className="p-8 md:p-12">
                <h2 className="text-h2 text-foreground font-semibold mb-4">Security Questions?</h2>
                <p className="text-body text-muted-foreground leading-relaxed mb-6">
                  Contact our security team for questions, vulnerability reports, or to request our SOC
                  2 report.
                </p>
                <p className="text-body text-muted-foreground leading-relaxed">
                  <strong className="text-foreground">Email:</strong>{' '}
                  <a href="mailto:security@stratum.ai" className="text-secondary hover:underline">
                    security@stratum.ai
                  </a>
                </p>
              </MktCard>
            </div>
          </section>
        </>
      )}
    </PageLayout>
  );
}
