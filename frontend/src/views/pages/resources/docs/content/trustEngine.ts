import type { DocArticle } from '../types';

export const trustEngineArticles: DocArticle[] = [
  {
    slug: 'signal-health',
    category: 'Trust Engine',
    title: 'Signal Health',
    description:
      'The composite 0–100 score that tells you how reliable your data is right now — and whether autopilot is allowed to run.',
    readTime: '7 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Signal Health is the heartbeat of the Trust Engine. It is a single composite score from 0 to 100 that summarizes how reliable your incoming data is at this moment. Every automation in Stratum reads this score before it acts, so understanding what moves it is the key to understanding why autopilot runs, holds, or stands down.',
      },
      {
        type: 'paragraph',
        text: 'The score is computed continuously. As collectors pull metrics, events, and webhook deliveries from your connected platforms, the Health Calculator re-evaluates the blend in near real time — you never wait for a nightly batch to learn that something degraded.',
      },
      { type: 'heading', text: 'The five weighted components' },
      {
        type: 'paragraph',
        text: 'Signal Health is a weighted average of five inputs. Each measures a different failure mode, so a problem in any one of them pulls the composite down proportionally to its weight:',
      },
      {
        type: 'list',
        items: [
          'Event Match Quality (EMQ) — 35%: how well your tracked events match platform data, which directly drives attribution accuracy.',
          'API Health — 25%: the responsiveness and error rate of the platform APIs feeding your account.',
          'Event Loss — 20%: the share of expected events that never arrived or were dropped in transit.',
          'Platform Stability — 10%: how steady the upstream platform has been, independent of your own integration.',
          'Data Quality — 10%: the completeness and consistency of the fields on the events you do receive.',
        ],
      },
      {
        type: 'callout',
        tone: 'info',
        title: 'Why EMQ dominates',
        text: 'EMQ carries the heaviest weight because poor match quality quietly corrupts every downstream decision — attribution, ROAS, and the budget moves autopilot makes from them. Fix EMQ first when health drops.',
      },
      { type: 'heading', text: 'How the bands map to action' },
      {
        type: 'paragraph',
        text: 'The raw score is meaningless without the bands that translate it into a decision. Stratum uses three:',
      },
      {
        type: 'list',
        items: [
          '70–100 Healthy (green) — signals are reliable and autopilot is enabled.',
          '40–69 Degraded (yellow) — quality is questionable, so Stratum alerts and holds rather than acts.',
          '0–39 Unhealthy (red) — data cannot be trusted and manual intervention is required.',
        ],
      },
      { type: 'heading', text: 'Reading a drop' },
      {
        type: 'paragraph',
        text: 'When the composite falls, open the breakdown and look at which component moved. A sudden EMQ collapse usually means an identifier stopped flowing — a broken tag, an expired token, or a CAPI outage. A spike in event loss points at delivery problems, while an API health dip is often the platform itself. Because the weights are fixed and visible, you can always reconstruct exactly why the number changed.',
      },
      {
        type: 'callout',
        tone: 'success',
        text: 'Signal Health is not a vanity metric — it is the input the Trust Gate evaluates before every automation. Keep it green and autopilot stays armed.',
      },
    ],
  },
  {
    slug: 'trust-gates',
    category: 'Trust Engine',
    title: 'Trust Gates',
    description:
      'The decision checkpoint that evaluates signal health before any automation executes — PASS, HOLD, or BLOCK.',
    readTime: '6 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'A Trust Gate is the checkpoint that sits between an automation and the action it wants to take. Before any execution, the gate reads the current Signal Health score and returns one of three outcomes. Nothing reaches your ad platforms without passing through it.',
      },
      { type: 'heading', text: 'The PASS / HOLD / BLOCK model' },
      {
        type: 'list',
        items: [
          'PASS — signal health meets the threshold, so the automation proceeds and executes.',
          'HOLD — health is degraded; the gate alerts you but executes nothing.',
          'BLOCK — health is unhealthy; the action is stopped and manual approval is required.',
        ],
      },
      {
        type: 'paragraph',
        text: 'The gate is re-evaluated on every execution, not once at setup. An automation that passed this morning can hold this afternoon if EMQ slips — the decision always reflects the data as it is right now.',
      },
      { type: 'heading', text: 'Where the gate sits' },
      {
        type: 'paragraph',
        text: 'In the Trust Engine flow, signals move from collectors to the Health Calculator, which produces the composite score. The Trust Gate consumes that score and decides whether the Automation Executor is allowed to run:',
      },
      {
        type: 'code',
        language: 'text',
        code: 'Signal Collectors → Health Calculator → Trust Gate → Automation Executor\n                                            │\n                                  PASS ──────┤\n                                  HOLD ──────┤ (alert only)\n                                  BLOCK ─────┘ (manual approval)',
      },
      { type: 'heading', text: 'A worked example' },
      {
        type: 'paragraph',
        text: 'Suppose a tracking outage takes your CAPI endpoint offline for twenty minutes. Events stop matching, EMQ falls, and because EMQ carries 35% of the weight the composite drops from 82 into the degraded band at 58. At that moment an autopilot rule wants to shift $400 of budget toward a campaign whose ROAS just spiked.',
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'The gate protects you here',
        text: 'That ROAS spike is an artifact of the outage, not real performance. Because health is 58, the gate returns HOLD: it alerts you and refuses to move the budget. When events resume and health climbs back above 70, the gate passes again — and only then does autopilot reconsider the move on trustworthy data.',
      },
      { type: 'heading', text: 'The audit trail' },
      {
        type: 'paragraph',
        text: 'Every gate decision is written to the tenant audit log alongside the signal-health snapshot that justified it. Open an automation’s history and you can see, for each evaluation, the score at that instant, the outcome, and the action that was taken or withheld. Nothing the Trust Engine does is a black box.',
      },
    ],
  },
  {
    slug: 'autopilot',
    category: 'Trust Engine',
    title: 'Autopilot Rules',
    description:
      'How automations act on healthy data — enforcement modes, the actions they take, and the safety guarantees behind them.',
    readTime: '7 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Autopilot is what executes once a Trust Gate passes. An autopilot rule pairs an objective with an enforcement mode, then lets the Trust Engine decide on every cycle whether the data is good enough to act. The result is automation you can leave running without fear of it acting on bad signals.',
      },
      { type: 'heading', text: 'What autopilot can do' },
      {
        type: 'list',
        items: [
          'Adjust campaign budgets up or down.',
          'Modify bidding strategies.',
          'Pause or enable campaigns.',
          'Scale spend based on measured performance.',
        ],
      },
      { type: 'heading', text: 'Enforcement modes' },
      {
        type: 'paragraph',
        text: 'Enforcement mode controls how strictly the gate is applied to a given rule. There are three:',
      },
      {
        type: 'list',
        items: [
          'Advisory — Stratum recommends the action but executes nothing. Use it to evaluate the engine’s judgment.',
          'Soft-Block — executes when health is healthy; holds and alerts when degraded.',
          'Hard-Block — executes only when healthy; anything below threshold requires manual approval.',
        ],
      },
      {
        type: 'callout',
        tone: 'info',
        title: 'Advisory is a real mode, not a dry run',
        text: 'In Advisory the engine evaluates the gate and surfaces exactly the action it would take, with the score behind it — so you can audit its reasoning before handing over control.',
      },
      { type: 'heading', text: 'Graduating a rule' },
      {
        type: 'paragraph',
        text: 'The recommended path is to graduate trust gradually rather than arming a rule cold:',
      },
      {
        type: 'list',
        ordered: true,
        items: [
          'Start in Advisory and compare the engine’s recommendations against your own decisions for a few days.',
          'Move to Soft-Block once the recommendations consistently match your intent — the rule now acts on healthy data and stands down when signals degrade.',
          'Promote to Hard-Block for your most sensitive spend, where you want zero execution unless the data is unambiguously healthy.',
        ],
      },
      { type: 'heading', text: 'Safety guarantees' },
      {
        type: 'paragraph',
        text: 'Two invariants hold regardless of mode. First, autopilot never auto-executes when signal health is below the healthy threshold — degraded data can only ever produce a hold or a manual request, never an automatic action. Second, every executed action and every gate decision is written to the audit log with the health snapshot that justified it, so the full chain from signal to action is always reconstructable.',
      },
      {
        type: 'callout',
        tone: 'success',
        text: 'Trust-gated autopilot means the worst case for a degraded signal is an alert and a held action — not a bad budget move executed on broken data.',
      },
    ],
  },
  {
    slug: 'thresholds',
    category: 'Trust Engine',
    title: 'Thresholds',
    description:
      'The healthy and degraded cutoffs, how to tune them per tenant, and when tighter or looser limits make sense.',
    readTime: '5 min',
    blocks: [
      {
        type: 'paragraph',
        text: 'Thresholds are the numbers that turn a Signal Health score into a gate decision. Two cutoffs define the three bands, and both are configurable per tenant so you can match the engine’s caution to your own risk tolerance.',
      },
      { type: 'heading', text: 'The defaults' },
      {
        type: 'list',
        items: [
          'HEALTHY_THRESHOLD = 70 — at or above this, signals are healthy and autopilot is eligible.',
          'DEGRADED_THRESHOLD = 40 — between 40 and 69 the gate holds; below 40 it blocks.',
        ],
      },
      {
        type: 'callout',
        tone: 'warning',
        title: 'The hard floor',
        text: 'Stratum never auto-executes when signal_health is below 70. You can raise the healthy threshold, but autopilot will not act on degraded data regardless of how a rule is configured.',
      },
      { type: 'heading', text: 'Configuring per tenant' },
      {
        type: 'paragraph',
        text: 'Thresholds live in the tenant’s TrustGateConfig. Adjusting them shifts where the bands fall without touching any individual automation — every gate in the workspace reads the same config:',
      },
      {
        type: 'code',
        language: 'json',
        code: '{\n  "trust_gate_config": {\n    "healthy_threshold": 70,\n    "degraded_threshold": 40,\n    "enforcement_mode": "soft_block"\n  }\n}',
      },
      { type: 'heading', text: 'When to tighten or loosen' },
      {
        type: 'paragraph',
        text: 'Raise the healthy threshold — say to 80 — when you manage high-stakes spend and want autopilot to act only on pristine data; the trade-off is more holds during normal noise. Lower it cautiously when your signals are inherently noisier and you would rather act on imperfect data than stall, accepting a higher chance of acting on a transient dip.',
      },
      {
        type: 'callout',
        tone: 'info',
        text: 'Change thresholds in small steps and watch the audit log. If a new cutoff produces a wave of holds or executions, you will see exactly which scores crossed the line and can dial it back.',
      },
    ],
  },
];
