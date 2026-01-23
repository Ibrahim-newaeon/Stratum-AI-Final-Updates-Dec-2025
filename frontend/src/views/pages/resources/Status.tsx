/**
 * System Status Page
 * 2026 Theme - Electric Neon / OLED-Optimized
 */

import { useState } from 'react';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  ClockIcon,
  SignalIcon,
  ServerIcon,
  CloudIcon,
  CpuChipIcon,
  ShieldCheckIcon,
  ArrowPathIcon,
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

const services: Service[] = [
  { name: 'API Gateway', status: 'operational', uptime: '99.99%', latency: '45ms', icon: ServerIcon },
  { name: 'Dashboard', status: 'operational', uptime: '99.98%', latency: '120ms', icon: CloudIcon },
  { name: 'Trust Engine', status: 'operational', uptime: '99.99%', latency: '85ms', icon: ShieldCheckIcon },
  { name: 'CDP Pipeline', status: 'operational', uptime: '99.97%', latency: '150ms', icon: CpuChipIcon },
  { name: 'Audience Sync', status: 'operational', uptime: '99.95%', latency: '200ms', icon: ArrowPathIcon },
  { name: 'Webhooks', status: 'operational', uptime: '99.98%', latency: '65ms', icon: SignalIcon },
];

const recentIncidents: Incident[] = [
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

const getStatusColor = (status: ServiceStatus) => {
  switch (status) {
    case 'operational':
      return '#00FF88';
    case 'degraded':
      return '#FFB800';
    case 'outage':
      return '#FF4757';
    case 'maintenance':
      return '#00D4FF';
    default:
      return '#94A3B8';
  }
};

const getStatusIcon = (status: ServiceStatus) => {
  switch (status) {
    case 'operational':
      return <CheckCircleIcon className="w-5 h-5" style={{ color: '#00FF88' }} />;
    case 'degraded':
      return <ExclamationTriangleIcon className="w-5 h-5" style={{ color: '#FFB800' }} />;
    case 'outage':
      return <XCircleIcon className="w-5 h-5" style={{ color: '#FF4757' }} />;
    case 'maintenance':
      return <ClockIcon className="w-5 h-5" style={{ color: '#00D4FF' }} />;
    default:
      return null;
  }
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'minor':
      return '#FFB800';
    case 'major':
      return '#FF6B6B';
    case 'critical':
      return '#FF4757';
    default:
      return '#94A3B8';
  }
};

