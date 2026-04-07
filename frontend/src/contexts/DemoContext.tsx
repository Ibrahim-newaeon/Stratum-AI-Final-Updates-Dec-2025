/**
 * Demo Mode Context - Experience Stratum AI without signing up
 *
 * Provides sample data and demo state management for
 * prospects to explore the platform's capabilities.
 */

import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react';

// Demo tenant data
export const DEMO_TENANT = {
  id: 'demo-tenant-001',
  name: 'Acme Commerce',
  industry: 'E-commerce',
  tier: 'growth',
  createdAt: '2024-01-15',
};

// Demo user data
export const DEMO_USER = {
  id: 'demo-user-001',
  name: 'Demo User',
  email: 'demo@stratum.ai',
  role: 'admin',
  avatar: null,
};

// Demo metrics data
export const DEMO_METRICS = {
  // Signal Health
  signalHealth: {
    overall: 82,
    components: {
      dataQuality: 88,
      dataRecency: 79,
      dataVolume: 85,
      sourceReliability: 76,
    },
    trend: 'improving',
    lastUpdated: new Date().toISOString(),
  },

  // Trust Gate Stats
  trustGate: {
    totalDecisions: 1247,
    passed: 1089,
    held: 112,
    blocked: 46,
    passRate: 87.3,
    avgResponseTime: 23, // ms
  },

  // Revenue Metrics
  revenue: {
    arr: 2450000,
    mrr: 204166,
    arrGrowth: 42.5,
    mrrGrowth: 3.8,
    ltv: 4850,
    cac: 1230,
    ltvCacRatio: 3.94,
    churnRate: 2.1,
    nrr: 118,
  },

  // Marketing Metrics
  marketing: {
    totalSpend: 87500,
    roas: 4.2,
    ctr: 2.8,
    cvr: 3.4,
    cpc: 1.42,
    cpm: 12.5,
    impressions: 7000000,
    clicks: 196000,
    conversions: 6664,
  },

  // CDP Stats
  cdp: {
    totalProfiles: 125000,
    identifiedProfiles: 89000,
    anonymousProfiles: 36000,
    segments: 24,
    activeAudiences: 8,
    eventsLast24h: 450000,
    avgEmq: 7.8,
  },

  // AI Predictions
  predictions: {
    churnRisk: {
      high: 1250,
      medium: 3400,
      low: 84350,
    },
    ltvPrediction: {
      accuracy: 92.3,
      avgPredictedLtv: 4850,
      confidence: 0.89,
    },
  },
};

// Demo campaigns
export const DEMO_CAMPAIGNS = [
  {
    id: 'camp-001',
    name: 'Summer Sale 2024',
    platform: 'meta',
    status: 'active',
    budget: 25000,
    spend: 18750,
    roas: 4.8,
    impressions: 2100000,
    clicks: 58800,
    conversions: 2352,
    signalHealth: 89,
  },
  {
    id: 'camp-002',
    name: 'Brand Awareness Q1',
    platform: 'google',
    status: 'active',
    budget: 15000,
    spend: 12300,
    roas: 3.2,
    impressions: 4500000,
    clicks: 90000,
    conversions: 1800,
    signalHealth: 76,
  },
  {
    id: 'camp-003',
    name: 'Retargeting - Cart Abandoners',
    platform: 'meta',
    status: 'active',
    budget: 8000,
    spend: 6400,
    roas: 6.1,
    impressions: 850000,
    clicks: 34000,
    conversions: 1020,
    signalHealth: 94,
  },
  {
    id: 'camp-004',
    name: 'TikTok Product Launch',
    platform: 'tiktok',
    status: 'paused',
    budget: 12000,
    spend: 8900,
    roas: 2.9,
    impressions: 3200000,
    clicks: 128000,
    conversions: 1280,
    signalHealth: 62,
  },
];

