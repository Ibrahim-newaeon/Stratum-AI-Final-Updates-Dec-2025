/**
 * About Page
 * Company information and mission
 */

import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import { SparklesIcon } from '@heroicons/react/24/outline';

const team = [
  { name: 'Sarah Chen', role: 'CEO & Co-Founder', image: 'SC' },
  { name: 'Marcus Rodriguez', role: 'CTO & Co-Founder', image: 'MR' },
  { name: 'Emily Watson', role: 'VP of Product', image: 'EW' },
  { name: 'David Kim', role: 'VP of Engineering', image: 'DK' },
  { name: 'Lisa Thompson', role: 'VP of Sales', image: 'LT' },
  { name: 'James Park', role: 'VP of Customer Success', image: 'JP' },
];

const values = [
  {
    title: 'Trust First',
    description: 'We build systems that earn and maintain trust through transparency and reliability.',
  },
  {
    title: 'Customer Obsessed',
    description: 'Every decision starts with how it impacts our customers success.',
  },
  {
    title: 'Data Driven',
    description: 'We practice what we preach - decisions backed by evidence, not assumptions.',
  },
  {
    title: 'Move Fast, Stay Safe',
    description: 'Speed matters, but not at the cost of quality or security.',
  },
];

export default function About() {
  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(168, 85, 247, 0.1)',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              color: '#a855f7',
            }}
          >
            <SparklesIcon className="w-4 h-4" />
            About Us
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Building the Future of</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Revenue Operations
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-3xl mx-auto"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            We&apos;re on a mission to help growth teams make smarter decisions with AI-powered
            intelligence and trust-gated automation.
          </p>
        </div>
      </section>

      {/* Story Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <div
            className="p-8 md:p-12 rounded-3xl"
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-6">Our Story</h2>
            <div className="space-y-4" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              <p>
                Stratum AI was founded in 2024 by a team of marketing technologists who experienced
                firsthand the chaos of managing campaigns across multiple platforms with unreliable
                data.
              </p>
              <p>
                We watched companies waste millions on automated optimizations that were based on
                corrupted signals, delayed conversions, and incomplete attribution. The more
                automated the system, the bigger the potential for disaster.
              </p>
              <p>
                That&apos;s why we built Stratum AI - a revenue operating system with trust at its
                core. Our Trust-Gated Autopilot ensures that automations only execute when your data
                is healthy, preventing costly mistakes while still enabling the speed and scale that
                modern growth teams need.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: '150+', label: 'Growth Teams' },
              { value: '$2B+', label: 'Ad Spend Managed' },
              { value: '50+', label: 'Integrations' },
              { value: '99.9%', label: 'Uptime' },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-4xl font-bold" style={{ color: '#f97316' }}>
                  {stat.value}
                </div>
                <div className="text-sm mt-2" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-12">Our Values</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {values.map((value) => (
              <div
                key={value.title}
                className="p-6 rounded-2xl"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <h3 className="text-xl font-semibold text-white mb-2">{value.title}</h3>
                <p style={{ color: 'rgba(255, 255, 255, 0.6)' }}>{value.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-12">Leadership Team</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
            {team.map((member) => (
              <div key={member.name} className="text-center">
                <div
                  className="w-20 h-20 rounded-2xl flex items-center justify-center text-2xl font-bold mx-auto mb-3"
                  style={{
                    background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 100%)',
                    color: '#ffffff',
                  }}
                >
                  {member.image}
                </div>
                <h3 className="font-semibold text-white">{member.name}</h3>
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                  {member.role}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div
            className="p-12 rounded-3xl"
            style={{
              background:
                'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">Join Our Mission</h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              We&apos;re always looking for talented people to join our team.
            </p>
            <Link
              to="/careers"
              className="inline-flex px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:opacity-90"
              style={{
                background: '#f97316',
                boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
              }}
            >
              View Open Positions
            </Link>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
