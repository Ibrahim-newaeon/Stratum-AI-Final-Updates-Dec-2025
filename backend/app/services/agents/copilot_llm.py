# =============================================================================
# Stratum AI - Copilot LLM Bridge
# =============================================================================
"""
LLM-backed message generator for the Copilot.

This is an *optional* upgrade path on top of the keyword classifier in
`copilot_agent.py`. When `settings.copilot_llm_enabled` is True and a
working Anthropic API key is configured, we hand the user's question
plus the tenant's live metrics to Claude and use Claude's prose as the
response text.

When `settings.copilot_rag_enabled` is also True (and OPENAI_API_KEY is
set), we additionally retrieve the top-K most relevant Stratum doc
chunks for the operator's question and inject them into the prompt as
grounding context, returning the source paths back so the dashboard can
render citations underneath the response.

The keyword classifier still runs first to produce `intent`,
`suggestions`, and `data_cards` — those stay deterministic so the
dashboard's UX (chip suggestions, structured cards) doesn't change
between LLM-on and LLM-off.

Failure semantics: any error (missing key, network, rate limit,
timeout, validation, truncation) returns ``LLMResult(text=None, citations=[])``.
The caller treats `text=None` as "use the template message" and shows
the keyword-classifier output unchanged. RAG retrieval failures are
non-fatal — we log + fall back to LLM-without-docs and return empty
citations rather than failing the whole call.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Public types
# =============================================================================


@dataclass(frozen=True)
class Citation:
    """A doc reference that the dashboard can render under the response."""

    source_path: str  # e.g. "docs/architecture/trust-engine.md"
    title: str  # e.g. "Trust Engine » Phases"
    distance: float


@dataclass(frozen=True)
class LLMResult:
    """Output of generate_llm_message."""

    text: Optional[str]
    citations: List[Citation] = field(default_factory=list)


# =============================================================================
# System prompt
# =============================================================================

SYSTEM_PROMPT = """You are Stratum Copilot, an in-product assistant inside the \
Stratum AI dashboard. Stratum is a Revenue Operating System for agency \
ad-ops teams: every automation passes a Trust Gate (a composite of \
EMQ 35%, API health 25%, event loss 20%, platform stability 10%, data \
quality 10%) before it touches a client's budget.

Your job is to answer the operator's question in 2–4 short sentences \
using the live data and Stratum doc excerpts they're given below. Be \
concrete, cite numbers exactly as provided, and end with one actionable \
next step when the question implies one.

When the answer relies on a Stratum doc excerpt, ground your wording in \
that excerpt — don't paraphrase loosely or invent details. The dashboard \
will render the source docs as citations underneath your reply, so don't \
restate file paths in prose.

Tone: confident, calm, professional. No hedging filler ("It looks like…", \
"It seems…"). No marketing. No emojis. No headings. No bullet lists \
unless the user explicitly asked for a list. Plain prose.

If the data shows a problem, name it. If the data is missing or null, \
say so honestly — never invent numbers. If the user's question is \
outside the dashboard's scope (general advice, code, weather), \
politely decline and redirect to a Stratum-relevant follow-up."""


# =============================================================================
# Prompt building
# =============================================================================


def _build_user_prompt(
    message: str,
    user_name: Optional[str],
    metrics: Optional[Dict[str, Any]],
    health_data: Optional[Dict[str, Any]],
    anomaly_data: Optional[Dict[str, Any]],
    intent: str,
    docs: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Compose the user-turn content with structured live context + docs."""
    context: Dict[str, Any] = {
        "classified_intent": intent,
        "user_first_name": user_name,
        "metrics": _safe(metrics),
        "signal_health": _safe(health_data),
        "anomalies": _safe(anomaly_data),
    }
    parts: List[str] = [
        f"Live tenant context (JSON):\n```json\n{json.dumps(context, default=str, indent=2)}\n```\n"
    ]
    if docs:
        parts.append(_format_doc_excerpts(docs))
    parts.append(f"Operator's message:\n{message}\n")
    return "\n".join(parts)


def _format_doc_excerpts(docs: List[Dict[str, Any]]) -> str:
    """
    Render retrieved doc chunks as a numbered block. Numbers are
    1-based to read naturally in prose. Each entry is content-only —
    Claude doesn't need the file path inline, since citations come
    back through the structured response.
    """
    lines: List[str] = ["Stratum doc excerpts (most relevant first):"]
    for i, doc in enumerate(docs, start=1):
        title = doc.get("title") or doc.get("source_path") or "untitled"
        content = (doc.get("content") or "").strip()
        # Trim aggressive whitespace — chunks already preserve paragraph
        # boundaries, but multiple blank lines waste tokens.
        content = "\n".join(
            line.rstrip() for line in content.split("\n") if line.strip()
        )
        lines.append(f"\n[{i}] {title}\n{content}")
    return "\n".join(lines)


