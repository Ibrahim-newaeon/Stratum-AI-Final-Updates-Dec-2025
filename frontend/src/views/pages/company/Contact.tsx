/**
 * Contact Page
 * Contact form and information - submits to CMS API
 */

import { useState } from 'react';
import { PageLayout } from '@/components/landing/PageLayout';
import { pageSEO, SEO } from '@/components/common/SEO';
import {
  ChatBubbleLeftRightIcon,
  CheckCircleIcon,
  EnvelopeIcon,
  ExclamationCircleIcon,
  MapPinIcon,
} from '@heroicons/react/24/outline';
import { useSubmitContact } from '@/api/cms';

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
            <div
              className="w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center"
              style={{ background: 'rgba(52, 199, 89, 0.1)' }}
            >
              <CheckCircleIcon className="w-10 h-10 text-green-500" />
            </div>
            <h1 className="text-3xl font-bold text-white mb-4">Message Sent!</h1>
            <p className="text-lg mb-8" style={{ color: 'var(--landing-text)' }}>
              Thank you for reaching out. We'll get back to you as soon as possible.
            </p>
            <button
              onClick={() => setSubmitted(false)}
              className="px-6 py-3 rounded-full font-semibold text-white transition-opacity hover:opacity-90"
              style={{
                background: 'var(--landing-accent-coral)',
                boxShadow: '0 4px 20px rgba(255, 77, 77, 0.3)',
              }}
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
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(255, 179, 71, 0.1)',
              border: '1px solid rgba(255, 179, 71, 0.3)',
              color: '#FF8A4A',
            }}
          >
            <ChatBubbleLeftRightIcon className="w-4 h-4" />
            Contact Us
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "Geist, system-ui, sans-serif" }}
          >
            <span className="text-white">Get in</span>
            <br />
            <span
              style={{ color: 'var(--landing-accent-coral)' }}
            >
              Touch
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto"
            style={{ color: 'var(--landing-text)' }}
          >
            Have questions? We&apos;d love to hear from you. Send us a message and we&apos;ll
            respond as soon as possible.
          </p>
        </div>
      </section>

      {/* Contact Info + Form */}
      <section className="py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            {/* Contact Info */}
            <div className="space-y-6">
              <div
                className="p-6 rounded-2xl"
                style={{
                  background: 'var(--landing-card)',
                  border: '1px solid var(--landing-border)',
                }}
              >
                <EnvelopeIcon className="w-8 h-8 mb-4" style={{ color: 'var(--landing-accent-coral)' }} />
                <h3 className="text-lg font-semibold text-white mb-2">Email Us</h3>
                <p style={{ color: 'var(--landing-text)' }}>
                  <a href="mailto:hello@stratum.ai" className="hover:text-white transition-colors">
                    hello@stratum.ai
                  </a>
                </p>
                <p className="text-sm mt-2" style={{ color: 'var(--landing-text-dim)' }}>
                  For sales inquiries
                </p>
                <p style={{ color: 'var(--landing-text)' }}>
                  <a href="mailto:sales@stratum.ai" className="hover:text-white transition-colors">
                    sales@stratum.ai
                  </a>
                </p>
              </div>

              <div
                className="p-6 rounded-2xl"
                style={{
                  background: 'var(--landing-card)',
                  border: '1px solid var(--landing-border)',
                }}
              >
                <MapPinIcon className="w-8 h-8 mb-4" style={{ color: 'var(--landing-accent-warm)' }} />
                <h3 className="text-lg font-semibold text-white mb-2">Headquarters</h3>
                <p style={{ color: 'var(--landing-text)' }}>
                  548 Market Street
                  <br />
                  Suite 35000
                  <br />
                  San Francisco, CA 94104
                </p>
              </div>

              <div
                className="p-6 rounded-2xl"
                style={{
                  background: 'var(--landing-card)',
                  border: '1px solid var(--landing-border)',
                }}
              >
                <ChatBubbleLeftRightIcon className="w-8 h-8 mb-4" style={{ color: 'var(--landing-accent-warm)' }} />
                <h3 className="text-lg font-semibold text-white mb-2">Support</h3>
                <p style={{ color: 'var(--landing-text)' }}>
                  For existing customers, visit our{' '}
                  <a href="/help" className="text-[var(--landing-accent-coral)] hover:underline">
                    Help Center
                  </a>{' '}
                  or email{' '}
                  <a href="mailto:support@stratum.ai" className="text-[var(--landing-accent-coral)] hover:underline">
                    support@stratum.ai
                  </a>
                </p>
              </div>
            </div>

            {/* Contact Form */}
            <div className="lg:col-span-2">
              <form
                onSubmit={handleSubmit}
                className="p-8 rounded-3xl"
                style={{
                  background: 'var(--landing-card)',
                  border: '1px solid var(--landing-border)',
                }}
              >
                <h2 className="text-2xl font-bold text-white mb-6">Send us a Message</h2>

                {error && (
                  <div
                    className="flex items-center gap-3 p-4 rounded-xl mb-6"
                    style={{
                      background: 'rgba(239, 68, 68, 0.1)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                    }}
                  >
                    <ExclamationCircleIcon className="w-5 h-5 text-red-500" />
                    <p className="text-red-400">{error}</p>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-[width] focus:ring-2"
                      style={{
                        background: 'var(--landing-surface-glass)',
                        border: '1px solid var(--landing-border-glass)',
                      }}
                      placeholder="Your name"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">Email</label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-[width] focus:ring-2"
                      style={{
                        background: 'var(--landing-surface-glass)',
                        border: '1px solid var(--landing-border-glass)',
                      }}
                      placeholder="your@email.com"
                      required
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">Company</label>
                    <input
                      type="text"
                      value={formData.company}
                      onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-[width] focus:ring-2"
                      style={{
                        background: 'var(--landing-surface-glass)',
                        border: '1px solid var(--landing-border-glass)',
                      }}
                      placeholder="Your company"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">Subject</label>
                    <select
                      value={formData.subject}
                      onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl text-white outline-none transition-[width] focus:ring-2"
                      style={{
                        background: 'var(--landing-surface-glass)',
                        border: '1px solid var(--landing-border-glass)',
                      }}
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
                  <label className="block text-sm font-medium text-white mb-2">Message</label>
                  <textarea
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    className="w-full px-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-[width] focus:ring-2 min-h-[9.375rem]"
                    style={{
                      background: 'var(--landing-surface-glass)',
                      border: '1px solid var(--landing-border-glass)',
                    }}
                    placeholder="How can we help you?"
                    required
                  />
                </div>
                <button
                  type="submit"
                  disabled={submitContact.isPending}
                  className="w-full py-4 rounded-full font-semibold text-white transition-[width] hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{
                    background: 'var(--landing-accent-coral)',
                    boxShadow: '0 4px 20px rgba(255, 77, 77, 0.3)',
                  }}
                >
                  {submitContact.isPending ? 'Sending...' : 'Send Message'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
