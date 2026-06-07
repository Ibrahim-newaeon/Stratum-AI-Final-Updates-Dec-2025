/**
 * Careers Page — landing-themed (ink + ember).
 * Job listings and company culture.
 */

import { Link } from 'react-router-dom';
import { usePageContent, type CareersPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { MktHero, MktSectionHeader, MktCard, MktFeatureCard } from '@/components/landing/marketing';
import { SEO } from '@/components/common/SEO';
import {
  BriefcaseIcon,
  CurrencyDollarIcon,
  MapPinIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';

const fallbackPositions = [
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

const fallbackBenefits = [
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
  const { content } = usePageContent<CareersPageContent>('careers');

  // Use CMS data if available, otherwise fallback
  const jobs = content?.positions?.length
    ? content.positions.map((p) => ({
        title: p.title,
        department: p.department,
        location: p.location,
        type: p.type,
        salary: p.salary,
      }))
    : fallbackPositions;

  const benefits = content?.benefits?.length
    ? content.benefits.map((b) => b.title)
    : fallbackBenefits;

  return (
    <PageLayout>
      <SEO title="Careers" description="Join the Stratum AI team. Help build the future of trust-gated marketing automation." url="https://stratum-ai.com/careers" />

      <MktHero
        badge="We're Hiring"
        badgeIcon={BriefcaseIcon}
        title="Build the future"
        highlight="with us"
        subtitle="Join a team of passionate builders creating the next generation of revenue intelligence."
      />

      {/* Benefits */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="Perks" title="Why" highlight="Stratum AI?" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {benefits.map((benefit, i) => (
              <MktFeatureCard
                key={benefit}
                icon={SparklesIcon}
                title={benefit}
                description=""
                delay={(i % 4) * 0.05}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Open Positions */}
      <section className="py-24 lg:py-28">
        <div className="max-w-3xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="Careers" title="Open" highlight="positions" />
          <div className="space-y-4">
            {jobs.map((job, i) => (
              <MktCard key={job.title} delay={i * 0.05} className="p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div>
                    <h3 className="text-h3 text-foreground font-semibold">{job.title}</h3>
                    <div className="flex flex-wrap items-center gap-4 mt-3">
                      <span className="text-meta uppercase text-secondary px-2 py-1 rounded-full bg-secondary/10 border border-secondary/20">
                        {job.department}
                      </span>
                      <span className="flex items-center gap-1 text-meta uppercase text-muted-foreground">
                        <MapPinIcon className="w-4 h-4" />
                        {job.location}
                      </span>
                      <span className="flex items-center gap-1 text-meta uppercase text-muted-foreground">
                        <CurrencyDollarIcon className="w-4 h-4" />
                        {job.salary}
                      </span>
                    </div>
                  </div>
                  <Link
                    to="/contact"
                    className="inline-flex items-center justify-center px-6 py-2.5 rounded-full text-body font-semibold bg-card border border-border text-foreground hover:bg-foreground/5 transition-colors duration-200 flex-shrink-0"
                  >
                    Apply Now
                  </Link>
                </div>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
