/**
 * Careers Page
 * Job listings and company culture
 */

import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import { BriefcaseIcon, CurrencyDollarIcon, MapPinIcon } from '@heroicons/react/24/outline';

const jobs = [
  {
    title: 'Senior Backend Engineer',
    department: 'Engineering',
    location: 'Remote (US/EU)',
    type: 'Full-time',
    salary: '$180K - $220K',
  },
  {
    title: 'Senior Frontend Engineer',
    department: 'Engineering',
    location: 'Remote (US/EU)',
    type: 'Full-time',
    salary: '$170K - $210K',
  },
  {
    title: 'ML Engineer',
    department: 'Engineering',
    location: 'Remote (US/EU)',
    type: 'Full-time',
    salary: '$190K - $240K',
  },
  {
    title: 'Product Manager',
    department: 'Product',
    location: 'San Francisco, CA',
    type: 'Full-time',
    salary: '$160K - $200K',
  },
  {
    title: 'Account Executive',
    department: 'Sales',
    location: 'New York, NY',
    type: 'Full-time',
    salary: '$120K - $150K + Commission',
  },
  {
    title: 'Customer Success Manager',
    department: 'Customer Success',
    location: 'Remote (US)',
    type: 'Full-time',
    salary: '$100K - $130K',
  },
];

const benefits = [
  'Competitive salary + equity',
  'Unlimited PTO',
  'Remote-first culture',
  'Health, dental & vision',
  '401(k) matching',
  'Learning & development budget',
  'Home office stipend',
  'Annual team retreats',
];

export default function Careers() {
  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm mb-6"
            style={{
              background: 'rgba(34, 197, 94, 0.1)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
              color: '#22c55e',
            }}
          >
            <BriefcaseIcon className="w-4 h-4" />
            We&apos;re Hiring
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Build the Future</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              With Us
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            Join a team of passionate builders creating the next generation of revenue intelligence.
          </p>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-12 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-white text-center mb-8">Why Stratum AI?</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {benefits.map((benefit) => (
              <div
                key={benefit}
                className="p-4 rounded-xl text-center"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <span className="text-sm text-white">{benefit}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Open Positions */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-white text-center mb-12">Open Positions</h2>
          <div className="space-y-4">
            {jobs.map((job) => (
              <div
                key={job.title}
                className="p-6 rounded-2xl transition-all hover:scale-[1.01] cursor-pointer"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div>
                    <h3 className="text-lg font-semibold text-white">{job.title}</h3>
                    <div className="flex flex-wrap items-center gap-4 mt-2">
                      <span
                        className="text-sm px-2 py-1 rounded"
                        style={{
                          background: 'rgba(168, 85, 247, 0.1)',
                          color: '#a855f7',
                        }}
                      >
                        {job.department}
                      </span>
                      <span
                        className="flex items-center gap-1 text-sm"
                        style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                      >
                        <MapPinIcon className="w-4 h-4" />
                        {job.location}
                      </span>
                      <span
                        className="flex items-center gap-1 text-sm"
                        style={{ color: 'rgba(255, 255, 255, 0.5)' }}
                      >
                        <CurrencyDollarIcon className="w-4 h-4" />
                        {job.salary}
                      </span>
                    </div>
                  </div>
                  <button
                    className="px-6 py-2 rounded-lg text-sm font-medium transition-all hover:bg-white/10"
                    style={{
                      background: 'rgba(255, 255, 255, 0.06)',
                      border: '1px solid rgba(255, 255, 255, 0.12)',
                      color: '#ffffff',
                    }}
                  >
                    Apply Now
                  </button>
                </div>
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
                'linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">Don&apos;t See Your Role?</h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              We&apos;re always looking for talented people. Send us your resume and we&apos;ll
              reach out when a matching role opens up.
            </p>
            <Link
              to="/contact"
              className="inline-flex px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:opacity-90"
              style={{
                background: '#f97316',
                boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
              }}
            >
              Get in Touch
            </Link>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
