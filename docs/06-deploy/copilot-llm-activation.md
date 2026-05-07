# Activation Checklist — Copilot LLM Bridge (Phase D)

The Copilot LLM bridge was shipped as code in commit `58e9856`. It's
**off by default** until three Railway env vars are set on the backend
service. This checklist covers turning it on safely.

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
3. Copy the value. It starts with `sk-ant-api03-…`. Treat like Stripe
   secret — store in your password manager, **never** paste in chat.

## Step 2 — Add a hard usage cap (optional but recommended)

In the Anthropic console:

1. Workspace settings → **Usage Limits**
2. Set a monthly cap (e.g. $50 / month while you're getting comfortable
   with cost shape). The bridge's `copilot_llm_max_tokens=600` plus
   typical input ≈ 2000 tokens means a Haiku call costs ~$0.003.
   $50 ≈ 16,000 calls.

## Step 3 — Set Railway env vars on the backend service

Railway dashboard → your project → **backend** service → **Variables**
tab → **+ New Variable**. Add three:

| Variable              | Value                                |
| --------------------- | ------------------------------------ |
| `ANTHROPIC_API_KEY`   | the `sk-ant-api03-…` key from Step 1 |
| `COPILOT_LLM_ENABLED` | `true`                               |
| `COPILOT_LLM_MODEL`   | `claude-haiku-4-5-20251001`          |

Click **Deploy** if Railway doesn't redeploy automatically.

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
4. Check Railway logs for `copilot_llm_response` events including
   `input_tokens` and `output_tokens` per call.

## Step 5 — Verify the fallback works

Disable temporarily to confirm the keyword path still works:

```
COPILOT_LLM_ENABLED=false   # Railway → save → wait for redeploy
```

Send the same question. The response should still answer (template-
shaped, shorter prose). Re-enable when satisfied.

## Rollback

If something goes wrong on production:

```
COPILOT_LLM_ENABLED=false
```

Save → Railway redeploys → Copilot reverts to keyword classifier with
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

## Out of scope for this checklist

- Switching providers (OpenAI / Vertex AI / etc.) — the bridge is
  Anthropic-specific. To swap, replace the `from anthropic import …`
  block in `copilot_llm.py` with the equivalent SDK.
- RAG over Stratum docs — current implementation passes raw live
  metrics as context. Adding doc retrieval is a separate, larger
  effort.
- Streaming responses — the API endpoint returns a complete message;
  no SSE / chunked streaming wired up yet.

## Owner

Operator setting these env vars must have **superadmin** role on the
Stratum platform. The Anthropic key itself is workspace-scoped and
not bound to a Stratum user — anyone with Railway access to the
backend service can rotate it.
