/**
 * Case Studies Page
 * StratumAI Dark Enterprise Theme
 */

import { Link } from 'react-router-dom';
import { usePageContent, type CaseStudiesPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  AcademicCapIcon,
  ArrowRightIcon,
  BuildingOffice2Icon,
  BuildingStorefrontIcon,
  GlobeAltIcon,
  HeartIcon,
  ShoppingBagIcon,
  TrophyIcon,
} from '@heroicons/react/24/outline';

const fallbackCaseStudies = [
  {
    id: 'luxe-ecommerce',
    company: 'Luxe Commerce',
    industry: 'E-Commerce',
    icon: ShoppingBagIcon,
    logo: 'L',
    color: '#FFB347',
    headline: '340% increase in ROAS with Trust-Gated Automation',
    description:
      'How a luxury fashion retailer transformed their ad performance by only executing when signal health was optimal.',
    metrics: [
      { label: 'ROAS Increase', value: '340%' },
      { label: 'CAC Reduction', value: '45%' },
      { label: 'Time Saved', value: '20hrs/week' },
    ],
    quote:
      'Stratum AI changed how we think about automation. The trust gates give us confidence to scale aggressively.',
    author: 'Sarah Chen',
    role: 'VP of Growth',
  },
  {
    id: 'fintech-global',
    company: 'FinServe Global',
    industry: 'Financial Services',
    icon: BuildingOffice2Icon,
    logo: 'F',
    color: '#00D4FF',
    headline: '67% reduction in wasted ad spend',
    description:
      'A fintech unicorn used signal health monitoring to pause campaigns before they burned budget.',
    metrics: [
      { label: 'Spend Saved', value: '$2.3M' },
      { label: 'Lead Quality', value: '+89%' },
      { label: 'Compliance Score', value: '100%' },
    ],
    quote:
      'The visibility into signal health helped us maintain compliance while scaling our acquisition campaigns.',
    author: 'Marcus Webb',
    role: 'Director of Performance Marketing',
  },
  {
    id: 'health-direct',
    company: 'HealthDirect',
    industry: 'Healthcare',
    icon: HeartIcon,
    logo: 'H',
    color: '#00D4AA',
    headline: 'Unified 2M+ patient profiles across channels',
    description:
      'How a healthcare network used CDP to create personalized patient journeys while maintaining HIPAA compliance.',
    metrics: [
      { label: 'Profiles Unified', value: '2.3M' },
      { label: 'Engagement Rate', value: '+156%' },
      { label: 'Match Rate', value: '94%' },
    ],
    quote:
      'The identity resolution capabilities let us personalize without compromising patient privacy.',
    author: 'Dr. Lisa Park',
    role: 'Chief Digital Officer',
  },
  {
    id: 'edutech-academy',
    company: 'LearnPath Academy',
    industry: 'Education',
    icon: AcademicCapIcon,
    logo: 'L',
    color: '#FFB800',
    headline: '5x improvement in student acquisition efficiency',
    description:
      'An online education platform used predictive churn analysis to optimize their enrollment funnels.',
    metrics: [
      { label: 'Enrollment Rate', value: '+212%' },
      { label: 'Churn Reduction', value: '38%' },
      { label: 'LTV Increase', value: '+67%' },
    ],
    quote:
      'Predictive churn scoring helped us intervene early and keep students engaged throughout their journey.',
    author: 'James Liu',
    role: 'Head of Growth',
  },
  {
    id: 'retail-chain',
    company: 'Metro Retail Group',
    industry: 'Retail',
    icon: BuildingStorefrontIcon,
    logo: 'M',
    color: '#FF6B6B',
    headline: 'Synced 500K customer segments to 4 ad platforms',
    description:
      'A national retail chain used Audience Sync to maintain consistent targeting across all digital channels.',
    metrics: [
      { label: 'Segments Synced', value: '127' },
      { label: 'Audience Size', value: '500K+' },
      { label: 'Attribution Accuracy', value: '+73%' },
    ],
    quote:
      'One-click audience sync eliminated hours of manual work and kept our targeting fresh across platforms.',
    author: 'Amanda Torres',
    role: 'CMO',
  },
  {
    id: 'saas-enterprise',
    company: 'CloudStack Pro',
    industry: 'B2B SaaS',
    icon: GlobeAltIcon,
    logo: 'C',
    color: '#A78BFA',
    headline: 'Reduced sales cycle by 40% with predictive scoring',
    description:
      'An enterprise SaaS company used ML-powered lead scoring to prioritize high-intent accounts.',
    metrics: [
      { label: 'Sales Cycle', value: '-40%' },
      { label: 'Win Rate', value: '+52%' },
      { label: 'Pipeline Value', value: '+$4.2M' },
    ],
    quote:
      'The predictive models surfaced accounts we would have missed. It changed how our sales team prioritizes.',
    author: 'Robert Chang',
    role: 'VP of Revenue',
  },
];

const fallbackStats = [
  { value: '$50M+', label: 'Ad Spend Optimized' },
  { value: '340%', label: 'Avg. ROAS Improvement' },
  { value: '10M+', label: 'Profiles Unified' },
  { value: '500+', label: 'Companies Trust Us' },
];

