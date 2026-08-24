# Activation Checklist — Copilot LLM Bridge

The Copilot LLM bridge was shipped as code in commit `58e9856`. It's
**off by default** until three env vars are set on the backend
service. This checklist covers turning it on safely.

> **Status:** activated on production 2026-08-24. RAG
> (`COPILOT_RAG_ENABLED`) remains off — see "Shipped since this
> checklist was written" below. Re-verify against the running
> container, not this document, before relying on either.

## What ships in the code

```
backend/app/services/agents/copilot_llm.py     New — Anthropic Claude bridge
backend/app/api/v1/endpoints/copilot.py        Calls generate_llm_message()
                                               and overrides response.message
                                               when the LLM returns text
backend/app/core/config.py                     copilot_llm_enabled (default False)
                                               anthropic_api_key (default None)
                                               copilot_llm_model
                                               copilot_llm_max_tokens (600)
                                               copilot_llm_timeout_seconds (8.0)
backend/requirements.txt                       anthropic==0.45.2
```

Added after the original Phase D commit:

```
backend/app/services/agents/copilot_llm_stream.py   Streaming variant
backend/app/services/agents/doc_index.py            RAG chunk/embed/retrieve
backend/app/models/copilot_doc.py                   copilot_doc_chunks
backend/app/core/config.py                          copilot_rag_enabled
                                                    openai_api_key
                                                    copilot_rag_top_k
                                                    copilot_rag_chunk_chars
```

The keyword classifier still runs first — it produces the intent,
the suggestion chips, and the structured data cards that the dashboard
renders deterministically. The LLM bridge only swaps in a Claude-
generated **message text**. If anything fails (missing key, network,
timeout, rate limit, truncation), the template message stays in place.
Users never see a degraded experience.

## Step 1 — Get an Anthropic API key

1. Sign in at https://console.anthropic.com
2. Workspace → **API Keys** → **Create key**. Name it something like
   `Stratum Production Copilot`.
3. Copy the value. It starts with `sk-ant-api03-…`. Treat like a Stripe
   secret — store in your password manager, **never** paste it into
   chat, a ticket, or a commit. Anything pasted into a transcript is
   compromised: revoke it and issue a new one rather than reusing it.

To get the key onto the host without leaving it in shell history,
either paste it inside an editor (`nano /opt/stratum/.env`) or use a
hidden read:

```
read -s -p "key: " K && printf '\nANTHROPIC_API_KEY=%s\n' "$K" >> /opt/stratum/.env && unset K
```

`read -s` keeps the value off the screen and out of `.bash_history`.

## Step 2 — Add a hard usage cap (optional but recommended)

In the Anthropic console:

1. Workspace settings → **Usage Limits**
2. Set a monthly cap (e.g. $50 / month while you're getting comfortable
   with cost shape). The bridge's `copilot_llm_max_tokens=600` plus
   typical input ≈ 2000 tokens means a Haiku call costs ~$0.003.
   $50 ≈ 16,000 calls.

## Step 3 — Set the env vars on the backend

Add all three to `/opt/stratum/.env` (mode 600) on the Hetzner origin:

| Variable              | Value                                |
| --------------------- | ------------------------------------ |
| `ANTHROPIC_API_KEY`   | the `sk-ant-api03-…` key from Step 1 |
| `COPILOT_LLM_ENABLED` | `true`                               |
| `COPILOT_LLM_MODEL`   | `claude-haiku-4-5-20251001`          |

Then restart so the containers actually load them. Use the **Deploy
workflow** — `gh workflow run deploy.yml -f target=prod` — or
`bash ./scripts/deploy-hetzner.sh update` on the host.

> **Never run a bare `docker compose up -d` in `/opt/stratum`.** It
> took production down on 2026-08-24. Prod's API publishes no host
> port (`ports: !reset []` in `docker-compose.hetzner.yml`), but the
> base `docker-compose.yml` publishes `127.0.0.1:8000` — which
> `stratum_staging_api` already holds. Omitting the `-f` overlays
> recreates the API from base config and it fails to bind. If you must
> run compose by hand, pass the full set from
> `scripts/deploy-remote.sh`:
> `-f docker-compose.yml -f docker-compose.prod.yml -f
> docker-compose.hetzner.yml -f docker-compose.observability.yml`.

### Two failure modes that look like success

