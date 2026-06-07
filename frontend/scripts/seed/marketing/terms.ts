import type { MarketingSeedEntry } from './types';

const content = `<p>Last updated: January 15, 2026</p>
<h2>1. Acceptance of Terms</h2>
<p>By accessing or using Stratum AI's services, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our services.</p>
<h2>2. Description of Services</h2>
<p>Stratum AI provides a revenue operating system with trust-gated automation, customer data platform, and marketing intelligence capabilities. Our services include but are not limited to signal health monitoring, audience synchronization, predictive analytics, and automated campaign optimization.</p>
<h2>3. Account Registration</h2>
<ul>
<li>You must provide accurate and complete registration information</li>
<li>You are responsible for maintaining the security of your account</li>
<li>You must notify us immediately of any unauthorized access</li>
<li>You may not share your account credentials with others</li>
</ul>
<h2>4. Acceptable Use</h2>
<p>You agree not to:</p>
<ul>
<li>Violate any applicable laws or regulations</li>
<li>Infringe on the rights of others</li>
<li>Transmit harmful code or interfere with our services</li>
<li>Attempt to gain unauthorized access to our systems</li>
<li>Use our services for spam or unsolicited communications</li>
<li>Reverse engineer or decompile our software</li>
</ul>
<h2>5. Payment Terms</h2>
<ul>
<li>Fees are billed in advance on a monthly or annual basis</li>
<li>All fees are non-refundable unless otherwise stated</li>
<li>We may change pricing with 30 days notice</li>
<li>You are responsible for all applicable taxes</li>
</ul>
<h2>6. Intellectual Property</h2>
<p>All intellectual property rights in our services remain with Stratum AI. You are granted a limited, non-exclusive license to use our services for your internal business purposes. You retain ownership of your data.</p>
<h2>7. Data Processing</h2>
<p>Our processing of personal data is governed by our Privacy Policy and Data Processing Agreement. You represent that you have the right to provide us with any data you submit and that such data complies with applicable laws.</p>
<h2>8. Limitation of Liability</h2>
<p>TO THE MAXIMUM EXTENT PERMITTED BY LAW, STRATUM AI SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES. OUR TOTAL LIABILITY SHALL NOT EXCEED THE AMOUNTS PAID BY YOU IN THE TWELVE MONTHS PRECEDING THE CLAIM.</p>
<h2>9. Indemnification</h2>
<p>You agree to indemnify and hold harmless Stratum AI from any claims, damages, or expenses arising from your use of our services or violation of these terms.</p>
<h2>10. Termination</h2>
<p>Either party may terminate this agreement with 30 days written notice. We may suspend or terminate your access immediately for violation of these terms. Upon termination, you may request export of your data within 30 days.</p>
<h2>11. Governing Law</h2>
<p>These terms are governed by the laws of the State of California. Any disputes shall be resolved in the courts of San Francisco County, California.</p>
<h2>12. Contact</h2>
<p>For questions about these terms, please contact us at:<br /><strong>Email:</strong> legal@stratum.ai</p>`;

const entry: MarketingSeedEntry = {
  slug: 'terms',
  title: 'Terms of Service',
  template: 'default',
  meta_title: 'Terms of Service',
  meta_description:
    'Stratum AI Terms of Service. Review the terms governing your use of our revenue operating system.',
  content,
};

export default entry;
