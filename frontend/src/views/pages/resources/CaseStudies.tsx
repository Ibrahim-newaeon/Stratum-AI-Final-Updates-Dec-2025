/**
 * Case Studies Page — landing-themed (ink + ember).
 * Success stories from industry leaders.
 */

import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { usePageContent, type CaseStudiesPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { MktHero, MktCard, MktStat } from '@/components/landing/marketing';
import {
  AcademicCapIcon,
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
      <MktHero
        badge="Case Studies"
        badgeIcon={TrophyIcon}
        title="Success stories from"
        highlight="industry leaders"
        subtitle="Discover how companies across industries use Stratum AI to transform their marketing performance with trust-gated automation."
      />

      {/* Stats */}
      <section className="pb-12">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {stats.map((stat, i) => (
              <MktStat
                key={stat.label}
                value={stat.value}
                label={stat.label}
                delay={(i % 4) * 0.05}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Case Studies Grid */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {caseStudies.map((study, i) => (
              <MktCard key={study.id} delay={(i % 3) * 0.05} className="group p-6 flex flex-col">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-secondary/10 border border-secondary/20 flex items-center justify-center">
                      <span className="text-body font-semibold text-secondary">{study.logo}</span>
                    </div>
                    <div>
                      <h3 className="text-h3 text-foreground font-semibold">{study.company}</h3>
                      <span className="text-micro uppercase text-muted-foreground">
                        {study.industry}
                      </span>
                    </div>
                  </div>
                  <study.icon className="w-5 h-5 text-muted-foreground" />
                </div>

                {/* Headline */}
                <h4 className="text-h3 text-foreground font-semibold mb-3 group-hover:text-secondary transition-colors">
                  {study.headline}
                </h4>

                <p className="text-body text-muted-foreground mb-5">{study.description}</p>

                {/* Metrics */}
                <div className="grid grid-cols-3 gap-2 mb-5">
                  {study.metrics.map((metric) => (
                    <div
                      key={metric.label}
                      className="p-2 rounded-xl bg-card border border-border text-center"
                    >
                      <div className="text-display-xs text-gradient-primary font-medium">
                        {metric.value}
                      </div>
                      <div className="mt-1 text-micro uppercase text-muted-foreground">
                        {metric.label}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Quote */}
                <div className="rounded-xl bg-secondary/5 p-4 mb-5">
                  <p className="text-body text-muted-foreground italic">"{study.quote}"</p>
                  <p className="mt-2 text-meta uppercase text-muted-foreground">
                    {study.author}
                    {study.role ? `, ${study.role}` : ''}
                  </p>
                </div>

                {/* Read more */}
                <Link
                  to={`/case-studies/${study.id}`}
                  className="mt-auto inline-flex items-center gap-2 text-body font-medium text-secondary hover:gap-3 transition-all"
                >
                  <span>Read Full Story</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
