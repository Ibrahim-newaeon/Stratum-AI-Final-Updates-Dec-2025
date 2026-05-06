# =============================================================================
# Stratum AI - Copilot LLM Bridge
# =============================================================================
"""
LLM-backed message generator for the Copilot.

This is an *optional* upgrade path on top of the keyword classifier in
`copilot_agent.py`. When `settings.copilot_llm_enabled` is True and a
working Anthropic API key is configured, we hand the user's question
plus the tenant's live metrics to Claude and use Claude's prose as the
response text. The keyword classifier still runs first to produce
`intent`, `suggestions`, and `data_cards` — those stay deterministic
so the dashboard's UX (chip suggestions, structured cards) doesn't
change between LLM-on and LLM-off.

Failure semantics: any error (missing key, network, rate limit,
timeout, validation, truncation) returns None. The caller treats None
as "use the template message" and shows the keyword-classifier output
unchanged. The user never sees an LLM error.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# System prompt
# =============================================================================

SYSTEM_PROMPT = """You are Stratum Copilot, an in-product assistant inside the \
Stratum AI dashboard. Stratum is a Revenue Operating System for agency \
ad-ops teams: every automation passes a Trust Gate (a composite of \
EMQ 35%, API health 25%, event loss 20%, platform stability 10%, data \
quality 10%) before it touches a client's budget.

Your job is to answer the operator's question in 2–4 short sentences \
using the live data they're given below. Be concrete, cite numbers \
exactly as provided, and end with one actionable next step when the \
question implies one.

Tone: confident, calm, professional. No hedging filler ("It looks like…", \
"It seems…"). No marketing. No emojis. No headings. No bullet lists \
unless the user explicitly asked for a list. Plain prose.

If the data shows a problem, name it. If the data is missing or null, \
say so honestly — never invent numbers. If the user's question is \
outside the dashboard's scope (general advice, code, weather), \
politely decline and redirect to a Stratum-relevant follow-up."""


def _build_user_prompt(
    message: str,
    user_name: Optional[str],
    metrics: Optional[Dict[str, Any]],
    health_data: Optional[Dict[str, Any]],
    anomaly_data: Optional[Dict[str, Any]],
    intent: str,
) -> str:
    """Compose the user-turn content with structured live context."""
    context: Dict[str, Any] = {
        "classified_intent": intent,
        "user_first_name": user_name,
        "metrics": _safe(metrics),
        "signal_health": _safe(health_data),
        "anomalies": _safe(anomaly_data),
    }
    return (
        f"Live tenant context (JSON):\n```json\n{json.dumps(context, default=str, indent=2)}\n```\n\n"
        f"Operator's message:\n{message}\n"
    )


def _safe(value: Any) -> Any:
    """Drop None/empty so the prompt stays compact."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if v is not None}
    return value


# =============================================================================
# Generator
# =============================================================================

async def generate_llm_message(
    message: str,
    user_name: Optional[str],
    metrics: Optional[Dict[str, Any]],
    health_data: Optional[Dict[str, Any]],
    anomaly_data: Optional[Dict[str, Any]],
    intent: str,
) -> Optional[str]:
    """
    Generate a Copilot response message via Anthropic Claude.

    Returns:
        - the model's prose response on success
        - None on any failure (caller falls back to template message)
    """
    if not settings.copilot_llm_enabled:
        return None
    if not settings.anthropic_api_key:
        logger.warning("copilot_llm_disabled_no_key")
        return None

    try:
        # Lazy import so the SDK stays optional at import-time. If
        # anthropic isn't installed (e.g. dev env without LLM enabled),
        # this only blows up when the feature is actually toggled on.
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.warning("copilot_llm_anthropic_sdk_missing")
        return None

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model=settings.copilot_llm_model,
                max_tokens=settings.copilot_llm_max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": _build_user_prompt(
                            message=message,
                            user_name=user_name,
                            metrics=metrics,
                            health_data=health_data,
                            anomaly_data=anomaly_data,
                            intent=intent,
                        ),
                    }
                ],
            ),
            timeout=settings.copilot_llm_timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "copilot_llm_timeout",
            timeout=settings.copilot_llm_timeout_seconds,
            model=settings.copilot_llm_model,
        )
        return None
    except Exception as e:  # noqa: BLE001 — fail open on any SDK error
        logger.warning(
            "copilot_llm_error",
            error_type=type(e).__name__,
            error=str(e)[:200],
            model=settings.copilot_llm_model,
        )
        return None

    # Extract the first text block. The Messages API returns a list of
    # content blocks; we only use text — no tools/images here.
    text_parts = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text" and getattr(block, "text", None)
    ]
    if not text_parts:
        logger.warning("copilot_llm_empty_response", model=settings.copilot_llm_model)
        return None

    output = "\n".join(text_parts).strip()
    if not output:
        return None

    # Cost / observability log. Token counts come back on the response
    # usage object across all current Anthropic SDK versions.
    usage = getattr(response, "usage", None)
    logger.info(
        "copilot_llm_response",
        model=settings.copilot_llm_model,
        intent=intent,
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        stop_reason=getattr(response, "stop_reason", None),
        message_chars=len(output),
    )
    return output
