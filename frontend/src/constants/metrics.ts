/**
 * Stratum AI - Centralized Metrics Registry
 *
 * Defines all ~120 platform metrics across Meta, Google, TikTok, and Snapchat.
 * Each metric includes per-platform availability, display format, category,
 * and flags for cost-toggle / price-metric behaviour.
 */

// =============================================================================
// Types
// =============================================================================

export type MetricCategory =
  | 'reach_awareness'
  | 'engagement'
  | 'video'
  | 'conversion'
  | 'quality_relevance'
  | 'audience'
  | 'messaging'
  | 'delivery_auction'
  | 'attribution'
  | 'shopping_catalog'
  | 'ar_interactive';

export type AdPlatform = 'meta' | 'google' | 'tiktok' | 'snapchat';

export type MetricFormat = 'number' | 'percentage' | 'currency' | 'decimal' | 'duration';

export interface MetricDefinition {
  /** Unique snake_case identifier used as DB key and API field name */
  id: string;
  /** Human-readable label */
  label: string;
  /** Short description of what the metric measures */
  description: string;
  /** Category grouping */
  category: MetricCategory;
  /** Platforms where this metric is available */
  platforms: AdPlatform[];
  /** Display format hint */
  format: MetricFormat;
  /**
   * When true, this metric is also shown when the cost toggle is ON.
   * Example: Conversion Value, Purchase Value, Assisted Conv Value.
   */
  showWithCostTrigger?: boolean;
  /**
   * When true, this is a price/cost metric controlled by the cost toggle.
   * (spend, revenue, ROAS, CPA, CPC, CPM, CPV)
   */
  isPriceMetric?: boolean;
}

export interface CategoryDefinition {
  id: MetricCategory;
  label: string;
  description: string;
}

// =============================================================================
// Category Definitions
// =============================================================================

export const METRIC_CATEGORIES: CategoryDefinition[] = [
  { id: 'reach_awareness', label: 'Reach & Awareness', description: 'Impressions, reach, frequency, and brand lift metrics' },
  { id: 'engagement', label: 'Engagement', description: 'Clicks, reactions, shares, follows, and interaction metrics' },
  { id: 'video', label: 'Video', description: 'Video views, watch time, completion rates, and play percentages' },
  { id: 'conversion', label: 'Conversion', description: 'Conversions, purchases, registrations, app installs, and funnel events' },
  { id: 'quality_relevance', label: 'Quality & Relevance', description: 'Ad quality scores, relevance rankings, and optimization scores' },
  { id: 'audience', label: 'Audience', description: 'Audience size, saturation, overlap, and penetration metrics' },
  { id: 'messaging', label: 'Messaging', description: 'Messaging conversations, replies, and connection metrics' },
  { id: 'delivery_auction', label: 'Delivery & Auction', description: 'Delivery status, learning phase, auction competitiveness, and ad position' },
  { id: 'attribution', label: 'Attribution', description: 'Attribution windows, data-driven attribution, and assisted conversions' },
  { id: 'shopping_catalog', label: 'Shopping / Catalog', description: 'Product catalog views, sales, wishlists, and cart abandonment' },
  { id: 'ar_interactive', label: 'AR / Interactive', description: 'Augmented reality lens plays, shares, saves, and interactive add-on clicks' },
];

// =============================================================================
// Metric Registry
// =============================================================================

