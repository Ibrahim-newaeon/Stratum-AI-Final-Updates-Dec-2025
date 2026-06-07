/**
 * System Status Page — landing-themed (ink + ember).
 */

import { useState } from 'react';
import { usePageContent, type StatusPageContent } from '@/api/cms';
import { PageLayout } from '@/components/landing/PageLayout';
import { CTA } from '@/components/landing/CTA';
import { MktCard } from '@/components/landing/marketing';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  CloudIcon,
  CpuChipIcon,
  ExclamationTriangleIcon,
  ServerIcon,
  ShieldCheckIcon,
  SignalIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';

type ServiceStatus = 'operational' | 'degraded' | 'outage' | 'maintenance';

interface Service {
  name: string;
  status: ServiceStatus;
  uptime: string;
  latency: string;
  icon: typeof ServerIcon;
}

interface Incident {
  id: string;
  title: string;
  status: 'investigating' | 'identified' | 'monitoring' | 'resolved';
  severity: 'minor' | 'major' | 'critical';
  createdAt: string;
  updatedAt: string;
  updates: { time: string; message: string }[];
}

const fallbackServices: Service[] = [
  {
    name: 'API Gateway',
    status: 'operational',
    uptime: '99.99%',
    latency: '45ms',
    icon: ServerIcon,
  },
  { name: 'Dashboard', status: 'operational', uptime: '99.98%', latency: '120ms', icon: CloudIcon },
  {
    name: 'Trust Engine',
    status: 'operational',
    uptime: '99.99%',
    latency: '85ms',
    icon: ShieldCheckIcon,
  },
  {
    name: 'CDP Pipeline',
    status: 'operational',
    uptime: '99.97%',
    latency: '150ms',
    icon: CpuChipIcon,
  },
  {
    name: 'Audience Sync',
    status: 'operational',
    uptime: '99.95%',
    latency: '200ms',
    icon: ArrowPathIcon,
  },
  { name: 'Webhooks', status: 'operational', uptime: '99.98%', latency: '65ms', icon: SignalIcon },
];

const fallbackIncidents: Incident[] = [
  {
    id: '1',
    title: 'Elevated API Latency',
    status: 'resolved',
    severity: 'minor',
    createdAt: 'January 18, 2026 - 14:23 UTC',
    updatedAt: 'January 18, 2026 - 15:45 UTC',
    updates: [
      { time: '15:45', message: 'Issue resolved. All systems operating normally.' },
      { time: '15:10', message: 'Fix deployed. Monitoring for stability.' },
      { time: '14:35', message: 'Root cause identified as database connection pool saturation.' },
      { time: '14:23', message: 'Investigating elevated API response times.' },
    ],
  },
];

const uptimeHistory = [
  { date: 'Jan 22', uptime: 100 },
  { date: 'Jan 21', uptime: 100 },
  { date: 'Jan 20', uptime: 100 },
  { date: 'Jan 19', uptime: 100 },
  { date: 'Jan 18', uptime: 99.8 },
  { date: 'Jan 17', uptime: 100 },
  { date: 'Jan 16', uptime: 100 },
  { date: 'Jan 15', uptime: 100 },
  { date: 'Jan 14', uptime: 100 },
  { date: 'Jan 13', uptime: 100 },
  { date: 'Jan 12', uptime: 100 },
  { date: 'Jan 11', uptime: 100 },
  { date: 'Jan 10', uptime: 100 },
  { date: 'Jan 9', uptime: 100 },
];

const getStatusTextClass = (status: ServiceStatus) => {
  switch (status) {
    case 'operational':
      return 'text-success';
    case 'degraded':
      return 'text-warning';
    case 'outage':
      return 'text-destructive';
    case 'maintenance':
      return 'text-accent';
    default:
      return 'text-muted-foreground';
  }
};

const getStatusIcon = (status: ServiceStatus) => {
  switch (status) {
    case 'operational':
      return <CheckCircleIcon className="w-5 h-5 text-success" />;
    case 'degraded':
      return <ExclamationTriangleIcon className="w-5 h-5 text-warning" />;
    case 'outage':
      return <XCircleIcon className="w-5 h-5 text-destructive" />;
    case 'maintenance':
      return <ClockIcon className="w-5 h-5 text-accent" />;
    default:
      return null;
  }
};

const getSeverityDotClass = (severity: string) => {
  switch (severity) {
    case 'minor':
      return 'bg-warning';
    case 'major':
      return 'bg-destructive';
    case 'critical':
      return 'bg-destructive';
    default:
      return 'bg-muted-foreground';
  }
};

const getUptimeBarClass = (uptime: number) => {
  if (uptime === 100) return 'bg-success';
  if (uptime > 99) return 'bg-warning';
  return 'bg-destructive';
};

const serviceIconMap: Record<string, typeof ServerIcon> = {
  ServerIcon,
  CloudIcon,
  ShieldCheckIcon,
  CpuChipIcon,
  ArrowPathIcon,
  SignalIcon,
};

