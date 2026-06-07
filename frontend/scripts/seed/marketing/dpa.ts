import type { MarketingSeedEntry } from './types';

const content = `<p>Last updated: January 15, 2026</p>
<h2>1. Introduction</h2>
<p>This Data Processing Agreement ("DPA") forms part of the Terms of Service between Stratum AI, Inc. ("Processor") and the Customer ("Controller") and governs the processing of personal data by Processor on behalf of Controller.</p>
<h2>2. Definitions</h2>
<ul>
<li><strong>"Personal Data"</strong> means any information relating to an identified or identifiable natural person.</li>
<li><strong>"Processing"</strong> means any operation performed on Personal Data.</li>
<li><strong>"Data Subject"</strong> means the individual to whom Personal Data relates.</li>
<li><strong>"Sub-processor"</strong> means any third party engaged by Processor to process Personal Data.</li>
</ul>
<h2>3. Scope of Processing</h2>
<h3>3.1 Subject Matter</h3>
<p>Processor processes Personal Data to provide the services described in the Terms of Service, including customer data platform, audience synchronization, and marketing automation.</p>
<h3>3.2 Categories of Data</h3>
<ul>
<li>Contact information (name, email, phone)</li>
<li>Identifiers (customer IDs, device IDs)</li>
<li>Behavioral data (events, page views, purchases)</li>
<li>Marketing data (campaign interactions, conversions)</li>
</ul>
<h3>3.3 Categories of Data Subjects</h3>
<ul>
<li>Controller's customers and prospects</li>
<li>Controller's website visitors</li>
<li>Controller's employees (if applicable)</li>
</ul>
<h2>4. Processor Obligations</h2>
<ul>
<li>Process Personal Data only on documented instructions from Controller</li>
<li>Ensure personnel are bound by confidentiality obligations</li>
<li>Implement appropriate technical and organizational security measures</li>
<li>Assist Controller with Data Subject requests</li>
<li>Assist Controller with security incident notifications</li>
<li>Delete or return Personal Data upon termination</li>
<li>Make available information necessary for compliance audits</li>
</ul>
<h2>5. Sub-processors</h2>
<p>Controller provides general authorization for Processor to engage Sub-processors. Processor maintains a list of current Sub-processors at stratum.ai/legal/subprocessors. Processor will notify Controller of any new Sub-processors 30 days in advance.</p>
<h2>6. International Transfers</h2>
<p>For transfers of Personal Data outside the EEA, Processor ensures appropriate safeguards through:</p>
<ul>
<li>Standard Contractual Clauses (SCCs)</li>
<li>Data Privacy Framework certification (where applicable)</li>
<li>Other lawful transfer mechanisms</li>
</ul>
<h2>7. Security Measures</h2>
<p>Processor implements the following security measures:</p>
<ul>
<li>Encryption of data at rest and in transit</li>
<li>Access controls and authentication</li>
<li>Regular security testing and audits</li>
<li>Incident response procedures</li>
<li>Employee security training</li>
<li>Physical security of data centers</li>
</ul>
<h2>8. Data Subject Rights</h2>
<p>Processor will assist Controller in responding to Data Subject requests for access, rectification, erasure, restriction, portability, and objection, taking into account the nature of the processing.</p>
<h2>9. Data Breach Notification</h2>
<p>Processor will notify Controller without undue delay, and in any event within 48 hours, after becoming aware of a Personal Data breach. Notification will include the nature of the breach, categories of data affected, and recommended mitigation measures.</p>
<h2>10. Audit Rights</h2>
<p>Controller may audit Processor's compliance with this DPA once per year with reasonable notice. Processor will provide SOC 2 Type II reports and other compliance documentation upon request.</p>
<h2>11. Term and Termination</h2>
<p>This DPA remains in effect for the duration of the Terms of Service. Upon termination, Processor will delete all Personal Data within 90 days unless retention is required by law.</p>
<h2>12. Contact</h2>
<p>For questions about this DPA, please contact our Data Protection Officer at:</p>
<p><strong>Email:</strong> dpo@stratum.ai<br /><strong>Address:</strong> 548 Market Street, Suite 35000, San Francisco, CA 94104</p>`;

const entry: MarketingSeedEntry = {
  slug: 'dpa',
  title: 'Data Processing Agreement',
  template: 'default',
  meta_title: 'Data Processing Agreement',
  meta_description:
    'Stratum AI Data Processing Agreement. Details on how we process personal data on behalf of our customers.',
  content,
};

export default entry;