export default function CaseStudiesPage() {
  const { content } = usePageContent<CaseStudiesPageContent>('case-studies');

  // Use CMS data if available, otherwise fallback
  const caseStudies = content?.studies?.length
    ? content.studies.map((s, i) => ({
        id: `study-${i}`,
        company: s.company,
        industry: s.industry,
        icon: ShoppingBagIcon,
        logo: s.logo,
        color: '#FFB347',
        headline: s.challenge,
        description: s.solution,
        metrics: s.results.map((r) => ({ label: r.metric, value: r.value })),
        quote: s.quote || '',
        author: s.quotee || '',
        role: '',
      }))
    : fallbackCaseStudies;

  const stats = content?.stats?.length ? content.stats : fallbackStats;

  return (
    <PageLayout>
      <div className="min-h-screen">
        {/* Hero Section */}
        <section className="relative py-20 overflow-hidden">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto">
              <div
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-6"
                style={{
                  background: 'rgba(0, 212, 255, 0.1)',
                  border: '1px solid rgba(0, 212, 255, 0.2)',
                }}
              >
                <TrophyIcon className="w-4 h-4 text-[#00D4FF]" />
                <span className="text-sm font-medium text-[#00D4FF]">Case Studies</span>
              </div>

              <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
                Success Stories from{' '}
                <span
                  style={{ color: '#FF4D4D' }}
                >
                  Industry Leaders
                </span>
              </h1>

              <p className="text-lg" style={{ color: '#8B8D9E' }}>
                Discover how companies across industries use Stratum AI to transform their marketing
                performance with trust-gated automation.
              </p>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mt-16">
              {stats.map((stat) => (
                <div key={stat.label} className="text-center">
                  <div
                    className="text-3xl md:text-4xl font-bold mb-2"
                    style={{ color: '#FF4D4D' }}
                  >
                    {stat.value}
                  </div>
                  <div className="text-sm" style={{ color: '#8B8D9E' }}>{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Case Studies Grid */}
        <section className="py-16">
          <div className="max-w-7xl mx-auto px-6 lg:px-8">
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {caseStudies.map((study) => (
                <Link key={study.id} to={`/case-studies/${study.id}`} className="group block">
                  <div
                    className="h-full p-6 rounded-2xl transition-all duration-300 hover:-translate-y-2"
                    style={{
                      background: '#12131F',
                      border: '1px solid #1E1F30',
                    }}
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold"
                          style={{
                            background: `linear-gradient(135deg, ${study.color} 0%, ${study.color}80 100%)`,
                          }}
                        >
                          {study.logo}
                        </div>
                        <div>
                          <h3 className="font-semibold text-white">{study.company}</h3>
                          <span className="text-xs" style={{ color: 'rgba(139,141,158,0.7)' }}>{study.industry}</span>
                        </div>
                      </div>
                      <study.icon className="w-5 h-5" style={{ color: 'rgba(139,141,158,0.5)' }} />
                    </div>

                    {/* Headline */}
                    <h4 className="text-lg font-semibold text-white mb-3 group-hover:text-[#FF4D4D] transition-colors">
                      {study.headline}
                    </h4>

                    <p className="text-sm mb-4" style={{ color: '#8B8D9E' }}>{study.description}</p>

                    {/* Metrics */}
                    <div className="grid grid-cols-3 gap-2 mb-4">
                      {study.metrics.map((metric) => (
                        <div
                          key={metric.label}
                          className="p-2 rounded-lg text-center"
                          style={{ background: '#12131F', border: '1px solid #1E1F30' }}
                        >
                          <div className="text-lg font-bold" style={{ color: study.color }}>
                            {metric.value}
                          </div>
                          <div className="text-[10px]" style={{ color: 'rgba(139,141,158,0.7)' }}>{metric.label}</div>
                        </div>
                      ))}
                    </div>

                    {/* Quote */}
                    <div
                      className="p-3 rounded-lg mb-4"
                      style={{
                        background: `${study.color}08`,
                        borderLeft: `2px solid ${study.color}`,
                      }}
                    >
                      <p className="text-sm italic" style={{ color: '#8B8D9E' }}>"{study.quote}"</p>
                      <p className="text-xs mt-2" style={{ color: 'rgba(139,141,158,0.7)' }}>
                        {study.author}, {study.role}
                      </p>
                    </div>

                    {/* Read more */}
                    <div className="flex items-center gap-2 text-sm font-medium text-[#FFB347] group-hover:gap-3 transition-all">
                      <span>Read Full Story</span>
                      <ArrowRightIcon className="w-4 h-4" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-16">
          <div className="max-w-4xl mx-auto px-6 lg:px-8">
            <div
              className="rounded-2xl p-8 md:p-12 text-center"
              style={{
                background: '#12131F',
                border: '1px solid #1E1F30',
              }}
            >
              <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
                Ready to write your success story?
              </h2>
              <p className="mb-8" style={{ color: '#8B8D9E' }}>
                Join hundreds of companies using Stratum AI to transform their marketing
                performance.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  to="/signup"
                  className="px-8 py-4 rounded-full font-semibold text-white transition-all duration-200"
                  style={{
                    background: '#FF4D4D',
                    boxShadow: '0 4px 20px rgba(255,77,77,0.3)',
                  }}
                >
                  Start Free Trial
                </Link>
                <Link
                  to="/contact"
                  className="px-8 py-4 rounded-xl font-semibold text-white transition-all duration-200"
                  style={{
                    background: 'rgba(255, 255, 255, 0.06)',
                    border: '1px solid #1E1F30',
                  }}
                >
                  Talk to Sales
                </Link>
              </div>
            </div>
          </div>
        </section>
      </div>
    </PageLayout>
  );
}