export default function StatusPage() {
  const { content } = usePageContent<StatusPageContent>('status');
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null);

  // Use CMS data if available, otherwise fallback
  const services: Service[] = content?.services?.length
    ? content.services.map((s) => ({
        name: s.name,
        status: s.status as ServiceStatus,
        uptime: s.uptime,
        latency: s.latency,
        icon: serviceIconMap[s.name.replace(/\s+/g, '')] || ServerIcon,
      }))
    : fallbackServices;

  const recentIncidents: Incident[] = content?.incidents?.length
    ? content.incidents.map((inc, i) => ({
        id: String(i + 1),
        title: inc.title,
        status: inc.status as Incident['status'],
        severity: inc.severity as Incident['severity'],
        createdAt: inc.date,
        updatedAt: inc.date,
        updates: inc.updates,
      }))
    : fallbackIncidents;

  const allOperational = services.every((s) => s.status === 'operational');

  return (
    <PageLayout>
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 pb-12 lg:pt-24 lg:pb-16">
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
          <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-[820px] h-[420px] rounded-full bg-primary/5 blur-3xl" />
        </div>
        <div className="relative max-w-4xl mx-auto px-6 lg:px-8 text-center">
          {/* Overall Status */}
          <div
            className={`inline-flex items-center gap-3 px-6 py-3 rounded-full mb-8 animate-enter border ${
              allOperational
                ? 'bg-success/10 border-success/30'
                : 'bg-warning/10 border-warning/30'
            }`}
          >
            {allOperational ? (
              <CheckCircleIcon className="w-6 h-6 text-success" />
            ) : (
              <ExclamationTriangleIcon className="w-6 h-6 text-warning" />
            )}
            <span
              className={`text-body font-semibold ${
                allOperational ? 'text-success' : 'text-warning'
              }`}
            >
              {allOperational ? 'All Systems Operational' : 'Some Systems Degraded'}
            </span>
          </div>

          <h1
            className="text-display-sm md:text-display text-foreground animate-enter"
            style={{ animationDelay: '0.05s' }}
          >
            Stratum AI <span className="text-gradient-primary">System Status</span>
          </h1>

          <p
            className="mt-6 text-body text-muted-foreground animate-enter"
            style={{ animationDelay: '0.15s' }}
          >
            Real-time status and uptime monitoring for all Stratum AI services.
          </p>
        </div>
      </section>

      {/* Uptime Graph */}
      <section className="py-8">
        <div className="max-w-4xl mx-auto px-6 lg:px-8">
          <MktCard className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-h3 text-foreground font-semibold">Uptime - Last 14 Days</h3>
              <span className="text-success font-mono text-meta">99.98% average</span>
            </div>
            <div className="flex gap-1">
              {uptimeHistory.map((day, i) => (
                <div key={i} className="flex-1 group relative">
                  <div
                    className={`h-10 rounded transition-transform duration-200 group-hover:scale-110 opacity-80 ${getUptimeBarClass(
                      day.uptime
                    )}`}
                  />
                  <div className="absolute -top-10 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                    <div className="px-2 py-1 rounded text-micro text-foreground whitespace-nowrap bg-card border border-border">
                      {day.date}: {day.uptime}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-2 text-micro text-muted-foreground">
              <span>14 days ago</span>
              <span>Today</span>
            </div>
          </MktCard>
        </div>
      </section>

      {/* Services List */}
      <section className="py-8">
        <div className="max-w-4xl mx-auto px-6 lg:px-8">
          <h2 className="text-h1 text-foreground font-semibold mb-6">Services</h2>
          <div className="space-y-3">
            {services.map((service) => (
              <MktCard
                key={service.name}
                className="flex items-center justify-between p-4"
              >
                <div className="flex items-center gap-4">
                  <service.icon className="w-5 h-5 text-muted-foreground" />
                  <span className="text-body text-foreground font-medium">{service.name}</span>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <span className="text-micro text-muted-foreground">Uptime</span>
                    <p className="text-meta text-foreground font-mono">{service.uptime}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-micro text-muted-foreground">Latency</span>
                    <p className="text-meta text-foreground font-mono">{service.latency}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusIcon(service.status)}
                    <span
                      className={`text-meta font-medium capitalize ${getStatusTextClass(
                        service.status
                      )}`}
                    >
                      {service.status}
                    </span>
                  </div>
                </div>
              </MktCard>
            ))}
          </div>
        </div>
      </section>

      {/* Recent Incidents */}
      <section className="py-8">
        <div className="max-w-4xl mx-auto px-6 lg:px-8">
          <h2 className="text-h1 text-foreground font-semibold mb-6">Recent Incidents</h2>

          {recentIncidents.length === 0 ? (
            <MktCard className="p-8 text-center">
              <CheckCircleIcon className="w-12 h-12 mx-auto mb-4 text-success" />
              <p className="text-body text-foreground font-medium">No incidents reported</p>
              <p className="text-meta text-muted-foreground mt-1">
                All systems have been operating normally.
              </p>
            </MktCard>
          ) : (
            <div className="space-y-4">
              {recentIncidents.map((incident) => (
                <MktCard key={incident.id} className="overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between p-4"
                    onClick={() =>
                      setExpandedIncident(expandedIncident === incident.id ? null : incident.id)
                    }
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={`w-2 h-2 rounded-full ${getSeverityDotClass(
                          incident.severity
                        )}`}
                      />
                      <span className="text-body text-foreground font-medium">
                        {incident.title}
                      </span>
                      <span
                        className={`text-micro font-medium px-2 py-0.5 rounded-full capitalize border ${
                          incident.status === 'resolved'
                            ? 'bg-success/10 text-success border-success/20'
                            : 'bg-warning/10 text-warning border-warning/20'
                        }`}
                      >
                        {incident.status}
                      </span>
                    </div>
                    <span className="text-meta text-muted-foreground">{incident.createdAt}</span>
                  </button>

                  {expandedIncident === incident.id && (
                    <div className="px-4 pb-4 border-t border-border">
                      <div className="mt-4 space-y-3">
                        {incident.updates.map((update, i) => (
                          <div key={i} className="flex gap-3">
                            <span className="text-micro w-12 flex-shrink-0 text-muted-foreground">
                              {update.time}
                            </span>
                            <span className="text-meta text-muted-foreground">
                              {update.message}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </MktCard>
              ))}
            </div>
          )}
        </div>
      </section>

      <CTA />
    </PageLayout>
  );
}
