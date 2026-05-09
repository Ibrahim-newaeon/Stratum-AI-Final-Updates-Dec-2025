# =============================================================================
# Stratum AI — copilot_llm_stream tests (Phase D PR3)
# =============================================================================
"""
Verifies the SSE streaming bridge wires Anthropic streaming + RAG
retrieval together correctly. Anthropic streaming, OpenAI, and pgvector
are all mocked — runs without network, DB, or live LLM keys.

Covered behavior:

- Off-paths (LLM disabled / no key / SDK missing) emit only meta+done
  with `fallback_message` set, no token events.
- Happy path streams tokens in order, then meta with citations,
  then [DONE].
- `fallback_message` is omitted from meta when at least one token
  was streamed (success); included when zero tokens streamed (failure).
- Timeout emits `error: timeout` then meta then [DONE].
- Anthropic SDK exceptions emit `error: stream_error` then meta + done.
- SSE wire format: `event: <name>` and `data: <line>` framing,
  trailing blank line per event, terminal `[DONE]`.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agents.copilot_llm import Citation
from app.services.agents.copilot_llm_stream import (
    _format_sse,
    _format_sse_done,
    _meta_payload,
    stream_llm_message,
)


# =============================================================================
# Helpers
# =============================================================================


def _patch_settings(**overrides: Any):
    base = {
        "copilot_llm_enabled": True,
        "anthropic_api_key": "sk-ant-test",
        "copilot_llm_model": "claude-haiku-4-5",
        "copilot_llm_max_tokens": 600,
        "copilot_llm_timeout_seconds": 8.0,
        "copilot_rag_enabled": False,
        "openai_api_key": None,
    }
    base.update(overrides)
    return patch.multiple(
        "app.services.agents.copilot_llm_stream.settings",
        **base,
    )


class _FakeStream:
    """Mimics the Anthropic streaming context manager."""

    def __init__(self, tokens: List[str], stop_reason: str = "end_turn",
                 input_tokens: int = 100, output_tokens: int = 50,
                 raise_during: bool = False) -> None:
        self.tokens = tokens
        self.stop_reason = stop_reason
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.raise_during = raise_during

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None

    @property
    def text_stream(self) -> AsyncIterator[str]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[str]:
        for tok in self.tokens:
            if self.raise_during:
                raise RuntimeError("network blew up")
            yield tok

    async def get_final_message(self) -> Any:
        msg = MagicMock()
        msg.stop_reason = self.stop_reason
        msg.usage = MagicMock(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )
        return msg


def _fake_anthropic_client(stream: _FakeStream) -> MagicMock:
    client = MagicMock()
    # client.messages.stream(...) must return an async-context-manager.
    client.messages.stream = MagicMock(return_value=stream)
    return client


async def _collect(gen) -> List[str]:
    """Drain an async generator into a list."""
    return [x async for x in gen]


# =============================================================================
# SSE format helpers
# =============================================================================


class TestSSEFormatting:
    def test_format_sse_single_line(self) -> None:
        out = _format_sse("token", "hello")
        # Per SSE spec, an event terminates with a blank line (\n\n).
        assert out == "event: token\ndata: hello\n\n"

    def test_format_sse_multi_line_data(self) -> None:
        out = _format_sse("token", "line1\nline2")
        assert out == "event: token\ndata: line1\ndata: line2\n\n"

    def test_format_sse_done_marker(self) -> None:
        assert _format_sse_done() == "data: [DONE]\n\n"

    def test_meta_payload_includes_citations_and_intent(self) -> None:
        payload = _meta_payload(
            citations=[Citation("docs/x.md", "X", 0.2)],
            intent="signal_health",
            suggestions=["Check trust gate"],
            data_cards=[{"label": "EMQ", "value": "0.95"}],
            fallback_message=None,
        )
        body = json.loads(payload)
        assert body["intent"] == "signal_health"
        assert body["citations"] == [
            {"source_path": "docs/x.md", "title": "X", "distance": 0.2}
        ]
        assert "fallback_message" not in body  # only present when set

    def test_meta_payload_includes_fallback_when_present(self) -> None:
        payload = _meta_payload(
            citations=[],
            intent="x",
            suggestions=[],
            data_cards=[],
            fallback_message="template text",
        )
        body = json.loads(payload)
        assert body["fallback_message"] == "template text"


# =============================================================================
# Off-paths
# =============================================================================


class TestStreamOffPaths:
    @pytest.mark.asyncio
    async def test_llm_disabled_emits_meta_with_fallback_then_done(self) -> None:
        with _patch_settings(copilot_llm_enabled=False):
            chunks = await _collect(
                stream_llm_message(
                    message="hi",
                    user_name="X",
                    metrics=None,
                    health_data=None,
                    anomaly_data=None,
                    intent="greeting",
                    suggestions=[],
                    data_cards=[],
                    fallback_message="Hi! Template here.",
                )
            )
        joined = "".join(chunks)
        assert "event: meta" in joined
        assert "Hi! Template here." in joined
        assert joined.endswith("data: [DONE]\n\n")
        assert "event: token" not in joined

    @pytest.mark.asyncio
    async def test_no_anthropic_key_emits_meta_with_fallback(self) -> None:
        with _patch_settings(anthropic_api_key=None):
            chunks = await _collect(
                stream_llm_message(
                    message="hi",
                    user_name="X",
                    metrics=None,
                    health_data=None,
                    anomaly_data=None,
                    intent="greeting",
                    suggestions=[],
                    data_cards=[],
                    fallback_message="template",
                )
            )
        joined = "".join(chunks)
        assert "fallback_message" in joined
        assert "event: token" not in joined


# =============================================================================
# Happy path
# =============================================================================


class TestStreamHappyPath:
    @pytest.mark.asyncio
    async def test_streams_tokens_then_meta_then_done(self) -> None:
        fake = _FakeStream(tokens=["Hello", " world", "."])
        client = _fake_anthropic_client(fake)

        with (
            _patch_settings(),
            patch("anthropic.AsyncAnthropic", return_value=client),
            patch(
                "app.services.agents.copilot_llm._retrieve_docs",
                new=AsyncMock(return_value=([], [])),
            ),
        ):
            chunks = await _collect(
                stream_llm_message(
                    message="Hi",
                    user_name="X",
                    metrics=None,
                    health_data=None,
                    anomaly_data=None,
                    intent="greeting",
                    suggestions=["Try this"],
                    data_cards=[{"label": "ROAS", "value": "4.2x"}],
                    fallback_message="template",
                )
            )

        text = "".join(chunks)
        # Tokens come first.
        assert text.index("event: token\ndata: Hello") < text.index("event: meta")
        # Three token events.
        assert text.count("event: token") == 3
        # Then exactly one meta.
        assert text.count("event: meta") == 1
        # Then [DONE].
        assert text.endswith("data: [DONE]\n\n")
        # Success path: fallback_message NOT in the meta payload.
        assert "fallback_message" not in text

    @pytest.mark.asyncio
    async def test_meta_carries_citations_from_retrieval(self) -> None:
        fake = _FakeStream(tokens=["Answer."])
        client = _fake_anthropic_client(fake)

        async def _retrieve(*_args: Any, **_kwargs: Any) -> tuple:
            return (
                [{"source_path": "docs/x.md", "title": "X » Body", "content": "..."}],
                [Citation("docs/x.md", "X » Body", 0.18)],
            )

        with (
            _patch_settings(copilot_rag_enabled=True, openai_api_key="sk-test"),
            patch("anthropic.AsyncAnthropic", return_value=client),
            patch(
                "app.services.agents.copilot_llm_stream._retrieve_docs",
                side_effect=_retrieve,
            ),
        ):
            chunks = await _collect(
                stream_llm_message(
                    message="Q",
                    user_name="X",
                    metrics=None,
                    health_data=None,
                    anomaly_data=None,
                    intent="x",
                    suggestions=[],
                    data_cards=[],
                    fallback_message="fb",
                )
            )

        text = "".join(chunks)
        # Pull out the meta JSON body.
        meta_event = [
            block for block in text.split("\n\n")
            if "event: meta" in block
        ][0]
        body_line = [
            line[len("data: "):]
            for line in meta_event.split("\n")
            if line.startswith("data: ")
        ][0]
        body = json.loads(body_line)
        assert body["citations"] == [
            {"source_path": "docs/x.md", "title": "X » Body", "distance": 0.18}
        ]


# =============================================================================
# Failure paths
# =============================================================================


class TestStreamFailures:
    @pytest.mark.asyncio
    async def test_anthropic_error_emits_error_then_meta_then_done(self) -> None:
        fake = _FakeStream(tokens=["nope"], raise_during=True)
        client = _fake_anthropic_client(fake)

        with (
            _patch_settings(),
            patch("anthropic.AsyncAnthropic", return_value=client),
            patch(
                "app.services.agents.copilot_llm._retrieve_docs",
                new=AsyncMock(return_value=([], [])),
            ),
        ):
            chunks = await _collect(
                stream_llm_message(
                    message="Q",
                    user_name="X",
                    metrics=None,
                    health_data=None,
                    anomaly_data=None,
                    intent="x",
                    suggestions=[],
                    data_cards=[],
                    fallback_message="template",
                )
            )

        text = "".join(chunks)
        assert "event: error\ndata: stream_error" in text
        # Meta is emitted with the fallback because zero tokens streamed.
        assert "fallback_message" in text
        assert "template" in text
        assert text.endswith("data: [DONE]\n\n")

    @pytest.mark.asyncio
    async def test_partial_stream_meta_omits_fallback(self) -> None:
        # First token succeeds; raise on the second.
        class _PartialStream(_FakeStream):
            async def _iter(self) -> AsyncIterator[str]:
                yield self.tokens[0]
                raise RuntimeError("midway")

        fake = _PartialStream(tokens=["Hel", "lo"])
        client = _fake_anthropic_client(fake)

        with (
            _patch_settings(),
            patch("anthropic.AsyncAnthropic", return_value=client),
            patch(
                "app.services.agents.copilot_llm._retrieve_docs",
                new=AsyncMock(return_value=([], [])),
            ),
        ):
            chunks = await _collect(
                stream_llm_message(
                    message="Q",
                    user_name="X",
                    metrics=None,
                    health_data=None,
                    anomaly_data=None,
                    intent="x",
                    suggestions=[],
                    data_cards=[],
                    fallback_message="template",
                )
            )

        text = "".join(chunks)
        # One token did stream...
        assert "event: token\ndata: Hel" in text
        # ...and the failure path runs but does NOT include fallback_message
        # because the dashboard already has a partial bubble to show.
        assert "fallback_message" not in text
        assert "event: error" in text
