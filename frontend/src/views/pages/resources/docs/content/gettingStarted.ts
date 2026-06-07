import type { DocArticle } from '../types';

export const gettingStartedArticles: DocArticle[] = [
  {
    slug: 'quickstart',
    category: 'Getting Started',
    title: 'Quick Start Guide',
    description:
      'Go from sign-up to your first trust-gated automation in about ten minutes.',
    readTime: '5 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Stratum AI is a revenue operating system with trust-gated autopilot: automations only execute when signal health passes your safety thresholds. This guide walks you through the fastest path to a working setup — connect a platform, watch signal health populate, and arm your first automation.',
      },
      {
        type: 'callout',
        tone: 'info',
        title: 'Before you begin',
        text: 'You need an active workspace and admin access to at least one ad platform (Meta, Google, TikTok, or Snapchat). A 14-day trial is enough to complete every step here.',
      },
      { type: 'heading', text: 'Step 1 — Create your workspace' },
      {
        type: 'paragraph',
        text: 'Each workspace is an isolated tenant with its own users, integrations, and analytics. After verifying your email you will land in an empty Overview — the action-first dashboard that sorts everything by what needs your attention.',
      },
      { type: 'heading', text: 'Step 2 — Connect a platform' },
      {
        type: 'list',
        ordered: true,
        items: [
          'Open Integrations and choose a provider.',
          'Complete the OAuth consent flow — Stratum never sees your password; we store only an encrypted refresh token.',
          'Select the ad accounts you want Stratum to read.',
        ],
      },
      {
        type: 'paragraph',
        text: 'Within a few minutes the signal collectors begin pulling metrics, events, and webhook deliveries from the connected account.',
      },
      { type: 'heading', text: 'Step 3 — Watch signal health populate' },
      {
        type: 'paragraph',
        text: 'Signal Health is a composite 0–100 score of how reliable your data is right now. It blends Event Match Quality, API health, event loss, platform stability, and data quality. Give it 15–30 minutes after connecting to settle.',
      },
      {
        type: 'callout',
        tone: 'success',
        text: 'A score of 70 or above is healthy — green — and autopilot is eligible to run. 40–69 is degraded and holds; below 40 blocks and requires manual review.',
      },
      { type: 'heading', text: 'Step 4 — Arm your first automation' },
      {
        type: 'paragraph',
        text: 'Create a simple budget-pacing or bid automation and leave it in Advisory mode at first. Advisory surfaces the action Stratum would take without executing it, so you can build trust in the recommendations before handing over control.',
      },
      { type: 'heading', text: 'Next steps' },
      {
        type: 'list',
        items: [
          'Read Installation to wire the SDK or CAPI into your site.',
          'Read Authentication to issue an API key for programmatic access.',
          'Follow First Campaign for an end-to-end automation walkthrough.',
        ],
      },
    ],
  },
  {
    slug: 'installation',
    category: 'Getting Started',
    title: 'Installation',
    description:
      'Add the Stratum tag and server-side events so the platform can measure and act on your traffic.',
    readTime: '6 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Stratum measures two complementary streams: client-side events from the browser tag and server-side events from the Conversions API (CAPI). Using both maximizes Event Match Quality and keeps signal health resilient to browser limitations.',
      },
      { type: 'heading', text: 'Install the web tag' },
      {
        type: 'paragraph',
        text: 'Drop the snippet into the <head> of every page. It loads asynchronously and will not block rendering.',
      },
      {
        type: 'code',
        language: 'html',
        code: '<script\n  async\n  src="https://cdn.stratumai.app/s.js"\n  data-workspace="YOUR_WORKSPACE_ID"\n></script>',
      },
      {
        type: 'paragraph',
        text: 'Track a conversion by calling the global helper once the tag has loaded:',
      },
      {
        type: 'code',
        language: 'javascript',
        code: "stratum('track', 'Purchase', {\n  value: 129.0,\n  currency: 'USD',\n  order_id: 'A1B2C3',\n});",
      },
      { type: 'heading', text: 'Send server-side events (recommended)' },
      {
        type: 'paragraph',
        text: 'Server events are not affected by ad blockers or cookie restrictions, so they raise match quality. POST them to the events endpoint with your secret API key.',
      },
      {
        type: 'code',
        language: 'bash',
        code: 'curl -X POST https://api.stratumai.app/api/v1/events \\\n  -H "Authorization: Bearer $STRATUM_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d \'{\n    "name": "Purchase",\n    "value": 129.0,\n    "currency": "USD",\n    "user": { "email": "h@shed.example" }\n  }\'',
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'Hash PII before it leaves your servers',
        text: 'Email and phone identifiers should be lower-cased, trimmed, and SHA-256 hashed before being sent. Stratum never requires raw PII for matching.',
      },
      { type: 'heading', text: 'Verify the install' },
      {
        type: 'list',
        ordered: true,
        items: [
          'Open Integrations → Signal Health and confirm events are arriving.',
          'Trigger a test conversion and watch it appear in the live event stream within seconds.',
          'Check that Event Match Quality climbs as identifiers are matched.',
        ],
      },
    ],
  },
  {
    slug: 'auth',
    category: 'Getting Started',
    title: 'Authentication',
    description:
      'How API keys, OAuth, JWT sessions, and MFA work together to secure access to Stratum.',
    readTime: '5 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Stratum supports three authentication paths: interactive sessions for the dashboard, API keys for server-to-server calls, and OAuth for connecting external ad platforms. All three are scoped to a single tenant.',
      },
      { type: 'heading', text: 'API keys' },
      {
        type: 'paragraph',
        text: 'Generate a key under Settings → API. Keys are shown once at creation, carry workspace-scoped permissions, and should be stored as a secret in your backend — never in frontend code or a committed file.',
      },
      {
        type: 'code',
        language: 'bash',
        code: 'curl https://api.stratumai.app/api/v1/signals \\\n  -H "Authorization: Bearer $STRATUM_API_KEY"',
      },
      { type: 'heading', text: 'Dashboard sessions and MFA' },
      {
        type: 'paragraph',
        text: 'Interactive logins issue a short-lived JWT. The token carries your user and tenant identity and permissions, but never raw PII. We strongly recommend enabling TOTP-based multi-factor authentication for every user with automation privileges.',
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'JWTs expire quickly and are refreshed transparently in the dashboard. For programmatic access, prefer an API key over scripting a login.',
      },
      { type: 'heading', text: 'OAuth for platform connections' },
      {
        type: 'paragraph',
        text: 'When you connect Meta, Google, TikTok, or Snapchat, Stratum runs the provider OAuth flow and stores only an encrypted refresh token. We request the minimum scopes needed to read performance data and manage the entities your automations control.',
      },
      {
        type: 'list',
        items: [
          'Revoke a connection any time from Integrations — the stored token is deleted immediately.',
          'Rotating an API key invalidates the old one on the next request.',
          'All authentication events are written to the tenant audit log.',
        ],
      },
    ],
  },
  {
    slug: 'first-campaign',
    category: 'Getting Started',
    title: 'Your First Campaign',
    description:
      'Build, arm, and graduate a trust-gated automation from advisory to autopilot.',
    readTime: '8 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'This walkthrough takes a real optimization — shifting budget toward your best-performing campaigns — and runs it through the trust gate so it only acts when your data is reliable.',
      },
      { type: 'heading', text: '1. Define the objective' },
      {
        type: 'paragraph',
        text: 'Pick a measurable goal such as maintaining ROAS above a target while spending the day’s budget evenly. Stratum frames every automation around a metric it can verify from signal data.',
      },
      { type: 'heading', text: '2. Choose an enforcement mode' },
      {
        type: 'list',
        items: [
          'Advisory — recommends the action, executes nothing. Start here.',
          'Soft-Block — executes when healthy, holds and alerts when degraded.',
          'Hard-Block — executes only when healthy; anything below threshold requires manual approval.',
        ],
      },
      {
        type: 'callout',
        tone: 'success',
        title: 'Build trust before you delegate',
        text: 'Run in Advisory for a few days and compare Stratum’s recommendations against your own decisions. Graduate to Soft-Block once the recommendations consistently match your intent.',
      },
      { type: 'heading', text: '3. Set the trust gate' },
      {
        type: 'paragraph',
        text: 'The trust gate checks signal health before each execution. With the default healthy threshold of 70, the automation runs normally when green, holds when degraded, and blocks when unhealthy — so a tracking outage can never trigger a bad budget move.',
      },
      { type: 'heading', text: '4. Review the audit trail' },
      {
        type: 'paragraph',
        text: 'Every gate decision and every executed action is logged with the signal health snapshot that justified it. Open the automation’s history to see exactly why it ran, held, or blocked.',
      },
      { type: 'heading', text: '5. Graduate to autopilot' },
      {
        type: 'paragraph',
        text: 'When you are confident, switch to Soft-Block or Hard-Block. The automation now runs on its own while the trust gate keeps it honest — acting on healthy data and standing down the moment your signals degrade.',
      },
    ],
  },
];