**A wrong model ID is silent.** `copilot_llm.py` catches every
exception and returns `text=None`, which the caller reads as "use the
template". So a typo'd or truncated `COPILOT_LLM_MODEL` means Anthropic
rejects every call, the error is swallowed, and the Copilot keeps
answering in templates — with the flag still reading `true`. Verify the
value in full, not by eye:

```
docker exec stratum_api printenv COPILOT_LLM_MODEL
```

**The file is not the process.** Containers read env at start, so a
variable can sit in `.env` while the running API knows nothing about
it. Always confirm against the container, never `grep` the file:

```
docker exec stratum_api printenv COPILOT_LLM_ENABLED
docker exec stratum_api printenv ANTHROPIC_API_KEY | wc -c
```

Expect `true` and a count near 108. `wc -c` proves the key is present
without printing it.

> **Model choice:** `claude-haiku-4-5` is the cheap+fast default.
> If responses feel weak, switch to `claude-sonnet-4-5-20251001` —
> ~5× the cost per call, noticeably better reasoning on harder
> dashboard questions.

## Step 4 — Verify on the deployed dashboard

1. Open the dashboard, click the Copilot bubble at the bottom-right.
2. Send: **"What's my signal health?"**
3. Expected: a conversational, paragraph-shaped answer that cites your
   live numbers (e.g. "Your composite score is 87. EMQ is at 0.95
   which is healthy; event loss is the weakest input at…").
   Pre-LLM template is short and templated; post-LLM is prose.
4. Check `docker logs stratum_api` for `copilot_llm_response` events including
   `input_tokens` and `output_tokens` per call.

## Step 5 — Verify the fallback works

Disable temporarily to confirm the keyword path still works:

```
COPILOT_LLM_ENABLED=false   # edit .env, then deploy-hetzner.sh update
```

Send the same question. The response should still answer (template-
shaped, shorter prose). Re-enable when satisfied.

## Rollback

If something goes wrong on production:

```
COPILOT_LLM_ENABLED=false
```

Edit .env → redeploy → Copilot reverts to the keyword classifier with
zero code changes. The bridge is fail-open by design; this just makes
the bypass explicit.

## Cost monitoring

Every successful call is logged via structlog at `logger.info` with
key `copilot_llm_response`:

```
{
  "event": "copilot_llm_response",
  "model": "claude-haiku-4-5-20251001",
  "intent": "signal_health",
  "input_tokens": 1840,
  "output_tokens": 142,
  "stop_reason": "end_turn",
  "message_chars": 612
}
```

Aggregate `input_tokens + output_tokens` across the day to estimate
Anthropic spend. If you ship a metrics pipeline, drop these straight
into a counter named `copilot_llm_tokens_total` with `{model, intent}`
labels.

## Shipped since this checklist was written

Two things this document listed as "out of scope" have since landed.
Both are off by default and gated the same way the LLM bridge is.

**RAG over Stratum docs** — `copilot_llm.py` retrieves the top-K most
relevant doc chunks and injects them as grounding context, returning
source paths so the dashboard can render citations. Requires two more
env vars:

| Variable             | Value                                        |
| -------------------- | -------------------------------------------- |
| `COPILOT_RAG_ENABLED`| `true`                                       |
| `OPENAI_API_KEY`     | embeddings only — `text-embedding-3-small`   |

Corpus must be indexed into `copilot_doc_chunks` first (see
`app/services/agents/doc_index.py`). Retrieval failure is non-fatal:
it falls back to LLM-without-docs and returns empty citations rather
than failing the call. Note this adds a **second vendor** — decide
that deliberately rather than switching it on with the Claude bridge.

**Streaming responses** — `POST /copilot/chat/stream` streams the
message via `app/services/agents/copilot_llm_stream.py`. If the LLM
fails before any token is emitted, the stream carries
`fallback_message` instead.

## Out of scope for this checklist

- Switching providers (Vertex AI etc.) for the *message* bridge — it
  is Anthropic-specific. To swap, replace the `from anthropic import …`
  block in `copilot_llm.py` with the equivalent SDK. (Embeddings for
  RAG are separately OpenAI-specific.)

## Owner

Operator setting these env vars must have **superadmin** role on the
Stratum platform. The Anthropic key itself is workspace-scoped and
not bound to a Stratum user — anyone with host access to the
backend service can rotate it.
