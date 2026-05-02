/**
 * Stratum AI - Platform Setup Modal
 *
 * Shows all required tokens, IDs, and credentials needed to connect
 * each integration platform. Opens when user clicks a platform card.
 */

import { useState, useEffect, useRef } from 'react'
import {
  XMarkIcon,
  ClipboardDocumentIcon,
  CheckIcon,
  ArrowTopRightOnSquareIcon,
  EyeIcon,
  EyeSlashIcon,
  ShieldCheckIcon,
  KeyIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

// ─── Platform Credential Definitions ────────────────────────────────────────

export interface CredentialField {
  key: string
  label: string
  type: 'text' | 'password' | 'url' | 'select'
  placeholder: string
  helpText: string
  whereToFind: string
  required: boolean
  options?: { value: string; label: string }[] // for select type
}

export interface PlatformCredentialConfig {
  id: string
  name: string
  category: 'ad-platform' | 'crm' | 'messaging' | 'analytics' | 'payments' | 'commerce'
  color: string
  icon: string // first letter or emoji
  subtitle: string
  description: string
  docsUrl: string
  authMethod: 'oauth' | 'api-key' | 'webhook' | 'oauth+api-key'
  credentials: CredentialField[]
  oauthScopes?: string[]
  apiVersion?: string
  notes?: string[]
  capiEvents?: string[]
  audienceFormat?: string
}

export const platformCredentials: PlatformCredentialConfig[] = [
  // ── Ad Platforms ────────────────────────────────────────────────────────
  {
    id: 'meta',
    name: 'Meta Ads',
    category: 'ad-platform',
    color: 'from-blue-500 to-blue-700',
    icon: 'M',
    subtitle: 'Facebook & Instagram Ads',
    description: 'Connect Meta Ads for campaign management, Conversions API (CAPI), and Custom Audience sync.',
    docsUrl: 'https://developers.facebook.com/docs/marketing-apis',
    authMethod: 'oauth+api-key',
    apiVersion: 'v25.0',
    credentials: [
      {
        key: 'meta_app_id',
        label: 'App ID',
        type: 'text',
        placeholder: '123456789012345',
        helpText: 'Your Meta App unique identifier.',
        whereToFind: 'Meta for Developers → Your App → Settings → Basic → App ID',
        required: true,
      },
      {
        key: 'meta_app_secret',
        label: 'App Secret',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'OAuth client secret for your Meta App.',
        whereToFind: 'Meta for Developers → Your App → Settings → Basic → App Secret',
        required: true,
      },
      {
        key: 'meta_access_token',
        label: 'System User Access Token',
        type: 'password',
        placeholder: 'EAAxxxxxxx...',
        helpText: 'Long-lived System User token (never expires). Preferred over user tokens.',
        whereToFind: 'Business Settings → System Users → Generate Token → Select App → Grant permissions',
        required: true,
      },
      {
        key: 'pixel_id',
        label: 'Pixel ID',
        type: 'text',
        placeholder: '123456789012345',
        helpText: 'Facebook Pixel ID for Conversions API event tracking.',
        whereToFind: 'Meta Ads Manager → Events Manager → Data Sources → select Pixel → ID in header',
        required: true,
      },
      {
        key: 'meta_ad_account_ids',
        label: 'Ad Account IDs',
        type: 'text',
        placeholder: '123456789,987654321',
        helpText: 'Comma-separated ad account IDs (without act_ prefix).',
        whereToFind: 'Meta Ads Manager → Account dropdown → Settings → Ad Account ID',
        required: false,
      },
    ],
    oauthScopes: ['ads_management', 'ads_read', 'business_management', 'pages_read_engagement'],
    capiEvents: ['Purchase', 'Lead', 'AddToCart', 'InitiateCheckout', 'Subscribe', 'CompleteRegistration', 'Contact', 'ViewContent'],
    audienceFormat: 'Email, Phone, MADID — all SHA-256 hashed automatically',
    notes: [
      'Tokens are exchanged for a 60-day long-lived token and auto-refreshed before expiry.',
      'System User tokens (generated in Business Manager) are recommended as they never expire.',
      'All PII (emails, phones) is SHA-256 hashed before sending to Meta.',
      'Custom Audiences support up to 10,000 users per batch.',
    ],
  },
  {
    id: 'google',
    name: 'Google Ads',
    category: 'ad-platform',
    color: 'from-green-500 to-blue-500',
    icon: 'G',
    subtitle: 'Google Ads & Enhanced Conversions',
    description: 'Connect Google Ads for campaign management, Enhanced Conversions, and Customer Match audiences.',
    docsUrl: 'https://developers.google.com/google-ads/api/docs/start',
    authMethod: 'oauth+api-key',
    apiVersion: 'v15',
    credentials: [
      {
        key: 'google_ads_developer_token',
        label: 'Developer Token',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxx',
        helpText: 'Google Ads API developer token for API access.',
        whereToFind: 'Google Ads → Tools & Settings → Setup → API Center → Developer Token',
        required: true,
      },
      {
        key: 'google_ads_client_id',
        label: 'OAuth Client ID',
        type: 'text',
        placeholder: '123456789-xxxxxx.apps.googleusercontent.com',
        helpText: 'OAuth 2.0 Client ID for authentication.',
        whereToFind: 'Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs',
        required: true,
      },
      {
        key: 'google_ads_client_secret',
        label: 'OAuth Client Secret',
        type: 'password',
        placeholder: 'GOCSPX-xxxxxxxxxxxxxxx',
        helpText: 'OAuth 2.0 Client Secret paired with the Client ID.',
        whereToFind: 'Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs → Secret',
        required: true,
      },
      {
        key: 'google_ads_refresh_token',
        label: 'Refresh Token',
        type: 'password',
        placeholder: '1//xxxxxxxxxxxxxxxxxx',
        helpText: 'Long-lived refresh token for persistent API access.',
        whereToFind: 'Generated during OAuth consent flow — Stratum handles this automatically after first connection.',
        required: true,
      },
      {
        key: 'google_ads_customer_id',
        label: 'Customer ID',
        type: 'text',
        placeholder: '123-456-7890',
        helpText: 'Google Ads account Customer ID (with or without dashes).',
        whereToFind: 'Google Ads → top-right corner → Customer ID (format: 123-456-7890)',
        required: true,
      },
      {
        key: 'conversion_action_id',
        label: 'Conversion Action ID',
        type: 'text',
        placeholder: '123456789',
        helpText: 'ID of the conversion action for Enhanced Conversions.',
        whereToFind: 'Google Ads → Tools & Settings → Measurement → Conversions → select action → Conversion Action ID',
        required: false,
      },
    ],
    oauthScopes: ['https://www.googleapis.com/auth/adwords'],
    capiEvents: ['Enhanced Conversions for Web'],
    audienceFormat: 'Hashed email, phone, first name, last name, country, postal code — retention 1-540 days',
    notes: [
      'A persistent refresh token keeps the connection alive — no re-authentication needed.',
      'Developer Token requires Basic or Standard access level for production use.',
      'Customer Match audiences support up to 100,000 users per batch.',
      'Enhanced Conversions require a configured conversion action in Google Ads.',
    ],
  },
  {
    id: 'tiktok',
    name: 'TikTok Ads',
    category: 'ad-platform',
    color: 'from-pink-500 to-gray-900',
    icon: 'T',
    subtitle: 'TikTok for Business',
    description: 'Connect TikTok Ads for campaign management, Events API, and DMP Custom Audiences.',
    docsUrl: 'https://business-api.tiktok.com/portal/docs',
    authMethod: 'oauth+api-key',
    apiVersion: 'v1.3',
    credentials: [
      {
        key: 'tiktok_app_id',
        label: 'App ID',
        type: 'text',
        placeholder: '1234567890123456789',
        helpText: 'TikTok Marketing API App ID.',
        whereToFind: 'TikTok for Business → Developer Portal → My Apps → App ID',
        required: true,
      },
      {
        key: 'tiktok_secret',
        label: 'App Secret',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'TikTok Marketing App Secret.',
        whereToFind: 'TikTok for Business → Developer Portal → My Apps → App Secret',
        required: true,
      },
      {
        key: 'tiktok_access_token',
        label: 'Access Token',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'OAuth access token (valid 24 hours, auto-refreshed).',
        whereToFind: 'Generated during OAuth flow — Stratum handles this automatically.',
        required: true,
      },
      {
        key: 'tiktok_advertiser_id',
        label: 'Advertiser ID',
        type: 'text',
        placeholder: '1234567890123456789',
        helpText: 'Your TikTok Ads Manager advertiser account ID.',
        whereToFind: 'TikTok Ads Manager → Account Settings → Advertiser ID',
        required: true,
      },
      {
        key: 'tiktok_pixel_id',
        label: 'Pixel Code',
        type: 'text',
        placeholder: 'CXXXXXXXXXXXXXXXXX',
        helpText: 'TikTok Pixel code for Events API tracking.',
        whereToFind: 'TikTok Ads Manager → Assets → Events → Web Events → Pixel Code',
        required: true,
      },
      {
        key: 'tiktok_capi_token',
        label: 'Events API Token',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Separate access token specifically for Events API.',
        whereToFind: 'TikTok Ads Manager → Assets → Events → Web Events → Settings → Generate Access Token',
        required: false,
      },
    ],
    oauthScopes: ['advertiser.read', 'advertiser.write', 'campaign.read', 'campaign.write', 'report.read'],
    capiEvents: ['ViewContent', 'AddToCart', 'PlaceAnOrder', 'CompletePayment', 'Subscribe'],
    audienceFormat: 'Separate uploads per type: EMAIL_SHA256, PHONE_SHA256, IDFA_SHA256, GAID_SHA256',
    notes: [
      'Access tokens last 24 hours and are auto-refreshed. Refresh tokens valid 365 days.',
      'DMP Custom Audiences support up to 50,000 users per batch.',
      'Events API requires a separate token from the OAuth access token.',
      'Pixel Code is different from Pixel ID — use the code starting with "C".',
    ],
  },
  {
    id: 'snapchat',
    name: 'Snapchat Ads',
    category: 'ad-platform',
    color: 'from-yellow-400 to-yellow-600',
    icon: 'S',
    subtitle: 'Snapchat Marketing API',
    description: 'Connect Snapchat Ads for campaign management, Snap Audience Match (SAM), and Conversion tracking.',
    docsUrl: 'https://developers.snap.com/api/marketing-api',
    authMethod: 'oauth+api-key',
    apiVersion: 'v1',
    credentials: [
      {
        key: 'snapchat_client_id',
        label: 'Client ID',
        type: 'text',
        placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
        helpText: 'OAuth 2.0 Client ID for Snapchat Marketing API.',
        whereToFind: 'Snap Kit Developer Portal → Your App → OAuth2 Client ID',
        required: true,
      },
      {
        key: 'snapchat_client_secret',
        label: 'Client Secret',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'OAuth 2.0 Client Secret.',
        whereToFind: 'Snap Kit Developer Portal → Your App → OAuth2 Client Secret',
        required: true,
      },
      {
        key: 'snapchat_ad_account_id',
        label: 'Ad Account ID',
        type: 'text',
        placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
        helpText: 'Your Snapchat Ads Manager account ID.',
        whereToFind: 'Snapchat Ads Manager → Account Settings → Ad Account ID',
        required: true,
      },
      {
        key: 'snapchat_pixel_id',
        label: 'Snap Pixel ID',
        type: 'text',
        placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
        helpText: 'Snap Pixel ID for conversion tracking.',
        whereToFind: 'Snapchat Ads Manager → Events Manager → Snap Pixel → Pixel ID',
        required: true,
      },
      {
        key: 'snapchat_capi_token',
        label: 'Conversions API Token',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Separate token for Conversions API event submission.',
        whereToFind: 'Snapchat Ads Manager → Events Manager → Conversions API → Generate Token',
        required: false,
      },
    ],
    oauthScopes: ['snapchat-marketing-api'],
    capiEvents: ['PURCHASE', 'ADD_CART', 'VIEW_CONTENT', 'SIGN_UP', 'PAGE_VIEW'],
    audienceFormat: 'Hashed email, phone, MADID — default 180-day retention',
    notes: [
      'Access tokens last 30 minutes and are auto-refreshed. Refresh tokens valid 1 year.',
      'Token refresh uses Basic auth (base64 encoded client_id:client_secret).',
      'Snap Audience Match supports up to 100,000 users per batch.',
      'All identifiers are SHA-256 hashed before upload.',
    ],
  },

  // ── CRM Platforms ───────────────────────────────────────────────────────
  {
    id: 'hubspot',
    name: 'HubSpot',
    category: 'crm',
    color: 'from-orange-500 to-orange-700',
    icon: 'H',
    subtitle: 'CRM & Marketing Hub',
    description: 'Sync contacts, companies, and deals between Stratum AI and HubSpot CRM.',
    docsUrl: 'https://developers.hubspot.com/docs/api/overview',
    authMethod: 'oauth',
    credentials: [
      {
        key: 'hubspot_client_id',
        label: 'OAuth Client ID',
        type: 'text',
        placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
        helpText: 'OAuth App Client ID from your HubSpot developer account.',
        whereToFind: 'HubSpot Developer Account → Apps → Your App → Auth → Client ID',
        required: true,
      },
      {
        key: 'hubspot_client_secret',
        label: 'OAuth Client Secret',
        type: 'password',
        placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
        helpText: 'OAuth App Client Secret.',
        whereToFind: 'HubSpot Developer Account → Apps → Your App → Auth → Client Secret',
        required: true,
      },
      {
        key: 'hubspot_api_key',
        label: 'API Key (Legacy)',
        type: 'password',
        placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
        helpText: 'Legacy API key — OAuth is preferred for new integrations.',
        whereToFind: 'HubSpot → Settings → Integrations → API Key (deprecated)',
        required: false,
      },
    ],
    oauthScopes: [
      'crm.objects.contacts.read', 'crm.objects.contacts.write',
      'crm.objects.deals.read', 'crm.objects.deals.write',
      'crm.objects.owners.read',
      'crm.schemas.contacts.read', 'crm.schemas.deals.read',
    ],
    notes: [
      'OAuth is the recommended auth method — API keys are deprecated.',
      'Tokens are auto-refreshed using the refresh token.',
      'All tokens are encrypted before database storage.',
      'Syncs contacts, companies, deals, and owners.',
    ],
  },
  {
    id: 'salesforce',
    name: 'Salesforce',
    category: 'crm',
    color: 'from-blue-400 to-cyan-600',
    icon: 'SF',
    subtitle: 'CRM & Sales Cloud',
    description: 'Connect Salesforce to sync contacts, leads, opportunities, and accounts.',
    docsUrl: 'https://developer.salesforce.com/docs/apis',
    authMethod: 'oauth',
    apiVersion: 'v59.0',
    credentials: [
      {
        key: 'salesforce_client_id',
        label: 'Connected App Client ID',
        type: 'text',
        placeholder: '3MVG9xxxxxxxxxxxxxxx',
        helpText: 'Consumer Key from your Salesforce Connected App.',
        whereToFind: 'Salesforce Setup → App Manager → Your Connected App → Consumer Key',
        required: true,
      },
      {
        key: 'salesforce_client_secret',
        label: 'Connected App Client Secret',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Consumer Secret from your Salesforce Connected App.',
        whereToFind: 'Salesforce Setup → App Manager → Your Connected App → Consumer Secret',
        required: true,
      },
      {
        key: 'salesforce_instance_url',
        label: 'Instance URL',
        type: 'select',
        placeholder: 'Select environment',
        helpText: 'Choose Production or Sandbox login endpoint.',
        whereToFind: 'Use Production for live data, Sandbox for testing.',
        required: true,
        options: [
          { value: 'https://login.salesforce.com', label: 'Production (login.salesforce.com)' },
          { value: 'https://test.salesforce.com', label: 'Sandbox (test.salesforce.com)' },
        ],
      },
    ],
    oauthScopes: ['api', 'refresh_token', 'offline_access'],
    notes: [
      'Supports SOQL queries for contacts, leads, opportunities, and accounts.',
      'Use Sandbox for testing before connecting production.',
      'Tokens are encrypted and stored securely.',
      'Supports bidirectional data writeback.',
    ],
  },
  {
    id: 'zoho',
    name: 'Zoho CRM',
    category: 'crm',
    color: 'from-red-500 to-red-700',
    icon: 'Z',
    subtitle: 'Zoho CRM Suite',
    description: 'Sync contacts, deals, accounts, and leads with Zoho CRM.',
    docsUrl: 'https://www.zoho.com/crm/developer/docs/api/v3/',
    authMethod: 'oauth',
    apiVersion: 'v3',
    credentials: [
      {
        key: 'zoho_client_id',
        label: 'OAuth Client ID',
        type: 'text',
        placeholder: '1000.xxxxxxxxxxxxxxx',
        helpText: 'OAuth 2.0 Client ID from Zoho API Console.',
        whereToFind: 'Zoho API Console → Your App → Client ID',
        required: true,
      },
      {
        key: 'zoho_client_secret',
        label: 'OAuth Client Secret',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'OAuth 2.0 Client Secret.',
        whereToFind: 'Zoho API Console → Your App → Client Secret',
        required: true,
      },
      {
        key: 'zoho_region',
        label: 'Data Center Region',
        type: 'select',
        placeholder: 'Select your region',
        helpText: 'Must match the region where your Zoho account is hosted.',
        whereToFind: 'Check your Zoho login URL — zoho.com (US), zoho.eu (EU), zoho.in (India), etc.',
        required: true,
        options: [
          { value: 'com', label: 'United States (zoho.com)' },
          { value: 'eu', label: 'Europe (zoho.eu)' },
          { value: 'in', label: 'India (zoho.in)' },
          { value: 'au', label: 'Australia (zoho.com.au)' },
          { value: 'jp', label: 'Japan (zoho.jp)' },
          { value: 'cn', label: 'China (zoho.com.cn)' },
        ],
      },
    ],
    oauthScopes: [
      'ZohoCRM.modules.contacts.READ', 'ZohoCRM.modules.contacts.WRITE',
      'ZohoCRM.modules.deals.READ', 'ZohoCRM.modules.deals.WRITE',
      'ZohoCRM.modules.accounts.READ', 'ZohoCRM.modules.leads.READ',
      'ZohoCRM.users.READ', 'ZohoCRM.org.READ',
    ],
    notes: [
      'API endpoints vary by region — make sure to select the correct data center.',
      'Tokens are auto-refreshed and encrypted before storage.',
      'Supports contacts, deals, accounts, and leads sync.',
    ],
  },
  {
    id: 'pipedrive',
    name: 'Pipedrive',
    category: 'crm',
    color: 'from-emerald-500 to-emerald-700',
    icon: 'P',
    subtitle: 'Sales CRM',
    description: 'Connect Pipedrive to sync deals, contacts, and organizations.',
    docsUrl: 'https://developers.pipedrive.com/docs/api/v1',
    authMethod: 'oauth',
    credentials: [
      {
        key: 'pipedrive_client_id',
        label: 'OAuth Client ID',
        type: 'text',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'OAuth 2.0 Client ID from Pipedrive Developer Hub.',
        whereToFind: 'Pipedrive Developer Hub → Your App → OAuth & Access Scopes → Client ID',
        required: true,
      },
      {
        key: 'pipedrive_client_secret',
        label: 'OAuth Client Secret',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'OAuth 2.0 Client Secret.',
        whereToFind: 'Pipedrive Developer Hub → Your App → OAuth & Access Scopes → Client Secret',
        required: true,
      },
    ],
    notes: [
      'Pipedrive API domain varies per account (api-{subdomain}.pipedrive.com).',
      'Tokens are auto-refreshed via OAuth refresh token.',
      'Syncs deals, contacts, organizations, and activities.',
    ],
  },

  // ── Messaging ───────────────────────────────────────────────────────────
  {
    id: 'whatsapp',
    name: 'WhatsApp Business',
    category: 'messaging',
    color: 'from-green-500 to-green-700',
    icon: 'W',
    subtitle: 'WhatsApp Cloud API',
    description: 'Send customer messages and receive webhook notifications via WhatsApp Business API.',
    docsUrl: 'https://developers.facebook.com/docs/whatsapp/cloud-api',
    authMethod: 'api-key',
    apiVersion: 'v18.0',
    credentials: [
      {
        key: 'whatsapp_phone_number_id',
        label: 'Phone Number ID',
        type: 'text',
        placeholder: '123456789012345',
        helpText: 'The ID assigned to your WhatsApp Business phone number.',
        whereToFind: 'Meta Business Suite → WhatsApp Manager → Phone Numbers → Phone Number ID',
        required: true,
      },
      {
        key: 'whatsapp_access_token',
        label: 'Permanent Access Token',
        type: 'password',
        placeholder: 'EAAxxxxxxx...',
        helpText: 'System User permanent token for WhatsApp Cloud API.',
        whereToFind: 'Meta Business Settings → System Users → Generate Token → select WhatsApp app → whatsapp_business_messaging permission',
        required: true,
      },
      {
        key: 'whatsapp_business_account_id',
        label: 'Business Account ID',
        type: 'text',
        placeholder: '123456789012345',
        helpText: 'Your WhatsApp Business Account (WABA) ID.',
        whereToFind: 'Meta Business Suite → WhatsApp Manager → Overview → Business Account ID',
        required: true,
      },
      {
        key: 'whatsapp_verify_token',
        label: 'Webhook Verify Token',
        type: 'text',
        placeholder: 'my-custom-verify-token',
        helpText: 'A custom string you set for webhook verification. Must match the token configured in Meta webhook settings.',
        whereToFind: 'You create this value — enter the same string in Meta Webhook Configuration.',
        required: true,
      },
      {
        key: 'whatsapp_app_secret',
        label: 'App Secret',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Meta App Secret for webhook signature verification (HMAC-SHA1).',
        whereToFind: 'Meta for Developers → Your App → Settings → Basic → App Secret',
        required: true,
      },
    ],
    notes: [
      'Uses Meta Graph API — same App Secret as Meta Ads if using the same app.',
      'Webhook endpoint: /api/v1/whatsapp/webhook',
      'Signature verification uses HMAC-SHA1 with the App Secret.',
      'Permanent System User tokens are recommended for production.',
    ],
  },
  {
    id: 'slack',
    name: 'Slack',
    category: 'messaging',
    color: 'from-purple-500 to-purple-700',
    icon: 'SL',
    subtitle: 'Team Notifications',
    description: 'Receive Trust Gate decisions, anomaly alerts, and daily summaries in your Slack channels.',
    docsUrl: 'https://api.slack.com/messaging/webhooks',
    authMethod: 'webhook',
    credentials: [
      {
        key: 'slack_webhook_url',
        label: 'Incoming Webhook URL',
        type: 'url',
        placeholder: 'https://hooks.slack.com/services/T00/B00/xxxx',
        helpText: 'Slack Incoming Webhook URL for posting messages to a channel.',
        whereToFind: 'Slack → Apps → Incoming Webhooks → Add New Webhook to Workspace → Copy Webhook URL',
        required: true,
      },
      {
        key: 'slack_channel',
        label: 'Channel Name',
        type: 'text',
        placeholder: '#stratum-alerts',
        helpText: 'Target Slack channel for notifications (optional — webhook URL includes default channel).',
        whereToFind: 'The channel name you selected when creating the webhook.',
        required: false,
      },
    ],
    notes: [
      'Notifications include: Trust Gate decisions (PASS/HOLD/BLOCK), anomaly alerts, signal health changes, daily/weekly summaries.',
      'Webhook URL is stored encrypted in the database.',
      'You can test the connection from the Settings page.',
    ],
  },

  // ── Payments ────────────────────────────────────────────────────────────
  {
    id: 'stripe',
    name: 'Stripe',
    category: 'payments',
    color: 'from-violet-500 to-indigo-700',
    icon: '$',
    subtitle: 'Payments & Subscriptions',
    description: 'Manage subscriptions, process payments, and receive webhook events from Stripe.',
    docsUrl: 'https://stripe.com/docs/api',
    authMethod: 'api-key',
    apiVersion: '2024-12-18.acacia',
    credentials: [
      {
        key: 'stripe_secret_key',
        label: 'Secret API Key',
        type: 'password',
        placeholder: 'sk_live_xxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Stripe Secret API Key for server-side operations.',
        whereToFind: 'Stripe Dashboard → Developers → API Keys → Secret Key',
        required: true,
      },
      {
        key: 'stripe_publishable_key',
        label: 'Publishable Key',
        type: 'text',
        placeholder: 'pk_live_xxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Stripe Publishable Key for client-side (frontend) use.',
        whereToFind: 'Stripe Dashboard → Developers → API Keys → Publishable Key',
        required: true,
      },
      {
        key: 'stripe_webhook_secret',
        label: 'Webhook Signing Secret',
        type: 'password',
        placeholder: 'whsec_xxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Secret for verifying webhook signatures from Stripe.',
        whereToFind: 'Stripe Dashboard → Developers → Webhooks → Your Endpoint → Signing Secret',
        required: true,
      },
      {
        key: 'stripe_starter_price_id',
        label: 'Starter Tier Price ID',
        type: 'text',
        placeholder: 'price_xxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Stripe Price ID for the Starter subscription plan.',
        whereToFind: 'Stripe Dashboard → Products → Starter Plan → Pricing → Price ID',
        required: false,
      },
      {
        key: 'stripe_professional_price_id',
        label: 'Professional Tier Price ID',
        type: 'text',
        placeholder: 'price_xxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Stripe Price ID for the Professional subscription plan.',
        whereToFind: 'Stripe Dashboard → Products → Professional Plan → Pricing → Price ID',
        required: false,
      },
      {
        key: 'stripe_enterprise_price_id',
        label: 'Enterprise Tier Price ID',
        type: 'text',
        placeholder: 'price_xxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Stripe Price ID for the Enterprise subscription plan.',
        whereToFind: 'Stripe Dashboard → Products → Enterprise Plan → Pricing → Price ID',
        required: false,
      },
    ],
    notes: [
      'Webhook endpoint: /api/v1/stripe_webhook',
      'Events handled: customer.subscription.updated, customer.subscription.deleted, invoice.payment_succeeded',
      'Use test keys (sk_test_, pk_test_) for development, live keys for production.',
      'Webhook signing secret is required for signature verification.',
    ],
  },

  // ── Analytics ───────────────────────────────────────────────────────────
  {
    id: 'google-analytics',
    name: 'Google Analytics',
    category: 'analytics',
    color: 'from-orange-500 to-yellow-600',
    icon: 'GA',
    subtitle: 'GA4 Web Analytics',
    description: 'Track website traffic, user behavior, and conversion events with Google Analytics 4.',
    docsUrl: 'https://developers.google.com/analytics/devguides/reporting/data/v1',
    authMethod: 'oauth',
    credentials: [
      {
        key: 'ga_measurement_id',
        label: 'Measurement ID',
        type: 'text',
        placeholder: 'G-XXXXXXXXXX',
        helpText: 'GA4 Measurement ID (starts with G-).',
        whereToFind: 'Google Analytics → Admin → Data Streams → Your Stream → Measurement ID',
        required: true,
      },
      {
        key: 'ga_property_id',
        label: 'Property ID',
        type: 'text',
        placeholder: '123456789',
        helpText: 'GA4 Property ID for API access.',
        whereToFind: 'Google Analytics → Admin → Property Settings → Property ID',
        required: true,
      },
      {
        key: 'ga_api_secret',
        label: 'Measurement Protocol API Secret',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxx',
        helpText: 'Secret for sending events via Measurement Protocol.',
        whereToFind: 'Google Analytics → Admin → Data Streams → Your Stream → Measurement Protocol → Create API Secret',
        required: false,
      },
    ],
    notes: [
      'Uses Google OAuth for authentication — same credentials as Google Ads if using the same project.',
      'Measurement Protocol allows server-side event tracking.',
    ],
  },
  {
    id: 'google-tag-manager',
    name: 'Google Tag Manager',
    category: 'analytics',
    color: 'from-blue-500 to-blue-700',
    icon: 'GT',
    subtitle: 'Tag Management',
    description: 'Manage tracking pixels, conversion tags, and marketing scripts through GTM.',
    docsUrl: 'https://developers.google.com/tag-platform/tag-manager/api/v2',
    authMethod: 'api-key',
    credentials: [
      {
        key: 'gtm_container_id',
        label: 'Container ID',
        type: 'text',
        placeholder: 'GTM-XXXXXXX',
        helpText: 'GTM Container ID (starts with GTM-).',
        whereToFind: 'Google Tag Manager → Admin → Container Settings → Container ID',
        required: true,
      },
      {
        key: 'gtm_account_id',
        label: 'Account ID',
        type: 'text',
        placeholder: '123456789',
        helpText: 'GTM Account ID for API access.',
        whereToFind: 'Google Tag Manager → Admin → Account Settings → Account ID',
        required: false,
      },
    ],
    notes: [
      'Install the GTM snippet on your website to use with Stratum.',
      'Server-side GTM containers can be used for enhanced data control.',
    ],
  },

  // ── Commerce ────────────────────────────────────────────────────────────
  {
    id: 'shopify',
    name: 'Shopify',
    category: 'commerce',
    color: 'from-green-500 to-lime-600',
    icon: 'SH',
    subtitle: 'E-commerce Platform',
    description: 'Sync orders, products, and customer data from your Shopify store.',
    docsUrl: 'https://shopify.dev/docs/api',
    authMethod: 'api-key',
    credentials: [
      {
        key: 'shopify_store_url',
        label: 'Store URL',
        type: 'text',
        placeholder: 'your-store.myshopify.com',
        helpText: 'Your Shopify store domain (without https://).',
        whereToFind: 'Shopify Admin → Settings → Domains → your-store.myshopify.com',
        required: true,
      },
      {
        key: 'shopify_access_token',
        label: 'Admin API Access Token',
        type: 'password',
        placeholder: 'shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'Access token from a custom Shopify app.',
        whereToFind: 'Shopify Admin → Settings → Apps and Sales Channels → Develop Apps → Your App → API Credentials → Admin API Access Token',
        required: true,
      },
      {
        key: 'shopify_api_key',
        label: 'API Key',
        type: 'text',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'API key from your custom Shopify app.',
        whereToFind: 'Shopify Admin → Settings → Apps and Sales Channels → Develop Apps → Your App → API Credentials → API Key',
        required: false,
      },
      {
        key: 'shopify_api_secret',
        label: 'API Secret Key',
        type: 'password',
        placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
        helpText: 'API Secret for webhook signature verification.',
        whereToFind: 'Shopify Admin → Settings → Apps and Sales Channels → Develop Apps → Your App → API Credentials → API Secret Key',
        required: false,
      },
    ],
    notes: [
      'Create a custom app in Shopify Admin for API access.',
      'Required scopes: read_orders, read_products, read_customers.',
      'Webhook signature verification uses the API Secret Key.',
    ],
  },
]

// ─── Category Labels ──────────────────────────────────────────────────────

const categoryLabels: Record<string, string> = {
  'ad-platform': 'Ad Platforms',
  crm: 'CRM & Sales',
  messaging: 'Messaging & Notifications',
  analytics: 'Analytics & Tracking',
  payments: 'Payments',
  commerce: 'E-Commerce',
}

const categoryOrder = ['ad-platform', 'crm', 'messaging', 'payments', 'analytics', 'commerce']

// ─── Modal Component ──────────────────────────────────────────────────────

interface PlatformSetupModalProps {
  platform: PlatformCredentialConfig | null
  onClose: () => void
  onConnect?: (platformId: string) => void
}

export function PlatformSetupModal({ platform, onClose, onConnect }: PlatformSetupModalProps) {
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set())
  const [activeTab, setActiveTab] = useState<'credentials' | 'info'>('credentials')
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
    }
  }, [])

  if (!platform) return null

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text)
    setCopiedField(field)
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    timeoutRef.current = setTimeout(() => setCopiedField(null), 2000)
  }

  const toggleVisibility = (field: string) => {
    setVisibleFields((prev) => {
      const next = new Set(prev)
      if (next.has(field)) next.delete(field)
      else next.add(field)
      return next
    })
  }

  const requiredFields = platform.credentials.filter((c) => c.required)
  const optionalFields = platform.credentials.filter((c) => !c.required)

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-start justify-center z-50 p-4 overflow-y-auto" onClick={onClose}>
      <div
        className="w-full max-w-2xl my-8 rounded-2xl border border-foreground/10 bg-[#0d0d12] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={cn('relative rounded-t-2xl p-6 bg-gradient-to-r', platform.color)}>
          <button
            onClick={onClose}
            aria-label="Close"
            className="absolute top-4 right-4 p-1.5 rounded-lg bg-black/20 hover:bg-black/40 transition-colors text-white"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-4">
            <div className="h-14 w-14 rounded-xl bg-foreground/20 backdrop-blur-sm flex items-center justify-center">
              <span className="text-xl font-bold text-white">{platform.icon}</span>
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{platform.name}</h2>
              <p className="text-sm text-foreground/80">{platform.subtitle}</p>
            </div>
          </div>
          <p className="mt-3 text-sm text-foreground/70">{platform.description}</p>

          {/* Auth badge + API version */}
          <div className="flex items-center gap-2 mt-3">
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-foreground/15 text-white text-xs font-medium">
              <ShieldCheckIcon className="h-3.5 w-3.5" />
              {platform.authMethod === 'oauth' ? 'OAuth 2.0' : platform.authMethod === 'oauth+api-key' ? 'OAuth 2.0 + API Key' : platform.authMethod === 'webhook' ? 'Webhook' : 'API Key'}
            </span>
            {platform.apiVersion && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-foreground/15 text-white text-xs font-medium">
                API {platform.apiVersion}
              </span>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-foreground/10">
          <button
            onClick={() => setActiveTab('credentials')}
            className={cn(
              'flex-1 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === 'credentials'
                ? 'text-white border-b-2 border-primary'
                : 'text-foreground/50 hover:text-foreground/80'
            )}
          >
            <KeyIcon className="h-4 w-4 inline mr-2" />
            Required Credentials
          </button>
          <button
            onClick={() => setActiveTab('info')}
            className={cn(
              'flex-1 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === 'info'
                ? 'text-white border-b-2 border-primary'
                : 'text-foreground/50 hover:text-foreground/80'
            )}
          >
            <InformationCircleIcon className="h-4 w-4 inline mr-2" />
            Setup Info
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'credentials' ? (
            <div className="space-y-6">
              {/* Required Credentials */}
              <div>
                <h3 className="text-sm font-semibold text-foreground/90 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-400" />
                  Required ({requiredFields.length})
                </h3>
                <div className="space-y-3">
                  {requiredFields.map((field) => (
                    <CredentialFieldCard
                      key={field.key}
                      field={field}
                      isVisible={visibleFields.has(field.key)}
                      isCopied={copiedField === field.key}
                      onToggleVisibility={() => toggleVisibility(field.key)}
                      onCopy={() => copyToClipboard(field.placeholder, field.key)}
                    />
                  ))}
                </div>
              </div>

              {/* Optional Credentials */}
              {optionalFields.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground/90 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-gray-400" />
                    Optional ({optionalFields.length})
                  </h3>
                  <div className="space-y-3">
                    {optionalFields.map((field) => (
                      <CredentialFieldCard
                        key={field.key}
                        field={field}
                        isVisible={visibleFields.has(field.key)}
                        isCopied={copiedField === field.key}
                        onToggleVisibility={() => toggleVisibility(field.key)}
                        onCopy={() => copyToClipboard(field.placeholder, field.key)}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {/* OAuth Scopes */}
              {platform.oauthScopes && platform.oauthScopes.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground/90 uppercase tracking-wider mb-3">OAuth Scopes Required</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {platform.oauthScopes.map((scope) => (
                      <span
                        key={scope}
                        className="inline-block px-2.5 py-1 text-xs rounded-md bg-foreground/5 text-foreground/70 border border-foreground/10 font-mono"
                      >
                        {scope}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* CAPI Events */}
              {platform.capiEvents && platform.capiEvents.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground/90 uppercase tracking-wider mb-3">Supported Events</h3>
                  <div className="flex flex-wrap gap-2">
                    {platform.capiEvents.map((event) => (
                      <span
                        key={event}
                        className="inline-block px-3 py-1.5 text-xs rounded-full bg-emerald-950/40 text-emerald-400 border border-emerald-800/50"
                      >
                        {event}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Audience Format */}
              {platform.audienceFormat && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground/90 uppercase tracking-wider mb-3">Audience Sync Format</h3>
                  <p className="text-sm text-foreground/60">{platform.audienceFormat}</p>
                </div>
              )}

              {/* Notes */}
              {platform.notes && platform.notes.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-foreground/90 uppercase tracking-wider mb-3">Important Notes</h3>
                  <ul className="space-y-2">
                    {platform.notes.map((note, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-foreground/60">
                        <span className="text-primary mt-0.5 shrink-0">&#8226;</span>
                        <span>{note}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Documentation Link */}
              <a
                href={platform.docsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm text-primary hover:text-primary/80 transition-colors"
              >
                <ArrowTopRightOnSquareIcon className="h-4 w-4" />
                View Official Documentation
              </a>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-foreground/10">
          <a
            href={platform.docsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-foreground/50 hover:text-foreground/80 transition-colors flex items-center gap-1"
          >
            <ArrowTopRightOnSquareIcon className="h-3.5 w-3.5" />
            Docs
          </a>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-foreground/10 hover:bg-foreground/5 text-sm text-foreground/70 transition-colors"
            >
              Close
            </button>
            {onConnect && (
              <button
                onClick={() => onConnect(platform.id)}
                className="px-6 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-sm font-medium transition-colors"
              >
                Connect {platform.name}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Credential Field Card ────────────────────────────────────────────────

function CredentialFieldCard({
  field,
  isVisible,
  isCopied,
  onToggleVisibility,
  onCopy,
}: {
  field: CredentialField
  isVisible: boolean
  isCopied: boolean
  onToggleVisibility: () => void
  onCopy: () => void
}) {
  const [showWhereToFind, setShowWhereToFind] = useState(false)

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between mb-1.5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground/90">{field.label}</span>
            {field.required && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-medium">REQUIRED</span>
            )}
          </div>
          <p className="text-xs text-foreground/40 mt-0.5">{field.helpText}</p>
        </div>
        <div className="flex items-center gap-1">
          {field.type === 'password' && (
            <button
              onClick={onToggleVisibility}
              className="p-1.5 rounded-lg hover:bg-foreground/5 text-foreground/40 hover:text-foreground/70 transition-colors"
              title={isVisible ? 'Hide' : 'Show'}
            >
              {isVisible ? <EyeSlashIcon className="h-4 w-4" /> : <EyeIcon className="h-4 w-4" />}
            </button>
          )}
          <button
            onClick={onCopy}
            className="p-1.5 rounded-lg hover:bg-foreground/5 text-foreground/40 hover:text-foreground/70 transition-colors"
            title="Copy placeholder"
          >
            {isCopied ? <CheckIcon className="h-4 w-4 text-emerald-400" /> : <ClipboardDocumentIcon className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Field display */}
      {field.type === 'select' && field.options ? (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {field.options.map((opt) => (
            <span
              key={opt.value}
              className="inline-block px-2.5 py-1 text-xs rounded-md bg-foreground/5 text-foreground/60 border border-foreground/8"
            >
              {opt.label}
            </span>
          ))}
        </div>
      ) : (
        <div className="mt-2 px-3 py-2 rounded-lg bg-black/30 border border-foreground/5">
          <code className="text-xs text-foreground/50 font-mono">
            {field.type === 'password' && !isVisible
              ? field.placeholder.replace(/./g, '•')
              : field.placeholder}
          </code>
        </div>
      )}

      {/* Where to find */}
      <button
        onClick={() => setShowWhereToFind(!showWhereToFind)}
        className="mt-2 text-[11px] text-primary/70 hover:text-primary transition-colors flex items-center gap-1"
      >
        <InformationCircleIcon className="h-3.5 w-3.5" />
        {showWhereToFind ? 'Hide' : 'Where to find this'}
      </button>
      {showWhereToFind && (
        <div className="mt-1.5 px-3 py-2 rounded-lg bg-primary/5 border border-primary/10">
          <p className="text-xs text-primary/80">{field.whereToFind}</p>
        </div>
      )}
    </div>
  )
}

// ─── Exports ──────────────────────────────────────────────────────────────

export { categoryLabels, categoryOrder }

export function getPlatformsByCategory() {
  const grouped: Record<string, PlatformCredentialConfig[]> = {}
  for (const cat of categoryOrder) {
    grouped[cat] = platformCredentials.filter((p) => p.category === cat)
  }
  return grouped
}

export function getPlatformById(id: string) {
  return platformCredentials.find((p) => p.id === id) ?? null
}
