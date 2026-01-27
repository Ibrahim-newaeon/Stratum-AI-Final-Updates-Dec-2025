/**
 * API Docs Page
 * API documentation overview
 */

import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/landing/PageLayout';
import {
  BookOpenIcon,
  CodeBracketIcon,
  CommandLineIcon,
  CubeIcon,
} from '@heroicons/react/24/outline';

const quickLinks = [
  {
    icon: BookOpenIcon,
    title: 'Getting Started',
    description: 'Learn the basics and set up your first integration.',
    href: '#getting-started',
  },
  {
    icon: CodeBracketIcon,
    title: 'API Reference',
    description: 'Complete reference for all API endpoints.',
    href: '#api-reference',
  },
  {
    icon: CommandLineIcon,
    title: 'SDKs & Libraries',
    description: 'Official SDKs for JavaScript, Python, and more.',
    href: '#sdks',
  },
  {
    icon: CubeIcon,
    title: 'Webhooks',
    description: 'Real-time event notifications for your app.',
    href: '#webhooks',
  },
];

const endpoints = [
  { method: 'GET', path: '/api/v1/signals', description: 'List all signals' },
  { method: 'POST', path: '/api/v1/signals', description: 'Create a new signal' },
  { method: 'GET', path: '/api/v1/signals/:id/health', description: 'Get signal health score' },
  { method: 'GET', path: '/api/v1/automations', description: 'List all automations' },
  { method: 'POST', path: '/api/v1/automations/execute', description: 'Execute automation' },
  { method: 'GET', path: '/api/v1/cdp/profiles', description: 'Search customer profiles' },
  { method: 'POST', path: '/api/v1/cdp/segments', description: 'Create a segment' },
  { method: 'POST', path: '/api/v1/audience-sync', description: 'Sync audience to platform' },
];

export default function ApiDocs() {
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
            <CodeBracketIcon className="w-4 h-4" />
            Developer Documentation
          </div>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold mb-6"
            style={{ fontFamily: "'Inter', sans-serif" }}
          >
            <span className="text-white">Build with the</span>
            <br />
            <span
              style={{
                background: 'linear-gradient(135deg, #a855f7 0%, #06b6d4 50%, #f97316 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Stratum API
            </span>
          </h1>
          <p
            className="text-lg md:text-xl max-w-2xl mx-auto"
            style={{ color: 'rgba(255, 255, 255, 0.7)' }}
          >
            Everything you need to integrate Stratum AI into your applications.
          </p>
        </div>
      </section>

      {/* Quick Links */}
      <section className="py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {quickLinks.map((link) => (
              <a
                key={link.title}
                href={link.href}
                className="p-6 rounded-2xl transition-all hover:scale-[1.02] group"
                style={{
                  background: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                }}
              >
                <link.icon className="w-8 h-8 mb-4" style={{ color: '#06b6d4' }} />
                <h3 className="text-lg font-semibold text-white mb-2">{link.title}</h3>
                <p className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.6)' }}>
                  {link.description}
                </p>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* API Reference Preview */}
      <section className="py-12 px-6" id="api-reference">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white mb-8">API Reference</h2>
          <div
            className="rounded-2xl overflow-hidden"
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <div className="p-4 border-b" style={{ borderColor: 'rgba(255, 255, 255, 0.08)' }}>
              <h3 className="font-semibold text-white">Popular Endpoints</h3>
            </div>
            <div className="divide-y" style={{ borderColor: 'rgba(255, 255, 255, 0.08)' }}>
              {endpoints.map((endpoint) => (
                <div
                  key={`${endpoint.method}-${endpoint.path}`}
                  className="p-4 flex items-center gap-4 hover:bg-white/5 transition-colors"
                >
                  <span
                    className="px-2 py-1 rounded text-xs font-mono font-bold"
                    style={{
                      background:
                        endpoint.method === 'GET'
                          ? 'rgba(34, 197, 94, 0.2)'
                          : 'rgba(59, 130, 246, 0.2)',
                      color: endpoint.method === 'GET' ? '#22c55e' : '#3b82f6',
                    }}
                  >
                    {endpoint.method}
                  </span>
                  <code className="text-sm text-white font-mono flex-1">{endpoint.path}</code>
                  <span className="text-sm" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
                    {endpoint.description}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Code Example */}
      <section className="py-12 px-6" id="getting-started">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl font-bold text-white mb-8">Quick Start</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xl font-semibold text-white mb-4">1. Get your API key</h3>
              <p className="mb-6" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                Sign up for Stratum AI and generate an API key from your dashboard settings.
              </p>
              <h3 className="text-xl font-semibold text-white mb-4">2. Install the SDK</h3>
              <div
                className="p-4 rounded-xl font-mono text-sm mb-6"
                style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#22c55e',
                }}
              >
                npm install @stratum-ai/sdk
              </div>
              <h3 className="text-xl font-semibold text-white mb-4">3. Make your first request</h3>
              <p style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
                Use the SDK to connect to the API and start tracking signals.
              </p>
            </div>
            <div
              className="p-6 rounded-2xl font-mono text-sm overflow-x-auto"
              style={{
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <pre style={{ color: 'rgba(255, 255, 255, 0.9)' }}>
                {`import { StratumClient } from '@stratum-ai/sdk';

const stratum = new StratumClient({
  apiKey: process.env.STRATUM_API_KEY,
});

// Get signal health
const health = await stratum.signals.getHealth('sig_123');
console.log(health.score); // 85

// Execute automation if healthy
if (health.score >= 70) {
  await stratum.automations.execute('auto_456');
}`}
              </pre>
            </div>
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
                'linear-gradient(135deg, rgba(6, 182, 212, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">Ready to Start Building?</h2>
            <p className="text-lg mb-8" style={{ color: 'rgba(255, 255, 255, 0.7)' }}>
              Get your API key and start integrating in minutes.
            </p>
            <Link
              to="/signup"
              className="inline-flex px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:opacity-90"
              style={{
                background: '#f97316',
                boxShadow: '0 4px 20px rgba(249, 115, 22, 0.4)',
              }}
            >
              Get API Key
            </Link>
          </div>
        </div>
      </section>
    </PageLayout>
  );
}
