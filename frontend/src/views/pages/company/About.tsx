/**
 * About Page — landing-themed (ink + ember).
 * Company information and mission.
 */

import { usePageContent, type AboutPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import {
  MktHero,
  MktSectionHeader,
  MktCard,
  MktFeatureCard,
  MktStat,
} from '@/components/landing/marketing';
import { pageSEO, SEO } from '@/components/common/SEO';
import {
  BoltIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  SparklesIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';

const valueIcons = [ShieldCheckIcon, UserGroupIcon, ChartBarIcon, BoltIcon];

const fallbackTeam = [
  { name: 'Sarah Chen', role: 'CEO & Co-Founder', image: 'SC' },
  { name: 'Marcus Rodriguez', role: 'CTO & Co-Founder', image: 'MR' },
  { name: 'Emily Watson', role: 'VP of Product', image: 'EW' },
  { name: 'David Kim', role: 'VP of Engineering', image: 'DK' },
  { name: 'Lisa Thompson', role: 'VP of Sales', image: 'LT' },
  { name: 'James Park', role: 'VP of Customer Success', image: 'JP' },
];

const fallbackValues = [
  {
    title: 'Trust First',
    description:
      'We build systems that earn and maintain trust through transparency and reliability.',
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

const fallbackStats = [
  { value: '150+', label: 'Growth Teams' },
  { value: '$2B+', label: 'Ad Spend Managed' },
  { value: '50+', label: 'Integrations' },
  { value: '99.9%', label: 'Uptime' },
];

export default function About() {
  const { content } = usePageContent<AboutPageContent>('about');

  // Use CMS data if available, otherwise fallback
  const team = content?.team?.length ? content.team : fallbackTeam;
  const values = content?.values?.length ? content.values : fallbackValues;
  const stats = content?.stats?.length ? content.stats : fallbackStats;

  return (
    <PageLayout>
      <SEO {...pageSEO.about} url="https://stratum-ai.com/about" />

      <MktHero
        badge="About Us"
        badgeIcon={SparklesIcon}
        title="Building the future of"
        highlight="revenue operations"
        subtitle="We're on a mission to help growth teams make smarter decisions with AI-powered intelligence and trust-gated automation."
      >
        <div className="mt-16 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, i) => (
            <MktStat key={stat.label} value={stat.value} label={stat.label} delay={i * 0.05} />
          ))}
        </div>
      </MktHero>

      {/* Story */}
      <section className="pb-12">
        <div className="max-w-3xl mx-auto px-6 lg:px-8">
          <MktCard className="p-8 md:p-12">
            <h2 className="text-h1 text-foreground font-semibold mb-6">Our Story</h2>
            <div className="space-y-4 text-body text-muted-foreground leading-relaxed">
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
          </MktCard>
        </div>
      </section>

      {/* Values */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="What drives us" title="Our" highlight="values" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {values.map((value, i) => (
              <MktFeatureCard
                key={value.title}
                icon={valueIcons[i % valueIcons.length]}
                title={value.title}
                description={value.description}
                delay={(i % 2) * 0.05}
              />
            ))}
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="py-24 lg:py-28">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <MktSectionHeader eyebrow="The people" title="Leadership" highlight="team" />
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
            {team.map((member, i) => (
              <MktCard key={member.name} className="p-6 text-center" delay={(i % 6) * 0.05}>
                <div className="w-20 h-20 rounded-2xl bg-secondary/10 border border-secondary/20 flex items-center justify-center text-display-xs font-semibold text-secondary mx-auto mb-4">
                  {member.image}
                </div>
                <h3 className="text-h3 text-foreground font-semibold">{member.name}</h3>
                <p className="mt-1 text-meta uppercase text-muted-foreground">{member.role}</p>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
