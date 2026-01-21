/**
 * Contact Page
 * Contact form and information
 */

import { useState } from 'react';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  EnvelopeIcon,
  MapPinIcon,
  ChatBubbleLeftRightIcon,
} from '@heroicons/react/24/outline';

export default function Contact() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    subject: '',
    message: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle form submission
    console.log('Form submitted:', formData);
  };

  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(6, 182, 212, 0.1)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              color: '#06b6d4',
            }}
          >
            <ChatBubbleLeftRightIcon className="w-4 h-4" />
            Contact Us
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Get in</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Touch
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
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
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <EnvelopeIcon className="w-8 h-8 mb-4" style={{ color: '#f97316' }} />
                <h3 className="text-lg font-semibold text-white mb-2">Email Us</h3>
                <p style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  <a href="mailto:hello@stratum.ai" className="hover:text-white transition-colors">
                    hello@stratum.ai
                  </a>
                </p>
                <p className="text-sm mt-2" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                  For sales inquiries
                </p>
                <p style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  <a href="mailto:sales@stratum.ai" className="hover:text-white transition-colors">
                    sales@stratum.ai
                  </a>
                </p>
              </div>

              <div
                className="p-6 rounded-2xl"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <MapPinIcon className="w-8 h-8 mb-4" style={{ color: '#a855f7' }} />
                <h3 className="text-lg font-semibold text-white mb-2">Headquarters</h3>
                <p style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
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
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <ChatBubbleLeftRightIcon className="w-8 h-8 mb-4" style={{ color: '#06b6d4' }} />
                <h3 className="text-lg font-semibold text-white mb-2">Support</h3>
                <p style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  For existing customers, visit our{' '}
                  <a href="#" className="text-orange-500 hover:underline">
                    Help Center
                  </a>{' '}
                  or email{' '}
                  <a
                    href="mailto:support@stratum.ai"
                    className="text-orange-500 hover:underline"
                  >
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
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <h2 className="text-2xl font-bold text-white mb-6">Send us a Message</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">Name</label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all focus:ring-2"
                      style={{
                        background: 'rgba(255, 255, 255, 0.06)',
                        border: '1px solid rgba(255, 255, 255, 0.12)',
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
                      className="w-full px-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all focus:ring-2"
                      style={{
                        background: 'rgba(255, 255, 255, 0.06)',
                        border: '1px solid rgba(255, 255, 255, 0.12)',
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
                      className="w-full px-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all focus:ring-2"
                      style={{
                        background: 'rgba(255, 255, 255, 0.06)',
                        border: '1px solid rgba(255, 255, 255, 0.12)',
                      }}
                      placeholder="Your company"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">Subject</label>
                    <select
                      value={formData.subject}
                      onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl text-white outline-none transition-all focus:ring-2"
                      style={{
                        background: 'rgba(255, 255, 255, 0.06)',
                        border: '1px solid rgba(255, 255, 255, 0.12)',
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
                    className="w-full px-4 py-3 rounded-xl text-white placeholder-white/40 outline-none transition-all focus:ring-2 min-h-[150px]"
                    style={{
                      background: 'rgba(255, 255, 255, 0.06)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                    }}
                    placeholder="How can we help you?"
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="w-full py-4 rounded-xl font-semibold text-white transition-all hover:opacity-90"
                  style={{
                    background: '#f97316',
                    boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
                  }}
                >
                  Send Message
                </button>
              </form>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
