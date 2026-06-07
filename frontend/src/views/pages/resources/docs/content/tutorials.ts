import type { DocArticle } from '../types';

export const tutorialsArticles: DocArticle[] = [
  {
    slug: 'tutorials/videos',
    category: 'Tutorials',
    title: 'Video Tutorials',
    description:
      'A short catalog of guided video walkthroughs for the core Stratum workflows.',
    readTime: '3 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'These walkthroughs cover the workflows most people reach for in their first week. Each is task-focused and recorded against the live product, so the screens match what you see. Pick the one closest to what you are trying to do.',
      },
      { type: 'heading', text: 'Getting connected' },
      {
        type: 'list',
        items: [
          'Connect Meta in 3 minutes — run the OAuth consent flow, pick ad accounts, and confirm the signal collectors start pulling data. (3:12)',
          'Install the web tag and CAPI — add the snippet, send your first server event, and watch Event Match Quality climb. (4:40)',
        ],
      },
      { type: 'heading', text: 'Trust and automation' },
      {
        type: 'list',
        items: [
          'Read Signal Health — what the 0–100 score means and how EMQ, API health, event loss, platform stability, and data quality roll up. (3:55)',
          'Build your first Trust Gate — set a healthy threshold, choose an enforcement mode, and arm an automation in Advisory. (6:20)',
          'Graduate from Advisory to autopilot — review the audit trail and switch a proven automation to Soft-Block. (4:05)',
        ],
      },
      { type: 'heading', text: 'CDP and audiences' },
      {
        type: 'list',
        items: [
          'Create a predictive segment — define a churn-risk audience from RFM and lifecycle traits. (5:30)',
          'Sync an audience to a platform — push a segment to Meta or Google with SHA-256 hashed identifiers. (3:48)',
        ],
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'Each video has a matching written guide elsewhere in these docs. If you prefer to read, follow Quick Start, First Campaign, and the CDP articles for the same material at your own pace.',
      },
    ],
  },
  {
    slug: 'tutorials/use-cases',
    category: 'Tutorials',
    title: 'Use Cases',
    description:
      'Four end-to-end scenarios showing how trust-gated autopilot and the CDP solve real revenue problems.',
    readTime: '8 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'The patterns below are the ones teams reach for most. Each gives you the goal, the Stratum setup, and the outcome you should expect. They assume at least one connected platform and signal health that has settled.',
      },
      { type: 'heading', text: 'Protect ROAS during a tracking outage' },
      {
        type: 'paragraph',
        text: 'Goal: stop automations from making bad budget decisions when your data goes dark — a pixel break, a CAPI gateway error, or a platform API incident.',
      },
      {
        type: 'list',
        ordered: true,
        items: [
          'Run your budget and bid automations in Soft-Block or Hard-Block enforcement.',
          'Leave the trust gate at the default healthy threshold of 70.',
          'When event loss spikes or API health drops, signal health falls into the degraded band (40–69) and the gate returns HOLD instead of executing.',
        ],
      },
      {
        type: 'paragraph',
        text: 'Outcome: the moment your signals degrade, autopilot stands down and alerts you rather than scaling spend on numbers it cannot trust. When health recovers above 70 the gate returns PASS and execution resumes automatically.',
      },
      {
        type: 'callout',
        tone: 'success',
        title: 'Why this works',
        text: 'The gate evaluates signal health before every execution, so a transient outage can never silently corrupt a budget move. The held action and its health snapshot are written to the audit log.',
      },
      { type: 'heading', text: 'Scale spend on a healthy winner' },
      {
        type: 'paragraph',
        text: 'Goal: push more budget toward a campaign that is beating its ROAS target, but only while the underlying data is reliable.',
      },
      {
        type: 'list',
        ordered: true,
        items: [
          'Create a pacing automation that increases budget when ROAS stays above your target across the measurement window.',
          'Start in Advisory and compare the recommendations to your own calls for a few days.',
          'Graduate to Soft-Block once the recommendations consistently match your intent.',
        ],
      },
      {
        type: 'paragraph',
        text: 'Outcome: Stratum compounds spend into the winner during healthy periods and pauses scaling whenever signal health dips — capturing upside without overcommitting on noisy data.',
      },
      { type: 'heading', text: 'Win back At-Risk customers' },
      {
        type: 'paragraph',
        text: 'Goal: re-engage customers whose behavior signals declining engagement before they churn.',
      },
      {
        type: 'list',
        ordered: true,
        items: [
          'Build a predictive segment in the CDP targeting the At-Risk lifecycle stage, refined by RFM — low recency, previously high frequency or monetary value.',
          'Sync the segment to Meta and Google as a custom audience; identifiers are SHA-256 hashed before they leave Stratum.',
          'Run a win-back campaign against that audience and track recovered revenue with data-driven attribution.',
        ],
      },
      {
        type: 'paragraph',
        text: 'Outcome: a tightly-targeted, privacy-safe audience that focuses spend on customers worth saving, with attribution showing what the win-back actually recovered.',
      },
      { type: 'heading', text: 'Cut CAC by reallocating budget' },
      {
        type: 'paragraph',
        text: 'Goal: lower Customer Acquisition Cost by moving budget away from inefficient sources and toward those acquiring customers more cheaply.',
      },
      {
        type: 'list',
        ordered: true,
        items: [
          'Use attribution — last-click for a quick read, data-driven (DDA) for a fuller picture — to compare CAC and MER across platforms.',
          'Configure an automation that shifts budget toward the lower-CAC sources within your guardrails.',
          'Keep the trust gate active so reallocation only fires on healthy signals.',
        ],
      },
      {
        type: 'paragraph',
        text: 'Outcome: blended CAC trends down while MER holds or improves, and every reallocation is gated on trustworthy data and recorded in the audit trail.',
      },
    ],
  },
  {
    slug: 'tutorials/best-practices',
    category: 'Tutorials',
    title: 'Best Practices',
    description:
      'Field-tested guidance for running trust-gated autopilot, the CDP, and integrations safely.',
    readTime: '9 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'These practices come from how the platform is meant to be operated. None of them are mandatory, but following them keeps automations trustworthy, audiences clean, and your tenant secure.',
      },
      { type: 'heading', text: 'Roll out automations gradually' },
      {
        type: 'list',
        items: [
          'Start every new automation in Advisory — it recommends the action and executes nothing, so you can judge the recommendations against reality.',
          'Move to Soft-Block once the recommendations consistently match your intent; it executes when healthy and holds with an alert when degraded.',
          'Reserve Hard-Block for high-stakes actions where anything below threshold should require manual approval.',
        ],
      },
      {
        type: 'callout',
        tone: 'success',
        title: 'Build trust before you delegate',
        text: 'A few days in Advisory is the cheapest insurance you can buy. You learn the system’s judgment with zero risk, then graduate with confidence.',
      },
      { type: 'heading', text: 'Set thresholds to your risk tolerance' },
      {
        type: 'paragraph',
        text: 'The defaults — healthy at 70, degraded 40–69, unhealthy below 40 — are a sensible starting point, but thresholds are configurable per tenant. Raise the healthy threshold for sensitive accounts so the gate is stricter; loosen it only when you genuinely accept more noise. Never hardcode thresholds outside the config.',
      },
      { type: 'heading', text: 'Raise EMQ with server events' },
      {
        type: 'list',
        items: [
          'Send conversions through the Conversions API (CAPI) as well as the browser tag — server events are immune to ad blockers and cookie limits.',
          'Include as many matchable identifiers as you can (email, phone, order id), since Event Match Quality is 35% of signal health.',
          'Lower-case, trim, and SHA-256 hash PII before it leaves your servers.',
        ],
      },
      { type: 'heading', text: 'Segment before you sync' },
      {
        type: 'paragraph',
        text: 'Define and inspect a segment in the CDP — behavioral, demographic, or predictive — before pushing it anywhere. Confirm the profile count and lifecycle mix look right, then sync to Meta, Google, TikTok, or Snapchat. Audience matching uses hashed identifiers, so raw PII never reaches the platform.',
      },
      { type: 'heading', text: 'Monitor signal health continuously' },
      {
        type: 'list',
        items: [
          'Treat the Overview as a triage queue — it surfaces what needs attention first.',
          'Investigate a sustained drop into the degraded band before it blocks; check API health and event loss as leading indicators.',
          'Remember the weights: EMQ 35%, API Health 25%, Event Loss 20%, Platform Stability 10%, Data Quality 10%.',
        ],
      },
      { type: 'heading', text: 'Use audit logs as your source of truth' },
      {
        type: 'paragraph',
        text: 'Every gate decision and executed action is logged with the signal health snapshot that justified it. When an automation ran, held, or blocked, the audit trail tells you exactly why — use it for post-incident reviews and stakeholder reporting rather than guessing.',
      },
      { type: 'heading', text: 'Lock down access' },
      {
        type: 'list',
        items: [
          'Grant least-privilege OAuth scopes — only what an integration needs to read performance data and manage the entities it controls.',
          'Enable TOTP-based MFA for every user with automation privileges.',
          'Store API keys as backend secrets, never in frontend code or committed files, and rotate them periodically.',
          'Keep PII out of tokens and logs; rely on encrypted database fields and hashed identifiers.',
        ],
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'A common pitfall',
        text: 'Do not disable the trust gate for a "quick fix." Bypassing it is exactly how a tracking outage turns into a bad budget move that the audit log will later attribute to a manual override.',
      },
    ],
  },
  {
    slug: 'tutorials/troubleshooting',
    category: 'Tutorials',
    title: 'Troubleshooting',
    description:
      'Diagnose and fix the most common issues with signals, gates, integrations, and webhooks.',
    readTime: '7 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Most issues trace back to a handful of root causes. Each section below gives the likely cause and the fix. When in doubt, start at the Overview and the audit log — they usually point straight at the problem.',
      },
      { type: 'subheading', text: 'Signal health is stuck Degraded or Blocked' },
      {
        type: 'paragraph',
        text: 'Cause: one or more components are dragging the composite score down — most often falling API health or rising event loss. Fix: open Signal Health and inspect the breakdown. A degraded platform API or a CAPI gateway returning errors will surface here; resolve the upstream issue and the score recovers on its own once data flows cleanly again.',
      },
      { type: 'subheading', text: 'An automation is not executing' },
      {
        type: 'paragraph',
        text: 'Cause: the trust gate is returning HOLD or BLOCK, or the automation is in the wrong enforcement mode. Fix: check the automation’s latest gate decision in the audit log. If health is below your healthy threshold the gate is correctly holding — wait for recovery or investigate the signal drop. If you expected execution while degraded, confirm you are not in Advisory (which never executes) and review your enforcement mode.',
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'Advisory mode is working as designed when it does not execute — it only ever recommends. Move to Soft-Block to allow execution on healthy signals.',
      },
      { type: 'subheading', text: 'Low EMQ or audience match rate' },
      {
        type: 'paragraph',
        text: 'Cause: events are missing identifiers, or you are relying on browser events alone. Fix: send conversions through CAPI in addition to the web tag, and include every matchable identifier you have (email, phone, order id). Make sure PII is lower-cased, trimmed, and SHA-256 hashed in the format the platform expects — a formatting mismatch silently tanks match rates.',
      },
      { type: 'subheading', text: 'OAuth token expired or revoked' },
      {
        type: 'paragraph',
        text: 'Cause: the platform refresh token was revoked, or the connecting user lost access on the platform side. Fix: reconnect the integration to run a fresh OAuth consent flow — Stratum stores only the new encrypted refresh token. Signal collection resumes once the connection is healthy again.',
      },
      { type: 'subheading', text: 'Hitting 429 rate limits' },
      {
        type: 'paragraph',
        text: 'Cause: too many API requests in a short window against the per-tenant Redis rate limit. Fix: back off and retry with exponential delay, honor any Retry-After header, and batch writes instead of sending one request per record. If a job consistently saturates the limit, spread it over a longer window.',
      },
      { type: 'subheading', text: 'A webhook is not being received' },
      {
        type: 'paragraph',
        text: 'Cause: a wrong endpoint URL, a failed signature verification, or a non-2xx response causing the sender to treat delivery as failed. Fix: confirm the endpoint is reachable and returns 2xx quickly, verify the signature using the shared secret with a constant-time comparison, and check the delivery log for the rejection reason before assuming the event was never sent.',
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'Still stuck?',
        text: 'Capture the relevant audit-log entry and signal health snapshot before escalating. They contain the exact decision, timestamp, and component scores support needs to reproduce the issue.',
      },
    ],
  },
];