export const METRIC_REGISTRY: Record<string, MetricDefinition> = {
  // ---------------------------------------------------------------------------
  // Price / Cost metrics (existing — controlled by cost toggle)
  // ---------------------------------------------------------------------------
  spend: {
    id: 'spend',
    label: 'Total Spend',
    description: 'Total advertising spend across campaigns',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'currency',
    isPriceMetric: true,
  },
  revenue: {
    id: 'revenue',
    label: 'Revenue',
    description: 'Total revenue attributed to campaigns',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'currency',
    isPriceMetric: true,
  },
  roas: {
    id: 'roas',
    label: 'Return on Ad Spend (ROAS)',
    description: 'Revenue divided by ad spend',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'decimal',
    isPriceMetric: true,
  },
  cpa: {
    id: 'cpa',
    label: 'Cost per Acquisition (CPA)',
    description: 'Average cost per conversion',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'currency',
    isPriceMetric: true,
  },
  cpc: {
    id: 'cpc',
    label: 'Cost per Click (CPC)',
    description: 'Average cost per click on an ad',
    category: 'engagement',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'currency',
    isPriceMetric: true,
  },
  cpm: {
    id: 'cpm',
    label: 'Cost per Mille (CPM)',
    description: 'Cost per 1,000 impressions',
    category: 'reach_awareness',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'currency',
    isPriceMetric: true,
  },
  cpv: {
    id: 'cpv',
    label: 'Cost per View (CPV)',
    description: 'Average cost per video view',
    category: 'video',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'currency',
    isPriceMetric: true,
  },

  // ---------------------------------------------------------------------------
  // Reach & Awareness
  // ---------------------------------------------------------------------------
  impressions: {
    id: 'impressions',
    label: 'Impressions',
    description: 'Total number of times ads were displayed',
    category: 'reach_awareness',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  reach: {
    id: 'reach',
    label: 'Reach',
    description: 'Unique users who saw the ad at least once',
    category: 'reach_awareness',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  frequency: {
    id: 'frequency',
    label: 'Frequency',
    description: 'Average number of times each user saw the ad',
    category: 'reach_awareness',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'decimal',
  },
  estimated_ad_recall_lift: {
    id: 'estimated_ad_recall_lift',
    label: 'Estimated Ad Recall Lift',
    description: 'Estimated additional people who would remember seeing the ad',
    category: 'reach_awareness',
    platforms: ['meta'],
    format: 'number',
  },
  brand_lift: {
    id: 'brand_lift',
    label: 'Brand Lift',
    description: 'Measured increase in brand awareness or favorability',
    category: 'reach_awareness',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'percentage',
  },
  impression_share: {
    id: 'impression_share',
    label: 'Impression Share',
    description: 'Percentage of available impressions your ads received',
    category: 'reach_awareness',
    platforms: ['google'],
    format: 'percentage',
  },
  search_impression_share: {
    id: 'search_impression_share',
    label: 'Search Impression Share',
    description: 'Percentage of search impressions your ads received',
    category: 'reach_awareness',
    platforms: ['google'],
    format: 'percentage',
  },
  lost_is_rank: {
    id: 'lost_is_rank',
    label: 'Lost IS (Rank)',
    description: 'Impression share lost due to ad rank',
    category: 'reach_awareness',
    platforms: ['google'],
    format: 'percentage',
  },
  lost_is_budget: {
    id: 'lost_is_budget',
    label: 'Lost IS (Budget)',
    description: 'Impression share lost due to budget constraints',
    category: 'reach_awareness',
    platforms: ['google'],
    format: 'percentage',
  },
  swipe_ups_organic: {
    id: 'swipe_ups_organic',
    label: 'Swipe Ups (Organic)',
    description: 'Organic swipe-up interactions on Snapchat',
    category: 'reach_awareness',
    platforms: ['snapchat'],
    format: 'number',
  },

  // ---------------------------------------------------------------------------
  // Engagement
  // ---------------------------------------------------------------------------
  clicks: {
    id: 'clicks',
    label: 'Clicks',
    description: 'Total clicks on the ad',
    category: 'engagement',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  ctr: {
    id: 'ctr',
    label: 'Click-Through Rate (CTR)',
    description: 'Percentage of impressions that resulted in a click',
    category: 'engagement',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'percentage',
  },
  link_clicks: {
    id: 'link_clicks',
    label: 'Link Clicks',
    description: 'Clicks on links within the ad directing off-platform',
    category: 'engagement',
    platforms: ['meta', 'tiktok', 'snapchat'],
    format: 'number',
  },
  outbound_clicks: {
    id: 'outbound_clicks',
    label: 'Outbound Clicks',
    description: 'Clicks that lead people off Meta platforms',
    category: 'engagement',
    platforms: ['meta'],
    format: 'number',
  },
  outbound_ctr: {
    id: 'outbound_ctr',
    label: 'Outbound CTR',
    description: 'Outbound clicks divided by impressions',
    category: 'engagement',
    platforms: ['meta'],
    format: 'percentage',
  },
  post_reactions: {
    id: 'post_reactions',
    label: 'Post Reactions',
    description: 'Total reactions (likes, loves, etc.) on ad posts',
    category: 'engagement',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  post_comments: {
    id: 'post_comments',
    label: 'Post Comments',
    description: 'Comments on ad posts',
    category: 'engagement',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  post_shares: {
    id: 'post_shares',
    label: 'Post Shares',
    description: 'Times the ad was shared',
    category: 'engagement',
    platforms: ['meta', 'tiktok', 'snapchat'],
    format: 'number',
  },
  post_saves: {
    id: 'post_saves',
    label: 'Post Saves',
    description: 'Times users saved the ad for later',
    category: 'engagement',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  page_likes: {
    id: 'page_likes',
    label: 'Page Likes',
    description: 'New page likes from the ad',
    category: 'engagement',
    platforms: ['meta'],
    format: 'number',
  },
  profile_visits: {
    id: 'profile_visits',
    label: 'Profile Visits',
    description: 'Visits to the advertiser profile from the ad',
    category: 'engagement',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  follows_paid: {
    id: 'follows_paid',
    label: 'Follows (Paid)',
    description: 'New followers gained from paid ads',
    category: 'engagement',
    platforms: ['meta', 'tiktok', 'snapchat'],
    format: 'number',
  },
  likes_content: {
    id: 'likes_content',
    label: 'Likes (Content)',
    description: 'Total likes on ad content',
    category: 'engagement',
    platforms: ['tiktok'],
    format: 'number',
  },
  interaction_rate: {
    id: 'interaction_rate',
    label: 'Interaction Rate',
    description: 'Overall interaction rate across engagement types',
    category: 'engagement',
    platforms: ['google', 'tiktok'],
    format: 'percentage',
  },
  engagements_youtube: {
    id: 'engagements_youtube',
    label: 'Engagements (YouTube)',
    description: 'Total engagements on YouTube ads',
    category: 'engagement',
    platforms: ['google'],
    format: 'number',
  },
  swipe_up_rate: {
    id: 'swipe_up_rate',
    label: 'Swipe Up Rate',
    description: 'Percentage of impressions that resulted in a swipe up',
    category: 'engagement',
    platforms: ['snapchat'],
    format: 'percentage',
  },
  screen_time: {
    id: 'screen_time',
    label: 'Screen Time',
    description: 'Average time spent viewing the ad',
    category: 'engagement',
    platforms: ['snapchat'],
    format: 'duration',
  },
  shares_story: {
    id: 'shares_story',
    label: 'Shares (Story)',
    description: 'Times the ad was shared to stories',
    category: 'engagement',
    platforms: ['snapchat'],
    format: 'number',
  },
  screenshots: {
    id: 'screenshots',
    label: 'Screenshots',
    description: 'Number of screenshots taken of the ad',
    category: 'engagement',
    platforms: ['snapchat'],
    format: 'number',
  },

  // ---------------------------------------------------------------------------
  // Video
  // ---------------------------------------------------------------------------
  video_views_3s: {
    id: 'video_views_3s',
    label: 'Video Views (3s)',
    description: 'Video plays of at least 3 seconds',
    category: 'video',
    platforms: ['meta', 'tiktok', 'snapchat'],
    format: 'number',
  },
  video_views_2s_continuous: {
    id: 'video_views_2s_continuous',
    label: 'Video Views (2s Continuous)',
    description: 'Continuous video plays of at least 2 seconds',
    category: 'video',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  thruplays_15s: {
    id: 'thruplays_15s',
    label: 'ThruPlays (15s)',
    description: 'Video plays to completion or at least 15 seconds',
    category: 'video',
    platforms: ['meta'],
    format: 'number',
  },
  video_plays_25: {
    id: 'video_plays_25',
    label: 'Video Plays 25%',
    description: 'Video played to 25% of its length',
    category: 'video',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  video_plays_50: {
    id: 'video_plays_50',
    label: 'Video Plays 50%',
    description: 'Video played to 50% of its length',
    category: 'video',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  video_plays_75: {
    id: 'video_plays_75',
    label: 'Video Plays 75%',
    description: 'Video played to 75% of its length',
    category: 'video',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  video_plays_100: {
    id: 'video_plays_100',
    label: 'Video Plays 100%',
    description: 'Video played to completion',
    category: 'video',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  average_watch_time: {
    id: 'average_watch_time',
    label: 'Average Watch Time',
    description: 'Average time users spent watching the video',
    category: 'video',
    platforms: ['meta', 'tiktok'],
    format: 'duration',
  },
  video_view_rate: {
    id: 'video_view_rate',
    label: 'Video View Rate',
    description: 'Percentage of impressions that resulted in a video view',
    category: 'video',
    platforms: ['google'],
    format: 'percentage',
  },
  avg_view_duration: {
    id: 'avg_view_duration',
    label: 'Avg. View Duration',
    description: 'Average duration of video views',
    category: 'video',
    platforms: ['google'],
    format: 'duration',
  },
  video_views_6s: {
    id: 'video_views_6s',
    label: 'Video Views (6s)',
    description: 'Video plays of at least 6 seconds',
    category: 'video',
    platforms: ['tiktok'],
    format: 'number',
  },
  video_completions: {
    id: 'video_completions',
    label: 'Video Completions',
    description: 'Total number of complete video plays',
    category: 'video',
    platforms: ['tiktok', 'snapchat'],
    format: 'number',
  },
  avg_screen_time: {
    id: 'avg_screen_time',
    label: 'Avg. Screen Time',
    description: 'Average screen time per session',
    category: 'video',
    platforms: ['snapchat'],
    format: 'duration',
  },

  // ---------------------------------------------------------------------------
  // Conversion
  // ---------------------------------------------------------------------------
  conversions: {
    id: 'conversions',
    label: 'Conversions',
    description: 'Total conversion events',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  conversions_total: {
    id: 'conversions_total',
    label: 'Total Conversions',
    description: 'Aggregate count of all conversion types',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  conversion_rate: {
    id: 'conversion_rate',
    label: 'Conversion Rate',
    description: 'Percentage of clicks that resulted in a conversion',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'percentage',
  },
  conversion_value: {
    id: 'conversion_value',
    label: 'Conversion Value',
    description: 'Total monetary value of conversions',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'currency',
    showWithCostTrigger: true,
  },
  purchases: {
    id: 'purchases',
    label: 'Purchases',
    description: 'Number of completed purchase events',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  purchase_value: {
    id: 'purchase_value',
    label: 'Purchase Value',
    description: 'Total monetary value of purchases',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'currency',
    showWithCostTrigger: true,
  },
  add_to_cart: {
    id: 'add_to_cart',
    label: 'Add to Cart',
    description: 'Items added to shopping cart',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  initiate_checkout: {
    id: 'initiate_checkout',
    label: 'Initiate Checkout',
    description: 'Checkout process started',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  leads_form_submits: {
    id: 'leads_form_submits',
    label: 'Leads / Form Submits',
    description: 'Lead generation or form submission events',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  registrations: {
    id: 'registrations',
    label: 'Registrations',
    description: 'New account registration events',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  view_content: {
    id: 'view_content',
    label: 'View Content',
    description: 'Content view events (e.g. product page)',
    category: 'conversion',
    platforms: ['meta', 'tiktok', 'snapchat'],
    format: 'number',
  },
  search_on_site: {
    id: 'search_on_site',
    label: 'Search on Site',
    description: 'On-site search events from ad traffic',
    category: 'conversion',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  add_payment_info: {
    id: 'add_payment_info',
    label: 'Add Payment Info',
    description: 'Payment information added during checkout',
    category: 'conversion',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  app_installs: {
    id: 'app_installs',
    label: 'App Installs',
    description: 'Mobile app installation events',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  app_events_custom: {
    id: 'app_events_custom',
    label: 'App Events (Custom)',
    description: 'Custom in-app events tracked via SDK',
    category: 'conversion',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  offline_conversions: {
    id: 'offline_conversions',
    label: 'Offline Conversions',
    description: 'Conversions tracked offline and uploaded',
    category: 'conversion',
    platforms: ['meta', 'google'],
    format: 'number',
  },
  store_visits: {
    id: 'store_visits',
    label: 'Store Visits',
    description: 'Estimated physical store visits from ads',
    category: 'conversion',
    platforms: ['meta', 'google', 'snapchat'],
    format: 'number',
  },
  phone_calls: {
    id: 'phone_calls',
    label: 'Phone Calls',
    description: 'Phone calls initiated from ads',
    category: 'conversion',
    platforms: ['google'],
    format: 'number',
  },
  directions_maps: {
    id: 'directions_maps',
    label: 'Directions (Maps)',
    description: 'Map direction requests from ads',
    category: 'conversion',
    platforms: ['google'],
    format: 'number',
  },
  all_conversions: {
    id: 'all_conversions',
    label: 'All Conversions',
    description: 'All conversion types including modeled conversions',
    category: 'conversion',
    platforms: ['google'],
    format: 'number',
  },
  view_through_conversions: {
    id: 'view_through_conversions',
    label: 'View-Through Conversions',
    description: 'Conversions after viewing but not clicking the ad',
    category: 'conversion',
    platforms: ['google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  click_through_conversions: {
    id: 'click_through_conversions',
    label: 'Click-Through Conversions',
    description: 'Conversions after clicking the ad',
    category: 'conversion',
    platforms: ['google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  assisted_conversions: {
    id: 'assisted_conversions',
    label: 'Assisted Conversions',
    description: 'Conversions where this ad assisted but was not the last click',
    category: 'conversion',
    platforms: ['google'],
    format: 'number',
  },
  pixel_purchase: {
    id: 'pixel_purchase',
    label: 'Pixel Purchase',
    description: 'Purchases tracked via pixel',
    category: 'conversion',
    platforms: ['tiktok', 'snapchat'],
    format: 'number',
  },
  on_web_events: {
    id: 'on_web_events',
    label: 'On-Web Events',
    description: 'Conversion events tracked on the web',
    category: 'conversion',
    platforms: ['tiktok'],
    format: 'number',
  },
  sign_up: {
    id: 'sign_up',
    label: 'Sign Up',
    description: 'Sign-up or registration events',
    category: 'conversion',
    platforms: ['snapchat'],
    format: 'number',
  },

  // ---------------------------------------------------------------------------
  // Quality & Relevance
  // ---------------------------------------------------------------------------
  quality_ranking: {
    id: 'quality_ranking',
    label: 'Quality Ranking',
    description: 'Ad quality ranking compared to competitors',
    category: 'quality_relevance',
    platforms: ['meta'],
    format: 'number',
  },
  engagement_rate_ranking: {
    id: 'engagement_rate_ranking',
    label: 'Engagement Rate Ranking',
    description: 'Engagement rate ranking compared to competitors',
    category: 'quality_relevance',
    platforms: ['meta'],
    format: 'number',
  },
  conversion_rate_ranking: {
    id: 'conversion_rate_ranking',
    label: 'Conversion Rate Ranking',
    description: 'Conversion rate ranking compared to competitors',
    category: 'quality_relevance',
    platforms: ['meta'],
    format: 'number',
  },
  ad_relevance_diagnostics: {
    id: 'ad_relevance_diagnostics',
    label: 'Ad Relevance Diagnostics',
    description: 'Overall ad relevance diagnostic score',
    category: 'quality_relevance',
    platforms: ['meta'],
    format: 'number',
  },
  quality_score: {
    id: 'quality_score',
    label: 'Quality Score',
    description: 'Google Ads quality score (1-10)',
    category: 'quality_relevance',
    platforms: ['google'],
    format: 'number',
  },
  landing_page_experience: {
    id: 'landing_page_experience',
    label: 'Landing Page Experience',
    description: 'Rating of the landing page experience',
    category: 'quality_relevance',
    platforms: ['google'],
    format: 'number',
  },
  expected_ctr: {
    id: 'expected_ctr',
    label: 'Expected CTR',
    description: 'Expected click-through rate compared to competitors',
    category: 'quality_relevance',
    platforms: ['google'],
    format: 'number',
  },
  ad_relevance: {
    id: 'ad_relevance',
    label: 'Ad Relevance',
    description: 'Ad relevance score for TikTok campaigns',
    category: 'quality_relevance',
    platforms: ['tiktok'],
    format: 'number',
  },
  optimization_score: {
    id: 'optimization_score',
    label: 'Optimization Score',
    description: 'Google Ads optimization score percentage',
    category: 'quality_relevance',
    platforms: ['google'],
    format: 'percentage',
  },

  // ---------------------------------------------------------------------------
  // Audience
  // ---------------------------------------------------------------------------
  audience_size: {
    id: 'audience_size',
    label: 'Audience Size',
    description: 'Total size of the target audience',
    category: 'audience',
    platforms: ['meta', 'google', 'tiktok', 'snapchat'],
    format: 'number',
  },
  audience_saturation: {
    id: 'audience_saturation',
    label: 'Audience Saturation',
    description: 'Percentage of audience reached',
    category: 'audience',
    platforms: ['meta'],
    format: 'percentage',
  },
  first_time_impression_ratio: {
    id: 'first_time_impression_ratio',
    label: 'First-Time Impression Ratio',
    description: 'Ratio of users seeing the ad for the first time',
    category: 'audience',
    platforms: ['meta'],
    format: 'percentage',
  },
  new_vs_returning: {
    id: 'new_vs_returning',
    label: 'New vs Returning',
    description: 'Breakdown of new versus returning users',
    category: 'audience',
    platforms: ['google'],
    format: 'percentage',
  },
  audience_segment_overlaps: {
    id: 'audience_segment_overlaps',
    label: 'Audience Segment Overlaps',
    description: 'Overlap between different audience segments',
    category: 'audience',
    platforms: ['meta', 'google'],
    format: 'percentage',
  },
  audience_penetration: {
    id: 'audience_penetration',
    label: 'Audience Penetration',
    description: 'Depth of audience penetration within target segments',
    category: 'audience',
    platforms: ['snapchat'],
    format: 'percentage',
  },

  // ---------------------------------------------------------------------------
  // Messaging
  // ---------------------------------------------------------------------------
  messaging_conversations_started: {
    id: 'messaging_conversations_started',
    label: 'Messaging Conversations Started',
    description: 'New messaging conversations initiated from ads',
    category: 'messaging',
    platforms: ['meta'],
    format: 'number',
  },
  messaging_replies: {
    id: 'messaging_replies',
    label: 'Messaging Replies',
    description: 'Replies received in ad-initiated conversations',
    category: 'messaging',
    platforms: ['meta'],
    format: 'number',
  },
  new_messaging_connections: {
    id: 'new_messaging_connections',
    label: 'New Messaging Connections',
    description: 'New messaging contacts from ads',
    category: 'messaging',
    platforms: ['meta'],
    format: 'number',
  },
  blocked_messaging_connections: {
    id: 'blocked_messaging_connections',
    label: 'Blocked Messaging Connections',
    description: 'Messaging connections that were blocked',
    category: 'messaging',
    platforms: ['meta'],
    format: 'number',
  },

  // ---------------------------------------------------------------------------
  // Delivery & Auction
  // ---------------------------------------------------------------------------
  delivery_status: {
    id: 'delivery_status',
    label: 'Delivery Status',
    description: 'Current delivery status of the ad set',
    category: 'delivery_auction',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  learning_phase_status: {
    id: 'learning_phase_status',
    label: 'Learning Phase Status',
    description: 'Whether the ad set is in the learning phase',
    category: 'delivery_auction',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  auction_overlap_rate: {
    id: 'auction_overlap_rate',
    label: 'Auction Overlap Rate',
    description: 'Rate at which your ads compete against each other',
    category: 'delivery_auction',
    platforms: ['meta'],
    format: 'percentage',
  },
  auction_competitiveness: {
    id: 'auction_competitiveness',
    label: 'Auction Competitiveness',
    description: 'How competitive the ad auction is',
    category: 'delivery_auction',
    platforms: ['meta'],
    format: 'percentage',
  },
  absolute_top_impression_pct: {
    id: 'absolute_top_impression_pct',
    label: 'Absolute Top Impression %',
    description: 'Percentage of impressions shown in the absolute top position',
    category: 'delivery_auction',
    platforms: ['google'],
    format: 'percentage',
  },
  top_impression_pct: {
    id: 'top_impression_pct',
    label: 'Top Impression %',
    description: 'Percentage of impressions shown in top positions',
    category: 'delivery_auction',
    platforms: ['google'],
    format: 'percentage',
  },
  ad_position_avg: {
    id: 'ad_position_avg',
    label: 'Avg. Ad Position',
    description: 'Average position of the ad on the page',
    category: 'delivery_auction',
    platforms: ['google'],
    format: 'decimal',
  },

  // ---------------------------------------------------------------------------
  // Attribution
  // ---------------------------------------------------------------------------
  seven_day_click_conversions: {
    id: 'seven_day_click_conversions',
    label: '7-Day Click Conversions',
    description: 'Conversions within 7 days of clicking the ad',
    category: 'attribution',
    platforms: ['meta'],
    format: 'number',
  },
  one_day_view_conversions: {
    id: 'one_day_view_conversions',
    label: '1-Day View Conversions',
    description: 'Conversions within 1 day of viewing the ad',
    category: 'attribution',
    platforms: ['meta'],
    format: 'number',
  },
  one_day_click_conversions: {
    id: 'one_day_click_conversions',
    label: '1-Day Click Conversions',
    description: 'Conversions within 1 day of clicking the ad',
    category: 'attribution',
    platforms: ['meta'],
    format: 'number',
  },
  twenty_eight_day_click_conversions: {
    id: 'twenty_eight_day_click_conversions',
    label: '28-Day Click Conversions',
    description: 'Conversions within 28 days of clicking the ad',
    category: 'attribution',
    platforms: ['meta'],
    format: 'number',
  },
  data_driven_attribution: {
    id: 'data_driven_attribution',
    label: 'Data-Driven Attribution',
    description: 'Conversions attributed using data-driven models',
    category: 'attribution',
    platforms: ['google'],
    format: 'number',
  },
  last_click_conversions: {
    id: 'last_click_conversions',
    label: 'Last-Click Conversions',
    description: 'Conversions attributed to the last click',
    category: 'attribution',
    platforms: ['google'],
    format: 'number',
  },
  assisted_conv_value: {
    id: 'assisted_conv_value',
    label: 'Assisted Conv. Value',
    description: 'Monetary value of assisted conversions',
    category: 'attribution',
    platforms: ['google'],
    format: 'currency',
    showWithCostTrigger: true,
  },

  // ---------------------------------------------------------------------------
  // Shopping / Catalog
  // ---------------------------------------------------------------------------
  content_views_dpa: {
    id: 'content_views_dpa',
    label: 'Content Views (DPA)',
    description: 'Content views from Dynamic Product Ads',
    category: 'shopping_catalog',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  product_catalog_sales: {
    id: 'product_catalog_sales',
    label: 'Product Catalog Sales',
    description: 'Sales from product catalog campaigns',
    category: 'shopping_catalog',
    platforms: ['meta', 'google'],
    format: 'number',
  },
  products_added_to_wishlist: {
    id: 'products_added_to_wishlist',
    label: 'Products Added to Wishlist',
    description: 'Products added to user wishlists',
    category: 'shopping_catalog',
    platforms: ['meta', 'tiktok'],
    format: 'number',
  },
  shopping_cart_abandonment: {
    id: 'shopping_cart_abandonment',
    label: 'Shopping Cart Abandonment',
    description: 'Rate of abandoned shopping carts',
    category: 'shopping_catalog',
    platforms: ['meta', 'google'],
    format: 'percentage',
  },
  product_click_through: {
    id: 'product_click_through',
    label: 'Product Click-Through',
    description: 'Clicks on specific products in catalog ads',
    category: 'shopping_catalog',
    platforms: ['google'],
    format: 'number',
  },

  // ---------------------------------------------------------------------------
  // AR / Interactive
  // ---------------------------------------------------------------------------
  ar_lens_plays: {
    id: 'ar_lens_plays',
    label: 'AR Lens Plays',
    description: 'Number of times the AR lens was played',
    category: 'ar_interactive',
    platforms: ['snapchat'],
    format: 'number',
  },
  ar_lens_shares: {
    id: 'ar_lens_shares',
    label: 'AR Lens Shares',
    description: 'Times the AR lens was shared',
    category: 'ar_interactive',
    platforms: ['snapchat'],
    format: 'number',
  },
  ar_lens_save: {
    id: 'ar_lens_save',
    label: 'AR Lens Save',
    description: 'Times the AR lens was saved by users',
    category: 'ar_interactive',
    platforms: ['snapchat'],
    format: 'number',
  },
  ar_lens_play_time: {
    id: 'ar_lens_play_time',
    label: 'AR Lens Play Time',
    description: 'Total time spent playing the AR lens',
    category: 'ar_interactive',
    platforms: ['snapchat'],
    format: 'duration',
  },
  interactive_addon_clicks: {
    id: 'interactive_addon_clicks',
    label: 'Interactive Add-on Clicks',
    description: 'Clicks on interactive ad add-ons',
    category: 'ar_interactive',
    platforms: ['snapchat'],
    format: 'number',
  },
};

// =============================================================================
// Backward-compatible METRIC_LABELS derived from registry
// =============================================================================

export const METRIC_LABELS: Record<string, string> = Object.fromEntries(
  Object.values(METRIC_REGISTRY).map((m) => [m.id, m.label])
);

// =============================================================================
// Helper Functions
// =============================================================================

/** Get all metrics belonging to a specific category */
export function getMetricsByCategory(category: MetricCategory): MetricDefinition[] {
  return Object.values(METRIC_REGISTRY).filter((m) => m.category === category);
}

/** Get all metrics available on a specific platform */
export function getMetricsByPlatform(platform: AdPlatform): MetricDefinition[] {
  return Object.values(METRIC_REGISTRY).filter((m) => m.platforms.includes(platform));
}

/** Get price/cost metrics controlled by the cost toggle */
export function getPriceMetrics(): MetricDefinition[] {
  return Object.values(METRIC_REGISTRY).filter((m) => m.isPriceMetric);
}

/** Get all non-price metrics */
export function getNonPriceMetrics(): MetricDefinition[] {
  return Object.values(METRIC_REGISTRY).filter((m) => !m.isPriceMetric);
}

/** Get metrics that should also be displayed when cost toggle is ON */
export function getCostTriggerMetrics(): MetricDefinition[] {
  return Object.values(METRIC_REGISTRY).filter((m) => m.showWithCostTrigger);
}

/** Check if a metric is available on a given platform */
export function isMetricAvailable(metricId: string, platform: AdPlatform): boolean {
  const metric = METRIC_REGISTRY[metricId];
  return metric ? metric.platforms.includes(platform) : false;
}

/** Format a metric value for display based on its format type */
export function formatMetricValue(value: number, format: MetricFormat): string {
  switch (format) {
    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      }).format(value);
    case 'percentage':
      return `${value.toFixed(2)}%`;
    case 'decimal':
      return value.toFixed(2);
    case 'duration':
      // Convert seconds to mm:ss
      if (value < 60) return `${value.toFixed(1)}s`;
      const mins = Math.floor(value / 60);
      const secs = Math.round(value % 60);
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    case 'number':
    default:
      return new Intl.NumberFormat('en-US').format(Math.round(value));
  }
}
