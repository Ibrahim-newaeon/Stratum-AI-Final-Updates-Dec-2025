/**
 * Embed Widgets Type Definitions
 */

export type WidgetType =
  | 'signal_health'
  | 'roas_display'
  | 'campaign_performance'
  | 'trust_gate_status'
  | 'spend_tracker'
  | 'anomaly_alert';

export type WidgetSize = 'badge' | 'compact' | 'standard' | 'large' | 'custom';

export type BrandingLevel = 'full' | 'minimal' | 'none';

export type TokenStatus = 'active' | 'revoked' | 'expired';

export interface WidgetDataScope {
  campaigns?: string[];
  ad_accounts?: string[];
  date_range_days: number;
}

export interface WidgetCustomBranding {
  custom_logo_url?: string;
  custom_accent_color?: string;
  custom_background_color?: string;
  custom_text_color?: string;
}

export interface EmbedWidget {
  id: string;
  name: string;
  description?: string;
  widget_type: WidgetType;
  widget_size: WidgetSize;
  custom_width?: number;
  custom_height?: number;
  branding_level: BrandingLevel;
  data_scope: WidgetDataScope;
  refresh_interval_seconds: number;
  is_active: boolean;
  total_views: number;
  created_at: string;
  updated_at: string;
  custom_logo_url?: string;
  custom_accent_color?: string;
  custom_background_color?: string;
  custom_text_color?: string;
}

export interface EmbedToken {
  id: string;
  token_prefix: string;
  allowed_domains: string[];
  status: TokenStatus;
  expires_at: string;
  last_used_at?: string;
  total_requests: number;
  total_errors: number;
  created_at: string;
}

export interface EmbedTokenCreate {
  allowed_domains: string[];
  expires_in_days: number;
}

export interface EmbedTokenCreateResponse {
  id: string;
  token: string;
  refresh_token: string;
  token_prefix: string;
  allowed_domains: string[];
  expires_at: string;
  rate_limit_per_minute: number;
}

export interface DomainWhitelist {
  id: string;
  domain_pattern: string;
  is_verified: boolean;
  is_active: boolean;
  description?: string;
  created_at: string;
}

export interface EmbedCodeResponse {
  widget_id: string;
  iframe_code: string;
  script_code: string;
  preview_url: string;
  documentation_url: string;
}

export interface EmbedTierInfo {
  tier: string;
  branding_level: BrandingLevel;
  limits: {
    max_widgets: number;
    max_domains: number;
  };
  features: {
    basic_widgets: boolean;
    minimal_branding: boolean;
    white_label: boolean;
  };
}

// Widget data types for rendering
export interface SignalHealthData {
  overall_score: number;
  status: 'healthy' | 'degraded' | 'unhealthy';
  platforms: Record<string, number>;
  last_updated: string;
}

export interface ROASData {
  blended_roas: number;
  trend: 'up' | 'down' | 'stable';
  trend_percentage: number;
  period: string;
  last_updated: string;
}

export interface TrustGateData {
  status: 'pass' | 'hold' | 'block';
  signal_health: number;
  automation_mode: string;
  pending_actions: number;
  last_updated: string;
}

export interface SpendTrackerData {
  total_spend: number;
  budget?: number;
  utilization_percentage?: number;
  currency: string;
  period: string;
  last_updated: string;
}

export interface AnomalyAlertData {
  has_anomalies: boolean;
  anomaly_count: number;
  severity: 'none' | 'low' | 'medium' | 'high';
  most_recent?: string;
  last_updated: string;
}

export interface CampaignPerformanceData {
  campaigns: Array<{
    name: string;
    roas: number;
    spend: number;
    status: string;
  }>;
  total_campaigns: number;
  top_performer?: string;
  last_updated: string;
}

// Widget size dimensions
export const WIDGET_DIMENSIONS: Record<WidgetSize, { width: number; height: number }> = {
  badge: { width: 120, height: 40 },
  compact: { width: 200, height: 100 },
  standard: { width: 300, height: 200 },
  large: { width: 400, height: 300 },
  custom: { width: 0, height: 0 }, // Custom uses widget-specific dimensions
};

// Widget type labels and descriptions
export const WIDGET_TYPE_INFO: Record<WidgetType, { label: string; description: string; icon: string }> = {
  signal_health: {
    label: 'Signal Health',
    description: 'Display overall signal health score and platform breakdown',
    icon: 'shield',
  },
  roas_display: {
    label: 'ROAS Display',
    description: 'Show blended ROAS with trend indicator',
    icon: 'chart',
  },
  campaign_performance: {
    label: 'Campaign Performance',
    description: 'Mini table of top performing campaigns',
    icon: 'table',
  },
  trust_gate_status: {
    label: 'Trust Gate Status',
    description: 'Current trust gate status and automation mode',
    icon: 'lock',
  },
  spend_tracker: {
    label: 'Spend Tracker',
    description: 'Track ad spend against budget',
    icon: 'dollar',
  },
  anomaly_alert: {
    label: 'Anomaly Alert',
    description: 'Alert badge for detected anomalies',
    icon: 'alert',
  },
};