export default function StatusPage() {
  const [expandedIncident, setExpandedIncident] = useState<string | null>(null);

  const allOperational = services.every((s) => s.status === 'operational');

  return (
    <PageLayout>
      <div className="min-h-screen">
        {/* Hero Section */}
        <section className="relative py-20 overflow-hidden">
          <div className="max-w-4xl mx-auto px-6 lg:px-8 text-center">
            {/* Overall Status */}
            <div
              className="inline-flex items-center gap-3 px-6 py-3 rounded-full mb-8"
              style={{
                background: allOperational ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 183, 0, 0.1)',
                border: `1px solid ${allOperational ? 'rgba(0, 255, 136, 0.3)' : 'rgba(255, 183, 0, 0.3)'}`,
              }}
            >
              {allOperational ? (
                <CheckCircleIcon className="w-6 h-6 text-[#00FF88]" />
              ) : (
                <ExclamationTriangleIcon className="w-6 h-6 text-[#FFB800]" />
              )}
              <span
                className="text-lg font-semibold"
                style={{ color: allOperational ? '#00FF88' : '#FFB800' }}
              >
                {allOperational ? 'All Systems Operational' : 'Some Systems Degraded'}
              </span>
            </div>

            <h1 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Stratum AI{' '}
              <span style={{
                background: 'linear-gradient(135deg, #8B5CF6 0%, #00D4FF 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>
                System Status
              </span>
            </h1>

            <p className="text-gray-400">
              Real-time status and uptime monitoring for all Stratum AI services.
            </p>
          </div>
        </section>

        {/* Uptime Graph */}
        <section className="py-8">
          <div className="max-w-4xl mx-auto px-6 lg:px-8">
            <div
              className="p-6 rounded-2xl"
              style={{
                background: 'rgba(10, 10, 15, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
              }}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-semibold">Uptime - Last 14 Days</h3>
                <span className="text-[#00FF88] font-mono text-sm">99.98% average</span>
              </div>
              <div className="flex gap-1">
                {uptimeHistory.map((day, i) => (
                  <div key={i} className="flex-1 group relative">
                    <div
                      className="h-10 rounded transition-all duration-200 group-hover:scale-110"
                      style={{
                        background: day.uptime === 100 ? '#00FF88' : day.uptime > 99 ? '#FFB800' : '#FF4757',
                        opacity: 0.8,
                      }}
                    />
                    <div className="absolute -top-10 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                      <div className="px-2 py-1 rounded text-xs text-white whitespace-nowrap"
                        style={{ background: 'rgba(0,0,0,0.9)' }}>
                        {day.date}: {day.uptime}%
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-2 text-xs text-gray-500">
                <span>14 days ago</span>
                <span>Today</span>
              </div>
            </div>
          </div>
        </section>

        {/* Services List */}
        <section className="py-8">
          <div className="max-w-4xl mx-auto px-6 lg:px-8">
            <h2 className="text-xl font-bold text-white mb-6">Services</h2>
            <div className="space-y-3">
              {services.map((service) => (
                <div
                  key={service.name}
                  className="flex items-center justify-between p-4 rounded-xl"
                  style={{
                    background: 'rgba(10, 10, 15, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <div className="flex items-center gap-4">
                    <service.icon className="w-5 h-5 text-gray-400" />
                    <span className="text-white font-medium">{service.name}</span>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <span className="text-xs text-gray-500">Uptime</span>
                      <p className="text-sm text-white font-mono">{service.uptime}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-gray-500">Latency</span>
                      <p className="text-sm text-white font-mono">{service.latency}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(service.status)}
                      <span
                        className="text-sm font-medium capitalize"
                        style={{ color: getStatusColor(service.status) }}
                      >
                        {service.status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Recent Incidents */}
        <section className="py-8">
          <div className="max-w-4xl mx-auto px-6 lg:px-8">
            <h2 className="text-xl font-bold text-white mb-6">Recent Incidents</h2>

            {recentIncidents.length === 0 ? (
              <div
                className="p-8 rounded-xl text-center"
                style={{
                  background: 'rgba(10, 10, 15, 0.6)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                }}
              >
                <CheckCircleIcon className="w-12 h-12 mx-auto mb-4 text-[#00FF88]" />
                <p className="text-white font-medium">No incidents reported</p>
                <p className="text-gray-400 text-sm mt-1">All systems have been operating normally.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {recentIncidents.map((incident) => (
                  <div
                    key={incident.id}
                    className="rounded-xl overflow-hidden"
                    style={{
                      background: 'rgba(10, 10, 15, 0.6)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                    }}
                  >
                    <button
                      className="w-full flex items-center justify-between p-4"
                      onClick={() => setExpandedIncident(expandedIncident === incident.id ? null : incident.id)}
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ background: getSeverityColor(incident.severity) }}
                        />
                        <span className="text-white font-medium">{incident.title}</span>
                        <span
                          className="text-xs font-medium px-2 py-0.5 rounded capitalize"
                          style={{
                            background: incident.status === 'resolved' ? 'rgba(0, 255, 136, 0.2)' : 'rgba(255, 183, 0, 0.2)',
                            color: incident.status === 'resolved' ? '#00FF88' : '#FFB800',
                          }}
                        >
                          {incident.status}
                        </span>
                      </div>
                      <span className="text-gray-500 text-sm">{incident.createdAt}</span>
                    </button>

                    {expandedIncident === incident.id && (
                      <div className="px-4 pb-4 border-t border-white/5">
                        <div className="mt-4 space-y-3">
                          {incident.updates.map((update, i) => (
                            <div key={i} className="flex gap-3">
                              <span className="text-xs text-gray-500 w-12 flex-shrink-0">{update.time}</span>
                              <span className="text-sm text-gray-300">{update.message}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Subscribe to Updates */}
        <section className="py-16">
          <div className="max-w-2xl mx-auto px-6 lg:px-8 text-center">
            <div
              className="p-8 rounded-2xl"
              style={{
                background: 'rgba(10, 10, 15, 0.6)',
                border: '1px solid rgba(139, 92, 246, 0.15)',
              }}
            >
              <h3 className="text-xl font-bold text-white mb-2">Subscribe to Status Updates</h3>
              <p className="text-gray-400 mb-6">
                Get notified about incidents and maintenance windows.
              </p>
              <div className="flex gap-3 max-w-md mx-auto">
                <input
                  type="email"
                  placeholder="Enter your email"
                  className="flex-1 px-4 py-3 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#8B5CF6]/50"
                  style={{
                    background: 'rgba(0, 0, 0, 0.4)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }}
                />
                <button
                  className="px-6 py-3 rounded-xl font-semibold text-white transition-all duration-200"
                  style={{
                    background: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
                  }}
                >
                  Subscribe
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </PageLayout>
  );
}
