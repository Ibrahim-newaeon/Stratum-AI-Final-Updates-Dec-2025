/**
 * Contact Page — landing-themed (ink + ember).
 * Contact form and information - submits to CMS API.
 */

import { useState } from 'react';
import { PageLayout } from '@/components/landing/PageLayout';
import { MktHero, MktCard } from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';
import {
  ChatBubbleLeftRightIcon,
  CheckCircleIcon,
  EnvelopeIcon,
  ExclamationCircleIcon,
  MapPinIcon,
} from '@heroicons/react/24/outline';
import { useSubmitContact } from '@/api/cms';

const inputClass =
  'w-full px-4 py-3 rounded-xl bg-card border border-border text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/30 transition-colors';

export default function Contact() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    subject: '',
    message: '',
  });
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitContact = useSubmitContact();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      await submitContact.mutateAsync(formData);
      setSubmitted(true);
      setFormData({
        name: '',
        email: '',
        company: '',
        subject: '',
        message: '',
      });
    } catch (err) {
      setError('Failed to submit your message. Please try again.');
    }
  };

  if (submitted) {
    return (
      <PageLayout>
        <div className="py-32 px-6">
          <div className="max-w-xl mx-auto text-center">
            <div className="w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center bg-success/10 border border-success/20">
              <CheckCircleIcon className="w-10 h-10 text-success" />
            </div>
            <h1 className="text-display-xs md:text-display-sm text-foreground mb-4">Message sent!</h1>
            <p className="text-body text-muted-foreground mb-8">
              Thank you for reaching out. We&apos;ll get back to you as soon as possible.
            </p>
            <button
              onClick={() => setSubmitted(false)}
              className="bg-stratum-500 text-primary-foreground font-semibold rounded-full px-7 py-3.5 hover:brightness-110 hover:shadow-glow transition-all"
            >
              Send Another Message
            </button>
          </div>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <SEO {...pageSEO.contact} url="https://stratum-ai.com/contact" />

      <MktHero
        badge="Contact Us"
        badgeIcon={ChatBubbleLeftRightIcon}
        title="Get in"
        highlight="touch"
        subtitle="Have questions? We'd love to hear from you. Send us a message and we'll respond as soon as possible."
      />

      {/* Contact Info + Form */}
      <section className="pb-24 lg:pb-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Contact Info */}
            <div className="space-y-6">
              <MktCard className="p-6">
                <EnvelopeIcon className="w-8 h-8 mb-4 text-secondary" />
                <h3 className="text-h3 text-foreground font-semibold mb-2">Email Us</h3>
                <p className="text-body text-muted-foreground">
                  <a href="mailto:hello@stratum.ai" className="hover:text-foreground transition-colors">
                    hello@stratum.ai
                  </a>
                </p>
                <p className="text-meta uppercase text-muted-foreground mt-2">For sales inquiries</p>
                <p className="text-body text-muted-foreground">
                  <a href="mailto:sales@stratum.ai" className="hover:text-foreground transition-colors">
                    sales@stratum.ai
                  </a>
                </p>
              </MktCard>

              <MktCard className="p-6">
                <MapPinIcon className="w-8 h-8 mb-4 text-secondary" />
                <h3 className="text-h3 text-foreground font-semibold mb-2">Headquarters</h3>
                <p className="text-body text-muted-foreground">
                  548 Market Street
                  <br />
                  Suite 35000
                  <br />
                  San Francisco, CA 94104
                </p>
              </MktCard>

              <MktCard className="p-6">
                <ChatBubbleLeftRightIcon className="w-8 h-8 mb-4 text-secondary" />
                <h3 className="text-h3 text-foreground font-semibold mb-2">Support</h3>
                <p className="text-body text-muted-foreground">
                  For existing customers, visit our{' '}
                  <a href="/help" className="text-secondary hover:underline">
                    Help Center
                  </a>{' '}
                  or email{' '}
                  <a href="mailto:support@stratum.ai" className="text-secondary hover:underline">
                    support@stratum.ai
                  </a>
                </p>
              </MktCard>
            </div>

            {/* Contact Form */}
            <div className="lg:col-span-2">
              <MktCard className="p-8">
                <form onSubmit={handleSubmit}>
                  <h2 className="text-h1 text-foreground font-semibold mb-6">Send us a Message</h2>

                  {error && (
                    <div className="flex items-center gap-3 p-4 rounded-xl mb-6 bg-destructive/10 border border-destructive/30">
                      <ExclamationCircleIcon className="w-5 h-5 text-destructive flex-shrink-0" />
                      <p className="text-body text-destructive">{error}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div>
                      <label className="text-meta uppercase text-muted-foreground mb-2 block">Name</label>
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        className={inputClass}
                        placeholder="Your name"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-meta uppercase text-muted-foreground mb-2 block">Email</label>
                      <input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className={inputClass}
                        placeholder="your@email.com"
                        required
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div>
                      <label className="text-meta uppercase text-muted-foreground mb-2 block">Company</label>
                      <input
                        type="text"
                        value={formData.company}
                        onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                        className={inputClass}
                        placeholder="Your company"
                      />
                    </div>
                    <div>
                      <label className="text-meta uppercase text-muted-foreground mb-2 block">Subject</label>
                      <select
                        value={formData.subject}
                        onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                        className={inputClass}
                        required
                      >
                        <option value="">Select a topic</option>
                        <option value="sales">Sales Inquiry</option>
                        <option value="support">Support</option>
                        <option value="partnership">Partnership</option>
                        <option value="press">Press</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                  </div>
                  <div className="mb-6">
                    <label className="text-meta uppercase text-muted-foreground mb-2 block">Message</label>
                    <textarea
                      value={formData.message}
                      onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                      className={`${inputClass} min-h-[9.375rem]`}
                      placeholder="How can we help you?"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={submitContact.isPending}
                    className="w-full bg-stratum-500 text-primary-foreground font-semibold rounded-full px-7 py-3.5 hover:brightness-110 hover:shadow-glow transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitContact.isPending ? 'Sending...' : 'Send Message'}
                  </button>
                </form>
              </MktCard>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
