/**
 * CDP (Customer Data Platform) Components
 *
 * Export all CDP UI components for use across the application.
 */

// Segment Builder - Create and manage customer segments
export { SegmentBuilder } from './SegmentBuilder'
export { default as SegmentBuilderDefault } from './SegmentBuilder'

// Identity Graph - Visualize profile identity resolution
export { IdentityGraph, IdentityGraphVisualization } from './IdentityGraph'
export { default as IdentityGraphDefault } from './IdentityGraph'

// Funnel Builder - Create and analyze conversion funnels
export { FunnelBuilder } from './FunnelBuilder'
export { default as FunnelBuilderDefault } from './FunnelBuilder'

// RFM Dashboard - RFM analysis and customer segmentation
export { RFMDashboard } from './RFMDashboard'
export { default as RFMDashboardDefault } from './RFMDashboard'

// Webhook Manager - Configure webhook destinations
export { WebhookManager } from './WebhookManager'
export { default as WebhookManagerDefault } from './WebhookManager'

// Anomaly Dashboard - Monitor event volume anomalies
export { AnomalyDashboard } from './AnomalyDashboard'
export { default as AnomalyDashboardDefault } from './AnomalyDashboard'

// Profile Search - Advanced profile search and export
export { ProfileSearch } from './ProfileSearch'
export { default as ProfileSearchDefault } from './ProfileSearch'

// Audience Sync - Push segments to ad platforms
export { AudienceSync } from './AudienceSync'
export { default as AudienceSyncDefault } from './AudienceSync'
