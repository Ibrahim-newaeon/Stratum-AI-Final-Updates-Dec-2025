# Drip Campaigns — Execution Engine

**Status:** built. `feature_drip_campaigns` is still `False`.
**Before flipping it:** run the checks at the bottom of this page, per environment.

---

## What was wrong

`drip_campaigns.py` was 638 lines of working CRUD — flow-graph persistence,
prebuilt templates, analytics endpoints, and a visual builder in the frontend.
What it had never had was anything that *ran* a sequence:

- no Celery task existed anywhere under `app/workers/` for drip
- `activate` flipped `status` to `"active"` and nothing watched for triggers
- `manual_trigger` wrote a `DripExecutionRecord` marked *simulated* and
  returned success

Shipping a builder whose sequences silently never send is worse than a 503,
which is why the whole router was gated off rather than released.

---

## 1. Enrollment state

Two tables, in `app/models/drip.py`, added by migration `066_add_drip_enrollment`.

**`drip_sequence_versions`** — an immutable snapshot of the graph at publish
time. `nodes`/`edges` on `drip_sequences` stay an editable draft; activating
freezes a copy and bumps `version`. `drip_sequences.active_version_id` points at
the version new recipients enter on.

**`drip_enrollments`** — where one recipient stands in one run.

| Concern | Column | Note |
|---|---|---|
| Resume key | `sequence_id` + `recipient_hash` | deterministic, indexable |
| Position | `current_node_id`, `version_id` | resolved against the *pinned* graph |
| Scheduling | `next_due_at`, `status` | the sweep's only query, partial-indexed |
| Loop guard | `steps_completed` vs `MAX_ENROLLMENT_STEPS` | the builder allows back-edges |
| Claiming | `claimed_at`, `claimed_by` | separate from `status`, so a dead claim expires |
| Provenance | `entry_trigger`, `entry_context` | explains later why someone was enrolled |
| Failure | `attempt_count`, `last_error` | terminal `failed`, never a silent `completed` |

### Decisions worth knowing

**Six states, not five.** `pending → active → waiting → completed`, plus
`cancelled` and **`failed`**. Without `failed`, an enrollment whose step keeps
raising has nowhere to land: retried forever, or marked completed — which
reports a sequence that finished when it did not.

**Versioning, not an edit lock.** Blocking edits while active is simpler but
wrong for the user: a marketer fixing a typo in step 4 should not have to stop
the sequence. Freezing the graph per publish lets edits apply to new entrants
while in-flight recipients keep walking the path they started on. `version_id`
is `ON DELETE RESTRICT`, so a version with live enrollments cannot be deleted
out from under the interpreter.

**Hash *and* ciphertext for the address.** `encrypt_pii` is non-deterministic,
so the encrypted column cannot be compared or indexed — the partial unique index
that stops double-enrollment needs `recipient_hash` (`hash_pii_for_lookup`).
The row has a `tenant_id`, so encryption uses the explicit
`set_recipient_email()` + decrypting property pattern from
`CDPProfileIdentifier`, **not** `app.db.types.EncryptedString` (a
`TypeDecorator` never sees the row, so it cannot reach `tenant_id` and would put
every tenant under one global-derived key).

`drip_execution_logs.recipient_email` was widened and encrypted the same way in
the same migration. It had always been plaintext, which was survivable only
while nothing wrote to it.

**Uniqueness is partial.** `uq_drip_enrollment_live` covers only
`pending/active/waiting`, so completing a sequence frees the recipient to enter
it again — which a plain unique constraint would forbid forever.

---

## 2. Worker — `app/workers/drip_tasks.py`