def _safe(value: Any) -> Any:
    """Drop None/empty so the prompt stays compact."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if v is not None}
    return value


# =============================================================================
# RAG retrieval (best-effort wrapper around doc_index.retrieve_top_k)
# =============================================================================


async def _retrieve_docs(
    db: Optional[AsyncSession],
    query: str,
) -> tuple[List[Dict[str, Any]], List[Citation]]:
    """
    Best-effort doc retrieval. Returns ([] , []) on:
      - RAG not enabled
      - missing OPENAI_API_KEY
      - missing AsyncSession
      - any retrieval error (logged, swallowed)
    Never raises.
    """
    if not settings.copilot_rag_enabled or db is None:
        return [], []
    if not settings.openai_api_key:
        logger.warning("copilot_rag_no_openai_key")
        return [], []

    try:
        # Lazy import: only pulls in `openai` SDK when the flag is on.
        from app.services.agents.doc_index import retrieve_top_k

        chunks = await retrieve_top_k(db, query)
    except Exception as exc:  # noqa: BLE001 — fail open
        logger.warning(
            "copilot_rag_retrieval_failed",
            error_type=type(exc).__name__,
            error=str(exc)[:200],
        )
        return [], []

    docs: List[Dict[str, Any]] = []
    citations: List[Citation] = []
    for chunk in chunks:
        meta = chunk.metadata or {}
        title = meta.get("title") or chunk.source_path
        # Use the heading path when available — operators recognize
        # "Trust Engine » Phases" faster than a filename.
        heading_path = meta.get("heading_path") or []
        if heading_path:
            title = " » ".join(heading_path)
        docs.append(
            {
                "source_path": chunk.source_path,
                "title": title,
                "content": chunk.content,
            }
        )
        citations.append(
            Citation(
                source_path=chunk.source_path,
                title=title,
                distance=chunk.distance,
            )
        )
    return docs, citations


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
    *,
    db: Optional[AsyncSession] = None,
) -> LLMResult:
    """
    Generate a Copilot response via Anthropic Claude, optionally grounded
    in Stratum doc excerpts retrieved by similarity.

    Returns:
        LLMResult(text, citations)
        - text=None on any LLM failure (caller falls back to template).
        - citations=[] when RAG is disabled, no key, or no relevant docs.
        - text=str + citations=[] is valid when LLM succeeds without RAG.
    """
    if not settings.copilot_llm_enabled:
        return LLMResult(text=None)
    if not settings.anthropic_api_key:
        logger.warning("copilot_llm_disabled_no_key")
        return LLMResult(text=None)

    try:
        # Lazy import so the SDK stays optional at import-time.
        from anthropic import AsyncAnthropic
    except ImportError:
        logger.warning("copilot_llm_anthropic_sdk_missing")
        return LLMResult(text=None)

    # Best-effort RAG retrieval. Failures don't kill the bridge.
    docs, citations = await _retrieve_docs(db, message)

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
                            docs=docs,
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
        return LLMResult(text=None, citations=citations)
    except Exception as e:  # noqa: BLE001 — fail open on any SDK error
        logger.warning(
            "copilot_llm_error",
            error_type=type(e).__name__,
            error=str(e)[:200],
            model=settings.copilot_llm_model,
        )
        return LLMResult(text=None, citations=citations)

    text_parts = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text" and getattr(block, "text", None)
    ]
    if not text_parts:
        logger.warning("copilot_llm_empty_response", model=settings.copilot_llm_model)
        return LLMResult(text=None, citations=citations)

    output = "\n".join(text_parts).strip()
    if not output:
        return LLMResult(text=None, citations=citations)

    usage = getattr(response, "usage", None)
    logger.info(
        "copilot_llm_response",
        model=settings.copilot_llm_model,
        intent=intent,
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        stop_reason=getattr(response, "stop_reason", None),
        message_chars=len(output),
        citation_count=len(citations),
        rag_enabled=settings.copilot_rag_enabled and len(docs) > 0,
    )
    if citations:
        logger.info(
            "copilot_rag_retrieved",
            citation_count=len(citations),
            top_distance=citations[0].distance if citations else None,
            sources=[c.source_path for c in citations],
        )
    return LLMResult(text=output, citations=citations)


__all__ = ["Citation", "LLMResult", "generate_llm_message"]