// Demo segments
export const DEMO_SEGMENTS = [
  { id: 'seg-001', name: 'Champions', count: 8500, rfmScore: '555', status: 'active' },
  { id: 'seg-002', name: 'Loyal Customers', count: 15200, rfmScore: '445', status: 'active' },
  { id: 'seg-003', name: 'At Risk', count: 3400, rfmScore: '222', status: 'active' },
  { id: 'seg-004', name: 'New Customers', count: 12300, rfmScore: '511', status: 'active' },
  { id: 'seg-005', name: 'High Value Prospects', count: 5600, rfmScore: '144', status: 'active' },
  { id: 'seg-006', name: 'Cart Abandoners', count: 8900, rfmScore: '311', status: 'active' },
];

// Demo events
export const DEMO_EVENTS = [
  { type: 'purchase', count: 4520, trend: 12.5 },
  { type: 'add_to_cart', count: 18400, trend: 8.2 },
  { type: 'page_view', count: 245000, trend: -2.1 },
  { type: 'sign_up', count: 1250, trend: 15.8 },
  { type: 'product_view', count: 89000, trend: 5.4 },
];

// Demo trust gate history
export const DEMO_TRUST_GATE_HISTORY = [
  { time: '09:00', passed: 45, held: 3, blocked: 1 },
  { time: '10:00', passed: 52, held: 5, blocked: 2 },
  { time: '11:00', passed: 48, held: 4, blocked: 1 },
  { time: '12:00', passed: 38, held: 8, blocked: 3 },
  { time: '13:00', passed: 42, held: 6, blocked: 2 },
  { time: '14:00', passed: 55, held: 4, blocked: 1 },
  { time: '15:00', passed: 61, held: 3, blocked: 0 },
  { time: '16:00', passed: 58, held: 5, blocked: 2 },
];

interface DemoContextType {
  isDemoMode: boolean;
  enterDemoMode: () => void;
  exitDemoMode: () => void;
  demoTenant: typeof DEMO_TENANT;
  demoUser: typeof DEMO_USER;
  demoMetrics: typeof DEMO_METRICS;
  demoCampaigns: typeof DEMO_CAMPAIGNS;
  demoSegments: typeof DEMO_SEGMENTS;
  demoEvents: typeof DEMO_EVENTS;
  demoTrustGateHistory: typeof DEMO_TRUST_GATE_HISTORY;
}

const DemoContext = createContext<DemoContextType | undefined>(undefined);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Check URL for demo mode on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('demo') === 'true') {
      setIsDemoMode(true);
    }

    // Also check localStorage for returning demo users
    const storedDemo = localStorage.getItem('stratum_demo_mode');
    if (storedDemo === 'true') {
      setIsDemoMode(true);
    }
  }, []);

  const enterDemoMode = useCallback(() => {
    setIsDemoMode(true);
    localStorage.setItem('stratum_demo_mode', 'true');
    // Update URL without page reload
    const url = new URL(window.location.href);
    url.searchParams.set('demo', 'true');
    window.history.replaceState({}, '', url.toString());
  }, []);

  const exitDemoMode = useCallback(() => {
    setIsDemoMode(false);
    localStorage.removeItem('stratum_demo_mode');
    // Remove demo param from URL
    const url = new URL(window.location.href);
    url.searchParams.delete('demo');
    window.history.replaceState({}, '', url.toString());
  }, []);

  const value: DemoContextType = useMemo(
    () => ({
      isDemoMode,
      enterDemoMode,
      exitDemoMode,
      demoTenant: DEMO_TENANT,
      demoUser: DEMO_USER,
      demoMetrics: DEMO_METRICS,
      demoCampaigns: DEMO_CAMPAIGNS,
      demoSegments: DEMO_SEGMENTS,
      demoEvents: DEMO_EVENTS,
      demoTrustGateHistory: DEMO_TRUST_GATE_HISTORY,
    }),
    [isDemoMode, enterDemoMode, exitDemoMode]
  );

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo() {
  const context = useContext(DemoContext);
  if (context === undefined) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
}

export default DemoContext;
