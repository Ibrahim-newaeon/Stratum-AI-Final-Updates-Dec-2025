# Un-gate the Seven Launch Flags — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn on every feature currently held behind a launch flag in `backend/app/core/config.py:449-474`, or record a dated decision not to.

## Status — 2026-08-20

Tranches A and B were executed through PRs, and the checkboxes below were
never ticked. What actually landed, verified against `config.py` at
`15649873`:

| Task | Status | PRs |
|------|--------|-----|
| 1 — Rules engine | **Done**, `feature_automation_rules=True` | #700 |
| 2 — Newsletter beat | **Done**, `enable_newsletter_beat=True` | #702 |
| 3 — Campaign-builder beats | **Blocked** — platform credentials still unset | — |
| 4 — Knowledge graph | **Built, flag still off by design** | #703, #704, #709, #710, #711, #713 |
| 5–7 | Deferred, as written below | — |

Task 4 is not incomplete. The flag is enabled per environment only after
`scripts/backfill_knowledge_graph.py` has run there; see
`backend/app/workers/celery_app.py:258-262`. `feature_competitor_intel` was
also un-gated (#707/#708), which Task 7 anticipated as a decision.

Step-level checkboxes are left unticked rather than back-filled — nobody
recorded which individual steps ran, and inventing that record would defeat
the point of having one.

**Architecture:** Each feature is gated by one boolean on `Settings`. A flag guards up to three things: the API router (503s), the Celery beat entry (never scheduled), and a `*_shelved.py` test that asserts the flag is off. Un-gating therefore always touches at least two files — the flag and its shelved test — and the shelved test is the thing that stops an accidental flip, so it is updated deliberately, never deleted.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, Celery + Redis beat, pytest, PostgreSQL (pgvector image), Docker Compose.

## Global Constraints

- Flags live in `backend/app/core/config.py`. Field names are exact: `feature_automation_rules`, `feature_competitor_intel`, `feature_knowledge_graph`, `feature_drip_campaigns`, `enable_campaign_publish`, `enable_newsletter_beat`, `enable_campaign_builder_beat`.
- Every flag has a matching env var in SCREAMING_SNAKE (`FEATURE_AUTOMATION_RULES=true`), so production can be flipped without a code change. Prefer the env var for anything reversible; change the code default only when the feature is permanently on.
- Backend has no local Python toolchain on the maintainer's machine — `pytest` is CI-only. Lint is verifiable locally: `ruff`, `black`, `isort`, `mypy` are pinned in `requirements.txt`.
- CI enforces test-count floors (3,000 unit / 600 integration). Deleting shelved tests instead of updating them erodes that floor.
- `NODE_VERSION` in CI is `24`; unrelated to this plan but do not change it.
- Never enable a feature whose worker writes fabricated data. That is the standing rule this whole plan exists to respect.

---

## Tranche A — Ready now (no new subsystems)

### Task 1: Enable the Rules Engine

The gating comment is **stale**. It claims the evaluator reads `rule.conditions` while the model stores flat columns, causing `AttributeError` every 15 minutes. Commit `ff6823ca — fix(rules): reconcile beat evaluator with flat condition schema [Tier 3]` (2026-07-11, on `main`) fixed exactly that. `backend/app/workers/tasks/rules.py:188-189` now reads `rule.condition_field` / `rule.condition_operator`, which match `Rule` in `backend/app/base_models.py:781` (`condition_field`, `condition_operator`, `condition_value`, `condition_duration_hours`, `action_type`, `action_config`). The only surviving `.conditions` references are two prose comments.

**Files:**
- Modify: `backend/app/core/config.py:451`
- Modify: `backend/app/workers/celery_app.py:245-248` (stale comment)
- Modify: `backend/app/api/v1/endpoints/rules.py:36` (stale comment)
- Test: `backend/tests/integration/test_rules_competitor_shelved.py`

**Interfaces:**
- Consumes: `settings.feature_automation_rules: bool`
- Produces: beat entry `evaluate-active-rules` → task `app.workers.tasks.evaluate_all_rules`, queue `rules`, every 15 min.

- [ ] **Step 1: Prove the evaluator matches the model before flipping anything**

Run: `pytest backend/tests/unit/test_rules_worker_eval.py backend/tests/unit/test_rules_engine_pure.py -v`
Expected: PASS. These already exercise `_evaluate_condition` against the flat columns. If either fails, STOP — the gating comment was right after all and this task becomes a bug fix, not a flip.

- [ ] **Step 2: Update the shelved test to assert the new default**

In `backend/tests/integration/test_rules_competitor_shelved.py`, change the rules-flag assertion from off to on. Keep the competitor assertions untouched — that flag stays off (Task 7).

```python
def test_automation_rules_flag_defaults_on():
    """Rules shipped once ff6823ca reconciled the evaluator with the flat
    condition schema. Competitor intel stays off — see Task 7."""
    from app.core.config import settings

    assert settings.feature_automation_rules is True
    assert settings.feature_competitor_intel is False
```

- [ ] **Step 3: Run it and watch it fail**

Run: `pytest backend/tests/integration/test_rules_competitor_shelved.py -v -k automation_rules`
Expected: FAIL — `assert False is True`

- [ ] **Step 4: Flip the flag**

In `backend/app/core/config.py:451`:

```python
    feature_automation_rules: bool = Field(default=True)
```

- [ ] **Step 5: Run it and watch it pass**

Run: `pytest backend/tests/integration/test_rules_competitor_shelved.py -v`
Expected: PASS

- [ ] **Step 6: Delete both stale comments**

In `backend/app/workers/celery_app.py`, replace lines 245-248 with:

```python
# Re-enabled after ff6823ca reconciled the evaluator with the flat
# condition_field/operator/value schema. Set FEATURE_AUTOMATION_RULES=false
# to disable.
```

In `backend/app/api/v1/endpoints/rules.py:36`, delete the sentence beginning "The autonomous evaluator reads ``rule.conditions``" — it describes a bug that no longer exists.

- [ ] **Step 7: Run the full rules suite**

Run: `pytest backend/tests -k rules -v`
Expected: PASS, no test skipped for being shelved.

- [ ] **Step 8: Commit**

```bash
git add backend/app/core/config.py backend/app/workers/celery_app.py \
        backend/app/api/v1/endpoints/rules.py \
        backend/tests/integration/test_rules_competitor_shelved.py
git commit -m "feat(rules): enable the automation rules engine

The gate cited an AttributeError from the evaluator reading rule.conditions
against a model storing flat condition_field/operator/value columns.
ff6823ca reconciled that on 2026-07-11; only the comments were left behind."
```

- [ ] **Step 9: Verify one real beat tick in staging**

Deploy, then confirm the scheduler queued the task rather than crashing:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs scheduler --tail 50 | grep -i evaluate-active-rules
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs worker --tail 50 | grep -iE "Starting evaluation of all rules|Queued .* rule evaluation"
```

Expected: a "Queued N rule evaluation tasks" line, no `AttributeError`. This is the step that actually retires the risk — the unit tests cover `_evaluate_condition`, not the beat wiring.

---

### Task 2: Enable the newsletter scheduled-send sweep

Not a code defect. `enable_newsletter_beat` is off because `app.workers.newsletter_tasks.process_scheduled_campaigns` dispatches **live email** on a one-minute cron. Manual send already works. The blocker is deliverability confidence, not correctness.

**Files:**
- Modify: `backend/app/core/config.py:465`
- Test: `backend/tests/unit/` — add `test_newsletter_beat_enabled.py`

**Interfaces:**
- Consumes: `settings.enable_newsletter_beat: bool`
- Produces: beat entry → `app.workers.newsletter_tasks.process_scheduled_campaigns`, queue `default`, `crontab(minute="*")`.

**Precondition (human, not code):** confirm the sending domain's SPF/DKIM/DMARC pass and the provider key is domain-restricted. Per the deployment notes the Resend key is account-wide and shared with an unrelated project — resolve that first or this task ships spam risk.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_newsletter_beat_enabled.py`:

```python
"""The scheduled-send sweep dispatches live email on a one-minute cron.
Enabling it is a deliverability decision; this test pins the decision."""

import pytest

from app.core.config import settings


@pytest.mark.unit
def test_newsletter_beat_enabled_by_default():
    assert settings.enable_newsletter_beat is True


@pytest.mark.unit
def test_beat_entry_registered_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "enable_newsletter_beat", True)
    import importlib

    from app.workers import celery_app as mod

    importlib.reload(mod)
    assert "process-scheduled-newsletters" in mod.celery_app.conf.beat_schedule
```

The key `process-scheduled-newsletters` and task path `app.workers.newsletter_tasks.process_scheduled_campaigns` are verbatim from `backend/app/workers/celery_app.py:239-243`.

- [ ] **Step 2: Run it and watch it fail**

Run: `pytest backend/tests/unit/test_newsletter_beat_enabled.py -v`
Expected: FAIL — `assert False is True`

- [ ] **Step 3: Flip the flag**

In `backend/app/core/config.py:465`:

```python
    enable_newsletter_beat: bool = Field(default=True)
```

- [ ] **Step 4: Run it and watch it pass**

Run: `pytest backend/tests/unit/test_newsletter_beat_enabled.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/tests/unit/test_newsletter_beat_enabled.py
git commit -m "feat(newsletter): enable the scheduled-send sweep

Manual send was already live; the beat was opt-in only because it dispatches
real email on a one-minute cron. Deliverability prerequisites signed off."
```

---

### Task 3: Enable the campaign-builder connector beats

Three beat entries at `backend/app/workers/celery_app.py:214-230`: `sync_all_ad_accounts` (daily 02:00), `refresh_expiring_tokens` (every 6h), `connector_health_check` (every 30m). All hit **live platform APIs**.

**Files:**
- Modify: `backend/app/core/config.py:460`
- Test: `backend/tests/unit/` — add `test_campaign_builder_beat_enabled.py`

**Hard precondition:** `META_APP_ID`, `META_APP_SECRET`, `TIKTOK_APP_ID`, `TIKTOK_APP_SECRET`, `SNAPCHAT_CLIENT_ID`, `SNAPCHAT_CLIENT_SECRET`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_DEVELOPER_TOKEN` must all be populated in `/opt/stratum/.env`. They are currently unset. **Do not start this task before they are** — `refresh_expiring_tokens` against absent credentials produces a failing task every six hours and trains the team to ignore worker errors.

- [ ] **Step 1: Verify the credentials are actually present**

```bash
ssh -i ~/.ssh/<deploy-key> root@<origin-host> \
  "awk -F= '/^(META|TIKTOK|SNAPCHAT|GOOGLE_ADS)_/{print \$1 \": \" (length(\$2)>0 ? \"set\" : \"EMPTY\")}' /opt/stratum/.env"
```

Expected: every line reads `set`. Any `EMPTY` → stop, this task is blocked.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/unit/test_campaign_builder_beat_enabled.py`:

```python
"""Connector beats hit live platform APIs on a schedule."""

import importlib

import pytest

from app.core.config import settings


@pytest.mark.unit
def test_campaign_builder_beat_enabled_by_default():
    assert settings.enable_campaign_builder_beat is True


@pytest.mark.unit
def test_all_three_connector_beats_registered(monkeypatch):
    monkeypatch.setattr(settings, "enable_campaign_builder_beat", True)
    from app.workers import celery_app as mod

    importlib.reload(mod)
    tasks = {e["task"] for e in mod.celery_app.conf.beat_schedule.values()}
    assert "app.workers.campaign_builder_tasks.sync_all_ad_accounts" in tasks
    assert "app.workers.campaign_builder_tasks.refresh_expiring_tokens" in tasks
    assert "app.workers.campaign_builder_tasks.connector_health_check" in tasks
```

- [ ] **Step 3: Run it and watch it fail**

Run: `pytest backend/tests/unit/test_campaign_builder_beat_enabled.py -v`
Expected: FAIL — `assert False is True`

- [ ] **Step 4: Flip the flag**

In `backend/app/core/config.py:460`:

```python
    enable_campaign_builder_beat: bool = Field(default=True)
```

- [ ] **Step 5: Run it and watch it pass**

Run: `pytest backend/tests/unit/test_campaign_builder_beat_enabled.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/tests/unit/test_campaign_builder_beat_enabled.py
git commit -m "feat(campaigns): enable connector sync, token refresh and health beats

Platform credentials are now provisioned, which was the only blocker."
```

- [ ] **Step 7: Watch the first health-check tick**

Run 30 minutes after deploy:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs worker --tail 100 | grep -i connector_health
```

Expected: a health result per connected platform, no auth errors.

---

## Tranche B — Infrastructure

### Task 4: Provision Apache AGE and enable the Knowledge Graph

> **DONE 2026-08-18 — PR #703. Infrastructure landed; the flag is STILL OFF.**
> The steps below were wrong and were not followed literally.
>
> **The outcome changed.** AGE is provisioned and the graph exists, so the
> original blocker is gone — but nothing writes to the graph.
> `KnowledgeGraphSyncService` has seven populate methods and a `full_sync`
> orchestrator that nothing instantiates: no Celery task, no beat, and all 11
> KG routes are GETs. Turning the flag on would replace a 503 with `/stats`
> reporting zero nodes and `/insights/problems` returning `[]` — a confident
> wrong answer. Gate stays shut; flipping it is a one-line change once a writer
> exists, and `test_nothing_populates_the_graph_yet` fails the moment one does.
>
> **Follow-up needed: wire the KG writer.** Undecided and needing a spec —
> beat sweep vs per-tenant ETA tasks, cadence, re-entrancy after a worker
> restart, and whether a partial sync is recorded or rolled back. Same
> treatment as Tasks 5 and 6.
>
> Three gaps found before writing code:
>
> 1. **`CREATE EXTENSION age` alone turns 503 into 500.** `cypher()` addresses a
>    *named* graph — a schema AGE creates on demand — so `create_graph` plus the
>    vertex/edge labels are required before any route resolves. Step 4's
>    one-line migration does not do that.
> 2. **`ag_catalog` was never on the runtime search_path.** `cypher` and the
>    `agtype` return type both live there; all 20 call sites in `service.py`
>    are unqualified. Solved with a `_execute_graph` helper scoped to the
>    service (`LOAD 'age'` + `SET LOCAL search_path`), not an engine listener —
>    a listener would fail the whole app on a database without AGE.
> 3. **A complete AGE migration already existed and had never run**, at
>    `backend/alembic/versions/2026_02_07_knowledge_graph_age.py`. `alembic.ini`
>    sets `script_location = migrations`, so that directory is dead. Ported as
>    `065`, minus its indexes / helper / matview (unused, and each a way for the
>    migration to fail). Directory deleted.
>
> Step 9's CI advice was also unusable: it depends on a GHCR tag that does not
> exist yet on the PR that creates it. Both jobs build the image as a step and
> `docker run` it instead, since a service container cannot be built.


Unlike Task 1, **this gate is accurate**. `backend/app/services/knowledge_graph/insights.py` issues real Cypher through `self.kg.execute_cypher(...)` at lines 191, 208, 262, 272, 281, 417, 429, 446, 508, 520. Without the extension every one of those 500s, which is why the router 503s instead.

The database already runs a custom image (`pgvector/pgvector:pg16`, needed by migration 049's `CREATE EXTENSION vector`), so this is an image swap plus a migration — not a new architecture.

**Files:**
- Create: `backend/Dockerfile.postgres`
- Modify: `docker-compose.yml` (db service `image:` → `build:`)
- Modify: `docker-compose.prod.yml`, `docker-compose.hetzner.yml` if they pin the db image
- Create: `backend/migrations/versions/<rev>_add_age_extension.py`
- Modify: `backend/app/core/config.py:457`
- Modify: `backend/tests/unit/test_knowledge_graph_shelved.py`
- Modify: `.github/workflows/ci.yml` (Backend Tests postgres service image)

**Interfaces:**
- Consumes: `settings.feature_knowledge_graph: bool`
- Produces: `ag_catalog` schema and a loaded `age` extension available to `execute_cypher`.

- [ ] **Step 1: Build a Postgres image carrying both extensions**

Create `backend/Dockerfile.postgres`:

```dockerfile
# pgvector (migration 049) and Apache AGE (knowledge graph Cypher) in one
# image. The stock pgvector image lacks AGE; the stock AGE image lacks vector.
FROM pgvector/pgvector:pg16

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential postgresql-server-dev-16 git flex bison \
 && git clone --depth 1 --branch PG16/v1.5.0-rc0 \
      https://github.com/apache/age.git /tmp/age \
 && make -C /tmp/age install \
 && rm -rf /tmp/age /var/lib/apt/lists/*
```

- [ ] **Step 2: Point compose at it**

In `docker-compose.yml`, replace the `db` service's `image:` line with:

```yaml
    build:
      context: ./backend
      dockerfile: Dockerfile.postgres
```

Check `docker-compose.prod.yml` and `docker-compose.hetzner.yml` for a db `image:` override and apply the same change where present.

- [ ] **Step 3: Verify the extension is installable before writing the migration**

```bash
docker compose build db && docker compose up -d db && sleep 10
docker compose exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "CREATE EXTENSION IF NOT EXISTS age; LOAD 'age'; SET search_path = ag_catalog, public; SELECT 1;"
```

Expected: `1`. If this fails, STOP — the migration would fail identically on every environment.

- [ ] **Step 4: Write the migration**

```bash
cd backend && make migration msg="add age extension"
```

In the generated file:

```python
def upgrade() -> None:
    # Apache AGE backs the knowledge graph's Cypher queries
    # (services/knowledge_graph/insights.py). Requires the custom
    # postgres image built from backend/Dockerfile.postgres.
    op.execute("CREATE EXTENSION IF NOT EXISTS age")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS age")
```

- [ ] **Step 5: Run the migration**

Run: `cd backend && make migrate`
Expected: applies cleanly; `alembic heads` shows a single head.

- [ ] **Step 6: Update the shelved test**

In `backend/tests/unit/test_knowledge_graph_shelved.py`, `test_flag_defaults_off` currently asserts `settings.feature_knowledge_graph is False`. Replace it:

```python
def test_flag_defaults_on():
    """AGE is provisioned by backend/Dockerfile.postgres, so the KG ships."""
    from app.core.config import settings

    assert settings.feature_knowledge_graph is True
```

Keep `test_disabled_by_default_returns_503` but rename it to `test_disabled_returns_503` — it monkeypatches the flag to `False` and still documents the 503 path, which stays valid.

- [ ] **Step 7: Run it and watch it fail**

Run: `pytest backend/tests/unit/test_knowledge_graph_shelved.py -v`
Expected: FAIL on `test_flag_defaults_on`

- [ ] **Step 8: Flip the flag**

In `backend/app/core/config.py:457`:

```python
    feature_knowledge_graph: bool = Field(default=True)
```

- [ ] **Step 9: Point CI's Postgres at the same image**

In `.github/workflows/ci.yml`, the `backend-tests` job's `postgres` service uses `pgvector/pgvector:pg16`. A service container cannot be built from a Dockerfile, so publish the image to GHCR in `docker.yml` and reference the published tag here. Until that lands, add to the job:

```yaml
      - name: Install Apache AGE into the service container
        run: |
          # Service containers can't be built from a Dockerfile; install into
          # the running one so migration <rev> (CREATE EXTENSION age) applies.
          docker exec "$(docker ps -qf ancestor=pgvector/pgvector:pg16)" \
            bash -lc 'apt-get update && apt-get install -y --no-install-recommends \
              build-essential postgresql-server-dev-16 git flex bison && \
              git clone --depth 1 --branch PG16/v1.5.0-rc0 https://github.com/apache/age.git /tmp/age && \
              make -C /tmp/age install'
```

- [ ] **Step 10: Run the KG suite**

Run: `pytest backend/tests -k knowledge_graph -v`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add backend/Dockerfile.postgres docker-compose*.yml \
        backend/migrations/versions/*age* backend/app/core/config.py \
        backend/tests/unit/test_knowledge_graph_shelved.py .github/workflows/ci.yml
git commit -m "feat(kg): provision Apache AGE and enable the knowledge graph

insights.py issues real Cypher; without the extension every KG route 500s,
which is why it shipped behind a 503. Same image now carries pgvector and AGE."
```

---

## Tranche C — Needs its own spec before a plan exists

The remaining three are **not flag flips**. Writing task-level steps for them here would mean inventing design decisions that have not been made, which is exactly the placeholder failure this format forbids. Each needs a brainstorming pass and its own spec.

### Task 5 (deferred): `enable_campaign_publish`

**Why it can't be planned yet.** `backend/app/api/v1/endpoints/campaign_builder.py:892` sets `result_status=PublishResult.SUCCESS` unconditionally, with the comment "Will be updated by background task", and line 900 says `platform_campaign_id` will be set the same way — but no dispatch exists. The undecided questions: does publish go through `stratum/adapters/registry.py` or a new publisher; is it synchronous with a spinner or queued with a status poll; what happens to the other three platforms when one of four fails; is a partial publish rolled back or recorded as partial.

**Commercial note:** this is the highest-value item on the list. It is the capability investors will assume is live, and the one the marketing surface most wants to claim.

**Next action:** run `superpowers:brainstorming` scoped to "multi-platform campaign publish", produce `docs/superpowers/specs/YYYY-MM-DD-campaign-publish-design.md`, then a plan.

### Task 6 (deferred): `feature_drip_campaigns`

**Why it can't be planned yet.** There is no drip Celery task anywhere in `backend/app/workers/`. `manual_trigger` at `backend/app/api/v1/endpoints/drip_campaigns.py:452` writes a record explicitly labelled "simulated". `DripSequence` and `DripExecutionRecord` exist in `backend/app/models/drip.py`, so the storage model is done and the engine is not. Undecided: does step advancement run on a beat sweep or per-enrolment ETA tasks; what re-entrancy rule prevents double sends after a worker restart; how does an unsubscribe mid-sequence halt it; does it send through the newsletter sender or its own.

**Next action:** brainstorming → spec → plan. Sequence this **after** Task 2, so drip inherits a sending path already proven in production.

### Task 7 (decision, not engineering): `feature_competitor_intel`

**Why no amount of code fixes it.** The refresh worker fabricates estimated spend, impressions and CTR with `random.randint` (`backend/app/workers/celery_app.py:256-259`). There is no bug to fix — there is no data source. The options are: license an ad-intelligence provider and rewrite the worker against it; narrow the feature to metrics derivable from first-party data and rename it honestly; or delete the surface.

**Recommendation:** decide explicitly and record the date. An indefinitely gated feature still costs — it appears in the codebase, in audits, and in every capability review, and each time someone has to re-derive why it is off.

---

## Self-Review

**Spec coverage.** All seven flags are addressed: Tasks 1-3 (rules, newsletter beat, connector beats), Task 4 (knowledge graph), Tasks 5-7 deferred with a stated reason and a named next action rather than invented steps.

**Placeholder scan.** No TBDs. The one instruction requiring on-the-spot confirmation — the newsletter beat key string in Task 2, Step 1 — says so explicitly and gives the file and line to read it from, rather than guessing.

**Type consistency.** Flag names match `config.py` exactly. Task names match the beat `task:` strings verbatim from `celery_app.py:217-228` and `:240`. `PublishResult.SUCCESS`, `DripSequence`, `DripExecutionRecord`, `Rule.condition_field` and `execute_cypher` are all quoted from source.

**Sequencing risk.** Tasks 1-4 are independent and can run in any order or in parallel. Task 6 should follow Task 2. Task 3 is hard-blocked on credentials that do not exist yet, and Step 1 checks for them before any code changes.
