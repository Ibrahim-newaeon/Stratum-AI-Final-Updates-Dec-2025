import type { DocArticle } from '../types';

export const apiReferenceArticles: DocArticle[] = [
  {
    slug: 'webhooks',
    category: 'API Reference',
    title: 'Webhooks',
    description:
      'Receive real-time, server-to-server notifications when signal health, incidents, or automations change.',
    readTime: '6 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Webhooks let Stratum push events to your backend the moment something changes — no polling required. They are the server-side counterpart to the dashboard’s live updates: the dashboard streams over WebSocket and SSE, while your systems integrate over webhooks.',
      },
      { type: 'heading', text: 'What you can subscribe to' },
      {
        type: 'list',
        items: [
          'Signal health and EMQ changes — when a score crosses a threshold or shifts state.',
          'Incidents — opened, updated, or resolved tracking and platform incidents.',
          'Autopilot enforcement-mode changes — Advisory, Soft-Block, or Hard-Block transitions.',
          'Automation action status — when an action is executed, held, or blocked by the trust gate.',
        ],
      },
      {
        type: 'paragraph',
        text: 'Register an endpoint under Settings → Webhooks, choose the event types you care about, and Stratum will start delivering. Every delivery is a JSON POST to your URL.',
      },
      { type: 'heading', text: 'The delivery payload' },
      {
        type: 'paragraph',
        text: 'Each delivery has a stable envelope: a unique event id, an event type, a timestamp, the tenant id, and a typed data object. Use the id for idempotency so a redelivery is processed at most once.',
      },
      {
        type: 'code',
        language: 'json',
        code: '{\n  "id": "evt_9f3a1c2b",\n  "type": "signal_health.changed",\n  "created_at": "2026-06-07T14:22:08Z",\n  "tenant_id": "wsp_3k8d",\n  "data": {\n    "signal_id": "sig_meta_capi",\n    "previous_score": 72,\n    "current_score": 58,\n    "state": "degraded"\n  }\n}',
      },
      { type: 'heading', text: 'Verify the signature' },
      {
        type: 'paragraph',
        text: 'Every request carries an X-Stratum-Signature header — an HMAC-SHA256 of the raw request body, keyed with your webhook secret. Recompute it over the unparsed body and compare with a constant-time function so you reject any forged or replayed delivery.',
      },
      {
        type: 'code',
        language: 'javascript',
        code: "import crypto from 'node:crypto';\n\nfunction verify(rawBody, header, secret) {\n  const expected = crypto\n    .createHmac('sha256', secret)\n    .update(rawBody)\n    .digest('hex');\n  const a = Buffer.from(expected);\n  const b = Buffer.from(header);\n  return a.length === b.length && crypto.timingSafeEqual(a, b);\n}",
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'Hash the raw body, not the parsed JSON',
        text: 'Re-serializing the payload can change byte order or whitespace and break the signature. Verify against the exact bytes you received, then parse.',
      },
      { type: 'heading', text: 'Retries and reliability' },
      {
        type: 'list',
        items: [
          'Respond 2xx quickly — acknowledge first, then process asynchronously.',
          'Any non-2xx response triggers retries with exponential backoff over the following hours.',
          'Deduplicate on the event id; the same event may be delivered more than once.',
          'Order is best-effort — rely on created_at and the score values rather than arrival order.',
        ],
      },
    ],
  },
  {
    slug: 'sdks',
    category: 'API Reference',
    title: 'SDKs',
    description:
      'Official JavaScript/TypeScript and Python clients that wrap the REST API, signals, the CDP, and audience sync.',
    readTime: '5 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'The official SDKs give you typed access to the same REST surface documented in the API explorer — signal endpoints, the CDP profile and event store, and audience sync — without hand-rolling requests, auth headers, or retries.',
      },
      {
        type: 'callout',
        tone: 'info',
        title: 'Two layers, one platform',
        text: 'The server SDKs are for backend calls with your secret API key. For browser conversion tracking, use the lightweight web tag and its stratum(\'track\', ...) helper covered in Installation — never put a secret key in frontend code.',
      },
      { type: 'heading', text: 'JavaScript / TypeScript' },
      {
        type: 'paragraph',
        text: 'Install from npm and initialize the client with an API key read from your environment. The client is fully typed, so signals, profiles, and audiences come back as concrete shapes.',
      },
      {
        type: 'code',
        language: 'bash',
        code: 'npm install @stratumai/sdk',
      },
      {
        type: 'code',
        language: 'typescript',
        code: "import { Stratum } from '@stratumai/sdk';\n\nconst stratum = new Stratum({ apiKey: process.env.STRATUM_API_KEY });\n\n// List current signals and their health\nconst signals = await stratum.signals.list();\nfor (const s of signals) {\n  console.log(s.name, s.health, s.state);\n}",
      },
      { type: 'heading', text: 'Python' },
      {
        type: 'paragraph',
        text: 'Install from PyPI and construct the client the same way. The Python SDK mirrors the JS surface, so the resource names and methods line up across both languages.',
      },
      {
        type: 'code',
        language: 'python',
        code: 'pip install stratum-ai',
      },
      {
        type: 'code',
        language: 'python',
        code: 'import os\nfrom stratum import Stratum\n\nstratum = Stratum(api_key=os.environ["STRATUM_API_KEY"])\n\n# Send a server-side conversion event\nstratum.events.track(\n    name="Purchase",\n    value=129.0,\n    currency="USD",\n    user={"email_sha256": "9c1185a5c5e9fc54..."},\n)',
      },
      { type: 'heading', text: 'What the SDKs handle for you' },
      {
        type: 'list',
        items: [
          'Bearer authentication and base-URL configuration.',
          'Automatic retries with backoff, including 429 Retry-After handling.',
          'Typed resources for signals, CDP profiles and events, and audience sync.',
          'Pagination cursors so list calls iterate cleanly over large result sets.',
        ],
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'Keep PII out of the clear',
        text: 'When passing user identifiers to the CDP or audience sync, lower-case, trim, and SHA-256 hash email and phone before they leave your servers. The SDKs accept pre-hashed identifiers directly.',
      },
    ],
  },
  {
    slug: 'rate-limits',
    category: 'API Reference',
    title: 'Rate Limits',
    description:
      'How Stratum meters API traffic per tenant, the headers you get back, and how to handle a 429.',
    readTime: '4 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Stratum applies per-tenant rate limits to keep the platform fast and fair. Limits are enforced with a Redis-backed, token-bucket scheme: each workspace refills a budget of requests over time and spends from it as you call the API.',
      },
      { type: 'heading', text: 'Read the limit headers' },
      {
        type: 'paragraph',
        text: 'Every response includes your current standing, so you can pace requests before you ever hit a wall.',
      },
      {
        type: 'list',
        items: [
          'X-RateLimit-Limit — the size of your bucket for this window.',
          'X-RateLimit-Remaining — requests left before throttling kicks in.',
          'X-RateLimit-Reset — Unix timestamp when the bucket refills.',
        ],
      },
      { type: 'heading', text: 'When you exceed the limit' },
      {
        type: 'paragraph',
        text: 'Over-limit requests return 429 Too Many Requests with a Retry-After header telling you how many seconds to wait. Honor it rather than retrying immediately.',
      },
      {
        type: 'code',
        language: 'http',
        code: 'HTTP/1.1 429 Too Many Requests\nRetry-After: 12\nX-RateLimit-Limit: 600\nX-RateLimit-Remaining: 0\nX-RateLimit-Reset: 1749306140\nContent-Type: application/json\n\n{\n  "error": "rate_limited",\n  "message": "Too many requests. Retry after 12 seconds."\n}',
      },
      { type: 'heading', text: 'Stay under the limit' },
      {
        type: 'list',
        items: [
          'Back off exponentially on 429, seeding the first delay from Retry-After.',
          'Batch server-side events instead of sending one request per event.',
          'Cache reads — signal health and profile lookups rarely need to be re-fetched every second.',
          'Let the official SDKs absorb retries and Retry-After handling for you.',
        ],
      },
      {
        type: 'callout',
        tone: 'info',
        title: 'Limits scale with your plan',
        text: 'Rate limits rise across the Starter, Professional, and Enterprise tiers. If you are consistently throttled despite batching and backoff, upgrading your subscription raises the per-tenant budget.',
      },
    ],
  },
];
