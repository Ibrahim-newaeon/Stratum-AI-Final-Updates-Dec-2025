import type { DocArticle } from '../types';

export const integrationsArticles: DocArticle[] = [
  {
    slug: 'integrations/meta',
    category: 'Integrations',
    title: 'Meta Ads',
    description:
      'Connect Meta Marketing API to read performance, control campaigns, and raise match quality with CAPI and Custom Audiences.',
    readTime: '6 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'The Meta integration connects your Business and ad accounts to Stratum through the Meta Marketing API. Once connected, signal collectors pull campaign performance and event deliveries, a per-platform health calculation feeds Signal Health, and your trust-gated automations can manage budgets, bids, and campaign status.',
      },
      { type: 'heading', text: 'What you can do' },
      {
        type: 'list',
        items: [
          'Read campaign, ad set, and ad performance across your connected ad accounts.',
          'Let automations adjust budgets, bids, and pause or enable entities — always behind the trust gate.',
          'Send server-side conversions through the Conversions API (CAPI) to raise Event Match Quality.',
          'Activate CDP segments as Meta Custom Audiences for targeting and suppression.',
        ],
      },
      { type: 'heading', text: 'Connect via OAuth' },
      {
        type: 'list',
        ordered: true,
        items: [
          'Open Integrations and choose Meta.',
          'Complete Meta’s consent flow — Stratum never sees your password and stores only an encrypted refresh token.',
          'Select the Business and ad accounts you want Stratum to read and manage.',
          'Wait a few minutes for collectors to begin pulling metrics and events.',
        ],
      },
      {
        type: 'paragraph',
        text: 'Stratum requests the minimum scopes needed to read ads performance and manage the entities your automations control. Meta access tokens are short-lived; Stratum refreshes them automatically from the stored encrypted token, so you do not have to reconnect routinely.',
      },
      { type: 'heading', text: 'Conversions API and Custom Audiences' },
      {
        type: 'paragraph',
        text: 'CAPI sends conversion events server-side, bypassing browser and cookie limitations that suppress client-side pixels. Combined with the web tag, it keeps Event Match Quality high and signal health resilient. CDP segments push to Meta Custom Audiences for activation without ever exposing raw identifiers.',
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'Least scope, hashed PII',
        text: 'Stratum requests only the scopes it needs, and email and phone identifiers are lower-cased, trimmed, and SHA-256 hashed before they are sent to Meta for matching. Raw PII is never required for CAPI or audience sync.',
      },
      { type: 'heading', text: 'Troubleshooting' },
      {
        type: 'paragraph',
        text: 'If API health drops or actions start failing, the most common cause is a token that lost permissions on Meta’s side. Reconnect from Integrations to re-run consent. Revoking a connection deletes the stored token immediately, so a clean reconnect is always safe.',
      },
    ],
  },
  {
    slug: 'integrations/google',
    category: 'Integrations',
    title: 'Google Ads',
    description:
      'Connect Google Ads API to read Search, Display, and YouTube performance, import conversions, and sync Customer Match.',
    readTime: '6 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'The Google integration connects your Google Ads accounts through the Google Ads API. Stratum reads performance across Search, Display, and YouTube, lets automations manage your campaigns behind the trust gate, and activates CDP segments as Customer Match audiences.',
      },
      { type: 'heading', text: 'What you can do' },
      {
        type: 'list',
        items: [
          'Read campaign performance across Search, Display, and YouTube inventory.',
          'Let automations adjust budgets, bidding strategy, and campaign status under trust-gate control.',
          'Import server-side conversions so Google optimizes toward verified outcomes.',
          'Activate CDP segments as Google Customer Match audiences.',
        ],
      },
      { type: 'heading', text: 'Connect via OAuth' },
      {
        type: 'list',
        ordered: true,
        items: [
          'Open Integrations and choose Google.',
          'Complete Google’s OAuth consent flow — Stratum stores only an encrypted refresh token, never your password.',
          'Select the Google Ads accounts Stratum should read and manage.',
        ],
      },
      {
        type: 'paragraph',
        text: 'The Google Ads API is accessed through a developer token alongside your OAuth grant. Stratum manages the developer token centrally, so you only complete the OAuth consent — there is nothing to paste. We request the minimum scopes needed to read performance data and manage the entities automations control.',
      },
      { type: 'heading', text: 'Conversion import and Customer Match' },
      {
        type: 'paragraph',
        text: 'Conversion import sends server-side conversions into Google Ads so bidding optimizes against outcomes that survive browser restrictions — this lifts Event Match Quality the same way CAPI does on other platforms. Customer Match takes CDP segments and matches them against Google’s user base for targeting and exclusions.',
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'Hashed identifiers only',
        text: 'Customer Match and conversion import use SHA-256 hashed emails and phone numbers. Identifiers are normalized and hashed before they leave your environment, so raw PII is never shared with Google.',
      },
      { type: 'heading', text: 'Troubleshooting' },
      {
        type: 'paragraph',
        text: 'If conversions stop importing or accounts disappear from the picker, check that the connected Google user still has access to the manager and child accounts. Reconnect from Integrations to refresh consent; the previous token is deleted the moment you revoke.',
      },
    ],
  },
  {
    slug: 'integrations/tiktok',
    category: 'Integrations',
    title: 'TikTok Ads',
    description:
      'Connect TikTok Ads API to read performance, send Events API conversions, and sync DMP Custom Audiences.',
    readTime: '5 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'The TikTok integration connects your advertiser accounts through the TikTok Ads API. Stratum reads campaign performance, manages entities behind the trust gate, sends server-side conversions through the Events API, and activates CDP segments as TikTok Custom Audiences.',
      },
      { type: 'heading', text: 'What you can do' },
      {
        type: 'list',
        items: [
          'Read campaign, ad group, and ad performance from connected advertiser accounts.',
          'Let automations adjust budgets, bids, and status under trust-gate control.',
          'Send conversions server-side via the TikTok Events API to raise Event Match Quality.',
          'Activate CDP segments as TikTok DMP Custom Audiences.',
        ],
      },
      { type: 'heading', text: 'Connect via OAuth' },
      {
        type: 'list',
        ordered: true,
        items: [
          'Open Integrations and choose TikTok.',
          'Complete TikTok’s OAuth consent flow — Stratum stores only an encrypted refresh token.',
          'Select the advertiser accounts Stratum should read and manage.',
        ],
      },
      {
        type: 'paragraph',
        text: 'As with every platform, Stratum requests the minimum scopes needed to read performance data and manage the entities your automations control. The connection is registered in the integration registry, and collectors begin pulling metrics and events within a few minutes.',
      },
      { type: 'heading', text: 'Events API and Custom Audiences' },
      {
        type: 'paragraph',
        text: 'The TikTok Events API delivers conversions server-side, bypassing browser limits to keep match quality and signal health strong. DMP Custom Audiences let you push CDP segments to TikTok using SHA-256 hashed identifiers — raw PII is never sent.',
      },
      { type: 'heading', text: 'Troubleshooting' },
      {
        type: 'paragraph',
        text: 'If events stop matching or actions fail, confirm the connected user still has advertiser access and reconnect from Integrations. Revoking deletes the stored token immediately, so reconnecting always starts from a clean grant.',
      },
    ],
  },
  {
    slug: 'integrations/crm',
    category: 'Integrations',
    title: 'CRM Systems',
    description:
      'Sync HubSpot and Zoho contacts and companies into the CDP, and wire Slack and WhatsApp for notifications.',
    readTime: '5 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Beyond ad platforms, Stratum integrates with CRM and messaging systems. HubSpot and Zoho sync contacts and companies into the Customer Data Platform for enrichment and segmentation, while Slack and WhatsApp Business carry notifications out to your team and customers.',
      },
      { type: 'heading', text: 'HubSpot and Zoho' },
      {
        type: 'paragraph',
        text: 'Connecting a CRM lets Stratum mirror your contact and company records into the CDP, where they merge with behavioral events to build unified profiles. Those profiles power computed traits, lifecycle stages, and the segments you later activate as ad-platform audiences.',
      },
      {
        type: 'list',
        items: [
          'Contacts sync as CDP profiles, joined to existing identities by email.',
          'Companies sync as account records for B2B segmentation.',
          'Sync runs continuously after the initial backfill, keeping profiles current without manual exports.',
        ],
      },
      { type: 'heading', text: 'Connect via OAuth' },
      {
        type: 'list',
        ordered: true,
        items: [
          'Open Integrations and choose HubSpot or Zoho.',
          'Complete the provider’s OAuth consent flow — Stratum stores only an encrypted refresh token.',
          'Pick the objects to sync; the initial backfill begins immediately.',
        ],
      },
      { type: 'heading', text: 'Slack and WhatsApp' },
      {
        type: 'paragraph',
        text: 'Slack delivers alerts and scheduled reports to a channel of your choice — trust-gate holds, signal-health drops, and autopilot decisions all surface where your team already works. WhatsApp Business adds a customer messaging channel for transactional and lifecycle notifications.',
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'Least scope, hashed PII',
        text: 'CRM connections request only the scopes needed to read and sync the selected objects. When CRM profiles feed audience activation, their email and phone identifiers are SHA-256 hashed before any platform sync — raw PII never leaves the CDP unhashed.',
      },
      { type: 'heading', text: 'Troubleshooting' },
      {
        type: 'paragraph',
        text: 'If sync stalls, the connected CRM user’s permissions are the first thing to check. Reconnect from Integrations to refresh consent; revoking deletes the stored token immediately and stops all further syncing.',
      },
    ],
  },
];
