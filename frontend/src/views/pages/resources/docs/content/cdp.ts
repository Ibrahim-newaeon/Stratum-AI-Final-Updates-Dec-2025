import type { DocArticle } from '../types';

export const cdpArticles: DocArticle[] = [
  {
    slug: 'cdp/profiles',
    category: 'CDP',
    title: 'Profiles',
    description:
      'How Stratum unifies events and identifiers into a single customer record with computed traits and lifecycle stages.',
    readTime: '6 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'The Customer Data Platform (CDP) is Stratum’s profile and event store. A profile is a unified customer record that combines data from every connected source and touchpoint into one view — the foundation the rest of the platform reasons about.',
      },
      { type: 'heading', text: 'What a unified profile contains' },
      {
        type: 'list',
        items: [
          'Identity information — emails, phone numbers, and device IDs linked to the person.',
          'Behavioral events — the full timeline of tracked actions, from page views to purchases.',
          'Computed traits — attributes derived from that event history.',
          'Segment memberships — every dynamic segment the profile currently matches.',
        ],
      },
      {
        type: 'paragraph',
        text: 'Because the record is assembled continuously, a profile is never stale: a new event, a fresh identifier, or a changed trait updates membership and lifecycle stage in place.',
      },
      { type: 'heading', text: 'Computed traits' },
      {
        type: 'paragraph',
        text: 'Computed traits are derived from a profile’s event history rather than written directly. Stratum maintains them automatically as new events arrive:',
      },
      {
        type: 'list',
        items: [
          'Total purchases — count of completed orders.',
          'Days since last activity — recency of the most recent event.',
          'Average order value — mean revenue per order.',
          'Lifetime value (LTV) — predicted total revenue across the relationship.',
        ],
      },
      { type: 'heading', text: 'Lifecycle stages' },
      {
        type: 'paragraph',
        text: 'Every profile sits in exactly one lifecycle stage, advancing as identity resolves and behavior changes:',
      },
      {
        type: 'list',
        ordered: true,
        items: [
          'Anonymous — no identity yet, only a device or session.',
          'Known — identified via email or login.',
          'Lead — has expressed interest.',
          'Customer — has made a purchase.',
          'Active — recently engaged.',
          'At Risk — engagement is declining.',
          'Churned — no recent activity.',
        ],
      },
      { type: 'heading', text: 'Querying profiles' },
      {
        type: 'paragraph',
        text: 'Read profiles programmatically from the CDP endpoint with your workspace-scoped API key. Results include identity, computed traits, and current segment memberships.',
      },
      {
        type: 'code',
        language: 'bash',
        code: 'curl "https://api.stratumai.app/api/v1/cdp/profiles?lifecycle=at_risk" \\\n  -H "Authorization: Bearer $STRATUM_API_KEY"',
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'Profiles are tenant-isolated. An API key only ever returns records belonging to its own workspace.',
      },
    ],
  },
  {
    slug: 'cdp/segments',
    category: 'CDP',
    title: 'Segments',
    description:
      'Build behavioral, demographic, and predictive segments that re-evaluate themselves as profiles change.',
    readTime: '7 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'A segment is a dynamic group of profiles matching specific criteria. Segments are not static lists — they re-evaluate continuously, so a profile joins or leaves the moment its data crosses the rule boundary.',
      },
      { type: 'heading', text: 'Segment types' },
      {
        type: 'list',
        items: [
          'Behavioral — defined by event patterns, such as “purchased twice in 30 days” or “viewed pricing but never bought.”',
          'Demographic — defined by profile attributes, such as country, plan tier, or acquisition source.',
          'Predictive — defined by an ML model output, such as churn risk above a threshold.',
        ],
      },
      { type: 'heading', text: 'How rules evaluate dynamically' },
      {
        type: 'paragraph',
        text: 'Each segment carries a rule set evaluated against live profile data. When a new event arrives or a computed trait updates, Stratum re-checks affected profiles and adjusts membership in place — no manual rebuild, no nightly batch you have to wait on.',
      },
      {
        type: 'callout',
        tone: 'success',
        title: 'Membership is always current',
        text: 'Because segments reference computed traits like days since last activity, a profile can age into an “At Risk” segment automatically without any event being fired.',
      },
      { type: 'heading', text: 'RFM analysis' },
      {
        type: 'paragraph',
        text: 'For commerce workflows, Stratum supports RFM segmentation, scoring each profile on three axes:',
      },
      {
        type: 'list',
        items: [
          'Recency — how recently did they purchase?',
          'Frequency — how often do they purchase?',
          'Monetary — how much do they spend?',
        ],
      },
      {
        type: 'paragraph',
        text: 'RFM lets you isolate high-value cohorts — recent, frequent, big spenders — and treat declining ones differently from loyal ones.',
      },
      { type: 'heading', text: 'Creating a segment' },
      {
        type: 'paragraph',
        text: 'Create segments in the dashboard or via the API. Post a rule definition and Stratum begins evaluating it against every profile immediately.',
      },
      {
        type: 'code',
        language: 'bash',
        code: 'curl -X POST https://api.stratumai.app/api/v1/cdp/segments \\\n  -H "Authorization: Bearer $STRATUM_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d \'{\n    "name": "High-value at risk",\n    "type": "behavioral",\n    "rules": {\n      "all": [\n        { "trait": "total_purchases", "op": "gte", "value": 3 },\n        { "trait": "days_since_last_activity", "op": "gte", "value": 45 }\n      ]\n    }\n  }\'',
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'Once a segment exists you can push it to ad platforms with Audience Sync — see the next article.',
      },
    ],
  },
  {
    slug: 'cdp/identity',
    category: 'CDP',
    title: 'Identity Resolution',
    description:
      'How disparate identifiers collapse into one profile as a visitor moves from anonymous to known to customer.',
    readTime: '6 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Identity resolution is the process of connecting disparate identifiers to a single customer profile. A person rarely arrives fully identified — they browse anonymously, log in later, and purchase later still. Stratum stitches those moments together so they describe one human, not three.',
      },
      { type: 'heading', text: 'The identity graph' },
      {
        type: 'paragraph',
        text: 'Each profile is backed by an identity graph: a representation of how identifiers — email, phone, device IDs — connect to form the unified record. As new identifiers appear alongside known ones, edges are added and the graph grows.',
      },
      { type: 'heading', text: 'The resolution flow' },
      {
        type: 'paragraph',
        text: 'A typical journey advances through two resolution steps:',
      },
      {
        type: 'list',
        ordered: true,
        items: [
          'Anonymous → Known — a device or session profile gains an email or login, so the anonymous activity is now attributed to a known person.',
          'Known → Customer — that known person completes a purchase, advancing the lifecycle stage and enriching their computed traits.',
        ],
      },
      {
        type: 'callout',
        tone: 'success',
        title: 'No history is lost',
        text: 'When an anonymous profile is identified, its earlier events fold into the resolved profile — so the pre-login browsing that led to a purchase still counts.',
      },
      { type: 'heading', text: 'How deterministic identifiers merge' },
      {
        type: 'paragraph',
        text: 'Stratum merges on deterministic matches: a shared, exact identifier such as the same email or the same device ID seen on two profiles. When a match is found, the records are merged into one identity graph and their events, traits, and segment memberships are recomputed against the combined history.',
      },
      { type: 'heading', text: 'What happens on login and on purchase' },
      {
        type: 'list',
        items: [
          'On login — the session’s device ID links to the authenticated email, collapsing anonymous activity into the Known profile.',
          'On purchase — the order ties the profile to a verified customer identifier, moving the lifecycle stage to Customer and updating total purchases, average order value, and LTV.',
        ],
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'Identifiers used for matching are stored as encrypted PII at rest. Raw values are never exposed in profile reads or pushed to external platforms.',
      },
    ],
  },
  {
    slug: 'cdp/audience-sync',
    category: 'CDP',
    title: 'Audience Sync',
    description:
      'Push CDP segments to Meta, Google, TikTok, and Snapchat for targeting — privately, and kept fresh automatically.',
    readTime: '6 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Audience Sync pushes a CDP segment to advertising platforms so you can target — or suppress — those exact profiles in your campaigns. Build the audience once in Stratum and let it stay current everywhere it is used.',
      },
      { type: 'heading', text: 'The sync flow' },
      {
        type: 'list',
        ordered: true,
        items: [
          'Select a segment — choose any behavioral, demographic, or predictive segment from the CDP.',
          'Connect a platform — pick a destination you have already authorized via OAuth.',
          'Push — Stratum hashes the matchable identifiers and uploads the audience.',
          'Auto-refresh — configure a refresh cadence so membership changes propagate without a manual re-push.',
        ],
      },
      { type: 'heading', text: 'Destination platforms' },
      {
        type: 'list',
        items: [
          'Meta Custom Audiences',
          'Google Customer Match',
          'TikTok Custom Audiences',
          'Snapchat Audience Match',
        ],
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'Your PII never leaves your control',
        text: 'Before any audience is uploaded, email and phone identifiers are lower-cased, trimmed, and SHA-256 hashed. Only the hashes are sent to the platform — raw PII never leaves Stratum, and it remains encrypted at rest.',
      },
      { type: 'heading', text: 'Match-rate tracking' },
      {
        type: 'paragraph',
        text: 'After each push, Stratum records the match rate — the share of hashed identifiers the destination could resolve to its own users. Tracking match rate over time tells you whether an audience is large and clean enough to be worth targeting, and surfaces drops caused by stale or low-quality identifiers.',
      },
      { type: 'heading', text: 'Syncing via the API' },
      {
        type: 'paragraph',
        text: 'Trigger a sync programmatically by referencing a segment and a connected destination. Stratum handles hashing and upload, then returns a job you can poll for match-rate results.',
      },
      {
        type: 'code',
        language: 'bash',
        code: 'curl -X POST https://api.stratumai.app/api/v1/audience-sync \\\n  -H "Authorization: Bearer $STRATUM_API_KEY" \\\n  -H "Content-Type: application/json" \\\n  -d \'{\n    "segment_id": "seg_high_value_at_risk",\n    "destination": "meta_custom_audience",\n    "auto_refresh": "daily"\n  }\'',
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'With auto-refresh enabled, profiles that leave the segment are removed from the destination audience on the next refresh, and new matches are added — keeping spend aimed at the right people.',
      },
    ],
  },
];