- **`SyncSessionLocal`, never the async session.** A Celery task holding an
  async session is what abandoned asyncpg sockets in the 2026-08-17 outage
  (fixed in #682). The whole module is synchronous.
- `process_due_drip_steps` — beat sweep. Claims due rows and dispatches one
  advance per row.
- `advance_drip_enrollment` — executes exactly one node transition.
- `release_stale_drip_claims` — returns work abandoned by a dead worker.

**Claiming is done in the database, not Redis.** `SELECT ... FOR UPDATE SKIP
LOCKED` is the right primitive for a work queue: two workers sweeping at the
same instant take disjoint sets, and there is no lock to leak if one dies. The
Redis lock only stops two *sweeps* overlapping. `advance` additionally takes
`FOR UPDATE` on its own row, so a duplicate dispatch waits and then sees a
status it will not act on.

**Stale claims** older than `STALE_CLAIM_SECONDS` (15 min) reset to `waiting`.
`next_due_at` is untouched, so they resume on exactly the same schedule.

**Zero-wait steps chain themselves** rather than waiting for the next tick, so
`trigger → condition → email` sends within seconds. The chaining dispatch is
best-effort and after the commit: if the broker is down, the sweep picks the row
up a few minutes later rather than failing a step that already succeeded.

Beat entries (`process-due-drip-steps` every 5 min, plus the two daily scans)
are registered behind the flag, exactly as `enable_newsletter_beat` and
`feature_knowledge_graph` are. The *tasks* are registered unconditionally, so an
operator can drain in-flight enrollments after turning the feature off.

---

## 3. Interpreter — `app/services/drip/interpreter.py`

Pure functions over `(nodes, edges)`. No I/O, so the state machine is testable
without a broker, a database or an SMTP server.

| Node | Action | Next state |
|---|---|---|
| `trigger` | none | first outgoing edge |
| `email` | caller sends | next node, due now |
| `wait` | none | `waiting`, due in `delay_hours` |
| `condition` | none | true or false branch |
| `notification` | caller notifies | next node |
| `end` | none | `completed` |

**Conditions fail loudly.** An unknown condition, a ROAS comparison with no
threshold, or a ROAS comparison with no ROAS available all fail the enrollment.
Quietly taking the false branch would look exactly like a working sequence
making a real decision.

**Branch selection** uses edge labels when present; the builder does not set
them today, so the fallback is declaration order — first edge is the true
branch. One outgoing edge means both branches converge, which is legal.

**`validate_graph`** runs before a version is published: exactly one trigger,
every edge resolves, no orphans, no dead ends, no end node with outgoing edges,
conditions with one or two branches and a usable comparison, and **no loop
without a wait node** — a cycle containing a wait is a legitimate drip, a cycle
without one is a live spin.

---

## 4. Triggers — `app/services/drip/triggers.py`

| Trigger | Source |
|---|---|
| `user_subscribed`, `post_purchase`, `custom_event` | CDP ingestion → `enroll_from_cdp_events` |
| `cart_abandoned` | same, and a later purchase cancels it |
| `days_since_login` | daily scan over `CDPProfile.last_seen_at` |
| `campaign_roas_drop` | daily scan; recipient comes from `trigger_config.notify_emails` |
| `manual` | the trigger endpoint, now a real enrollment |

Event names have sensible defaults per trigger (the CDP has no fixed
vocabulary) and a sequence can override with `trigger_config.event_name(s)`. An
explicit name *replaces* the defaults rather than adding to them.

`custom_event` matches nothing without configuration, `days_since_login` is
skipped without a day count, and `campaign_roas_drop` is skipped without a
recipient. Each could have been given a plausible default; each default would
have mailed real people on an assumption nobody wrote down.

The dispatch from CDP ingestion happens **after the commit, inside a
try/except that swallows everything**. Enrollment is not part of the ingestion
contract: a drip misconfiguration must never make event collection fail.

---

## 5. Send path, tracking and consent

- Rendering, personalisation and tracking live in `app/services/drip/render.py`
  and follow the shape `newsletter_tasks` established.
- **Unsubscribe tokens are HMAC-signed.** The newsletter's equivalent
  base64-encodes `campaign_id:subscriber_id` and calls the result signed;
  decrementing an integer unsubscribes a stranger. This one is signed with the
  app secret, compared with `hmac.compare_digest`, and carries the recipient
  *hash* so no URL ever contains an email address.
- **Consent is re-checked before every step**, not only at enrollment — someone
  can unsubscribe on day 2 of a fourteen-day sequence.
- Suppression has two sources: an explicit CDP email-consent record with
  `granted = False`, and any prior enrollment cancelled as `unsubscribed` (which
  covers recipients with no CDP profile, since `cdp_consents.profile_id` is NOT
  NULL). Absence of a consent record is not treated as refusal.
- An unsubscribe footer is appended when the template forgot one. The
  `List-Unsubscribe` header alone is invisible in many clients.
- The click tracker refuses anything that is not `http(s)`. Without that it is
  an open redirect signed by our own domain.

### The public routes

`track/open`, `track/click` and `unsubscribe` are on a **separate router with no
feature gate and no auth**, exempted in `TenantMiddleware`, and registered
**before** the gated router.

The ordering is load-bearing: `/drip-campaigns/unsubscribe` has the same shape
as `/drip-campaigns/{sequence_id}`, so registered second every unsubscribe click
would bind to the sequence handler. These URLs live in inboxes forever — turning
the feature off later must not turn an opt-out into an error.

---

## 6. Counters and validation

`entry_count` is incremented on enrollment. `active_recipient_count` and
`completion_rate` are recomputed when an enrollment completes.
`revenue_attributed_cents` is still zero — it needs a join to CDP conversion
events within an attribution window, and is the one piece deliberately left.

`activate` now validates before publishing, and `update` on an active sequence
edits the draft only; the running version is untouched until the next activate.
Archiving cancels every in-flight enrollment.

---

## Tests

`tests/unit/test_drip_interpreter.py` (41), `test_drip_triggers.py` (31),
`test_drip_public_routes.py` (31), `test_drip_worker_guards.py` (21).

Integration tests cannot run on a Windows dev box — CI is the gate for those.

---

## Before flipping the flag, per environment

1. `alembic upgrade head` — expect `066_add_drip_enrollment`.
2. Confirm `SMTP`/SendGrid credentials are real in that environment. The send
   path will happily deliver.
3. Set `FEATURE_DRIP_CAMPAIGNS=true` and restart api + worker + **scheduler**
   (the beat entries only appear at import time).
4. Create a sequence, activate it, and check the response carries a `version`.
   An invalid graph returns 422 with the list of reasons.
5. Trigger it manually against an address you own, and confirm the mail arrives
   with a working unsubscribe link.
6. Click the unsubscribe link and confirm the enrollment moves to `cancelled`.

Turning it back off stops new enrollments and the sweep; in-flight enrollments
stay where they are, and `advance_drip_enrollment` remains dispatchable so they
can be drained by hand.
