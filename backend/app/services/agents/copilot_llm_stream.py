# =============================================================================
# Stratum AI - Copilot LLM Streaming Bridge
# =============================================================================
"""
Streaming variant of the Copilot LLM bridge.

Yields SSE-shaped events for the FastAPI /copilot/chat/stream endpoint
to relay to the browser. The contract is intentionally narrow so the
frontend SSE parser stays simple:

    event: token   data: "<text fragment>"   ← multiple, in order
    event: meta    data: {                    ← exactly one, before [DONE]
        "citations": [...],
        "intent": "...",
        "suggestions": [...],
        "data_cards": [...],
        "fallback_message": "...",            ← only present if streaming failed
    }
    event: error   data: "<short message>"    ← optional; followed by meta
    data: [DONE]                              ← always last

Token events are plain text (not JSON) because that's the natural
shape Anthropic streams and the frontend just needs to append. The
`meta` event is a single JSON object so the dashboard can render
citations, suggestions, and data cards once the stream completes.

Failure semantics are preserved: any failure path emits a meta event
with `fallback_message` populated from the keyword classifier so the
dashboard can replace the partial stream with the deterministic
template message rather than show a half-written response.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any, AsyncIterator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.services.agents.copilot_llm import (
    SYSTEM_PROMPT,
    Citation,
    _build_user_prompt,
    _retrieve_docs,
)

logger = get_logger(__name__)


# =============================================================================
# SSE event helpers
# =============================================================================


def _format_sse(event: str, data: str) -> str:
    """Frame a single SSE event. data is escaped per the SSE spec."""
    payload = data.replace("\r\n", "\n")
    lines = [f"event: {event}"]
    for line in payload.split("\n"):
        lines.append(f"data: {line}")
    lines.append("")  # trailing blank line terminates the event
    lines.append("")
    return "\n".join(lines)


def _format_sse_done() -> str:
    """The terminal '[DONE]' marker — separate event since it has no `event:` field."""
    return "data: [DONE]\n\n"


def _meta_payload(
    *,
    citations: List[Citation],
    intent: str,
    suggestions: List[str],
    data_cards: List[Dict[str, Any]],
    fallback_message: Optional[str] = None,
) -> str:
    """Build the JSON body of the `meta` event."""
    body: Dict[str, Any] = {
        "intent": intent,
        "suggestions": suggestions,
        "data_cards": data_cards,
        "citations": [
            {
                "source_path": c.source_path,
                "title": c.title,
                "distance": c.distance,
            }
            for c in citations
        ],
    }
    if fallback_message is not None:
        body["fallback_message"] = fallback_message
    return json.dumps(body, default=str)


# =============================================================================
# Streaming generator
# =============================================================================


async def stream_llm_message(
    *,
    message: str,
    user_name: Optional[str],
    metrics: Optional[Dict[str, Any]],
    health_data: Optional[Dict[str, Any]],
    anomaly_data: Optional[Dict[str, Any]],
    intent: str,
    suggestions: List[str],
    data_cards: List[Dict[str, Any]],
    fallback_message: str,
    db: Optional[AsyncSession] = None,
) -> AsyncIterator[str]:
    """
    Async generator that yields SSE-formatted strings.

    `fallback_message` is the keyword-classifier template — emitted in
    the meta event whenever the LLM path fails so the frontend can
    swap the partial stream for the deterministic message.
    """
    # ── Off-paths emit fallback meta + done immediately ───────────────
    if not settings.copilot_llm_enabled or not settings.anthropic_api_key:
        yield _format_sse(
            "meta",
            _meta_payload(
                citations=[],
                intent=intent,
                suggestions=suggestions,
                data_cards=data_cards,
                fallback_message=fallback_message,
            ),
        )
        yield _format_sse_done()
        return

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.warning("copilot_llm_anthropic_sdk_missing")
        yield _format_sse(
            "meta",
            _meta_payload(
                citations=[],
                intent=intent,
                suggestions=suggestions,
                data_cards=data_cards,
                fallback_message=fallback_message,
            ),
        )
        yield _format_sse_done()
        return

    docs, citations = await _retrieve_docs(db, message)

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_prompt = _build_user_prompt(
        message=message,
        user_name=user_name,
        metrics=metrics,
        health_data=health_data,
        anomaly_data=anomaly_data,
        intent=intent,
        docs=docs,
    )

    text_chars = 0
    final_stop_reason: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    streamed_any_token = False

    try:
        async with asyncio.timeout(settings.copilot_llm_timeout_seconds):
            async with client.messages.stream(
                model=settings.copilot_llm_model,
                max_tokens=settings.copilot_llm_max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                async for text_delta in stream.text_stream:
                    if not text_delta:
                        continue
                    streamed_any_token = True
                    text_chars += len(text_delta)
                    yield _format_sse("token", text_delta)
                # Final metadata when the stream completes cleanly.
                final_message = await stream.get_final_message()
                final_stop_reason = getattr(final_message, "stop_reason", None)
                usage = getattr(final_message, "usage", None)
                if usage is not None:
                    input_tokens = getattr(usage, "input_tokens", None)
                    output_tokens = getattr(usage, "output_tokens", None)
    except asyncio.TimeoutError:
        logger.warning(
            "copilot_llm_stream_timeout",
            timeout=settings.copilot_llm_timeout_seconds,
            model=settings.copilot_llm_model,
            streamed_any_token=streamed_any_token,
        )
        yield _format_sse("error", "timeout")
        yield _format_sse(
            "meta",
            _meta_payload(
                citations=citations,
                intent=intent,
                suggestions=suggestions,
                data_cards=data_cards,
                fallback_message=fallback_message if not streamed_any_token else None,
            ),
        )
        yield _format_sse_done()
        return
    except Exception as exc:  # noqa: BLE001 — fail open
        logger.warning(
            "copilot_llm_stream_error",
            error_type=type(exc).__name__,
            error=str(exc)[:200],
            model=settings.copilot_llm_model,
            streamed_any_token=streamed_any_token,
        )
        yield _format_sse("error", "stream_error")
        yield _format_sse(
            "meta",
            _meta_payload(
                citations=citations,
                intent=intent,
                suggestions=suggestions,
                data_cards=data_cards,
                fallback_message=fallback_message if not streamed_any_token else None,
            ),
        )
        yield _format_sse_done()
        return

    # ── Success: emit meta + done ─────────────────────────────────────
    yield _format_sse(
        "meta",
        _meta_payload(
            citations=citations,
            intent=intent,
            suggestions=suggestions,
            data_cards=data_cards,
            # fallback only if the model produced nothing at all
            fallback_message=fallback_message if not streamed_any_token else None,
        ),
    )
    yield _format_sse_done()

    logger.info(
        "copilot_llm_stream_complete",
        model=settings.copilot_llm_model,
        intent=intent,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        stop_reason=final_stop_reason,
        message_chars=text_chars,
        citation_count=len(citations),
        rag_enabled=settings.copilot_rag_enabled and len(docs) > 0,
    )


__all__ = [
    "_format_sse",
    "_format_sse_done",
    "_meta_payload",
    "stream_llm_message",
]
