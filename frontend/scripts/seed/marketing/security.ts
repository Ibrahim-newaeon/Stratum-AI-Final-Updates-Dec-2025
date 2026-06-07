import type { MarketingSeedEntry } from './types';

const content = `<h2>Security Features</h2>
<h3>Encryption at Rest</h3>
<p>All data is encrypted using AES-256 encryption when stored.</p>
<h3>Encryption in Transit</h3>
<p>TLS 1.3 encryption for all data transmission.</p>
<h3>Access Controls</h3>
<p>Role-based access control with multi-factor authentication.</p>
<h3>Audit Logging</h3>
<p>Comprehensive audit logs for all system activities.</p>
<h3>SOC 2 Type II</h3>
<p>Annual SOC 2 Type II certification for security controls.</p>
<h3>GDPR Compliant</h3>
<p>Full compliance with GDPR, CCPA, and other privacy regulations.</p>
<h2>Our Security Practices</h2>
<h3>Infrastructure Security</h3>
<p>Our infrastructure is hosted on AWS with multiple availability zones for high availability. We use VPCs, security groups, and network ACLs to isolate and protect our systems.</p>
<h3>Application Security</h3>
<p>We follow secure development practices including code reviews, static analysis, and regular penetration testing. All dependencies are continuously monitored for vulnerabilities.</p>
<h3>Data Protection</h3>
<p>Customer data is isolated using tenant-specific encryption keys. We implement data minimization principles and retain data only as long as necessary.</p>
<h3>Incident Response</h3>
<p>We maintain a 24/7 security operations team and have a documented incident response plan. Customers are notified within 72 hours of any security incident affecting their data.</p>
<h3>Employee Security</h3>
<p>All employees undergo background checks and security training. Access to customer data is limited to those who require it for their job function.</p>
<h2>Certifications &amp; Compliance</h2>
<ul>
<li>SOC 2 Type II</li>
<li>GDPR</li>
<li>CCPA</li>
<li>ISO 27001</li>
<li>HIPAA Ready</li>
</ul>
<h2>Security Questions?</h2>
<p>Contact our security team for questions, vulnerability reports, or to request our SOC 2 report.</p>
<p><strong>Email:</strong> <a href="mailto:security@stratum.ai">security@stratum.ai</a></p>`;

const entry: MarketingSeedEntry = {
  slug: 'security',
  title: 'Security',
  template: 'default',
  meta_title: 'Security',
  meta_description:
    'Enterprise-grade security at Stratum AI. SOC 2 Type II certified, GDPR compliant, with encryption at rest and in transit.',
  content,
};

export default entry;
