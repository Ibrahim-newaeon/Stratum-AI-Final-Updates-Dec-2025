import type { MarketingSeedEntry } from './types';

const content = `<p>Last updated: January 15, 2026</p>
<h2>1. Introduction</h2>
<p>Stratum AI, Inc. ("Stratum AI," "we," "us," or "our") respects your privacy and is committed to protecting your personal data. This privacy policy explains how we collect, use, disclose, and safeguard your information when you use our services.</p>
<h2>2. Information We Collect</h2>
<h3>2.1 Information You Provide</h3>
<ul>
<li>Account registration information (name, email, company)</li>
<li>Payment and billing information</li>
<li>Communications with our support team</li>
<li>Survey responses and feedback</li>
</ul>
<h3>2.2 Information Collected Automatically</h3>
<ul>
<li>Device and browser information</li>
<li>IP address and location data</li>
<li>Usage data and analytics</li>
<li>Cookies and similar technologies</li>
</ul>
<h2>3. How We Use Your Information</h2>
<ul>
<li>Provide and maintain our services</li>
<li>Process transactions and send billing information</li>
<li>Send technical notices and security alerts</li>
<li>Respond to your comments and questions</li>
<li>Analyze usage patterns to improve our services</li>
<li>Detect and prevent fraud and abuse</li>
</ul>
<h2>4. Data Sharing</h2>
<p>We may share your information with:</p>
<ul>
<li>Service providers who assist in our operations</li>
<li>Business partners with your consent</li>
<li>Legal authorities when required by law</li>
<li>Parties involved in a business transaction (merger, acquisition)</li>
</ul>
<h2>5. Data Security</h2>
<p>We implement industry-standard security measures to protect your data, including encryption at rest and in transit, access controls, and regular security audits. However, no method of transmission over the internet is 100% secure.</p>
<h2>6. Your Rights</h2>
<p>Depending on your location, you may have the right to:</p>
<ul>
<li>Access your personal data</li>
<li>Correct inaccurate data</li>
<li>Delete your data</li>
<li>Object to or restrict processing</li>
<li>Data portability</li>
<li>Withdraw consent</li>
</ul>
<h2>7. International Transfers</h2>
<p>Your data may be transferred to and processed in countries other than your own. We ensure appropriate safeguards are in place, including Standard Contractual Clauses approved by the European Commission.</p>
<h2>8. Data Retention</h2>
<p>We retain your data for as long as your account is active or as needed to provide services. We may retain certain information as required by law or for legitimate business purposes.</p>
<h2>9. Contact Us</h2>
<p>For questions about this privacy policy or our data practices, please contact our Data Protection Officer at:</p>
<p><strong>Email:</strong> privacy@stratum.ai<br /><strong>Address:</strong> 548 Market Street, Suite 35000, San Francisco, CA 94104</p>`;

const entry: MarketingSeedEntry = {
  slug: 'privacy',
  title: 'Privacy Policy',
  template: 'default',
  meta_title: 'Privacy Policy',
  meta_description:
    'Stratum AI Privacy Policy. Learn how we collect, use, and protect your personal data.',
  content,
};

export default entry;
