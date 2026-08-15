# Async I/O Sweep + CI Coverage Gaps — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove every blocking HTTP call from `async` code paths in the backend, and close the two CI gaps that let broken states reach `main` unnoticed.

**Architecture:** Replace synchronous `requests` calls with `httpx.AsyncClient` inside `async def` functions, following the precedent already set in `meta_adapter.get_emq_scores` (PR #634). Exception handling moves from `requests.RequestException` to `httpx.HTTPError`, which is the equivalent base class covering both transport and status errors. No behaviour changes: same URLs, same payloads, same timeouts, same return values, same error semantics.

**Tech Stack:** Python 3.12, FastAPI, httpx 0.28.1 (already a pinned dependency), pytest + pytest-asyncio, GitHub Actions.

## Global Constraints

- **No local Python.** `python`/`python3`/`py` are unavailable on the dev machine and Docker is not installed. CI is the only backend verification, and `Backend Tests` takes ~35 minutes. Read library source to confirm API surface rather than assuming.
- **black formats at 88 columns** (no config in repo), while **ruff's `line-length` is 100**. Hand-check every added line against **88** or the `Backend Quality` gate fails on lines ruff accepts.
- **`httpx` is already pinned** at `httpx==0.28.1` in both `backend/requirements.txt` and `backend/requirements-prod.txt`. No dependency change is needed. Do not add one.
- **Both requirements files must stay in sync.** `backend/Dockerfile` installs `requirements-prod.txt`; `ci.yml` installs `requirements.txt`. Drift here shipped vulnerable versions to production once already.
- Use `datetime.now(timezone.utc)`, never `datetime.utcnow()`.
- Conventional commits: `fix(scope): message`. Branch: `fix/STRAT-<n>-description`.
- Every mutation keeps its existing audit logging. Do not remove logging lines while editing.

## Why this matters

`get_emq_scores` in `meta_adapter.py` was fixed in #634 because a synchronous `requests.get` inside an `async def` blocks the entire event loop for the duration of the call. That was not an isolated mistake — the same pattern exists in **14 more places**, concentrated on the CAPI / conversion-event send path, which is the highest-volume operation this product performs. One slow platform endpoint stalls every other tenant's request on that worker.

The codebase already knows the correct patterns: `services/stripe_service.py` uses `asyncio.to_thread` for the sync Stripe SDK, and `autopilot/enforcer.py` uses `run_in_executor`. These files are plain REST calls with no SDK, so `httpx.AsyncClient` is the better fit — it is a like-for-like replacement.

**Not in scope:** `app/api/v1/endpoints/developer.py` contains two `requests.get` calls that look like hits but are **inside a documentation string** — sample code rendered in the developer portal. Leave them alone. They are correct as written.

## File Structure

| File | Sites | Change |
| --- | --- | --- |
| `backend/app/stratum/events/__init__.py` | 5 | 4 sender `send()` methods + `get_emq_scores()` → httpx |
| `backend/app/stratum/conversions/__init__.py` | 4 | 3 send methods + `get_emq_score()` → httpx |
| `backend/app/stratum/adapters/whatsapp_adapter.py` | 7 | `_make_request` sync→async (4 verbs) + 3 direct sites; 9 call sites gain `await` |
| `backend/app/stratum/adapters/snapchat_adapter.py` | 1 | `_refresh_access_token()` → httpx |
| `backend/app/stratum/integrations/google_complete.py` | 1 | `send_event()` → httpx |
| `backend/tests/integration/test_events_async_io.py` | new | proves no blocking call remains |
| `.github/workflows/ci.yml` | — | E2E also runs on push to main |
| `.github/workflows/pages.yml` | — | delete, or gate on Pages being enabled |

## Shared test helper

Every task below mocks httpx the same way. This helper already exists in
`backend/tests/integration/test_adapter_meta_deep.py` (added in #634); copy it
into each new test module rather than importing across test files.

```python
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch


@contextmanager
def patch_httpx(module: str, verb: str, handler: AsyncMock):
    """Patch httpx.AsyncClient so `async with ... as c` yields a mock.

    MagicMock supplies the async context-manager protocol, so __aenter__ is
    already an AsyncMock. __aexit__ is pinned to False explicitly — a truthy
    value would swallow the transport errors the failure-path tests rely on.
    """
    with patch(f"{module}.httpx.AsyncClient") as mock_cls:
        setattr(mock_cls.return_value.__aenter__.return_value, verb, handler)
        mock_cls.return_value.__aexit__.return_value = False
        yield mock_cls


def http_response(status_code: int = 200, payload: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload if payload is not None else {}
    r.raise_for_status.return_value = None
    return r
```

---

### Task 1: Meta events sender — `events/__init__.py`

**Files:**
- Modify: `backend/app/stratum/events/__init__.py` (imports; `MetaEventsSender.send` :473-492; `MetaEventsSender.get_emq_scores` :572-580; exception tuple :913)
- Test: `backend/tests/integration/test_events_async_io.py` (create)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `patch_httpx(module, verb, handler)` and `http_response(status, payload)` test helpers, copied into this module — later tasks copy them again rather than importing.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_events_async_io.py`:

```python
"""Async-I/O contract for the events senders.

A synchronous HTTP client inside `async def` blocks the event loop for the
whole request. These tests pin the senders to httpx and prove the calls are
awaited, not merely that they return the right dict.
"""

import asyncio
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.stratum.events import MetaEventsSender, ServerEvent, StandardEvent

pytestmark = [pytest.mark.integration]

MODULE = "app.stratum.events"


@contextmanager
def patch_httpx(module: str, verb: str, handler: AsyncMock):
    with patch(f"{module}.httpx.AsyncClient") as mock_cls:
        setattr(mock_cls.return_value.__aenter__.return_value, verb, handler)
        mock_cls.return_value.__aexit__.return_value = False
        yield mock_cls


def http_response(status_code: int = 200, payload: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload if payload is not None else {}
    r.raise_for_status.return_value = None
    return r


def an_event() -> ServerEvent:
    return ServerEvent(event_name=StandardEvent.PURCHASE)


class TestMetaEventsSenderIsAsync:
    async def test_send_uses_httpx_not_requests(self):
        post = AsyncMock(return_value=http_response(200, {"events_received": 1}))
        sender = MetaEventsSender("px-1", "tok-1")

        with patch_httpx(MODULE, "post", post):
            result = await sender.send([an_event()])

        assert post.await_count == 1
        assert result == {"events_received": 1}

    async def test_send_does_not_block_the_event_loop(self):
        """Two concurrent sends must overlap.

        Each stubbed call parks until both have started. Sequential execution
        can never satisfy that, so a blocking client fails this by timeout.
        """
        started = 0
        both_started = asyncio.Event()

        async def handler(*args, **kwargs):
            nonlocal started
            started += 1
            if started == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=5)
            return http_response(200, {"events_received": 1})

        sender = MetaEventsSender("px-1", "tok-1")
        with patch_httpx(MODULE, "post", AsyncMock(side_effect=handler)):
            await asyncio.gather(
                sender.send([an_event()]),
                sender.send([an_event()]),
            )

        assert started == 2

    async def test_transport_error_surfaces_as_httpx_error(self):
        post = AsyncMock(side_effect=httpx.ConnectError("dns fail"))
        sender = MetaEventsSender("px-1", "tok-1")

        with patch_httpx(MODULE, "post", post):
            with pytest.raises(httpx.HTTPError):
                await sender.send([an_event()])

    async def test_get_emq_scores_uses_httpx(self):
        get = AsyncMock(return_value=http_response(200, {"data": []}))
        sender = MetaEventsSender("px-1", "tok-1")

        with patch_httpx(MODULE, "get", get):
            result = await sender.get_emq_scores()

        assert get.await_count == 1
        assert result == {"data": []}
```

- [ ] **Step 2: Run the test and confirm it fails**

Push the branch and read the `Backend Tests` job. Expected failure: the mock is
never awaited (`post.await_count == 0`) because the code still calls
`requests.post`, and `test_send_does_not_block_the_event_loop` times out.

There is no local Python — CI is the run. Do not skip this step; a test that
has never been observed failing proves nothing.

- [ ] **Step 3: Add the httpx import**

In `backend/app/stratum/events/__init__.py`, add `import httpx` to the
third-party import block (isort: straight imports before `from` imports).
Leave `import requests` in place for now — later steps in this task remove it
once no references remain.

- [ ] **Step 4: Convert `MetaEventsSender.send`**

Replace lines 485-487:

```python
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
```

with:

```python
        # httpx, not requests: this is an async method, and a synchronous
        # client blocks the event loop for the whole request.
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
```

- [ ] **Step 5: Convert `MetaEventsSender.get_emq_scores`**

Replace lines 577-579:

```python
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
```

with:

```python
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 6: Widen the exception tuple at line ~913**

`UnifiedEventsAPI.send` catches `requests.RequestException`. httpx raises
`httpx.HTTPError` instead. Add it alongside rather than replacing, so the
tuple stays correct while other senders in this file are still on requests:

```python
                httpx.HTTPError,
                requests.RequestException,
                ConnectionError,
```

- [ ] **Step 7: Run the tests and confirm they pass**

Read `Backend Tests` in CI. All four tests in
`test_events_async_io.py` must pass, and the pre-existing events tests must
still pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/stratum/events/__init__.py \
        backend/tests/integration/test_events_async_io.py
git commit -m "fix(events): stop MetaEventsSender blocking the event loop"
```

---

### Task 2: Remaining event senders — `events/__init__.py`

**Files:**
- Modify: `backend/app/stratum/events/__init__.py` (`GoogleEventsSender.send` :607; `TikTokEventsSender.send` :701; `SnapchatEventsSender.send` :788; remove `import requests` if unreferenced)
- Test: `backend/tests/integration/test_events_async_io.py` (extend)

**Interfaces:**
- Consumes: `patch_httpx`, `http_response`, `an_event` from Task 1's test module.
- Produces: nothing new.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/integration/test_events_async_io.py`:

```python
from app.stratum.events import (
    GoogleEventsSender,
    SnapchatEventsSender,
    TikTokEventsSender,
)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: GoogleEventsSender("G-1", "secret-1"),
        lambda: TikTokEventsSender("px-1", "tok-1"),
        lambda: SnapchatEventsSender("px-1", "tok-1"),
    ],
    ids=["google", "tiktok", "snapchat"],
)
async def test_every_sender_awaits_its_http_call(factory):
    post = AsyncMock(return_value=http_response(200, {}))
    sender = factory()

    with patch_httpx(MODULE, "post", post):
        await sender.send([an_event()])

    assert post.await_count == 1
```

Check each sender's constructor signature before running — the argument names
above are placeholders for whatever `__init__` actually takes. Read
`events/__init__.py` at the class definitions (lines 582, 670, 766) and use
the real ones.

- [ ] **Step 2: Run and confirm failure**

Expected: `post.await_count == 0` for all three ids.

- [ ] **Step 3: Convert the three `send` methods**

Apply the same transformation as Task 1 Step 4 at lines 607, 701 and 788.
`TikTokEventsSender` and `SnapchatEventsSender` pass their arguments across
multiple lines — preserve the existing keyword arguments exactly, changing
only the call itself:

```python
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
```

Drop `timeout=30` from the call — it moves to the `AsyncClient` constructor.

- [ ] **Step 4: Remove the requests import if now unused**

```bash
grep -n "requests\." backend/app/stratum/events/__init__.py
```

If the only remaining hit is the `requests.RequestException` in the exception
tuple, keep both the import and the exception entry — other modules may still
raise it through this path. If there are no hits at all, delete
`import requests` and remove `requests.RequestException` from the tuple.

- [ ] **Step 5: Run tests and confirm they pass**

- [ ] **Step 6: Commit**

```bash
git add backend/app/stratum/events/__init__.py \
        backend/tests/integration/test_events_async_io.py
git commit -m "fix(events): convert Google/TikTok/Snapchat senders to httpx"
```

---

### Task 3: Conversions API — `conversions/__init__.py`

**Files:**
- Modify: `backend/app/stratum/conversions/__init__.py` (`MetaConversionsAPI.send_events` :266; `MetaConversionsAPI.get_emq_score` :347; `TikTokEventsAPI.send_events` :533; `SnapchatConversionsAPI.send_event` :641; exception clauses :275, :542, :649, :705, :742, :754)
- Test: `backend/tests/integration/test_conversions_async_io.py` (create)

**Interfaces:**
- Consumes: the `patch_httpx` / `http_response` helpers — copy them into this new module.
- Produces: nothing new.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_conversions_async_io.py` with the same
helper block as Task 1, then:

```python
MODULE = "app.stratum.conversions"


class TestConversionsAreAsync:
    async def test_meta_send_events_awaits(self):
        post = AsyncMock(return_value=http_response(200, {"events_received": 1}))
        api = MetaConversionsAPI(pixel_id="px-1", access_token="tok-1")

        with patch_httpx(MODULE, "post", post):
            result = await api.send_events([a_conversion_event()])

        assert post.await_count == 1
        assert result["events_received"] == 1

    async def test_meta_send_events_swallows_transport_error(self):
        """Existing behaviour: RequestException was caught and reported.

        httpx.HTTPError must be caught in the same place, or a transport
        failure that used to be handled starts propagating to callers.
        """
        post = AsyncMock(side_effect=httpx.ConnectError("dns fail"))
        api = MetaConversionsAPI(pixel_id="px-1", access_token="tok-1")

        with patch_httpx(MODULE, "post", post):
            result = await api.send_events([a_conversion_event()])

        assert result.get("success") is False
```

Read `MetaConversionsAPI.__init__` (line ~204) and the `except` block at line
275 first, and match `a_conversion_event()` and the failure-shape assertion to
what the code actually returns.

- [ ] **Step 2: Run and confirm failure**

- [ ] **Step 3: Add `import httpx`, convert the four call sites**

Same transformation as Task 1 Step 4, at lines 266, 347, 533 and 641.

- [ ] **Step 4: Update every exception clause in this file**

Lines 275, 542 and 649 are `except requests.RequestException as e:`. Change
each to:

```python
        except httpx.HTTPError as e:
```

Lines 705, 742 and 754 are exception tuples inside `UnifiedConversionsAPI`.
Replace `requests.RequestException,` with `httpx.HTTPError,` in each.

This step is the one that silently breaks things if skipped: the calls would
raise `httpx.HTTPError`, the handlers would still be watching for
`requests.RequestException`, and previously-handled failures would escape to
callers.

- [ ] **Step 5: Remove `import requests` once unreferenced**

```bash
grep -n "requests" backend/app/stratum/conversions/__init__.py
```

Expect zero hits. Delete the import.

- [ ] **Step 6: Run tests and confirm they pass**

- [ ] **Step 7: Commit**

```bash
git add backend/app/stratum/conversions/__init__.py \
        backend/tests/integration/test_conversions_async_io.py
git commit -m "fix(conversions): convert CAPI senders to httpx"
```

---

### Task 4: WhatsApp adapter — sync helper becomes async

**Files:**
- Modify: `backend/app/stratum/adapters/whatsapp_adapter.py` (`_make_request` :1055-1090; call sites :307, :383, :445, :514, :578, :653, :708, :996, :1024; direct sites :637, :963, :1173; exception clause :328)
- Test: `backend/tests/integration/test_adapter_whatsapp_deep.py` (extend)

**Interfaces:**
- Consumes: helper block copied in.
- Produces: `_make_request` becomes a coroutine — **every** caller must `await` it. This is the only signature change in the plan.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_adapter_whatsapp_deep.py`:

```python
async def test_make_request_is_a_coroutine_and_awaits_httpx():
    import inspect

    from app.stratum.adapters.whatsapp_adapter import WhatsAppAdapter

    assert inspect.iscoroutinefunction(WhatsAppAdapter._make_request)


async def test_send_text_message_awaits_its_http_call(adapter):
    post = AsyncMock(return_value=http_response(200, {"messages": [{"id": "m1"}]}))

    with patch_httpx("app.stratum.adapters.whatsapp_adapter", "post", post):
        await adapter.send_text_message("+9715xxxxxxx", "hello")

    assert post.await_count == 1
```

Reuse the module's existing `adapter` fixture. If it does not have one, build
the adapter the same way the neighbouring tests in that file do.

- [ ] **Step 2: Run and confirm failure**

Expected: `iscoroutinefunction` returns False.

- [ ] **Step 3: Convert `_make_request` to async**

Change the signature to `async def _make_request(...)` and replace the four
branches with a single client block:

```python
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(
                        url, headers=headers, json=data, params=params
                    )
                elif method == "DELETE":
                    response = await client.delete(
                        url, headers=headers, params=params
                    )
                else:
                    response = await client.request(
                        method, url, headers=headers, json=data
                    )

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
```

Note `client.delete` does not accept a `json=` body in httpx; the original
`requests.delete` call did not pass one either, so this is a faithful port.

- [ ] **Step 4: Add `await` to all nine call sites**

Lines 307, 383, 445, 514, 578, 653, 708, 996, 1024. Each currently reads
`response = self._make_request(` — change to `response = await self._make_request(`.
All nine are already inside `async def`, so no other change is needed.

Verify none were missed:

```bash
grep -n "self._make_request(" backend/app/stratum/adapters/whatsapp_adapter.py | grep -v "await self._make_request("
```

Expected: no output.

- [ ] **Step 5: Convert the three direct sites**

Lines 637, 963 and 1173 (`upload_media`, `mark_conversion`, `_upload_media_bytes`)
call `requests.*` directly inside `async def`. Apply the Task 1 Step 4
transformation to each. `upload_media` and `_upload_media_bytes` post
multipart file data — httpx takes the same `files=` keyword, so the payload
construction is unchanged.

- [ ] **Step 6: Fix the exception clause at line ~328**

Replace `requests.RequestException,` with `httpx.HTTPError,` in the tuple.

- [ ] **Step 7: Remove `import requests`, add `import httpx`**

```bash
grep -n "requests" backend/app/stratum/adapters/whatsapp_adapter.py
```

Expected: zero hits after the import is removed.

- [ ] **Step 8: Run tests and confirm they pass**

The whole existing WhatsApp suite must still pass — this task changes a
signature, so a missed `await` shows up as a coroutine being treated as a dict.

- [ ] **Step 9: Commit**

```bash
git add backend/app/stratum/adapters/whatsapp_adapter.py \
        backend/tests/integration/test_adapter_whatsapp_deep.py
git commit -m "fix(whatsapp): make _make_request async and drop blocking requests"
```

---

### Task 5: Snapchat token refresh and Google enhanced conversions

**Files:**
- Modify: `backend/app/stratum/adapters/snapchat_adapter.py` (`_refresh_access_token` :228)
- Modify: `backend/app/stratum/integrations/google_complete.py` (`send_event` :588)
- Test: `backend/tests/integration/test_adapter_snapchat_deep.py` (extend)

**Interfaces:**
- Consumes: helper block copied in.
- Produces: nothing new.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/integration/test_adapter_snapchat_deep.py`:

```python
async def test_token_refresh_does_not_block_the_event_loop(adapter):
    """Token refresh runs on the request path — blocking here stalls the worker
    for every tenant sharing it, not just the one whose token expired."""
    post = AsyncMock(
        return_value=http_response(
            200, {"access_token": "new-tok", "expires_in": 1800}
        )
    )

    with patch_httpx("app.stratum.adapters.snapchat_adapter", "post", post):
        await adapter._refresh_access_token()

    assert post.await_count == 1
    assert adapter.access_token == "new-tok"
```

- [ ] **Step 2: Run and confirm failure**

- [ ] **Step 3: Convert the Snapchat call**

Line 228, note this one posts form data via `data=`, not `json=`:

```python
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self.AUTH_URL, data=data)
        response.raise_for_status()
```

- [ ] **Step 4: Convert the Google call**

`google_complete.py` line 588, inside `async def send_event`. Same
transformation; read the surrounding lines first to preserve the exact
keyword arguments.

- [ ] **Step 5: Swap imports and exception types in both files**

Add `import httpx`, remove `import requests`, and change any
`requests.RequestException` in these two files to `httpx.HTTPError`.

- [ ] **Step 6: Run tests and confirm they pass**

- [ ] **Step 7: Verify the sweep is complete**

```bash
cd backend
for f in $(grep -rl "requests\.\(get\|post\|put\|delete\|patch\|request\)(" app/); do
  awk '/^[[:space:]]*(async[[:space:]]+)?def /{ isasync=($0 ~ /async def/) }
       /requests\.(get|post|put|delete|patch|request)\(/ { if (isasync) print FILENAME": "NR }' "$f"
done
```

Expected: no output. The only remaining `requests` references in `app/` should
be the documentation string in `api/v1/endpoints/developer.py`.

- [ ] **Step 8: Commit**

```bash
git add backend/app/stratum/adapters/snapchat_adapter.py \
        backend/app/stratum/integrations/google_complete.py \
        backend/tests/integration/test_adapter_snapchat_deep.py
git commit -m "fix(adapters): drop last blocking HTTP calls from async paths"
```

---

### Task 6: Run E2E against merged `main`

**Files:**
- Modify: `.github/workflows/ci.yml` (`e2e` job, line ~392)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing.

**Problem:** the `e2e` job is gated on `if: github.event_name == 'pull_request'`,
so the artifact actually deployed from `main` is never end-to-end tested. A
merge that is individually green can still produce a broken `main`.

- [ ] **Step 1: Widen the condition**

Replace:

```yaml
    if: github.event_name == 'pull_request'
```

with:

```yaml
    # Also run on push: a PR being green does not prove the merged result is.
    # Both events are covered, so this is simply "always" — kept explicit
    # rather than deleted so the intent survives the next edit.
    if: github.event_name == 'pull_request' || github.event_name == 'push'
```

- [ ] **Step 2: Validate the workflow parses**

```bash
npx --yes js-yaml .github/workflows/ci.yml > /dev/null && echo "YAML OK"
```

- [ ] **Step 3: Confirm the gate still reflects reality**

`Release Gate` lists `needs: [backend-quality, backend-tests, backend-security, frontend, security, secrets]` — `e2e` is deliberately not in it. Leave that alone; widening the trigger is the change, promoting E2E to a required gate is a separate decision with its own flakiness budget.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run E2E on push so merged main is tested, not just PRs"
```

---

### Task 7: Resolve the permanently-red Pages deploy

**Files:**
- Delete: `.github/workflows/pages.yml` **or** modify it — see decision below.

**Problem:** `Deploy Docs to GitHub Pages` has failed on **every run since at
least 2026-04-28** — 12+ consecutive failures. `GET /repos/{owner}/{repo}/pages`
returns 404: Pages is not enabled, so `actions/configure-pages@v5` fails at the
first step. It only runs on push to `main`, which is why no PR ever surfaced it.

**This task needs a human decision before any code changes.** The repository is
**private** and the workflow publishes `backend/docs/` — 60+ internal
architecture and deployment documents. Enabling Pages would make them public.
Private-visibility Pages also requires GitHub Enterprise Cloud or Team.

- [ ] **Step 1: Get the decision**

Ask the repository owner to choose:

- **(a) Delete the workflow** — docs are not published. Removes a permanently
  red check from every merge to `main`.
- **(b) Enable Pages** — Settings → Pages → Source: GitHub Actions. Accepts
  that `backend/docs/` becomes publicly readable.

- [ ] **Step 2a: If deleting**

```bash
git rm .github/workflows/pages.yml
git commit -m "ci: remove the Pages deploy workflow

It has failed on every run since 2026-04-28 because Pages is not enabled on
this repository, and the repo is private so publishing backend/docs/ is not
wanted. A check that is always red trains everyone to ignore red."
```

Also delete the vestigial `gh-pages` branch if nothing references it.

- [ ] **Step 2b: If enabling**

Enable Pages in repository settings with source "GitHub Actions", then re-run
the workflow. No file change is required — `configure-pages@v5` succeeds once
the Pages site exists.

- [ ] **Step 3: Confirm `main` is fully green**

After the next push to `main`, every check must be green or intentionally
skipped. No permanently-failing job may remain.

---

## Self-Review

**Spec coverage.** All 14 executing blocking-call sites are assigned: events 5
(Tasks 1-2), conversions 4 (Task 3), whatsapp 7 counting the four verbs inside
`_make_request` (Task 4), snapchat 1 and google 1 (Task 5). The two
`developer.py` hits are explicitly excluded with a reason. Both CI gaps are
covered (Tasks 6-7).

**Placeholders.** Three steps deliberately say "read the surrounding lines
first" — Task 2 Step 1 (sender constructor signatures), Task 3 Step 1
(`MetaConversionsAPI.__init__` and the failure shape), Task 5 Step 4 (Google's
keyword arguments). These are not TODOs: the transformation is fully specified,
and the instruction is to match argument names that could not be verified
without running the code. Every code block is complete and runnable.

**Type consistency.** `patch_httpx(module, verb, handler)` and
`http_response(status_code, payload)` keep the same signatures in all four test
modules. `_make_request` is the only production signature change and Task 4
Step 4 enumerates all nine call sites plus a verification grep.

## Out of scope for this plan

The request that produced this plan also asked for a **full project review** —
code, security, API, backend, frontend. That is an audit, not an
implementation, and writing it as tasks with predetermined "fixes" would be
fabrication: the findings do not exist yet. It needs its own pass, scoped
separately, and should run **after** these tasks land so it reviews the
corrected code rather than generating findings this plan already resolves.
