/**
 * Changelog / Release Notes Page — landing-themed (ink + ember).
 */

import { usePageContent, type ChangelogPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { MktHero, MktCard } from '@/components/landing/marketing';
import {
  BugAntIcon,
  RocketLaunchIcon,
  ShieldCheckIcon,
  SparklesIcon,
  WrenchScrewdriverIcon,
} from '@heroicons/react/24/outline';

const fallbackReleases = [
  {
    version: '3.2.0',
    date: 'January 15, 2026',
    type: 'major',
    highlights: [
      'New 2026 Dashboard Theme with OLED-optimized dark mode',
      'Enhanced Trust Engine with predictive signal analysis',
      'Multi-platform Audience Sync now supports 4 ad platforms',
    ],
    changes: [
      { type: 'feature', text: 'Added electric neon color palette for 2026 theme' },
      { type: 'feature', text: 'New glassmorphism effects with enhanced blur' },
      { type: 'feature', text: 'Animation harmony system with 3 timing layers' },
      { type: 'improvement', text: 'Improved CDP profile loading performance by 40%' },
      { type: 'improvement', text: 'Enhanced Trust Gate evaluation speed' },
      { type: 'fix', text: 'Fixed segment preview count accuracy' },
      { type: 'fix', text: 'Resolved timezone issues in event tracking' },
    ],
  },
  {
    version: '3.1.0',
    date: 'December 20, 2025',
    type: 'minor',
    highlights: [
      'Predictive Churn Analysis in CDP',
      'Computed Traits for advanced segmentation',
      'RFM Analysis dashboard',
    ],
    changes: [
      { type: 'feature', text: 'Predictive churn scoring with ML models' },
      { type: 'feature', text: 'Custom computed traits with formula builder' },
      { type: 'feature', text: 'RFM (Recency, Frequency, Monetary) analysis' },
      { type: 'feature', text: 'Funnel analysis with conversion tracking' },
      { type: 'improvement', text: 'Segment builder now supports nested conditions' },
      { type: 'fix', text: 'Fixed identity merge conflicts' },
    ],
  },
  {
    version: '3.0.0',
    date: 'November 1, 2025',
    type: 'major',
    highlights: [
      'Complete CDP (Customer Data Platform) launch',
      'Audience Sync to Meta, Google, TikTok, Snapchat',
      'Identity Graph visualization',
    ],
    changes: [
      { type: 'feature', text: 'Full CDP with unified customer profiles' },
      { type: 'feature', text: 'Real-time event ingestion and processing' },
      { type: 'feature', text: 'Cross-device identity resolution' },
      { type: 'feature', text: 'One-click audience sync to ad platforms' },
      { type: 'security', text: 'Enhanced encryption for PII data' },
      { type: 'improvement', text: 'New onboarding flow for faster setup' },
    ],
  },
  {
    version: '2.5.0',
    date: 'September 15, 2025',
    type: 'minor',
    highlights: [
      'Custom Autopilot Rules builder',
      'A/B Testing framework',
      'Enhanced reporting exports',
    ],
    changes: [
      { type: 'feature', text: 'Visual rule builder for custom automations' },
      { type: 'feature', text: 'Built-in A/B testing with statistical analysis' },
      { type: 'feature', text: 'Scheduled report exports in PDF/CSV' },
      { type: 'improvement', text: 'Campaign performance insights' },
      { type: 'fix', text: 'Fixed duplicate webhook deliveries' },
    ],
  },
];

const getTypeIcon = (type: string) => {
  switch (type) {
    case 'feature':
      return <SparklesIcon className="w-4 h-4 text-secondary" />;
    case 'improvement':
      return <RocketLaunchIcon className="w-4 h-4 text-accent" />;
    case 'fix':
      return <BugAntIcon className="w-4 h-4 text-warning" />;
    case 'security':
      return <ShieldCheckIcon className="w-4 h-4 text-success" />;
    default:
      return <WrenchScrewdriverIcon className="w-4 h-4 text-muted-foreground" />;
  }
};

const getTypeLabel = (type: string) => {
  switch (type) {
    case 'feature':
      return { text: 'New', classes: 'bg-secondary/10 text-secondary border border-secondary/20' };
    case 'improvement':
      return { text: 'Improved', classes: 'bg-accent/10 text-accent border border-accent/20' };
    case 'fix':
      return { text: 'Fixed', classes: 'bg-warning/10 text-warning border border-warning/20' };
    case 'security':
      return { text: 'Security', classes: 'bg-success/10 text-success border border-success/20' };
    default:
      return {
        text: 'Changed',
        classes: 'bg-foreground/5 text-muted-foreground border border-border',
      };
  }
};

export default function ChangelogPage() {
  const { content } = usePageContent<ChangelogPageContent>('changelog');

  // Use CMS data if available, otherwise fallback
  const releases = content?.releases?.length ? content.releases : fallbackReleases;

  return (
    <PageLayout>
      <MktHero
        badge="Changelog"
        badgeIcon={SparklesIcon}
        title="What's New in"
        highlight="Stratum AI"
        subtitle="Stay up to date with the latest features, improvements, and fixes."
      />

      {/* Releases Timeline */}
      <section className="pb-12">
        <div className="max-w-4xl mx-auto px-6 lg:px-8">
          <div className="space-y-12">
            {releases.map((release, index) => (
              <div key={release.version} className="relative">
                {/* Timeline line */}
                {index < releases.length - 1 && (
                  <div className="absolute left-[15px] top-12 bottom-0 w-px bg-border" />
                )}

                {/* Version header */}
                <div className="flex items-start gap-4 mb-6">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border ${
                      release.type === 'major'
                        ? 'bg-stratum-500 border-secondary/40'
                        : 'bg-secondary/20 border-secondary/40'
                    }`}
                  >
                    <span
                      className={`text-micro font-bold ${
                        release.type === 'major' ? 'text-primary-foreground' : 'text-secondary'
                      }`}
                    >
                      {release.type === 'major' ? 'M' : 'm'}
                    </span>
                  </div>

                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-h1 text-foreground font-semibold">v{release.version}</h2>
                      {release.type === 'major' && (
                        <span className="px-2 py-0.5 rounded-full text-micro font-medium bg-secondary/10 text-secondary border border-secondary/20">
                          Major Release
                        </span>
                      )}
                    </div>
                    <p className="text-meta uppercase text-muted-foreground">{release.date}</p>
                  </div>
                </div>

                {/* Highlights */}
                {release.highlights && (
                  <MktCard className="ml-12 mb-6 p-4">
                    <h3 className="text-meta uppercase text-secondary mb-3">Highlights</h3>
                    <ul className="space-y-2">
                      {release.highlights.map((highlight, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-2 text-body text-foreground"
                        >
                          <span className="text-secondary mt-1">•</span>
                          {highlight}
                        </li>
                      ))}
                    </ul>
                  </MktCard>
                )}

                {/* Changes list */}
                <div className="ml-12 space-y-3">
                  {release.changes.map((change, i) => {
                    const label = getTypeLabel(change.type);
                    return (
                      <MktCard
                        key={i}
                        className="flex items-start gap-3 p-3 hover:bg-foreground/[0.02]"
                      >
                        {getTypeIcon(change.type)}
                        <span
                          className={`text-micro font-medium px-2 py-0.5 rounded-full ${label.classes}`}
                        >
                          {label.text}
                        </span>
                        <span className="text-body text-muted-foreground flex-1">
                          {change.text}
                        </span>
                      </MktCard>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
